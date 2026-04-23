"""Trading PC feature access + decisions.duckdb write boundary.

Source: Story 1.4 AC-4 Task 4.2; architecture.md#D1 (read via Parquet external
scan, write only to decisions.duckdb), #PT-2 (5 writable tables on Trading PC).

FeatureStore is the one entry point: reads ticks/quotes/news via Parquet
views attached to a decisions.duckdb RW connection, writes to the 5 allowed
tables (modules_output, decisions, orders, anti_ego_events, labels_f1). The
write stubs raise NotImplementedError pointing at the story that populates
each table's DDL + INSERT.

Architectural invariant (#3): direct write to ticks/quotes/news is forbidden
here — tests/regression/test_trading_pc_write_scope.py greps for any
SQL INSERT targeting the Logger tables in this module and fails if found,
and also asserts that exactly 5 `insert_*` methods exist (adding a sixth
or removing one both trip the test).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import polars as pl
from athena.feature_store.duckdb_client import open_decisions_duckdb
from athena.feature_store.parquet_reader import attach_parquet_views

_MAX_LOOKBACK_MIN = 24 * 60


class FeatureStore:
    """Trading PC entry point — reads via Parquet external scan, writes only
    to decisions.duckdb's 5 RW tables."""

    def __init__(self, decisions_db: Path, parquet_root: Path) -> None:
        self._conn = open_decisions_duckdb(decisions_db)
        self._parquet_root = parquet_root
        # If the TZ-pin or view-attach raises, close the connection before
        # propagating — otherwise Python's GC is the only thing that releases
        # the .duckdb.wal lock, which on Windows leaves a stale lock file
        # blocking the next test/prod run.
        try:
            # Pin the session TZ so `now()` and TIMESTAMPTZ comparisons use UTC
            # regardless of the host's tzdata default (WSL2 ships Asia/Seoul).
            self._conn.execute("SET TimeZone='UTC'")
            attach_parquet_views(self._conn, parquet_root)
        except BaseException:
            self._conn.close()
            raise

    def refresh_views(self) -> None:
        """Re-attach Parquet views over the current shard tree state.

        Long-running Trading PC processes (orchestrator, backtest runner)
        should call this after each rsync tick so newly-arrived hourly
        shards become queryable without a process restart. `attach_parquet_views`
        is idempotent — re-calling on unchanged state is a no-op beyond a
        DuckDB `CREATE OR REPLACE VIEW` refresh.
        """
        attach_parquet_views(self._conn, self._parquet_root)

    # ─── Read path ──────────────────────────────────────────────────────────

    def query_recent_ticks(self, symbol: str, lookback_minutes: int) -> pl.DataFrame:
        if not 0 < lookback_minutes <= _MAX_LOOKBACK_MIN:
            raise ValueError(
                f"lookback_minutes must be in (0, {_MAX_LOOKBACK_MIN}]; got {lookback_minutes}"
            )
        # to_minutes(?) produces an INTERVAL from the bound int parameter.
        return self._conn.execute(
            'SELECT * FROM ticks WHERE symbol = ? AND "timestamp" > now() - to_minutes(?) '
            'ORDER BY "timestamp"',
            [symbol, lookback_minutes],
        ).pl()

    def query_news_for_symbol(self, symbol: str, since_utc: datetime) -> pl.DataFrame:
        # Reject naive datetimes: DuckDB binds them as plain TIMESTAMP, which
        # gets compared to TIMESTAMPTZ under the session TZ. Even though we
        # pin UTC in __init__, accepting naive input leaves the caller guessing
        # whether their local-time value was silently reinterpreted as UTC.
        if since_utc.tzinfo is None or since_utc.tzinfo.utcoffset(since_utc) is None:
            raise ValueError("since_utc must be timezone-aware (UTC); naive datetime forbidden")
        return self._conn.execute(
            "SELECT * FROM news WHERE symbol = ? AND published_at_utc >= ? "
            "ORDER BY published_at_utc",
            [symbol, since_utc],
        ).pl()

    # ─── Write path — Trading PC's 5-table scope (DDL lands in later stories) ──

    def insert_module_output(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError(
            "Story 1.5 (Pre-Trade Ledger) populates modules_output schema + INSERT"
        )

    def insert_decision(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError(
            "Story 1.5 (Pre-Trade Ledger) populates decisions schema + INSERT"
        )

    def insert_order(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError(
            "Story 4.3 (OrderIntent consumer) populates orders schema + INSERT"
        )

    def insert_anti_ego_event(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError("Story 3.1 (anti_ego_events table) populates schema + INSERT")

    def insert_label_f1(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError(
            "Story 3.3 (F1 labeling pipeline) populates labels_f1 schema + INSERT"
        )

    def close(self) -> None:
        self._conn.close()
