"""BaseDTO — 3-field contract enforced on every cross-module DTO.

Source-of-truth: architecture.md#Format-Patterns (lines 476-491), PRD NFR-M1.

Every DTO in any Athena package MUST inherit from BaseDTO so that:
- `timestamp` is UTC-aware (architecture.md line 494: "내부 저장·DTO: UTC aware 필수"),
   non-UTC tz-aware input is auto-normalised via `astimezone(UTC)`; naive datetime
   is rejected per Enforcement #6.
- `module_version` follows per-context semver (NFR-M2). Accepted forms:
     "M<n>.v<major>.<minor>.<patch>"   (M-module families, e.g. "M1.v1.2.0")
     "<context>.v<major>.<minor>.<patch>"  (package contexts, e.g. "core.v0.1.0")
- `policy_version_git_sha` embeds product identity (D15 / AR-COM4), bare hex
   (7-40 chars) optionally followed by "-dirty".

Pydantic 2.x ConfigDict: frozen + strict + extra=forbid.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Pydantic 2 uses Rust regex engine for Field(pattern=...). The patterns below
# stay deliberately simple (anchors + alternation) to remain Rust-compatible.
# Context alternation requires a leading letter so `-.v0.0.0` / `_.v0.0.0` are rejected.
_MODULE_VERSION_PATTERN = r"^M\d+\.v\d+\.\d+\.\d+$|^[a-z][a-z_]*\.v\d+\.\d+\.\d+$"
_POLICY_SHA_PATTERN = r"^[0-9a-f]{7,40}(-dirty)?$"


class BaseDTO(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    timestamp: datetime
    module_version: Annotated[str, Field(pattern=_MODULE_VERSION_PATTERN)]
    policy_version_git_sha: Annotated[str, Field(pattern=_POLICY_SHA_PATTERN)]

    @field_validator("timestamp")
    @classmethod
    def _require_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            raise ValueError(
                "timestamp must be timezone-aware (UTC); naive datetime forbidden "
                "per architecture.md#Enforcement-Guidelines #6"
            )
        # architecture.md line 494: cross-module DTOs store/transmit UTC only.
        # Non-UTC tz-aware input is normalised here rather than rejected so that
        # KST-attached inputs from user-facing layers do not produce silent off-by-9h bugs.
        return value.astimezone(UTC)
