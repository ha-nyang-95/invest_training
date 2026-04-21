"""Regression — verify ruff banned-api / DTZ rules ACTUALLY DETECT violations.

Story 1.1 Task 7.6:
- import pandas        -> TID253 with Enforcement #3 message
- import requests      -> TID253 with Enforcement #4 message
- urllib.request       -> TID253 with Enforcement #4 message
- datetime.now()       -> DTZ005 (naive datetime forbidden, Enforcement #6)
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT: Path = Path(__file__).resolve().parents[2]


def _ruff_executable() -> str:
    venv_scripts = Path(sys.executable).parent
    for candidate in (venv_scripts / "ruff.exe", venv_scripts / "ruff"):
        if candidate.exists():
            return str(candidate)
    found = shutil.which("ruff")
    if found is None:
        pytest.skip("ruff console script not on PATH")
    return found


def _ruff_check(filepath: Path) -> tuple[int, str]:
    """Run ruff with the repo's pyproject.toml config, target a single file."""
    result = subprocess.run(
        [
            _ruff_executable(),
            "check",
            "--config",
            str(REPO_ROOT / "pyproject.toml"),
            "--no-cache",
            str(filepath),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.returncode, result.stdout + result.stderr


@pytest.mark.parametrize(
    "source,expected_code,expected_msg_substring",
    [
        ("import pandas\n", "TID", "Enforcement-Guidelines #3"),
        ("import requests\n", "TID", "Enforcement-Guidelines #4"),
        ("from urllib import request\n", "TID", "Enforcement-Guidelines #4"),
        ("from datetime import datetime\nx = datetime.now()\n", "DTZ", ""),
    ],
    ids=["pandas-banned", "requests-banned", "urllib-request-banned", "naive-datetime-banned"],
)
def test_ruff_detects_violation(
    tmp_path: Path,
    source: str,
    expected_code: str,
    expected_msg_substring: str,
) -> None:
    bad_file = tmp_path / "bad_module.py"
    bad_file.write_text(source, encoding="utf-8")

    code, output = _ruff_check(bad_file)

    assert code != 0, f"expected ruff to fail for source {source!r}, got exit 0:\n{output}"
    assert expected_code in output, (
        f"expected rule code containing {expected_code!r} in output:\n{output}"
    )
    if expected_msg_substring:
        assert expected_msg_substring in output, (
            f"expected message substring {expected_msg_substring!r} in output:\n{output}"
        )
