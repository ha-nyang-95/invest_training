"""Story 1.4 Task 6.1 — DTO <-> DDL field-name parity regression.

Promotes the parity scenario from Task 1.5 into a dedicated regression file
so future stories that add a sixth/seventh storage table can extend the
parametrized list without touching schemas' unit tests.

Contract: every Pydantic storage DTO field must correspond to a DuckDB
column of the same name, and vice versa — no typos, no drift, no surprise
additions on one side only. The test exercises the *name set*; types are
covered by the DuckDB INSERT + Decimal roundtrip test in test_schemas.py.

Stage-2 (no marker) — runs on every pytest invocation.
"""

from __future__ import annotations

from typing import Any

import duckdb
import pytest
from athena.feature_store.schemas import (
    NewsRow,
    QuoteRow,
    TickRow,
    create_news_table,
    create_quotes_table,
    create_ticks_table,
)


@pytest.mark.parametrize(
    ("dto", "creator", "table_name"),
    [
        (TickRow, create_ticks_table, "ticks"),
        (QuoteRow, create_quotes_table, "quotes"),
        (NewsRow, create_news_table, "news"),
    ],
)
def test_dto_field_set_matches_ddl_columns(
    dto: type[TickRow | QuoteRow | NewsRow],
    creator: Any,
    table_name: str,
) -> None:
    conn = duckdb.connect(":memory:")
    creator(conn)
    pragma_rows = conn.execute(f"PRAGMA table_info('{table_name}')").fetchall()  # noqa: S608
    ddl_columns = {row[1] for row in pragma_rows}
    dto_fields = set(dto.model_fields.keys())
    missing_in_ddl = dto_fields - ddl_columns
    missing_in_dto = ddl_columns - dto_fields
    assert not missing_in_ddl, (
        f"{table_name}: DTO has fields not in DDL — {missing_in_ddl}. "
        "A DTO-only field would silently drop data at INSERT."
    )
    assert not missing_in_dto, (
        f"{table_name}: DDL has columns not in DTO — {missing_in_dto}. "
        "A DDL-only column would need a default or would break Pydantic validation."
    )
