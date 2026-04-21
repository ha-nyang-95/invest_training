"""BaseDTO 3-field contract tests (Story 1.1 Task 4.5)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

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
