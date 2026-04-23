"""LedgerClient — single Python entry-point for pre_trade_ledger.

Source-of-truth: Story 1.5 AC-2; architecture.md#Process-Patterns lines 571-575.

Invariants enforced here (and by tests/regression/test_trading_pc_write_scope.py):
* `append()` is the ONE write method. No `update`, no `delete`, no direct
  `conn.execute("INSERT INTO pre_trade_ledger_raw ...")` outside this file.
* The genesis entry (id=1, prev_hash NULL, event_type='genesis') is seeded
  eagerly on `__init__` and is idempotent — repeated client instantiation
  does not duplicate it.
* `append` is synchronous (architecture.md line 575: chain-consistency
  requires sequential write; async wrapper forbidden). V1.0 runs in a single
  asyncio loop with a single DuckDB connection, so cooperative scheduling
  plus the connection's internal mutex already serialize writes.

Multi-connection / multi-process concurrent append is explicitly out-of-scope
for V1.0 — see deferred-work.md entry `concurrent multi-connection append`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import duckdb
from athena.core.version import POLICY_VERSION_SHA
from athena.execution.ledger.dto import LedgerEventTypeV1
from athena.execution.ledger.hash_chain import canonical_json, compute_entry_hash
from athena.execution.ledger.schema import create_pre_trade_ledger

EMPTY_PARAM_HASH: str = "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a"
"""SHA-256 of the canonical empty JSON object `{}` (bytewise `b"{}"`).

V1.0 placeholder for `param_hash`. Story 6.1 replaces this with a real
policy-parameter serializer when the full LedgerWriter lands."""

LEDGER_CLIENT_MODULE_VERSION: str = "ledger_client.v0.1.0"
"""Written to every row's `module_version` column. Must satisfy the lowercase
context form of BaseDTO._MODULE_VERSION_PATTERN (§Invariant #1). Story spec
narrative used `"LedgerClient.v1.0.0"` — the pattern requires
`[a-z][a-z_]*\\.v\\d+\\.\\d+\\.\\d+`, so the persisted spelling is
snake_case. This is the sole divergence from the story-body code block;
Dev Notes Change Log records the reconciliation."""


class LedgerClient:
    """Pre-Trade Ledger 의 유일한 Python 진입점.

    Direct `conn.execute("INSERT INTO pre_trade_ledger_raw ...")` is
    forbidden — enforced by test_trading_pc_write_scope.py (AST scan) and
    by ruff custom rule (Story 1.9).
    """

    def __init__(
        self,
        conn: duckdb.DuckDBPyConnection,
        *,
        user_id: int = 1,
        module_version: str = LEDGER_CLIENT_MODULE_VERSION,
    ) -> None:
        self._conn = conn
        self._user_id = user_id
        self._module_version = module_version
        create_pre_trade_ledger(conn)
        self._ensure_genesis()

    def _ensure_genesis(self) -> None:
        """Seed id=1 genesis entry if missing. Idempotent."""
        existing = self._conn.execute("SELECT id FROM pre_trade_ledger_raw WHERE id = 1").fetchone()
        if existing is not None:
            return
        genesis_payload: dict[str, Any] = {
            "note": "ledger genesis — chain segment start",
            "policy_version_git_sha": POLICY_VERSION_SHA,
        }
        payload_json = canonical_json(genesis_payload)
        this_hash = compute_entry_hash(
            prev_hash=None,
            payload_json=payload_json,
            policy_version_git_sha=POLICY_VERSION_SHA,
            event_type="genesis",
            user_id=self._user_id,
        )
        self._conn.execute(
            "INSERT INTO pre_trade_ledger_raw "
            '(id, "timestamp", module_version, policy_version_git_sha, user_id, '
            "event_type, payload_json, prev_hash, this_hash, param_hash) VALUES "
            "(nextval('seq_pre_trade_ledger_id'), ?, ?, ?, ?, ?, ?, NULL, ?, ?)",
            [
                datetime.now(UTC),
                self._module_version,
                POLICY_VERSION_SHA,
                self._user_id,
                "genesis",
                payload_json,
                this_hash,
                EMPTY_PARAM_HASH,
            ],
        )

    def append(
        self,
        *,
        event_type: LedgerEventTypeV1,
        payload: dict[str, Any],
        param_hash: str = EMPTY_PARAM_HASH,
    ) -> int:
        """Append one entry, return the assigned id.

        V1.0 `event_type` is a Literal of {'genesis', 'schema_segment_transition'}.
        Story 6.1 widens the Literal; the signature is stable.
        """
        prev = self._conn.execute(
            "SELECT this_hash FROM pre_trade_ledger_raw ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if prev is None:
            raise RuntimeError(
                "pre_trade_ledger_raw has no genesis — LedgerClient __init__ failed?"
            )
        prev_hash = prev[0]
        payload_json = canonical_json(payload)
        this_hash = compute_entry_hash(
            prev_hash=prev_hash,
            payload_json=payload_json,
            policy_version_git_sha=POLICY_VERSION_SHA,
            event_type=event_type,
            user_id=self._user_id,
        )
        self._conn.execute(
            "INSERT INTO pre_trade_ledger_raw "
            '(id, "timestamp", module_version, policy_version_git_sha, user_id, '
            "event_type, payload_json, prev_hash, this_hash, param_hash) VALUES "
            "(nextval('seq_pre_trade_ledger_id'), ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                datetime.now(UTC),
                self._module_version,
                POLICY_VERSION_SHA,
                self._user_id,
                event_type,
                payload_json,
                prev_hash,
                this_hash,
                param_hash,
            ],
        )
        row = self._conn.execute("SELECT currval('seq_pre_trade_ledger_id')").fetchone()
        if row is None:
            raise RuntimeError(
                "currval('seq_pre_trade_ledger_id') returned no row — sequence "
                "should have advanced on the preceding INSERT"
            )
        return int(row[0])


__all__ = ["EMPTY_PARAM_HASH", "LedgerClient"]
