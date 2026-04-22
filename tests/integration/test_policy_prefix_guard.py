"""Story 1.3 Task 6.4 — policy-prefix-guard commit-msg hook integration tests.

Covers four scenarios using `tmp_git_repo` fixture (shared with cooling gate
tests via conftest.py). Staged files are driven via real `git add` inside the
repo, and the commit-msg argument is provided as a temp file.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.integration


def _stage(repo: Path, rel: str, content: str = "placeholder\n") -> None:
    target = repo / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(repo), "add", rel],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def _run_guard(repo: Path, msg: str) -> subprocess.CompletedProcess[str]:
    msg_path = repo / ".git" / "COMMIT_EDITMSG_TEST"
    msg_path.write_text(msg, encoding="utf-8")
    return subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "check_policy_prefix.py"),
            str(msg_path),
        ],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def test_non_policy_file_with_non_policy_prefix_passes(tmp_git_repo: Path) -> None:
    _stage(tmp_git_repo, "README.md", "# readme\n")
    result = _run_guard(tmp_git_repo, "feat: update readme")
    assert result.returncode == 0, result.stderr


def test_policy_file_without_policy_prefix_blocks(tmp_git_repo: Path) -> None:
    _stage(tmp_git_repo, "config/policy.toml", "# placeholder\n")
    result = _run_guard(tmp_git_repo, "feat: adjust policy")
    assert result.returncode == 1
    assert "policy file(s) changed" in result.stderr


def test_policy_file_with_policy_prefix_passes(tmp_git_repo: Path) -> None:
    _stage(tmp_git_repo, "config/policy.toml", "# placeholder\n")
    result = _run_guard(tmp_git_repo, "policy: adjust theta_entry")
    assert result.returncode == 0, result.stderr


def test_empty_stage_with_policy_prefix_passes(tmp_git_repo: Path) -> None:
    result = _run_guard(tmp_git_repo, "policy: noop")
    assert result.returncode == 0, result.stderr
