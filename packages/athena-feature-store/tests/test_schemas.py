"""Story 1.4 AC-1 Task 1.5 — schemas.py + DTO single source unit tests.

5 scenarios:
1. DDL smoke: create_*_table against :memory: succeeds + PRAGMA table_info
   shows user_id default='1' + notnull=1.
2. TickRow.model_validate with a valid dict succeeds.
3. Naive datetime on timestamp → ValidationError (BaseDTO._require_utc).
4. Decimal round-trip through DuckDB INSERT preserves precision.
5. DTO ↔ DDL field-name parity (exact equality) for all three tables.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast

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
from pydantic import ValidationError

VALID_TS = datetime(2026, 4, 21, 9, 0, 0, tzinfo=UTC)
VALID_MV = "feature_store.v0.1.0"
VALID_SHA = "a1b2c3d4e5f6"


def _tick_kwargs(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "timestamp": VALID_TS,
        "module_version": VALID_MV,
        "policy_version_git_sha": VALID_SHA,
        "symbol": "005930",
        "last_px": Decimal("70500.0000"),
        "last_qty": 100,
        "trade_side": "B",
        "seq_no": 1,
    }
    for side in ("bid", "ask"):
        for i in range(1, 11):
            base[f"{side}_px_{i}"] = Decimal(f"{70500 - i if side == 'bid' else 70500 + i}.0000")
            base[f"{side}_qty_{i}"] = 10 * i
    base.update(overrides)
    return base


# ─── Scenario 1: DDL + PRAGMA ───────────────────────────────────────────────


def test_create_ticks_table_ddl_and_pragma() -> None:
    conn = duckdb.connect(":memory:")
    create_ticks_table(conn)
    rows = conn.execute("PRAGMA table_info('ticks')").fetchall()
    by_name = {r[1]: r for r in rows}

    assert set(by_name.keys()) == set(TickRow.model_fields.keys())
    user_id_row = by_name["user_id"]
    assert user_id_row[3] == 1 or user_id_row[3] is True, f"user_id notnull: {user_id_row}"
    assert str(user_id_row[4]) == "1", f"user_id dflt_value: {user_id_row}"
    for col, info in by_name.items():
        if col == "symbol":
            # news.symbol is NULL-allowed, but ticks.symbol is NOT NULL
            assert info[3] == 1 or info[3] is True
        elif col == "user_id":
            continue  # already asserted
        else:
            assert info[3] == 1 or info[3] is True, f"{col} should be NOT NULL: {info}"


def test_create_quotes_table_ddl_and_pragma() -> None:
    conn = duckdb.connect(":memory:")
    create_quotes_table(conn)
    rows = conn.execute("PRAGMA table_info('quotes')").fetchall()
    names = {r[1] for r in rows}
    assert names == set(QuoteRow.model_fields.keys())


def test_create_news_table_ddl_and_pragma() -> None:
    conn = duckdb.connect(":memory:")
    create_news_table(conn)
    rows = conn.execute("PRAGMA table_info('news')").fetchall()
    by_name = {r[1]: r for r in rows}
    assert set(by_name.keys()) == set(NewsRow.model_fields.keys())
    # news.symbol is the only NULL-allowed storage column
    assert by_name["symbol"][3] == 0 or by_name["symbol"][3] is False
    assert by_name["headline"][3] == 1 or by_name["headline"][3] is True


def test_all_three_tables_present_alphabetical() -> None:
    conn = duckdb.connect(":memory:")
    create_ticks_table(conn)
    create_quotes_table(conn)
    create_news_table(conn)
    tables = conn.execute("SHOW TABLES").fetchall()
    assert tables == [("news",), ("quotes",), ("ticks",)]


# ─── Scenario 2: valid model_validate ────────────────────────────────────────


def test_tick_row_valid_roundtrip() -> None:
    tr = TickRow.model_validate(_tick_kwargs())
    assert tr.symbol == "005930"
    assert tr.user_id == 1
    assert tr.trade_side == "B"


def test_quote_row_valid() -> None:
    qr = QuoteRow.model_validate(
        {
            "timestamp": VALID_TS,
            "module_version": VALID_MV,
            "policy_version_git_sha": VALID_SHA,
            "symbol": "005930",
            "interval": "1m",
            "open": Decimal("70500.0000"),
            "high": Decimal("70600.0000"),
            "low": Decimal("70400.0000"),
            "close": Decimal("70550.0000"),
            "volume": 12345,
            "vi_active": False,
        }
    )
    assert qr.interval == "1m"
    assert qr.vi_active is False


def test_news_row_null_symbol_allowed() -> None:
    nr = NewsRow.model_validate(
        {
            "timestamp": VALID_TS,
            "module_version": VALID_MV,
            "policy_version_git_sha": VALID_SHA,
            "published_at_utc": VALID_TS,
            "source": "DART",
            "symbol": None,
            "headline": "공시",
            "body_text": "내용",
            "url": "https://dart.fss.or.kr/abc",
            "dedup_hash": "0" * 64,
        }
    )
    assert nr.symbol is None


# ─── Scenario 3: naive datetime rejected ─────────────────────────────────────


def test_naive_timestamp_rejected() -> None:
    naive_ts = datetime(2026, 4, 21, 9, 0, 0)  # noqa: DTZ001 — the test is the naive case
    with pytest.raises(ValidationError, match="timezone-aware"):
        TickRow.model_validate(_tick_kwargs(timestamp=naive_ts))


def test_naive_published_at_rejected() -> None:
    naive_ts = datetime(2026, 4, 21, 9, 0, 0)  # noqa: DTZ001 — the test is the naive case
    with pytest.raises(ValidationError, match="timezone-aware"):
        NewsRow.model_validate(
            {
                "timestamp": VALID_TS,
                "module_version": VALID_MV,
                "policy_version_git_sha": VALID_SHA,
                "published_at_utc": naive_ts,
                "source": "DART",
                "symbol": None,
                "headline": "x",
                "body_text": "x",
                "url": "https://example.com",
                "dedup_hash": "0" * 64,
            }
        )


# ─── Scenario 4: Decimal roundtrip through DuckDB INSERT ─────────────────────


def test_decimal_precision_roundtrip() -> None:
    conn = duckdb.connect(":memory:")
    create_ticks_table(conn)
    tr = TickRow.model_validate(_tick_kwargs(last_px=Decimal("70500.123")))
    field_names = list(TickRow.model_fields.keys())
    placeholders = ",".join(["?"] * len(field_names))
    columns = ",".join(f'"{k}"' for k in field_names)
    values = [getattr(tr, k) for k in field_names]
    conn.execute(f"INSERT INTO ticks ({columns}) VALUES ({placeholders})", values)  # noqa: S608
    result = conn.execute("SELECT last_px FROM ticks").fetchone()
    assert result is not None
    stored = cast(Decimal, result[0])
    assert stored == Decimal("70500.1230")


# ─── Scenario 5: DTO ↔ DDL parity (name-set exact equality) ──────────────────


@pytest.mark.parametrize(
    ("dto", "creator", "table"),
    [
        (TickRow, create_ticks_table, "ticks"),
        (QuoteRow, create_quotes_table, "quotes"),
        (NewsRow, create_news_table, "news"),
    ],
)
def test_dto_ddl_name_parity(
    dto: type[TickRow | QuoteRow | NewsRow],
    creator: Any,
    table: str,
) -> None:
    conn = duckdb.connect(":memory:")
    creator(conn)
    rows = conn.execute(f"PRAGMA table_info('{table}')").fetchall()  # noqa: S608
    ddl_names = {r[1] for r in rows}
    dto_names = set(dto.model_fields.keys())
    assert ddl_names == dto_names, (
        f"{table}: symmetric diff = {dto_names.symmetric_difference(ddl_names)}"
    )


@pytest.mark.parametrize("reserved", ["interval", "order", "select", "TABLE", "User"])
def test_validate_ident_rejects_reserved_keywords(reserved: str) -> None:
    """Review-flip fix: bare reserved keywords as table names compile today
    (the validator accepted anything `[a-zA-Z_][a-zA-Z0-9_]*`) but produce
    confusing ambiguity errors on subsequent SELECT. Reject up-front."""
    conn = duckdb.connect(":memory:")
    with pytest.raises(ValueError, match="reserved keyword"):
        create_ticks_table(conn, table_name=reserved)


def test_decimal_overflow_is_rejected_by_duckdb() -> None:
    """Review-flip fix: DECIMAL(18,4) max value is
    99,999,999,999,999.9999 (14 integer digits + 4 decimal). Attempts to
    INSERT a value that exceeds this must raise — a silent truncation
    would corrupt high-price ticks (matters for KRX tickers near 1M KRW
    where DECIMAL(18,4) already leaves headroom, and matters hard for
    any future expansion to higher-precision assets).

    Asserts the DuckDB layer flags overflow (via ConversionException or
    InvalidInputException depending on 1.x sub-version). We do not
    catch ValidationError from Pydantic here because BaseDTO does not
    cap Decimal at the DDL precision — the DB is the enforcement point."""
    overflow_value = Decimal("999999999999999999999.9999")  # 21 int digits — past DECIMAL(18,4)
    conn = duckdb.connect(":memory:")
    create_ticks_table(conn)
    with pytest.raises(duckdb.Error):
        # Minimal INSERT that exercises only the last_px column type.
        # Other columns filled with arbitrary valid values.
        params: list[Any] = [
            VALID_TS,
            VALID_MV,
            VALID_SHA,
            1,  # user_id
            "005930",
        ]
        # bid/ask_{px,qty}_1..10 = 20 cols
        for _side in ("bid", "ask"):
            for _i in range(1, 11):
                params.append(Decimal("70500.0000"))
                params.append(100)
        params += [overflow_value, 100, "B", 1]  # last_px, last_qty, trade_side, seq_no
        placeholders = ",".join("?" * len(params))
        conn.execute(f"INSERT INTO ticks VALUES ({placeholders})", params)  # noqa: S608
