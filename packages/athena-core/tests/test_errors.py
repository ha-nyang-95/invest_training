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


def test_error_code_values_are_strings_matching_names() -> None:
    for member in ErrorCode:
        assert isinstance(member.value, str)
        assert member.value == member.name


def test_athena_error_hierarchy() -> None:
    assert issubclass(MissingSecretError, AthenaError)
    assert issubclass(AthenaError, Exception)


def test_missing_secret_error_can_be_raised_and_caught() -> None:
    import pytest

    with pytest.raises(AthenaError):
        raise MissingSecretError("dummy")
