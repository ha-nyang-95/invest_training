"""BaseDTO 3-field contract tests (Story 1.1 Task 4.5)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from athena.core.dto import BaseDTO
from pydantic import ValidationError


def _valid(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "timestamp": datetime(2026, 4, 21, 12, 0, 0, tzinfo=UTC),
        "module_version": "M1.v0.1.0",
        "policy_version_git_sha": "a3f2d1c",
    }
    base.update(overrides)
    return base


def test_accepts_valid_utc_aware_input() -> None:
    dto = BaseDTO(**_valid())
    assert dto.timestamp.tzinfo is not None
    assert dto.module_version == "M1.v0.1.0"
    assert dto.policy_version_git_sha == "a3f2d1c"


def test_accepts_module_version_with_lowercase_context_prefix() -> None:
    dto = BaseDTO(**_valid(module_version="alpha_defense.v0.1.0"))
    assert dto.module_version == "alpha_defense.v0.1.0"


def test_accepts_core_module_version() -> None:
    # architecture.md line 625 injects MODULE_VERSION from athena.core.version
    # directly into the DTO field — format must match the regex.
    dto = BaseDTO(**_valid(module_version="core.v0.1.0"))
    assert dto.module_version == "core.v0.1.0"


@pytest.mark.parametrize(
    "bad_prefix",
    ["-.v0.0.0", "_.v0.0.0", "---.v0.0.0", "___.v0.0.0", "1abc.v0.0.0", "Abc.v0.0.0"],
)
def test_rejects_malformed_context_prefix(bad_prefix: str) -> None:
    with pytest.raises(ValidationError):
        BaseDTO(**_valid(module_version=bad_prefix))


def test_accepts_40_char_sha() -> None:
    sha40 = "abcdef0123456789" * 2 + "abcdefab"
    assert len(sha40) == 40
    dto = BaseDTO(**_valid(policy_version_git_sha=sha40))
    assert dto.policy_version_git_sha == sha40


def test_accepts_dirty_suffix() -> None:
    dto = BaseDTO(**_valid(policy_version_git_sha="a3f2d1c-dirty"))
    assert dto.policy_version_git_sha == "a3f2d1c-dirty"


def test_rejects_naive_datetime() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        BaseDTO(**_valid(timestamp=datetime(2026, 4, 21, 12, 0, 0)))  # noqa: DTZ001


def test_non_utc_tz_input_is_normalised_to_utc() -> None:
    # architecture.md line 494: cross-module DTO storage is UTC only.
    # KST 21:00 -> UTC 12:00 (Asia/Seoul is UTC+9).
    kst = datetime(2026, 4, 21, 21, 0, 0, tzinfo=ZoneInfo("Asia/Seoul"))
    dto = BaseDTO(**_valid(timestamp=kst))
    assert dto.timestamp.utcoffset() == timedelta(0)
    assert dto.timestamp == datetime(2026, 4, 21, 12, 0, 0, tzinfo=UTC)


def test_non_standard_offset_input_is_normalised_to_utc() -> None:
    # Indian Standard Time (UTC+05:30). 17:30 IST -> 12:00 UTC.
    ist = timezone(timedelta(hours=5, minutes=30))
    dto = BaseDTO(**_valid(timestamp=datetime(2026, 4, 21, 17, 30, 0, tzinfo=ist)))
    assert dto.timestamp.utcoffset() == timedelta(0)
    assert dto.timestamp.hour == 12 and dto.timestamp.minute == 0


def test_rejects_malformed_module_version() -> None:
    with pytest.raises(ValidationError):
        BaseDTO(**_valid(module_version="not-semver"))


def test_rejects_uppercase_in_policy_sha() -> None:
    with pytest.raises(ValidationError):
        BaseDTO(**_valid(policy_version_git_sha="ABCDEF1"))


def test_rejects_too_short_sha() -> None:
    with pytest.raises(ValidationError):
        BaseDTO(**_valid(policy_version_git_sha="abc123"))  # 6 chars, min is 7


def test_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        BaseDTO(**_valid(unexpected_field="x"))


def test_frozen_prevents_mutation() -> None:
    dto = BaseDTO(**_valid())
    with pytest.raises(ValidationError):
        dto.module_version = "M2.v0.0.1"  # type: ignore[misc]
