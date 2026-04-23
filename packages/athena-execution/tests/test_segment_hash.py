"""Story 1.5 Task 3.4 — segment_hash unit scenarios (AC-3 "Then").

Stage-2 (no marker) — DuckDB :memory: only.

Covers AC-3 Then 1-5: empty month, single-entry month, determinism, prev
chain propagation, policy version influence.
"""

from __future__ import annotations

import hashlib

import duckdb
from athena.execution.ledger import LedgerClient
from athena.execution.ledger.segment_hash import compute_segment_hash


def _conn_with_genesis() -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect(":memory:")
    LedgerClient(conn)  # seeds genesis → id=1
    return conn


def test_empty_month_has_zero_entries_and_fixed_canonical_form() -> None:
    conn = duckdb.connect(":memory:")
    LedgerClient(conn)  # genesis lands at `now()` — pick a future empty month.
    result = compute_segment_hash(
        conn,
        year=2099,
        month=12,
        prev_segment_hash=None,
        policy_version_git_sha="abcdef1234",
    )
    assert result.entry_count == 0
    assert result.first_id is None
    assert result.last_id is None
    # Deterministic canonical form: SHA256("" || SHA256(b"") || policy_sha)
    expected_inner = hashlib.sha256(b"").hexdigest()
    expected_body = "\x00".join(["", expected_inner, "abcdef1234"]).encode("utf-8")
    assert result.segment_hash == hashlib.sha256(expected_body).hexdigest()


def test_single_entry_month_captures_genesis_id_one() -> None:
    conn = _conn_with_genesis()
    row = conn.execute(
        "SELECT EXTRACT(year FROM created_at_utc), EXTRACT(month FROM created_at_utc) "
        "FROM pre_trade_ledger WHERE id = 1"
    ).fetchone()
    assert row is not None
    year, month = int(row[0]), int(row[1])
    result = compute_segment_hash(
        conn,
        year=year,
        month=month,
        prev_segment_hash=None,
        policy_version_git_sha="abcdef1234",
    )
    assert result.entry_count == 1
    assert result.first_id == 1
    assert result.last_id == 1
    # sorted_ids_hash for the single genesis id = SHA256(b"1")
    inner = hashlib.sha256(b"1").hexdigest()
    body = "\x00".join(["", inner, "abcdef1234"]).encode("utf-8")
    assert result.segment_hash == hashlib.sha256(body).hexdigest()


def test_determinism_same_inputs_produce_same_hash() -> None:
    conn = _conn_with_genesis()
    row = conn.execute(
        "SELECT EXTRACT(year FROM created_at_utc), EXTRACT(month FROM created_at_utc) "
        "FROM pre_trade_ledger WHERE id = 1"
    ).fetchone()
    assert row is not None
    year, month = int(row[0]), int(row[1])
    first = compute_segment_hash(
        conn, year=year, month=month, prev_segment_hash="beef" * 16, policy_version_git_sha="f" * 10
    )
    second = compute_segment_hash(
        conn, year=year, month=month, prev_segment_hash="beef" * 16, policy_version_git_sha="f" * 10
    )
    assert first.segment_hash == second.segment_hash


def test_prev_segment_hash_affects_current_segment_hash() -> None:
    conn = _conn_with_genesis()
    row = conn.execute(
        "SELECT EXTRACT(year FROM created_at_utc), EXTRACT(month FROM created_at_utc) "
        "FROM pre_trade_ledger WHERE id = 1"
    ).fetchone()
    assert row is not None
    year, month = int(row[0]), int(row[1])
    a = compute_segment_hash(
        conn,
        year=year,
        month=month,
        prev_segment_hash="a" * 64,
        policy_version_git_sha="abcdef1234",
    )
    b = compute_segment_hash(
        conn,
        year=year,
        month=month,
        prev_segment_hash="b" * 64,
        policy_version_git_sha="abcdef1234",
    )
    assert a.segment_hash != b.segment_hash
    assert a.prev_segment_hash == "a" * 64
    assert b.prev_segment_hash == "b" * 64


def test_policy_version_change_rotates_segment_hash() -> None:
    conn = _conn_with_genesis()
    row = conn.execute(
        "SELECT EXTRACT(year FROM created_at_utc), EXTRACT(month FROM created_at_utc) "
        "FROM pre_trade_ledger WHERE id = 1"
    ).fetchone()
    assert row is not None
    year, month = int(row[0]), int(row[1])
    one = compute_segment_hash(
        conn, year=year, month=month, prev_segment_hash=None, policy_version_git_sha="aaaaaaaaaa"
    )
    two = compute_segment_hash(
        conn, year=year, month=month, prev_segment_hash=None, policy_version_git_sha="bbbbbbbbbb"
    )
    assert one.segment_hash != two.segment_hash, (
        "policy_version_git_sha rotation must change segment_hash — otherwise "
        "a policy change would not be recorded in the chain (Story 6.8)"
    )
