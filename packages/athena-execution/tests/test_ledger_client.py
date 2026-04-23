"""Story 1.5 Task 2.3 — LedgerClient single-entry-point scenarios (AC-2 "Then").

Stage-2 (no marker) — DuckDB :memory: only.

Covers AC-2 Then 1-8:
1. Genesis auto-seed on first LedgerClient construction.
2. Idempotent genesis (second client on same connection does not duplicate).
3. Single append → id=2, prev_hash chains to genesis this_hash, this_hash is
   64-char hex.
4. Chain of N — 5 consecutive appends, each `prev_hash(n) == this_hash(n-1)`.
5. Canonical JSON determinism — the same payload dict serialises bytewise
   identical across calls, and dict key order is irrelevant.
6. Hash recomputation — independent recompute of stored rows matches DB values.
7. V1.0 event_type Literal — covered by a separate regression file
   (`tests/regression/test_ledger_event_type_literal.py`, Task 2.5) which
   runs mypy; this unit suite skips the mypy subprocess to stay cheap.
8. `HASH_PLACEHOLDER` (`"0"*64`) never appears as a persisted this_hash.
"""

from __future__ import annotations

import re

import duckdb
import pytest
from athena.execution.ledger import (
    HASH_PLACEHOLDER,
    LedgerClient,
    canonical_json,
    compute_entry_hash,
)
from athena.execution.ledger.client import EMPTY_PARAM_HASH

_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _fresh_conn() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(":memory:")


def test_genesis_auto_seed_on_first_construction() -> None:
    conn = _fresh_conn()
    LedgerClient(conn)
    count_row = conn.execute("SELECT COUNT(*) FROM pre_trade_ledger").fetchone()
    assert count_row is not None and count_row[0] == 1
    row = conn.execute(
        "SELECT event_type, prev_hash, this_hash FROM pre_trade_ledger WHERE id = 1"
    ).fetchone()
    assert row is not None
    event_type, prev_hash, this_hash = row
    assert event_type == "genesis"
    assert prev_hash is None
    assert _HEX64.match(this_hash) is not None


def test_genesis_idempotent_on_repeat_construction() -> None:
    conn = _fresh_conn()
    LedgerClient(conn)
    LedgerClient(conn)  # 2nd construction, same connection
    count_row = conn.execute("SELECT COUNT(*) FROM pre_trade_ledger").fetchone()
    assert count_row is not None and count_row[0] == 1


def test_single_append_chains_to_genesis() -> None:
    conn = _fresh_conn()
    client = LedgerClient(conn)
    new_id = client.append(
        event_type="schema_segment_transition",
        payload={"reason": "story-1.5 smoke"},
    )
    assert new_id == 2
    genesis_this = conn.execute("SELECT this_hash FROM pre_trade_ledger WHERE id = 1").fetchone()
    assert genesis_this is not None
    appended = conn.execute(
        "SELECT prev_hash, this_hash FROM pre_trade_ledger WHERE id = 2"
    ).fetchone()
    assert appended is not None
    prev_hash, this_hash = appended
    assert prev_hash == genesis_this[0]
    assert _HEX64.match(this_hash) is not None


def test_chain_of_five_is_contiguous() -> None:
    conn = _fresh_conn()
    client = LedgerClient(conn)
    for i in range(5):
        client.append(
            event_type="schema_segment_transition",
            payload={"step": i, "tag": f"n{i}"},
        )
    rows = conn.execute(
        "SELECT id, prev_hash, this_hash FROM pre_trade_ledger ORDER BY id"
    ).fetchall()
    assert len(rows) == 6  # genesis + 5
    for i in range(1, len(rows)):
        assert rows[i][1] == rows[i - 1][2], f"chain break at id={rows[i][0]}"


def test_canonical_json_is_deterministic_across_key_order() -> None:
    a = canonical_json({"a": 1, "b": 2})
    b = canonical_json({"b": 2, "a": 1})
    assert a == b == '{"a":1,"b":2}'


def test_canonical_json_roundtrip_through_append() -> None:
    conn = _fresh_conn()
    client = LedgerClient(conn)
    payload_a = {"a": 1, "b": 2, "nested": {"z": 9, "m": 5}}
    payload_b = {"nested": {"m": 5, "z": 9}, "b": 2, "a": 1}
    client.append(event_type="schema_segment_transition", payload=payload_a)
    client.append(event_type="schema_segment_transition", payload=payload_b)
    rows = conn.execute(
        "SELECT id, payload_json FROM pre_trade_ledger WHERE id IN (2, 3) ORDER BY id"
    ).fetchall()
    assert rows[0][1] == rows[1][1]  # bytewise identical canonical JSON


def test_recomputed_hash_chain_matches_db() -> None:
    """Independent recompute of each row's this_hash from stored columns must
    match DB value. This is the core tamper-evidence invariant."""
    conn = _fresh_conn()
    client = LedgerClient(conn)
    client.append(event_type="schema_segment_transition", payload={"x": 1})
    client.append(event_type="schema_segment_transition", payload={"x": 2})

    rows = conn.execute(
        "SELECT id, event_type, policy_version_git_sha, user_id, "
        "payload_json, prev_hash, this_hash FROM pre_trade_ledger ORDER BY id"
    ).fetchall()
    for row in rows:
        _, ev, psha, uid, pj, prev, this = row
        recomputed = compute_entry_hash(
            prev_hash=prev,
            payload_json=pj,
            policy_version_git_sha=psha,
            event_type=ev,
            user_id=uid,
        )
        assert recomputed == this


def test_hash_placeholder_never_reaches_db() -> None:
    """`HASH_PLACEHOLDER` is a unit-test sentinel — must not appear in any
    persisted this_hash. Regression guard against a future refactor that
    forgets to compute the hash before INSERT."""
    conn = _fresh_conn()
    client = LedgerClient(conn)
    for i in range(3):
        client.append(event_type="schema_segment_transition", payload={"i": i})
    rows = conn.execute("SELECT this_hash FROM pre_trade_ledger").fetchall()
    assert not any(r[0] == HASH_PLACEHOLDER for r in rows)


def test_empty_param_hash_is_sha256_of_empty_json_object() -> None:
    """Sanity: EMPTY_PARAM_HASH must equal sha256(b'{}'). Drift here would
    silently change every row's param_hash column."""
    import hashlib

    assert EMPTY_PARAM_HASH == hashlib.sha256(b"{}").hexdigest()


def test_append_without_genesis_raises_runtime_error() -> None:
    """Defensive: if genesis seed somehow failed, `append` must raise rather
    than silently inserting id=2 with NULL prev_hash (which would also trip
    the CHECK constraint)."""
    conn = _fresh_conn()
    client = LedgerClient(conn)
    conn.execute("DELETE FROM pre_trade_ledger_raw")
    with pytest.raises(RuntimeError, match="no genesis"):
        client.append(event_type="schema_segment_transition", payload={})
