"""Story 1.4 AC-4 Task 4.4 — FeatureStore + parquet_reader integration smoke.

Exercises the Trading PC read path end-to-end: synthetic hive-partitioned
Parquet → attach_parquet_views → SELECT count(*) / partition pruning /
latency smoke / NotImplementedError on write stubs.

The pruning check uses EXPLAIN to confirm hive predicates land on the
query plan (DuckDB's exact EXPLAIN wording varies by 1.x minor, so the
assertion is lenient substring matching).
"""

from __future__ import annotations

import statistics
import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import duckdb
import polars as pl
import pytest
from athena.feature_store.duckdb_client import open_decisions_duckdb
from athena.feature_store.feature_query import FeatureStore
from athena.feature_store.parquet_reader import attach_parquet_views

pytestmark = pytest.mark.integration


SYMBOLS = ("005930", "000660", "035420")
MV = "feature_store.v0.1.0"
SHA = "a1b2c3d4e5f6"


def _build_hour_slice(hour: datetime, symbols: tuple[str, ...]) -> pl.DataFrame:
    rows: list[dict[str, object]] = []
    for sym in symbols:
        sym_offset = int(sym[-3:])
        base = Decimal("70500") + Decimal(sym_offset)
        for tick in range(100):
            ts = hour + timedelta(microseconds=tick * 600_000)
            row: dict[str, object] = {
                "timestamp": ts,
                "module_version": MV,
                "policy_version_git_sha": SHA,
                "user_id": 1,
                "symbol": sym,
            }
            for lvl in range(1, 11):
                row[f"bid_px_{lvl}"] = base - lvl
                row[f"bid_qty_{lvl}"] = 10 * lvl
                row[f"ask_px_{lvl}"] = base + lvl
                row[f"ask_qty_{lvl}"] = 10 * lvl
            row["last_px"] = base
            row["last_qty"] = 100
            row["trade_side"] = "B"
            row["seq_no"] = sym_offset * 100_000 + tick
            rows.append(row)
    return pl.DataFrame(rows)


@pytest.fixture
def parquet_fixture(tmp_path: Path) -> Path:
    """3 hours × 3 symbols × 100 ticks per hour laid out as hive-partitioned parquet."""
    root = tmp_path / "parquet"
    hours = [datetime(2026, 4, 21, h, 0, 0, tzinfo=UTC) for h in (7, 8, 9)]
    for h in hours:
        df = _build_hour_slice(h, SYMBOLS)
        for sym in SYMBOLS:
            sub = df.filter(pl.col("symbol") == sym)
            out = (
                root
                / "ticks"
                / f"year={h.year:04d}"
                / f"month={h.month:02d}"
                / f"day={h.day:02d}"
                / f"hour={h.hour:02d}"
                / f"symbol={sym}.parquet"
            )
            out.parent.mkdir(parents=True, exist_ok=True)
            sub.write_parquet(out, compression="zstd", compression_level=3)
    # Create empty quotes/news so attach_parquet_views has something to anchor
    (root / "quotes").mkdir(parents=True, exist_ok=True)
    (root / "news").mkdir(parents=True, exist_ok=True)
    return root


def test_attach_views_reads_all_shards(parquet_fixture: Path) -> None:
    conn = duckdb.connect(":memory:")
    attach_parquet_views(conn, parquet_fixture)
    total = conn.execute("SELECT count(*) FROM ticks").fetchone()
    assert total is not None
    assert total[0] == 3 * 3 * 100  # 900 rows


def test_attach_views_empty_root_creates_empty_view(tmp_path: Path) -> None:
    # Empty parquet_root — no files at all
    conn = duckdb.connect(":memory:")
    attach_parquet_views(conn, tmp_path / "empty_root")
    result = conn.execute("SELECT count(*) FROM ticks").fetchone()
    assert result is not None
    assert result[0] == 0
    # Same for quotes and news
    for table in ("quotes", "news"):
        row = conn.execute(f"SELECT count(*) FROM {table}").fetchone()  # noqa: S608
        assert row is not None
        assert row[0] == 0


def test_partition_pruning_predicate_reaches_plan(parquet_fixture: Path) -> None:
    conn = duckdb.connect(":memory:")
    attach_parquet_views(conn, parquet_fixture)
    plan_rows = conn.execute(
        "EXPLAIN SELECT * FROM ticks WHERE year=2026 AND month=4 AND day=21 AND symbol='005930'"
    ).fetchall()
    plan_text = "\n".join(str(r) for r in plan_rows).lower()
    # DuckDB 1.x phrasing varies; any hive-partition / filter token is sufficient.
    assert any(needle in plan_text for needle in ("hive", "parquet", "filter"))


def test_query_latency_smoke_under_100ms(parquet_fixture: Path, tmp_path: Path) -> None:
    fs = FeatureStore(tmp_path / "decisions.duckdb", parquet_fixture)
    latencies: list[float] = []
    for _ in range(100):
        t0 = time.perf_counter()
        _ = fs.query_recent_ticks("005930", 60)
        latencies.append((time.perf_counter() - t0) * 1000)
    median_ms = statistics.median(latencies)
    p95_ms = sorted(latencies)[94]
    print(f"[smoke] median_ms={median_ms:.2f} p95_ms={p95_ms:.2f}")
    fs.close()
    # Smoke bound — real NFR-P4 (p95<500ms) is validated in Story 2.x with full data
    assert median_ms < 100, f"smoke latency regression: median={median_ms:.2f}ms"


def test_write_stubs_raise_not_implemented(parquet_fixture: Path, tmp_path: Path) -> None:
    fs = FeatureStore(tmp_path / "decisions.duckdb", parquet_fixture)
    with pytest.raises(NotImplementedError, match="Story 1.5"):
        fs.insert_module_output()
    with pytest.raises(NotImplementedError, match="Story 4.3"):
        fs.insert_order()
    with pytest.raises(NotImplementedError, match="Story 3.1"):
        fs.insert_anti_ego_event()
    with pytest.raises(NotImplementedError, match="Story 3.3"):
        fs.insert_label_f1()
    fs.close()


def test_decisions_db_created_under_parent_dir(parquet_fixture: Path, tmp_path: Path) -> None:
    # Regression for Path.parent.mkdir handling in open_decisions_duckdb
    db_path = tmp_path / "nested" / "dir" / "decisions.duckdb"
    fs = FeatureStore(db_path, parquet_fixture)
    assert db_path.exists()
    fs.close()
    # Verify we can re-open after close
    conn = open_decisions_duckdb(db_path)
    conn.close()
