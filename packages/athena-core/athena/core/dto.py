"""BaseDTO — 3-field contract enforced on every cross-module DTO.

Source-of-truth: architecture.md#Format-Patterns (lines 476-491), PRD NFR-M1.

Every DTO in any Athena package MUST inherit from BaseDTO so that:
- `timestamp` is UTC-aware (Enforcement #6: naive datetime forbidden)
- `module_version` follows semver (NFR-M2)
- `policy_version_git_sha` embeds product identity (D15 / AR-COM4)

Pydantic 2.x ConfigDict: frozen + strict + extra=forbid.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Pydantic 2 uses Rust regex engine for Field(pattern=...). The patterns below
# stay deliberately simple (anchors + alternation) to remain Rust-compatible.
_MODULE_VERSION_PATTERN = r"^M\d+\.v\d+\.\d+\.\d+$|^[a-z_-]+\.v\d+\.\d+\.\d+$"
_POLICY_SHA_PATTERN = r"^[0-9a-f]{7,40}(-dirty)?$"


class BaseDTO(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    timestamp: datetime
    module_version: Annotated[str, Field(pattern=_MODULE_VERSION_PATTERN)]
    policy_version_git_sha: Annotated[str, Field(pattern=_POLICY_SHA_PATTERN)]

    @field_validator("timestamp")
    @classmethod
    def _require_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            raise ValueError(
                "timestamp must be timezone-aware (UTC); naive datetime forbidden "
                "per architecture.md#Enforcement-Guidelines #6"
            )
        return value
