"""DuckDB schemas + Pydantic DTO single source for features_logger.duckdb.

Source: Story 1.4 AC-1; architecture.md#D1 (cross-PC substrate), #D4 (Pydantic
single source), #Format-Patterns (DECIMAL(18,4) prices, UTC-aware TIMESTAMPTZ),
#Naming-Patterns (idx_<table>_<cols>).

Every storage DTO inherits BaseDTO (3-field contract: timestamp /
module_version / policy_version_git_sha). The DDL includes the same 3 columns
so every row on disk is self-describing — which logger version and git SHA
produced the row is recorded inline for forensic replay (NFR-A2). The
column-name parity between DTO fields and PRAGMA table_info output is
enforced by tests/regression/test_dto_ddl_parity.py.

Ownership boundary: Logger PC is the sole writer for all three tables. Trading
PC consumes via Parquet external scan (see parquet_reader.py) and never opens
features_logger.duckdb directly.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, Literal

import duckdb
from athena.core.dto import BaseDTO
from pydantic import Field, field_validator

_IDENT_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def _validate_ident(name: str) -> None:
    if not _IDENT_PATTERN.match(name):
        raise ValueError(f"Invalid SQL identifier: {name!r}; expected [a-zA-Z_][a-zA-Z0-9_]*")


# ─── DTOs — single source of truth for column names & Python-side types ───────


class TickRow(BaseDTO):
    """Single L2 book snapshot (10 depth levels) + last trade + KIS seq_no.

    Inherits BaseDTO: timestamp (UTC-aware), module_version, policy_version_git_sha.
    """

    user_id: Annotated[int, Field(default=1, ge=0)] = 1
    symbol: Annotated[str, Field(min_length=1)]
    bid_px_1: Decimal
    bid_px_2: Decimal
    bid_px_3: Decimal
    bid_px_4: Decimal
    bid_px_5: Decimal
    bid_px_6: Decimal
    bid_px_7: Decimal
    bid_px_8: Decimal
    bid_px_9: Decimal
    bid_px_10: Decimal
    bid_qty_1: int
    bid_qty_2: int
    bid_qty_3: int
    bid_qty_4: int
    bid_qty_5: int
    bid_qty_6: int
    bid_qty_7: int
    bid_qty_8: int
    bid_qty_9: int
    bid_qty_10: int
    ask_px_1: Decimal
    ask_px_2: Decimal
    ask_px_3: Decimal
    ask_px_4: Decimal
    ask_px_5: Decimal
    ask_px_6: Decimal
    ask_px_7: Decimal
    ask_px_8: Decimal
    ask_px_9: Decimal
    ask_px_10: Decimal
    ask_qty_1: int
    ask_qty_2: int
    ask_qty_3: int
    ask_qty_4: int
    ask_qty_5: int
    ask_qty_6: int
    ask_qty_7: int
    ask_qty_8: int
    ask_qty_9: int
    ask_qty_10: int
    last_px: Decimal
    last_qty: int
    trade_side: Literal["B", "S", "_"]
    seq_no: int


class QuoteRow(BaseDTO):
    """OHLCV bar (1m/1d) with VI (volatility interruption) flag."""

    user_id: Annotated[int, Field(default=1, ge=0)] = 1
    symbol: Annotated[str, Field(min_length=1)]
    interval: Literal["1m", "1d"]
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    vi_active: bool


class NewsRow(BaseDTO):
    """DART / news row. `symbol` is the only NULL-allowed storage column —
    domain exception for disclosures unaffiliated with any ticker."""

    user_id: Annotated[int, Field(default=1, ge=0)] = 1
    published_at_utc: datetime
    source: Literal["DART", "naver", "daum", "yna", "mk", "hankyung"]
    symbol: str | None = None
    headline: Annotated[str, Field(min_length=1)]
    body_text: str
    url: Annotated[str, Field(min_length=1)]
    dedup_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]

    @field_validator("published_at_utc")
    @classmethod
    def _published_at_utc_must_be_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            raise ValueError(
                "published_at_utc must be timezone-aware (UTC); naive datetime forbidden"
            )
        return value.astimezone(UTC)


# ─── DDL functions — 1:1 with DTO fields (parity test enforces exact match) ──


_TICKS_COLUMNS = """
    "timestamp" TIMESTAMPTZ NOT NULL,
    module_version VARCHAR(64) NOT NULL,
    policy_version_git_sha VARCHAR(48) NOT NULL,
    user_id INTEGER NOT NULL DEFAULT 1,
    symbol VARCHAR NOT NULL,
    bid_px_1 DECIMAL(18,4) NOT NULL,
    bid_px_2 DECIMAL(18,4) NOT NULL,
    bid_px_3 DECIMAL(18,4) NOT NULL,
    bid_px_4 DECIMAL(18,4) NOT NULL,
    bid_px_5 DECIMAL(18,4) NOT NULL,
    bid_px_6 DECIMAL(18,4) NOT NULL,
    bid_px_7 DECIMAL(18,4) NOT NULL,
    bid_px_8 DECIMAL(18,4) NOT NULL,
    bid_px_9 DECIMAL(18,4) NOT NULL,
    bid_px_10 DECIMAL(18,4) NOT NULL,
    bid_qty_1 BIGINT NOT NULL,
    bid_qty_2 BIGINT NOT NULL,
    bid_qty_3 BIGINT NOT NULL,
    bid_qty_4 BIGINT NOT NULL,
    bid_qty_5 BIGINT NOT NULL,
    bid_qty_6 BIGINT NOT NULL,
    bid_qty_7 BIGINT NOT NULL,
    bid_qty_8 BIGINT NOT NULL,
    bid_qty_9 BIGINT NOT NULL,
    bid_qty_10 BIGINT NOT NULL,
    ask_px_1 DECIMAL(18,4) NOT NULL,
    ask_px_2 DECIMAL(18,4) NOT NULL,
    ask_px_3 DECIMAL(18,4) NOT NULL,
    ask_px_4 DECIMAL(18,4) NOT NULL,
    ask_px_5 DECIMAL(18,4) NOT NULL,
    ask_px_6 DECIMAL(18,4) NOT NULL,
    ask_px_7 DECIMAL(18,4) NOT NULL,
    ask_px_8 DECIMAL(18,4) NOT NULL,
    ask_px_9 DECIMAL(18,4) NOT NULL,
    ask_px_10 DECIMAL(18,4) NOT NULL,
    ask_qty_1 BIGINT NOT NULL,
    ask_qty_2 BIGINT NOT NULL,
    ask_qty_3 BIGINT NOT NULL,
    ask_qty_4 BIGINT NOT NULL,
    ask_qty_5 BIGINT NOT NULL,
    ask_qty_6 BIGINT NOT NULL,
    ask_qty_7 BIGINT NOT NULL,
    ask_qty_8 BIGINT NOT NULL,
    ask_qty_9 BIGINT NOT NULL,
    ask_qty_10 BIGINT NOT NULL,
    last_px DECIMAL(18,4) NOT NULL,
    last_qty BIGINT NOT NULL,
    trade_side VARCHAR(1) NOT NULL,
    seq_no BIGINT NOT NULL
