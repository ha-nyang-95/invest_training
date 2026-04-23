"""LedgerEntry DTO — pre_trade_ledger 의 Pydantic 표현.

Source-of-truth: Story 1.5 AC-1; architecture.md#D4 (Pydantic single source),
#Format-Patterns (UTC-aware TIMESTAMPTZ).

BaseDTO 상속 (frozen + strict + extra=forbid + UTC validator). V1.0 에서
LedgerClient 가 실제로 append 하는 event_type 은 "genesis" 와
"schema_segment_transition" 두 가지뿐이며, Story 6.1 full LedgerWriter 가
Literal 집합을 확장한다 (entry_authorized, order_placed, order_filled, exit_*,
compliance_* 등). 확장 시 본 DTO 의 Literal 과 tests/regression/
test_ledger_event_type_literal.py fixture 를 함께 수정할 것.

id / created_at_utc 는 DB server-side default (sequence / now()) 이므로 DTO
측에서는 read-back 용 optional 로 매핑해 DDL parity 테스트가 동일 컬럼 집합을
비교할 수 있도록 둔다.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from athena.core.dto import BaseDTO
from pydantic import Field

LedgerEventTypeV1 = Literal["genesis", "schema_segment_transition"]


class LedgerEntry(BaseDTO):
    # BaseDTO inherit: timestamp (UTC-aware), module_version, policy_version_git_sha.
    id: int | None = None
    user_id: Annotated[int, Field(default=1, ge=0)] = 1
    event_type: LedgerEventTypeV1
    payload_json: str
    prev_hash: Annotated[str, Field(min_length=64, max_length=64)] | None = None
    this_hash: Annotated[str, Field(min_length=64, max_length=64)]
    param_hash: Annotated[str, Field(min_length=64, max_length=64)]
    created_at_utc: datetime | None = None


__all__ = ["LedgerEntry", "LedgerEventTypeV1"]
