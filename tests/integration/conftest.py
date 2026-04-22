"""Shared fixtures for Story 1.3 integration tests (Task 4.5 + Task 6.4)."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"


def _load_script_module(name: str) -> ModuleType:
    """Import a `scripts/<name>.py` file as a module.

    `scripts/` is intentionally not a Python package (Story 1.3 Dev Notes
    invariant #6), so tests load the module by path.
    """
    path = SCRIPTS_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def load_script(
    monkeypatch: pytest.MonkeyPatch,
) -> Callable[[str], ModuleType]:
    """Load a script module, restoring `sys.modules` on teardown.

    Without the monkeypatch cleanup, a stale `sys.modules[name]` from a
    prior test could leak into a later test that imports the same script
    without going through this fixture.
    """

    def _load(name: str) -> ModuleType:
        previous = sys.modules.get(name)
        module = _load_script_module(name)
        if previous is None:
            monkeypatch.delitem(sys.modules, name, raising=False)
        else:
            monkeypatch.setitem(sys.modules, name, previous)
        return module

    return _load


@pytest.fixture
def tmp_git_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Initialise a disposable git repo for CI-gate script tests.

    - master branch, commit.gpgsign disabled for speed.
    - chdir into the repo so `git log` targets it.
    - environment tuned for deterministic timestamps via GIT_{AUTHOR,COMMITTER}_DATE.
    """
    subprocess.run(
        ["git", "init", "-b", "master", str(tmp_path)],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    for key, value in (
        ("user.email", "ci-test@athena.local"),
        ("user.name", "Athena CI Test"),
        ("commit.gpgsign", "false"),
        ("tag.gpgsign", "false"),
    ):
        subprocess.run(
            ["git", "-C", str(tmp_path), "config", key, value],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    monkeypatch.chdir(tmp_path)
    yield tmp_path


def make_commit(
    repo: Path,
    subject: str,
    *,
    when: datetime | None = None,
    allow_empty: bool = True,
) -> str:
    """Create a commit with deterministic author/committer timestamp.

    Returns the full commit SHA.
    """
    env = {}
    if when is not None:
        ts = when.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S+0000")
        env = {"GIT_AUTHOR_DATE": ts, "GIT_COMMITTER_DATE": ts}
    cmd = ["git", "-C", str(repo), "commit", "-m", subject]
    if allow_empty:
        cmd.append("--allow-empty")
    subprocess.run(
        cmd,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**_base_env(), **env},
    )
    sha = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()
    return sha


def _base_env() -> dict[str, str]:
    import os

    # Windows git needs `USERPROFILE` / `APPDATA` / `LOCALAPPDATA` to locate
    # gitconfig and `TMP` / `TEMP` for temp-object writes; omitting them makes
    # `git commit` hang or fail on Windows-hosted runners.
    keep = {
        "PATH",
        "USER",
        "USERNAME",
        "LOGNAME",
        "HOME",
        "HOMEPATH",
        "SYSTEMROOT",
        "USERPROFILE",
        "APPDATA",
        "LOCALAPPDATA",
        "TMP",
        "TEMP",
        "TMPDIR",
    }
    return {k: v for k, v in os.environ.items() if k in keep}


@pytest.fixture
def commit() -> Callable[..., str]:
    """Expose make_commit as a fixture for concise test code."""
    return make_commit
