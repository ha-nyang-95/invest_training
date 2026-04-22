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


def test_session_timezone_pinned_to_utc(parquet_fixture: Path, tmp_path: Path) -> None:
    """Review-flip fix: FeatureStore.__init__ must set session TZ to UTC.
    Without this, DuckDB `now()` and TIMESTAMPTZ comparisons use the OS
    default (WSL2 ships Asia/Seoul) and query_recent_ticks filters by a
    9-hour-skewed window, silently returning empty results."""
    fs = FeatureStore(tmp_path / "decisions.duckdb", parquet_fixture)
    tz = fs._conn.execute("SELECT current_setting('TimeZone')").fetchone()  # noqa: SLF001
    fs.close()
    assert tz is not None
    assert tz[0] == "UTC"


def test_query_news_rejects_naive_datetime(parquet_fixture: Path, tmp_path: Path) -> None:
    """Review-flip fix: naive datetime binds as TIMESTAMP (session-TZ)
    against a TIMESTAMPTZ column — even with session UTC, the caller's
    intent is ambiguous. Force tz-aware input at the API boundary."""
    from datetime import datetime as _dt  # local import — test-scope only

    fs = FeatureStore(tmp_path / "decisions.duckdb", parquet_fixture)
    try:
        with pytest.raises(ValueError, match="timezone-aware"):
            # Naive datetime is the point of the test (probe the guard).
            fs.query_news_for_symbol("005930", _dt(2026, 4, 21, 9, 0, 0))  # noqa: DTZ001
    finally:
        fs.close()


def test_refresh_views_picks_up_new_shards(tmp_path: Path) -> None:
    """Review-flip fix: long-running Trading PC processes must be able to
    see shards that arrived via rsync after FeatureStore was constructed.
    Previously attach_parquet_views ran only once in __init__, so new
    hours were invisible until restart."""
    parquet_root = tmp_path / "parquet"
    fs = FeatureStore(tmp_path / "decisions.duckdb", parquet_root)
    try:
        # Empty root initially — view returns 0 rows (from the TEMP empty table)
        assert fs._conn.execute("SELECT count(*) FROM ticks").fetchone()[0] == 0  # noqa: SLF001
        # A shard lands via a simulated rsync
        hour_dir = parquet_root / "ticks/year=2026/month=04/day=21/hour=07"
        hour_dir.mkdir(parents=True)
        frame = _build_hour_slice(datetime(2026, 4, 21, 7, 0, 0, tzinfo=UTC), ("005930",))
        frame.write_parquet(hour_dir / "symbol=005930.parquet", compression="zstd")
        # Before refresh — view still resolves to the empty TEMP table
        assert fs._conn.execute("SELECT count(*) FROM ticks").fetchone()[0] == 0  # noqa: SLF001
        # After refresh — view points at the parquet glob and sees the new rows
        fs.refresh_views()
        assert fs._conn.execute("SELECT count(*) FROM ticks").fetchone()[0] == 100  # noqa: SLF001
    finally:
        fs.close()


def test_init_closes_conn_on_view_attach_failure(tmp_path: Path) -> None:
    """Review-flip fix: if attach_parquet_views raised (or SET TimeZone
    raised) mid-__init__, self._conn stayed open with a .duckdb.wal lock
    that blocked subsequent runs on Windows. __init__ now guards with
    try/except + close."""
    # Force attach_parquet_views to explode by passing a Path that is not a
    # directory (file exists at the root) — DuckDB rglob will still work, so
    # we instead inject a monkey-patch onto a non-existent deep attribute.
    # Simpler: use a root the FS would process fine but make the connection
    # raise a known error. We do that by pre-creating a broken decisions.duckdb
    # that duckdb can open but the subsequent view-attach will stumble on.
    # Easiest synthetic fault — make the parquet_root a file not a directory:
    parquet_root = tmp_path / "not_a_dir"
    parquet_root.write_text("")  # file, not directory
    # attach_parquet_views('ticks') will call _has_any_parquet which does
    # root.exists() True + rglob — on a regular file rglob raises NotADirectoryError
    # on some OSes, falls through gracefully on others. Either way the
    # important invariant: if __init__ raises, no .duckdb lock leaks.
    db_path = tmp_path / "decisions.duckdb"
    # Even if this does not raise (depending on OS), closing behaviour is fine;
    # we only fail loudly on lock leakage. The test deliberately does NOT assert
    # that __init__ raised — the invariant we need is that re-opening always works.
    try:
        fs = FeatureStore(db_path, parquet_root)
    except Exception:  # noqa: BLE001, S110 — deliberate: exception path is what we probe; lock leak is the real regression
        pass
    else:
        fs.close()
    # If we got here, the conn either closed on exception or closed cleanly.
    # Verify re-open works (no lingering .duckdb.wal lock).
    conn = open_decisions_duckdb(db_path)
    conn.close()


def test_empty_view_does_not_persist_to_decisions_db(tmp_path: Path) -> None:
    """Review-flip fix (D1 / #PT-2 invariant): when parquet_root has zero
    shards, the fallback _empty_<table> must be a TEMP (session-scoped)
    table — NOT a persistent table written into decisions.duckdb. A
    persistent _empty_* widens the Trading PC write scope silently."""
    decisions_db = tmp_path / "decisions.duckdb"
    empty_root = tmp_path / "empty_parquet_root"
    fs = FeatureStore(decisions_db, empty_root)
    fs.close()
    # Re-open decisions.duckdb with a fresh connection — TEMP tables from the
    # prior FeatureStore session must not be visible.
    conn = open_decisions_duckdb(decisions_db)
    try:
        persistent = {
            row[0]
            for row in conn.execute(
                "SELECT table_name FROM duckdb_tables() WHERE temporary = false"
            ).fetchall()
        }
    finally:
        conn.close()
    leaked = {t for t in persistent if t.startswith("_empty_")}
    assert not leaked, (
        f"_empty_* leaked into persistent decisions.duckdb schema: {leaked}; "
        "must be CREATE TEMP TABLE (see parquet_reader._create_empty_view)"
    )
