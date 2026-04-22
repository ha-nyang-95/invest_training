"""Story 1.3 Task 3.5 — pytest markers regression.

Detects accidental rename/removal of the three CI-stage markers. pyproject.toml
lists markers as `name: description`; this test extracts the name prefix and
asserts the exact set.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_MARKERS = {"integration", "snapshot", "walk_forward"}


def _registered_marker_names() -> set[str]:
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    markers: list[str] = data["tool"]["pytest"]["ini_options"]["markers"]
    return {entry.split(":", 1)[0].strip() for entry in markers}


def test_ci_stage_markers_registered() -> None:
    assert _registered_marker_names() == EXPECTED_MARKERS


def test_ci_stage_markers_have_descriptions() -> None:
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    markers: list[str] = data["tool"]["pytest"]["ini_options"]["markers"]
    for entry in markers:
        name, _, description = entry.partition(":")
        assert name.strip() in EXPECTED_MARKERS
        assert description.strip(), f"marker {name!r} missing description"
