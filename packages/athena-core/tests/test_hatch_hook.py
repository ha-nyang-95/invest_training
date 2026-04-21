"""Integration test — Hatchling build hook injects git SHA into wheel (Story 1.1 AC-5)."""

from __future__ import annotations

import re
import shutil
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path

import pytest

REPO_ROOT: Path = Path(__file__).resolve().parents[3]
PACKAGE_NAME = "athena-core"

COMMIT_RE = re.compile(r'^__commit__\s*:\s*str\s*=\s*"([^"]+)"', re.MULTILINE)
BUILD_TIME_RE = re.compile(r'^__build_time_utc__\s*:\s*str\s*=\s*"([^"]+)"', re.MULTILINE)
COMMIT_VALUE_RE = re.compile(r"^[0-9a-f]{7,40}(-dirty)?$|^unknown-dev$")


@pytest.fixture(scope="module")
def built_wheel(tmp_path_factory: pytest.TempPathFactory) -> Path:
    uv = shutil.which("uv")
    if uv is None:
        pytest.skip("uv not on PATH; cannot exercise build hook integration test")

    out_dir = tmp_path_factory.mktemp("dist")
    result = subprocess.run(
        [uv, "build", "--package", PACKAGE_NAME, "--wheel", "--out-dir", str(out_dir)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=300,
    )
    assert result.returncode == 0, (
        f"uv build failed (exit {result.returncode}):\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )

    wheels = sorted(out_dir.glob("athena_core-*.whl"))
    assert len(wheels) == 1, f"expected exactly one athena-core wheel, got {wheels}"
    return wheels[0]


def test_wheel_contains_generated_version_file(built_wheel: Path) -> None:
    with zipfile.ZipFile(built_wheel) as zf:
        names = zf.namelist()
        assert "athena/core/_version.py" in names, (
            f"_version.py missing from wheel; contents: {names[:20]}..."
        )


def test_version_file_commit_matches_git_sha_or_fallback(built_wheel: Path) -> None:
    with zipfile.ZipFile(built_wheel) as zf:
        content = zf.read("athena/core/_version.py").decode("utf-8")

    match = COMMIT_RE.search(content)
    assert match, f"__commit__ not found in:\n{content}"
    commit = match.group(1)
    assert COMMIT_VALUE_RE.match(commit), (
        f"__commit__ value {commit!r} does not match expected pattern "
        f"(7-40 hex with optional -dirty, or 'unknown-dev')"
    )


def test_version_file_build_time_is_iso8601_utc(built_wheel: Path) -> None:
    with zipfile.ZipFile(built_wheel) as zf:
        content = zf.read("athena/core/_version.py").decode("utf-8")

    match = BUILD_TIME_RE.search(content)
    assert match, f"__build_time_utc__ not found in:\n{content}"
    build_time = match.group(1)

    parsed = datetime.fromisoformat(build_time)
    assert parsed.tzinfo is not None, f"__build_time_utc__ {build_time!r} is naive"
