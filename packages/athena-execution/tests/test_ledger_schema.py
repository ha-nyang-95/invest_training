"""Story 1.5 Task 1.6 — `pre_trade_ledger` DDL unit scenarios (AC-1 "Then").

Stage-2 (no marker) — DuckDB :memory: only.

Covers AC-1 Then 1-5:
1. `create_pre_trade_ledger(:memory:)` creates view + raw table + sequence,
   second call is idempotent.
2. Direct `INSERT INTO pre_trade_ledger_raw` succeeds (DB level accepts; the
   application-layer enforcement lives in LedgerClient / AST regression).
3. `DROP TABLE pre_trade_ledger` against the view raises Catalog Error — the
   view / table catalog separation is real.
4. CHECK constraint: `id=1` with non-NULL `prev_hash` is rejected.
5. CHECK constraint: `id>1` with NULL `prev_hash` is rejected.
"""

from __future__ import annotations

from datetime import UTC, datetime

import duckdb
import pytest
from athena.execution.ledger.schema import create_pre_trade_ledger


def _fresh_conn() -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect(":memory:")
    create_pre_trade_ledger(conn)
    return conn


def _genesis_insert(conn: duckdb.DuckDBPyConnection, *, prev_hash: str | None = None) -> None:
    conn.execute(
        "INSERT INTO pre_trade_ledger_raw "
        '(id, "timestamp", module_version, policy_version_git_sha, user_id, '
        "event_type, payload_json, prev_hash, this_hash, param_hash) VALUES "
        "(nextval('seq_pre_trade_ledger_id'), ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            datetime.now(UTC),
            "ledger_client.v0.1.0",
            "abcdef1234",
            1,
            "genesis",
            "{}",
            prev_hash,
            "0" * 64,
            "0" * 64,
        ],
    )


def test_create_is_idempotent_and_creates_view_plus_raw_table() -> None:
    conn = duckdb.connect(":memory:")
    create_pre_trade_ledger(conn)
    # 2nd call must not error — idempotent DDL.
    create_pre_trade_ledger(conn)

    tables = sorted(
        r[0]
        for r in conn.execute(
            "SELECT table_name FROM duckdb_tables() "
            "WHERE table_name IN ('pre_trade_ledger', 'pre_trade_ledger_raw')"
        ).fetchall()
    )
    views = sorted(
        r[0]
        for r in conn.execute(
            "SELECT view_name FROM duckdb_views() "
            "WHERE view_name IN ('pre_trade_ledger', 'pre_trade_ledger_raw')"
        ).fetchall()
    )
    assert tables == ["pre_trade_ledger_raw"], tables
    assert views == ["pre_trade_ledger"], views

    # PRAGMA exposes the full 11-column prefix + server-side default.
    pragma = conn.execute("PRAGMA table_info('pre_trade_ledger_raw')").fetchall()
    columns = [row[1] for row in pragma]
    assert columns == [
        "id",
        "timestamp",
        "module_version",
        "policy_version_git_sha",
        "user_id",
        "event_type",
        "payload_json",
        "prev_hash",
        "this_hash",
        "param_hash",
        "created_at_utc",
    ], columns
    # user_id default = 1 (NFR-M4 seam)
    user_id_row = next(r for r in pragma if r[1] == "user_id")
    assert user_id_row[4] == "1" or user_id_row[4] == 1
    # created_at_utc default mentions now() / current_timestamp (DuckDB may render
    # the default with either spelling across minor versions — substring match).
    created_at_row = next(r for r in pragma if r[1] == "created_at_utc")
    default_expr = str(created_at_row[4]).lower()
    assert default_expr.startswith("now") or "current_timestamp" in default_expr, default_expr


def test_direct_raw_insert_succeeds_db_level() -> None:
    """DuckDB 1.x has no row-level trigger — DB accepts direct INSERT. Defense
    is application-layer (LedgerClient sole entry) + AST regression (§Invariant
    #11). Make the coverage explicit so a future DuckDB trigger feature can
    tighten this without silently changing test semantics."""
    conn = _fresh_conn()
    _genesis_insert(conn)  # id=1, prev_hash=NULL — allowed
    count = conn.execute("SELECT COUNT(*) FROM pre_trade_ledger").fetchone()
    assert count is not None and count[0] == 1


def test_drop_table_on_view_raises_catalog_error() -> None:
    conn = _fresh_conn()
    with pytest.raises(duckdb.CatalogException):
        conn.execute("DROP TABLE pre_trade_ledger")


def test_check_constraint_rejects_genesis_with_prev_hash() -> None:
    conn = _fresh_conn()
    with pytest.raises(duckdb.ConstraintException):
        _genesis_insert(conn, prev_hash="a" * 64)


def test_check_constraint_rejects_non_genesis_with_null_prev_hash() -> None:
    conn = _fresh_conn()
    _genesis_insert(conn)  # id=1 genesis, NULL prev — allowed
    with pytest.raises(duckdb.ConstraintException):
        # id=2 with NULL prev_hash — rejected.
        conn.execute(
            "INSERT INTO pre_trade_ledger_raw "
            '(id, "timestamp", module_version, policy_version_git_sha, user_id, '
            "event_type, payload_json, prev_hash, this_hash, param_hash) VALUES "
            "(nextval('seq_pre_trade_ledger_id'), ?, ?, ?, ?, ?, ?, NULL, ?, ?)",
            [
                datetime.now(UTC),
                "ledger_client.v0.1.0",
                "abcdef1234",
                1,
                "schema_segment_transition",
                "{}",
                "0" * 64,
                "0" * 64,
            ],
        )
