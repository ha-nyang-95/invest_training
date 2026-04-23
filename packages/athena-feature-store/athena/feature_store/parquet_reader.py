"""Trading-PC-side Parquet external scan bridge.

Source: Story 1.4 AC-4 Task 4.1; architecture.md#EXT5 (DuckDB external scan).

`attach_parquet_views(conn, parquet_root)` registers three DuckDB views —
`ticks`, `quotes`, `news` — each backed by `read_parquet(...)` over the
rsync'd shard tree with `hive_partitioning=true` so year/month/day/hour/symbol
are first-class predicate columns for partition pruning.

W1 Day 1 fallback: when `{parquet_root}/{table}` has zero parquet files yet
(Logger PC setup is Story 1.7 prerequisite), we replace the view with an
empty in-memory table built from the same DDL (schemas.py), so downstream
SELECTs do not crash with a zero-glob error.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
from athena.feature_store.schemas import (
    create_news_table,
    create_quotes_table,
    create_ticks_table,
)


def _has_any_parquet(root: Path) -> bool:
    """O(1) presence check — stops on the first match. Plain `any(rglob(...))`
    still iterates every directory in a recursive glob in some Python
    versions; `next(..., None)` provides a clear short-circuit contract."""
    if not root.exists():
        return False
    return next(root.rglob("*.parquet"), None) is not None


def attach_parquet_views(conn: duckdb.DuckDBPyConnection, parquet_root: Path) -> None:
    """Attach ticks/quotes/news views over the rsync'd Parquet tree.

    Idempotent — safe to re-call after new shards arrive (see
    `FeatureStore.refresh_views`). The TOCTOU race between `_has_any_parquet`
    and DuckDB's own glob expansion (rsync may delete/add files in between)
    is handled by try/except around the view attach.
    """
    for table in ("ticks", "quotes", "news"):
        table_root = parquet_root / table
        if _has_any_parquet(table_root):
            # hive_partitioning=true reads year=/month=/day=/hour=/symbol= from the
            # directory structure and exposes them as predicate columns for DuckDB
            # to prune at scan time. Glob passed as POSIX so Windows dev paths work.
            # Single-quote escape for path literals containing `'` (legal on Linux).
            shard_glob = (table_root / "**" / "*.parquet").as_posix().replace("'", "''")
            try:
                conn.execute(
                    f"CREATE OR REPLACE VIEW {table} AS "  # noqa: S608
                    f"SELECT * FROM read_parquet('{shard_glob}', hive_partitioning=true)"
                )
            except duckdb.IOException:
                # TOCTOU: rsync deleted the last shard between the probe and
                # the CREATE VIEW. Fall through to the empty-view path so
                # downstream SELECT returns 0 rows rather than crashing.
                _create_empty_view(conn, table)
        else:
            _create_empty_view(conn, table)


def _create_empty_view(conn: duckdb.DuckDBPyConnection, table: str) -> None:
    # temporary=True makes `_empty_<table>` a TEMP (session-scoped) table,
    # so it does NOT materialise into the persistent decisions.duckdb file.
    # Without this, the view-attach step violates D1 / #PT-2 by dropping a
    # persistent `_empty_ticks` (etc.) into the Trading PC write zone.
    # DROP first so re-attach after a schema-evolution change doesn't see
    # a stale TEMP TABLE from the earlier session.
    empty_name = f"_empty_{table}"
    conn.execute(f"DROP TABLE IF EXISTS {empty_name}")  # noqa: S608
    creator = {
        "ticks": create_ticks_table,
        "quotes": create_quotes_table,
        "news": create_news_table,
    }[table]
    creator(conn, table_name=empty_name, temporary=True)
    conn.execute(
        f"CREATE OR REPLACE VIEW {table} AS SELECT * FROM {empty_name}"  # noqa: S608
    )
