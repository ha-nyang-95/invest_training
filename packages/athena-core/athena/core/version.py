"""Version identity (POLICY_VERSION_SHA, MODULE_VERSION) — hand-written.

Reads from `._version` which is generated at build time by
`packages/athena-core/hatch_build.py` (Story 1.1 AC-5). When the module is loaded
from a fresh source tree before any build has run, falls back to "unknown-dev".

`POLICY_VERSION_SHA` is post-processed to strip any `git describe` tag prefix
(e.g. `v1.0.0-5-gabcdef12` -> `abcdef12`) so the value is always the bare hex
SHA + optional `-dirty` suffix. This preserves NFR-M1 "product identity = git SHA"
and keeps `_POLICY_SHA_PATTERN` (athena.core.dto) satisfied without loosening the pattern.

`MODULE_VERSION` identifies the athena-core package itself in the 3-field DTO
contract (architecture.md#Format-Patterns line 483 example: "M1.v1.2.0"). Each
M-module (M1..M25) will define its own `MODULE_VERSION` constant; this one
covers DTOs emitted directly by athena-core.

CRITICAL (AR-COM4 — Story 1.1 Task 4.7 enforces via AST inspection):
This module MUST NOT call subprocess, os.popen, os.system, or shutil at runtime.
The Hatchling build hook is the ONLY sanctioned source of git SHA.
"""

from __future__ import annotations

import re

# Matches the trailing bare-hex segment of `git describe --always --dirty` output.
# Handles: "abcdef12", "abcdef12-dirty", "v1.0.0-5-gabcdef12", "v1.0.0-5-gabcdef12-dirty".
# The `g` prefix inserted by `git describe` before the hex is stripped by the
# `(?:g)?` non-capturing group anchored after a `-`.
_SHA_TAIL_RE = re.compile(r"(?:^|-g)([0-9a-f]{7,40})(-dirty)?$")


def _extract_policy_sha(raw: str) -> str:
    match = _SHA_TAIL_RE.search(raw)
    if match is None:
        return "unknown-dev"
    sha = match.group(1)
    return f"{sha}-dirty" if match.group(2) else sha


try:
    from . import _version

    POLICY_VERSION_SHA: str = _extract_policy_sha(_version.__commit__)
except (ImportError, AttributeError):
    POLICY_VERSION_SHA = "unknown-dev"

# Static semver; bumped only by a Change Control story (NFR-M2/M3).
_PACKAGE_SEMVER = "0.1.0"

# Matches BaseDTO._MODULE_VERSION_PATTERN second alternation: <context>.v<semver>.
# DN-3 deviation from story spec line 77 (`<package_semver>+<git_sha8>`): architecture.md
# line 625 injects MODULE_VERSION directly into DTO's `module_version` field, so the
# format MUST match the DTO regex. SHA lives separately in `policy_version_git_sha`.
MODULE_VERSION: str = f"core.v{_PACKAGE_SEMVER}"
