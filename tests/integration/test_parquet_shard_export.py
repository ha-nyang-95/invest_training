"""Story 1.4 AC-2 Task 2.4 — hourly Parquet shard export integration tests.

Seven scenarios: happy path, idempotent fail, check ok, check drift, empty
hour, NULL-symbol news, CLI smoke.
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import duckdb
import polars as pl
import pytest
from athena.feature_store.duckdb_client import open_logger_duckdb
from athena.feature_store.parquet_shard import (
    ShardDriftError,
    ShardOverwriteError,
    export_hour_shard,
)
from athena.feature_store.schemas import (
    create_news_table,
    create_quotes_table,
    create_ticks_table,
)

pytestmark = pytest.mark.integration

HOUR = datetime(2026, 4, 21, 9, 0, 0, tzinfo=UTC)
SYMBOLS = ("005930", "000660", "035420")
MV = "feature_store.v0.1.0"
SHA = "a1b2c3d4e5f6"


def _build_ticks_dataframe() -> pl.DataFrame:
    """Deterministic synthetic ticks — 3 symbols × 60 minutes × 100 ticks/minute.

    Each tick spaced 600ms apart within its minute (so all 100 fit in <60s).
    Prices = 70500 + symbol_offset + minute*0.5, bid = base - level, ask = base + level.
    """
    rows: list[dict[str, object]] = []
    for sym in SYMBOLS:
        sym_offset = int(sym[-3:])
        for minute in range(60):
            base = Decimal("70500") + Decimal(sym_offset) + Decimal(minute) / 2
            for tick in range(100):
                ts = HOUR + timedelta(minutes=minute, microseconds=tick * 600_000)
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
                row["seq_no"] = sym_offset * 100_000 + minute * 100 + tick
                rows.append(row)
    return pl.DataFrame(rows)


@pytest.fixture
def logger_db_with_ticks(tmp_path: Path) -> Iterator[tuple[duckdb.DuckDBPyConnection, Path]]:
    db_path = tmp_path / "features_logger.duckdb"
    conn = open_logger_duckdb(db_path)
    create_ticks_table(conn)
    synth = _build_ticks_dataframe()
    conn.register("synth_ticks", synth)
    conn.execute("INSERT INTO ticks SELECT * FROM synth_ticks")
    conn.unregister("synth_ticks")
    yield conn, tmp_path / "parquet"
    conn.close()


def test_happy_path_writes_one_file_per_symbol(
    logger_db_with_ticks: tuple[duckdb.DuckDBPyConnection, Path],
) -> None:
    conn, out_root = logger_db_with_ticks
    result = export_hour_shard(conn, "ticks", HOUR, out_root)
    assert result.files_written == 3
    assert result.files_matched == 0
    assert set(result.symbols) == set(SYMBOLS)
    assert result.bytes_written > 0
    for sym in SYMBOLS:
        path = out_root / "ticks/year=2026/month=04/day=21/hour=09" / f"symbol={sym}.parquet"
        assert path.exists()
        df = pl.read_parquet(path)
        assert df.height == 60 * 100
        assert set(df.columns) >= {"timestamp", "symbol", "bid_px_1", "seq_no", "user_id"}


def test_idempotent_fail_raises_overwrite(
    logger_db_with_ticks: tuple[duckdb.DuckDBPyConnection, Path],
) -> None:
    conn, out_root = logger_db_with_ticks
    export_hour_shard(conn, "ticks", HOUR, out_root)
    with pytest.raises(ShardOverwriteError) as excinfo:
        export_hour_shard(conn, "ticks", HOUR, out_root)
    assert excinfo.value.error_code == "SHARD_ALREADY_EXISTS"
    assert "path" in excinfo.value.context
    assert "existing_sha256" in excinfo.value.context


def test_idempotent_check_ok(
    logger_db_with_ticks: tuple[duckdb.DuckDBPyConnection, Path],
) -> None:
    conn, out_root = logger_db_with_ticks
    export_hour_shard(conn, "ticks", HOUR, out_root)
    result = export_hour_shard(conn, "ticks", HOUR, out_root, mode="check")
    assert result.files_written == 0
    assert result.files_matched == 3


def test_idempotent_check_drift(
    logger_db_with_ticks: tuple[duckdb.DuckDBPyConnection, Path],
) -> None:
    conn, out_root = logger_db_with_ticks
    export_hour_shard(conn, "ticks", HOUR, out_root)
    # Mutate one row in the source DuckDB so the fresh query disagrees with the shard
    conn.execute(
        'UPDATE ticks SET last_px = last_px + 1 WHERE symbol = ? AND "timestamp" = ?',
        [SYMBOLS[0], HOUR],
    )
    with pytest.raises(ShardDriftError) as excinfo:
        export_hour_shard(conn, "ticks", HOUR, out_root, mode="check")
    assert excinfo.value.error_code == "SHARD_DRIFT"
    assert SYMBOLS[0] in excinfo.value.context["path"]


def test_empty_hour_writes_nothing(tmp_path: Path) -> None:
    db_path = tmp_path / "empty.duckdb"
    conn = open_logger_duckdb(db_path)
    create_ticks_table(conn)
    # no INSERTs
    result = export_hour_shard(conn, "ticks", HOUR, tmp_path / "parquet")
    conn.close()
    assert result.files_written == 0
    assert result.files_matched == 0
    assert result.symbols == ()
    assert result.bytes_written == 0
    assert not (tmp_path / "parquet").exists()


def test_null_symbol_news_goes_to_sentinel_partition(tmp_path: Path) -> None:
    db_path = tmp_path / "news.duckdb"
    conn = open_logger_duckdb(db_path)
    create_news_table(conn)
    # One row with symbol=NULL, one with symbol='005930'
    ts2 = HOUR + timedelta(minutes=5)
    rows = [
        (HOUR, MV, SHA, 1, HOUR, "DART", None, "h1", "b1", "https://x/1", "0" * 64),
        (ts2, MV, SHA, 1, HOUR, "naver", "005930", "h2", "b2", "https://x/2", "1" * 64),
    ]
    placeholders = ",".join("?" * 11)
    for row in rows:
        conn.execute(
            f"INSERT INTO news VALUES ({placeholders})",  # noqa: S608
            list(row),
        )

    result = export_hour_shard(conn, "news", HOUR, tmp_path / "parquet")
    conn.close()
    assert result.files_written == 2
    part_dir = tmp_path / "parquet/news/year=2026/month=04/day=21/hour=09"
    assert (part_dir / "symbol=__NULL__.parquet").exists()
    assert (part_dir / "symbol=005930.parquet").exists()


def test_naive_hour_rejected(
    logger_db_with_ticks: tuple[duckdb.DuckDBPyConnection, Path],
) -> None:
    """Review-flip fix: naive datetime binds as TIMESTAMP (session-TZ) against
    a TIMESTAMPTZ column, so a KST-host call with naive `hour_utc_start`
    filters the wrong 9h window and silently returns zero rows — data loss
    invisible until downstream queries."""
    conn, out_root = logger_db_with_ticks
    # Naive datetime is the point of the test (probe the guard).
    naive_hour = datetime(2026, 4, 21, 9, 0, 0)  # noqa: DTZ001
    with pytest.raises(ValueError, match="timezone-aware"):
        export_hour_shard(conn, "ticks", naive_hour, out_root)


def test_symbol_validation_rejects_path_hostile_and_null_sentinel(tmp_path: Path) -> None:
    """Review-flip fix: a symbol containing `/`, `\\`, `:`, or the literal
    `__NULL__` sentinel used to land as a filesystem path segment —
    producing path traversal or collision with the NULL partition. Validate
    at export time before touching the filesystem."""
    from athena.feature_store.parquet_shard import _validate_symbol

    for bad in ("__NULL__", "a/b", "a\\b", "a:b", "a b", "x" * 40, ""):
        with pytest.raises(ValueError):
            _validate_symbol(bad)
    # Legal shapes pass
    for ok in ("005930", "AAPL", "XYZ-1", "x_y"):
        _validate_symbol(ok)


def test_write_leaves_no_tmp_file(
    logger_db_with_ticks: tuple[duckdb.DuckDBPyConnection, Path],
) -> None:
    """Review-flip fix: atomic write path uses `<file>.tmp.<pid>` then
    `replace()`. On a successful write there must be no `.tmp.*` residue
    in the partition dir; on a crash the except-branch unlinks the tmp.
    This test pins the happy-path cleanliness."""
    conn, out_root = logger_db_with_ticks
    export_hour_shard(conn, "ticks", HOUR, out_root)
    part_dir = out_root / "ticks/year=2026/month=04/day=21/hour=09"
    tmp_leftovers = list(part_dir.glob("*.tmp.*"))
    assert not tmp_leftovers, f"atomic rename left residue: {tmp_leftovers}"


def _run_cli(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "scripts/export_parquet_shard.py", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=cwd,
        check=False,
    )


def test_cli_rejects_bad_hour_spec(tmp_path: Path) -> None:
    """Review-flip fix: `now--5`, `now-0`, `YYYY-MM-DD HH` (space, no T), and
    pure garbage all used to either silently produce a future hour, a
    partial hour, or a bare traceback. Now all map to a SHARD_BAD_HOUR
    JSON contract with exit 2."""
    db = tmp_path / "empty.duckdb"
    conn = open_logger_duckdb(db)
    create_ticks_table(conn)
    conn.close()
    repo_root = Path(__file__).resolve().parents[2]
    for bad in ("now-0", "now--5", "now-abc", "2026-04-21 09", "notadate"):
        proc = _run_cli(
            [
                "--duckdb",
                str(db),
                "--out-root",
                str(tmp_path / "parquet"),
                "--hour",
                bad,
            ],
            cwd=repo_root,
        )
        assert proc.returncode == 2, f"{bad!r} should SHARD_BAD_HOUR; got {proc.returncode}"
        payload = json.loads(proc.stderr.strip().splitlines()[-1])
        assert payload["error_code"] == "SHARD_BAD_HOUR"


def test_cli_rejects_invalid_tables(
    logger_db_with_ticks: tuple[duckdb.DuckDBPyConnection, Path],
) -> None:
    """Review-flip fix: `--tables invalid,ticks` used to export ticks then
    crash on `invalid`, leaving a partial-state ticks shard that blocked
    the next retry with SHARD_ALREADY_EXISTS. All table names are now
    validated up-front (before DuckDB is opened)."""
    conn, out_root = logger_db_with_ticks
    db_path = Path(conn.execute("PRAGMA database_list").fetchone()[2])  # type: ignore[index]
    conn.close()
    repo_root = Path(__file__).resolve().parents[2]
    proc = _run_cli(
        [
            "--duckdb",
            str(db_path),
            "--out-root",
            str(out_root),
            "--hour",
            "2026-04-21T09",
            "--tables",
            "invalid,ticks",
        ],
        cwd=repo_root,
    )
    assert proc.returncode == 2
    payload = json.loads(proc.stderr.strip().splitlines()[-1])
    assert payload["error_code"] == "SHARD_BAD_TABLES"
    assert payload["invalid"] == ["invalid"]
    # And crucially no partial write: ticks shard should NOT exist
    assert not list(
        (out_root / "ticks").rglob("*.parquet") if (out_root / "ticks").exists() else []
    )


def test_cli_smoke_happy_path(
    logger_db_with_ticks: tuple[duckdb.DuckDBPyConnection, Path],
    tmp_path: Path,
) -> None:
    conn, out_root = logger_db_with_ticks
    # Also need quotes and news tables for the CLI (default --tables is ticks,quotes,news)
    # to not fail on missing tables. Since we only INSERT into ticks, quotes/news emit 0 files.
    create_quotes_table(conn)
    create_news_table(conn)
    db_path = Path(conn.execute("PRAGMA database_list").fetchone()[2])  # type: ignore[index]
    conn.close()  # release lock before subprocess opens RW

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/export_parquet_shard.py",
            "--duckdb",
            str(db_path),
            "--out-root",
            str(out_root),
            "--hour",
            "2026-04-21T09",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=Path(__file__).resolve().parents[2],
        check=False,
    )
    assert proc.returncode == 0, f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
    payload = json.loads(proc.stdout.strip())
    assert payload["hour"].startswith("2026-04-21T09")
    assert payload["tables"]["ticks"] == 3
    assert payload["tables"]["quotes"] == 0
    assert payload["tables"]["news"] == 0
    assert payload["bytes"] > 0
    # Review-flip fix: prove the subprocess left no lock behind. If the CLI's
    # `with open_logger_duckdb(...) as conn:` finally/__exit__ had leaked
    # the connection, re-opening RW here would fail on Windows with
    # IOException; on Linux DuckDB's fcntl lock still leaks an advisory
    # file, but the reopen succeeds. Either way, catching a failed reopen
    # pins-down resource cleanup behaviour.
    db_path = Path(proc.args[4])  # --duckdb argument we passed  # type: ignore[index]
    reopen = open_logger_duckdb(db_path)
    reopen.close()
