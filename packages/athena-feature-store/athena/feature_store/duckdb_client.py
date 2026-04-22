"""DuckDB connection openers with explicit read-mode + owner-PC intent.

Source: Story 1.4 AC-1 Task 1.3; architecture.md#D1 (single-writer per DB).

Three opener functions encode the cross-PC ownership boundary:
- `open_logger_duckdb` — Logger PC only; RW for ticks/quotes/news.
- `open_decisions_duckdb` — Trading PC only; RW for the 5 decisions tables.
- `open_features_logger_readonly` — defensive RO opener with 0 call sites in
  V1.0. Trading PC consumes features via Parquet external scan (see
  parquet_reader.py), not by opening features_logger.duckdb directly. This
  exists to fail loudly if a future story violates D1.
"""

from __future__ import annotations

from pathlib import Path

import duckdb


def open_logger_duckdb(path: Path) -> duckdb.DuckDBPyConnection:
    """Open features_logger.duckdb in RW mode (Logger PC only).

    Use as a context manager (`with open_logger_duckdb(...) as conn:`) or
    call `.close()` explicitly. DuckDB 1.x holds a .wal lock for the
    duration of an open connection; on Windows an un-closed connection
    leaves a stale lock that blocks the next open. The CLI wrapper
    (`scripts/export_parquet_shard.py`) uses the context-manager form.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path), read_only=False)


def open_decisions_duckdb(path: Path) -> duckdb.DuckDBPyConnection:
    """Open decisions.duckdb in RW mode (Trading PC only).

    Use as a context manager or call `.close()` explicitly (see
    `open_logger_duckdb` docstring for the lock-leak rationale).
    `FeatureStore.__init__` guards its own attach path with try/except
    + self._conn.close() for the same reason.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path), read_only=False)


def open_features_logger_readonly(path: Path) -> duckdb.DuckDBPyConnection:
    """Defensive RO opener. V1.0 call sites: 0 by design.

    Provided so that a future story attempting to open features_logger.duckdb
    from Trading PC (instead of going through Parquet external scan) fails
    review on the presence of a new caller of this function.
    """
    return duckdb.connect(str(path), read_only=True)
