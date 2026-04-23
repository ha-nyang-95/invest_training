"""Python binding for `pre_trade_ledger` DDL (see schema.sql).

Source-of-truth: Story 1.5 AC-1 Task 1.4.

`SCHEMA_SQL` is read at import time from the sibling `schema.sql` so the DDL
text is a single file — Story 6.1 's full writer re-parses the same text to
verify the on-disk schema matches the shipped spec.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

SCHEMA_SQL: str = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")


def create_pre_trade_ledger(conn: duckdb.DuckDBPyConnection) -> None:
    """Idempotent — safe to run on every LedgerClient init.

    All statements use IF NOT EXISTS / OR REPLACE so re-running on a
    connection that already has the table leaves it untouched.
    """
    conn.execute(SCHEMA_SQL)


__all__ = ["SCHEMA_SQL", "create_pre_trade_ledger"]