""".strip()

_QUOTES_COLUMNS = """
    "timestamp" TIMESTAMPTZ NOT NULL,
    module_version VARCHAR(64) NOT NULL,
    policy_version_git_sha VARCHAR(48) NOT NULL,
    user_id INTEGER NOT NULL DEFAULT 1,
    symbol VARCHAR NOT NULL,
    "interval" VARCHAR(3) NOT NULL,
    "open" DECIMAL(18,4) NOT NULL,
    high DECIMAL(18,4) NOT NULL,
    low DECIMAL(18,4) NOT NULL,
    "close" DECIMAL(18,4) NOT NULL,
    volume BIGINT NOT NULL,
    vi_active BOOLEAN NOT NULL
""".strip()

_NEWS_COLUMNS = """
    "timestamp" TIMESTAMPTZ NOT NULL,
    module_version VARCHAR(64) NOT NULL,
    policy_version_git_sha VARCHAR(48) NOT NULL,
    user_id INTEGER NOT NULL DEFAULT 1,
    published_at_utc TIMESTAMPTZ NOT NULL,
    source VARCHAR NOT NULL,
    symbol VARCHAR,
    headline VARCHAR NOT NULL,
    body_text VARCHAR NOT NULL,
    url VARCHAR NOT NULL,
    dedup_hash VARCHAR(64) NOT NULL
""".strip()


# `temporary=True` creates a session-scoped TEMP TABLE that dies with the
# connection and is NOT persisted to the underlying .duckdb file. This is
# load-bearing for parquet_reader._create_empty_view: it must not materialise
# `_empty_<table>` rows into decisions.duckdb (D1 / #PT-2: Trading PC writes
# only the 5 allowed tables). Indexes are skipped for temporary tables — the
# empty fallback has zero rows so no scan benefit.
def _create_kw(temporary: bool) -> str:
    return "CREATE TEMP TABLE" if temporary else "CREATE TABLE"


def create_ticks_table(
    conn: duckdb.DuckDBPyConnection, table_name: str = "ticks", *, temporary: bool = False
) -> None:
    _validate_ident(table_name)
    conn.execute(
        f"{_create_kw(temporary)} IF NOT EXISTS {table_name} ({_TICKS_COLUMNS})"  # noqa: S608
    )
    if not temporary:
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_{table_name}_symbol_ts "  # noqa: S608
            f'ON {table_name}(symbol, "timestamp")'
        )


def create_quotes_table(
    conn: duckdb.DuckDBPyConnection, table_name: str = "quotes", *, temporary: bool = False
) -> None:
    _validate_ident(table_name)
    conn.execute(
        f"{_create_kw(temporary)} IF NOT EXISTS {table_name} ({_QUOTES_COLUMNS})"  # noqa: S608
    )
    if not temporary:
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_{table_name}_symbol_ts "  # noqa: S608
            f'ON {table_name}(symbol, "timestamp")'
        )


def create_news_table(
    conn: duckdb.DuckDBPyConnection, table_name: str = "news", *, temporary: bool = False
) -> None:
    _validate_ident(table_name)
    conn.execute(
        f"{_create_kw(temporary)} IF NOT EXISTS {table_name} ({_NEWS_COLUMNS})"  # noqa: S608
    )
    if not temporary:
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_{table_name}_published_at "  # noqa: S608
            f"ON {table_name}(published_at_utc)"
        )
