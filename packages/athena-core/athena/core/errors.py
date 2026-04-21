"""ErrorCode taxonomy + AthenaError hierarchy.

Source-of-truth: architecture.md#D14 (lines 314-325).

The 8 ErrorCode values are FROZEN — adding values requires a Change Control
slot (NFR-M3, max 1 change per 12 weeks). Do not anticipate future codes here.
"""

from __future__ import annotations

from enum import StrEnum


class ErrorCode(StrEnum):
    KIS_RATE_LIMIT = "EGW00201"
    FEATURE_MISSING = "FEATURE_MISSING"
    LLM_TIMEOUT = "LLM_TIMEOUT"
    CONFIDENCE_BELOW_THRESHOLD = "CONFIDENCE_BELOW_THRESHOLD"
    DATA_STALE = "DATA_STALE"
    HEARTBEAT_LOST = "HEARTBEAT_LOST"
    SLIPPAGE_EXCEEDED = "SLIPPAGE_EXCEEDED"
    POLICY_NOT_COOLED = "POLICY_NOT_COOLED"


class AthenaError(Exception):
    """Base exception for all Athena-internal errors."""


class MissingSecretError(AthenaError):
    """A required secret was not present in the OS Keychain (resolved by Story 1.2)."""
