"""Pre-Trade Ledger substrate — Story 1.5.

`LedgerClient` is the sole Python entry-point for `pre_trade_ledger`
(decisions.duckdb 의 6번째 테이블). Direct `conn.execute("INSERT INTO
pre_trade_ledger_raw ...")` is forbidden — enforced by
tests/regression/test_trading_pc_write_scope.py (AST scan) and by ruff
custom rule (Story 1.9).
"""

from athena.execution.ledger.client import EMPTY_PARAM_HASH, LedgerClient
from athena.execution.ledger.dto import LedgerEntry, LedgerEventTypeV1
from athena.execution.ledger.hash_chain import (
    HASH_PLACEHOLDER,
    canonical_json,
    compute_entry_hash,
)
from athena.execution.ledger.schema import SCHEMA_SQL, create_pre_trade_ledger

__all__ = [
    "EMPTY_PARAM_HASH",
    "HASH_PLACEHOLDER",
    "SCHEMA_SQL",
    "LedgerClient",
    "LedgerEntry",
    "LedgerEventTypeV1",
    "canonical_json",
    "compute_entry_hash",
    "create_pre_trade_ledger",
]
