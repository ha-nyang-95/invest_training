"""Story 1.3 Task 4.5 — cooling gate + paper-replay marker integration tests.

Exercises `scripts/check_cooling.py` and `scripts/check_paper_replay_marker.py`
against a temporary git repo. Time is controlled via `_now_utc` monkeypatch
and commit timestamps via `GIT_AUTHOR_DATE` / `GIT_COMMITTER_DATE`.
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.integration

NOW = datetime(2026, 4, 22, 10, 0, 0, tzinfo=UTC)


def _run_script(script_name: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / f"{script_name}.py")],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def test_non_policy_head_cooling_gate_passes(
    tmp_git_repo: Path, commit: Callable[..., str]
) -> None:
    commit(tmp_git_repo, "feat: non-policy work")
    result = _run_script("check_cooling", tmp_git_repo)
    assert result.returncode == 0, result.stderr


def test_genesis_policy_commit_passes(
    tmp_git_repo: Path,
    commit: Callable[..., str],
    monkeypatch: pytest.MonkeyPatch,
    load_script: Callable[[str], ModuleType],
) -> None:
    commit(tmp_git_repo, "policy: genesis adjustment")
    check_cooling = load_script("check_cooling")
    monkeypatch.setattr(check_cooling, "_now_utc", lambda: NOW)
    assert check_cooling.main() == 0


def test_policy_after_cooled_window_passes(
    tmp_git_repo: Path,
    commit: Callable[..., str],
    monkeypatch: pytest.MonkeyPatch,
    load_script: Callable[[str], ModuleType],
) -> None:
    commit(tmp_git_repo, "policy: old", when=NOW - timedelta(hours=80))
    commit(tmp_git_repo, "policy: new", when=NOW)
    check_cooling = load_script("check_cooling")
    monkeypatch.setattr(check_cooling, "_now_utc", lambda: NOW)
    assert check_cooling.main() == 0


def test_policy_within_cooling_window_blocks(
    tmp_git_repo: Path,
    commit: Callable[..., str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    load_script: Callable[[str], ModuleType],
) -> None:
    commit(tmp_git_repo, "policy: old", when=NOW - timedelta(hours=10))
    commit(tmp_git_repo, "policy: new", when=NOW)
    check_cooling = load_script("check_cooling")
    monkeypatch.setattr(check_cooling, "_now_utc", lambda: NOW)
    rc = check_cooling.main()
    assert rc == 1
    err = capsys.readouterr().err.strip()
    payload = json.loads(err)
    assert payload["error_code"] == "POLICY_NOT_COOLED"
    # Expected window: 72h - 10h elapsed = exactly 62.0h (± 1s from commit
    # timestamp rounding via `%ct` integer seconds).
    assert 61.99 <= payload["cooling_remaining_hours"] <= 62.01
    # Alertmanager Medium payload must include the previous policy SHA for
    # forensic routing (spec AC-4 line 81).
    assert "prev_policy_sha" in payload
    assert len(payload["prev_policy_sha"]) == 7


def test_non_policy_head_paper_replay_passes(
    tmp_git_repo: Path, commit: Callable[..., str]
) -> None:
    commit(tmp_git_repo, "feat: non-policy work")
    result = _run_script("check_paper_replay_marker", tmp_git_repo)
    assert result.returncode == 0, result.stderr


def test_policy_head_without_marker_tag_blocks(
    tmp_git_repo: Path, commit: Callable[..., str]
) -> None:
    commit(tmp_git_repo, "policy: new release")
    result = _run_script("check_paper_replay_marker", tmp_git_repo)
    assert result.returncode == 1
    payload = json.loads(result.stderr.strip())
    assert payload["error_code"] == "PAPER_REPLAY_MISSING"
    assert payload["expected_tag"].startswith("paper-replay-ok/")
