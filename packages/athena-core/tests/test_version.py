"""Unit tests for athena.core.version: POLICY_VERSION_SHA extraction + MODULE_VERSION format.

Review-origin tests (bmad-code-review 2026-04-21):
- DN-2: `_extract_policy_sha` must strip `git describe` tag prefixes so the stored
  identity is always bare hex (optionally `-dirty`).
- DN-3: `MODULE_VERSION` must satisfy BaseDTO's `_MODULE_VERSION_PATTERN` so it can
  be injected directly into DTOs per architecture.md line 625.
"""

from __future__ import annotations

import re

import pytest
from athena.core.dto import BaseDTO
from athena.core.version import MODULE_VERSION, POLICY_VERSION_SHA, _extract_policy_sha

_POLICY_SHA_PATTERN = re.compile(r"^[0-9a-f]{7,40}(-dirty)?$")


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("abcdef1", "abcdef1"),
        ("abcdef1234567890", "abcdef1234567890"),
        ("abcdef1-dirty", "abcdef1-dirty"),
        ("v1.0.0-5-gabcdef1", "abcdef1"),
        ("v1.0.0-5-gabcdef1-dirty", "abcdef1-dirty"),
        ("release-2026-04-21-42-gabcdef1234567890-dirty", "abcdef1234567890-dirty"),
    ],
    ids=[
        "bare-7-hex",
        "bare-16-hex",
        "bare-with-dirty",
        "tag-prefixed",
        "tag-prefixed-dirty",
        "complex-tag-long-sha-dirty",
    ],
)
def test_extract_policy_sha_strips_tag_prefix(raw: str, expected: str) -> None:
    assert _extract_policy_sha(raw) == expected


@pytest.mark.parametrize(
    "raw",
    ["", "unknown-dev", "v1.0.0", "not-a-sha", "GHIJKL1"],
    ids=["empty", "fallback-token", "tag-only", "garbage", "non-hex"],
)
def test_extract_policy_sha_falls_back_on_unusable_input(raw: str) -> None:
    assert _extract_policy_sha(raw) == "unknown-dev"


def test_policy_version_sha_is_bare_hex_or_fallback() -> None:
    # In any environment (real git repo or tarball), POLICY_VERSION_SHA must be
    # a shape BaseDTO.policy_version_git_sha accepts OR the documented fallback.
    assert _POLICY_SHA_PATTERN.match(POLICY_VERSION_SHA) or POLICY_VERSION_SHA == "unknown-dev"


def test_module_version_matches_base_dto_pattern() -> None:
    # architecture.md line 625: `module_version=MODULE_VERSION` — the constant must
    # satisfy BaseDTO's regex so downstream DTO construction does not raise.
    # We build a DTO to assert validation actually accepts it (end-to-end check).
    from datetime import UTC, datetime

    dto = BaseDTO(
        timestamp=datetime(2026, 4, 21, 12, 0, 0, tzinfo=UTC),
        module_version=MODULE_VERSION,
        policy_version_git_sha="a3f2d1c",
    )
    assert dto.module_version == MODULE_VERSION


def test_module_version_uses_context_prefix_format() -> None:
    # Expected shape "core.v<semver>" — documents DN-3 deviation from story spec
    # line 77 (`<package_semver>+<git_sha8>`). SHA lives in policy_version_git_sha.
    assert MODULE_VERSION.startswith("core.v")
    assert "+" not in MODULE_VERSION
