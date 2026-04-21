"""Regression — verify .importlinter contracts ACTUALLY DETECT illegal imports.

A passing baseline alone is insufficient: we must prove the contracts produce
failures when violated. Each test injects an illegal import into a package's
source tree, runs `lint-imports`, asserts the expected contract name appears in
the failure output, then restores the source tree (try/finally guarantees cleanup).

Story 1.1 AC-3 — "two negative regression tests assert deliberately added illegal
imports get detected by lint-imports".
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

REPO_ROOT: Path = Path(__file__).resolve().parents[2]


def _lint_imports_executable() -> str:
    # Prefer venv-local script next to the active interpreter
    venv_scripts = Path(sys.executable).parent
    for candidate in (venv_scripts / "lint-imports.exe", venv_scripts / "lint-imports"):
        if candidate.exists():
            return str(candidate)
    found = shutil.which("lint-imports")
    if found is None:
        pytest.skip("lint-imports console script not on PATH")
    return found


@contextmanager
def _inject_illegal_import(package_dir: Path, illegal_line: str) -> Iterator[Path]:
    """Drop a single .py file with the illegal import, yield its path, delete on exit."""
    bad_file = package_dir / "_lint_regression_only.py"
    if bad_file.exists():
        pytest.fail(f"unexpected stale fixture file {bad_file} - prior test failed to clean up")
    bad_file.write_text(f"# DELETE ME - lint-imports regression fixture\n{illegal_line}\n", encoding="utf-8")
    try:
        yield bad_file
    finally:
        bad_file.unlink(missing_ok=True)


def _run_lint_imports() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [_lint_imports_executable()],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_baseline_clean_scaffold_passes() -> None:
    """Sanity: with no injection, lint-imports must pass."""
    result = _run_lint_imports()
    assert result.returncode == 0, (
        f"baseline lint-imports failed (exit {result.returncode}):\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


@pytest.mark.parametrize(
    "package_subdir,illegal_import,expected_contract_substring",
    [
        # Forbidden: execution -> orchestrator (AR-BND2)
        (
            "packages/athena-execution/athena/execution",
            "import athena.orchestrator  # noqa",
            "execution MUST NOT import orchestrator",
        ),
        # Forbidden: core -> any other athena.* (core is leaf)
        (
            "packages/athena-core/athena/core",
            "import athena.feature_store  # noqa",
            "athena.core is a leaf",
        ),
        # Forbidden: alpha_defense -> execution
        (
            "packages/athena-alpha-defense/athena/alpha_defense",
            "import athena.execution  # noqa",
            "alpha_defense MUST NOT import execution",
        ),
    ],
    ids=["execution->orchestrator", "core->feature_store", "alpha->execution"],
)
def test_contract_detects_violation(
    package_subdir: str,
    illegal_import: str,
    expected_contract_substring: str,
) -> None:
    package_dir = REPO_ROOT / package_subdir
    assert package_dir.is_dir(), f"fixture target {package_dir} not found"

    with _inject_illegal_import(package_dir, illegal_import):
        result = _run_lint_imports()

    assert result.returncode != 0, (
        f"expected lint-imports to FAIL after injecting {illegal_import!r} "
        f"into {package_subdir}, but it passed:\n{result.stdout}"
    )
    assert expected_contract_substring in result.stdout, (
        f"expected contract '{expected_contract_substring}' in failure output, got:\n"
        f"{result.stdout}"
    )
