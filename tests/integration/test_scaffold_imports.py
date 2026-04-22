"""Story 1.1 Task 3.4 — integration smoke.

Workspace, runtime deps, Python pin, uv discoverability.
"""

from __future__ import annotations

import shutil
import sys

import pytest


def test_python_version_is_3_13() -> None:
    """architecture.md line 183: Python 3.13 only, no 3.12 fallback."""
    assert sys.version_info[:2] == (3, 13), f"expected Python 3.13.x, got {sys.version_info}"


def test_all_six_athena_packages_importable() -> None:
    """AC-2: 6-package scaffold all importable as athena.<context> namespace."""
    import athena.alpha_defense  # noqa: F401
    import athena.core  # noqa: F401
    import athena.execution  # noqa: F401
    import athena.feature_store  # noqa: F401
    import athena.ops_defense  # noqa: F401
    import athena.orchestrator  # noqa: F401


def test_runtime_deps_importable() -> None:
    """AC-2: MVP Tier-1 runtime deps install successfully."""
    import duckdb  # noqa: F401
    import keyring  # noqa: F401
    import polars  # noqa: F401
    import pydantic  # noqa: F401
    import pydantic_settings  # noqa: F401


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="uvloop is not available on Windows; orchestrator runs on WSL2/Linux",
)
def test_uvloop_importable_on_non_windows() -> None:
    """uvloop only required on Trading PC (WSL2 Linux per architecture.md#D17)."""
    import uvloop  # noqa: F401


def test_python_kis_importable() -> None:
    """python-kis (Soju06) is the broker primary adapter (architecture.md line 185)."""
    import pykis  # noqa: F401  # python-kis exposes module as `pykis`


def test_uv_discoverable_on_path() -> None:
    """AC-2 implicit: `uv` must be on PATH so `uv sync` reproduces this state from a fresh clone."""
    assert shutil.which("uv") is not None, "uv binary not discoverable on PATH"
