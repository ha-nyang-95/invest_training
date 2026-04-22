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


def attach_parquet_views(conn: duckdb.DuckDBPyConnection, parquet_root: Path) -> None:
    for table in ("ticks", "quotes", "news"):
        table_root = parquet_root / table
        has_shards = table_root.exists() and any(table_root.rglob("*.parquet"))
        if has_shards:
            # hive_partitioning=true reads year=/month=/day=/hour=/symbol= from the
            # directory structure and exposes them as predicate columns for DuckDB
            # to prune at scan time. Glob passed as POSIX so Windows dev paths work.
            shard_glob = (table_root / "**" / "*.parquet").as_posix()
            conn.execute(
                f"CREATE OR REPLACE VIEW {table} AS "  # noqa: S608
                f"SELECT * FROM read_parquet('{shard_glob}', hive_partitioning=true)"
            )
        else:
            _create_empty_view(conn, table)


def _create_empty_view(conn: duckdb.DuckDBPyConnection, table: str) -> None:
    empty_name = f"_empty_{table}"
    creator = {
        "ticks": create_ticks_table,
        "quotes": create_quotes_table,
        "news": create_news_table,
    }[table]
    creator(conn, table_name=empty_name)
    conn.execute(
        f"CREATE OR REPLACE VIEW {table} AS SELECT * FROM {empty_name}"  # noqa: S608
    )
