"""Version identity (POLICY_VERSION_SHA, MODULE_VERSION) — hand-written.

Reads from `._version` which is generated at build time by
`packages/athena-core/hatch_build.py` (Story 1.1 AC-5). When the module is loaded
from a fresh source tree before any build has run, falls back to "unknown-dev".

CRITICAL (AR-COM4 — Story 1.1 Task 4.7 enforces via AST inspection):
This module MUST NOT call subprocess, os.popen, os.system, or shutil at runtime.
The Hatchling build hook is the ONLY sanctioned source of git SHA.
"""

from __future__ import annotations

try:
    from . import _version

    POLICY_VERSION_SHA: str = _version.__commit__
except (ImportError, AttributeError):
    POLICY_VERSION_SHA = "unknown-dev"

# Static semver; bumped only by a Change Control story (NFR-M2/M3).
_PACKAGE_SEMVER = "0.1.0"

MODULE_VERSION: str = f"{_PACKAGE_SEMVER}+{POLICY_VERSION_SHA[:8]}"
