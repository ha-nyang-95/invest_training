"""ErrorCode 8-member contract tests (Story 1.1 Task 4.6)."""

from __future__ import annotations

from athena.core.errors import AthenaError, ErrorCode, MissingSecretError

EXPECTED_MEMBERS = frozenset(
    {
        "KIS_RATE_LIMIT",
        "FEATURE_MISSING",
        "LLM_TIMEOUT",
        "CONFIDENCE_BELOW_THRESHOLD",
        "DATA_STALE",
        "HEARTBEAT_LOST",
        "SLIPPAGE_EXCEEDED",
        "POLICY_NOT_COOLED",
    }
)


def test_error_code_has_exactly_eight_members() -> None:
    assert len(list(ErrorCode)) == 8


def test_error_code_members_match_architecture_d14() -> None:
    actual = {member.name for member in ErrorCode}
    assert actual == EXPECTED_MEMBERS


# architecture.md#D14: `KIS_RATE_LIMIT` carries the KIS gateway error code `EGW00201`
# (broker's own wire value); the remaining 7 members use their symbolic name as value.
EXPECTED_VALUES = {
    "KIS_RATE_LIMIT": "EGW00201",
    "FEATURE_MISSING": "FEATURE_MISSING",
    "LLM_TIMEOUT": "LLM_TIMEOUT",
    "CONFIDENCE_BELOW_THRESHOLD": "CONFIDENCE_BELOW_THRESHOLD",
    "DATA_STALE": "DATA_STALE",
    "HEARTBEAT_LOST": "HEARTBEAT_LOST",
    "SLIPPAGE_EXCEEDED": "SLIPPAGE_EXCEEDED",
    "POLICY_NOT_COOLED": "POLICY_NOT_COOLED",
}


def test_error_code_values_match_architecture_d14() -> None:
    for member in ErrorCode:
        assert isinstance(member.value, str)
        assert member.value == EXPECTED_VALUES[member.name], (
            f"{member.name} value drift from architecture.md#D14"
        )


def test_athena_error_hierarchy() -> None:
    assert issubclass(MissingSecretError, AthenaError)
    assert issubclass(AthenaError, Exception)


def test_missing_secret_error_can_be_raised_and_caught() -> None:
    import pytest

    with pytest.raises(AthenaError):
        raise MissingSecretError("dummy")
