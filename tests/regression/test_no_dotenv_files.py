"""Regression — CI-level .env file ban across the entire workspace tree.

Scope: walks from repo root into EVERY subdirectory (except the explicit
exclude list) — deeper than the Story 1.2 import-time guard in
`athena.core.settings._ensure_no_dotenv_files`, which is depth-1 only.
This is the final defence: even if a .env gets accidentally buried under
`packages/*/fixtures/` or `docs/examples/`, this regression catches it.

Story 1.2 AC-3: no `.env` / `.env.*` file is allowed anywhere under the
workspace. NFR-S1 / PRD line 1020 — secrets belong only in the OS Keychain.

Design note on exclude list duplication: we intentionally do NOT import
`_EXCLUDE_DIRS` from `athena.core.settings`. The regression test's job is
to provide independent defence; sharing the list would allow a compromised
settings.py to silently widen the exclude set and leak .env files past CI.
Keep these two lists in sync manually — mismatches are caught by the
`test_exclude_lists_stay_in_sync` test below.
"""

from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path

REPO_ROOT: Path = Path(__file__).resolve().parents[2]

# Independently duplicated from athena.core.settings._EXCLUDE_DIRS
# (see module docstring above for rationale).
EXCLUDE_DIRS: frozenset[str] = frozenset(
    {
        ".venv",
        ".git",
        "_bmad",
        "_bmad-output",
        "node_modules",
        "build",
        "dist",
        "__pycache__",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
        ".import_linter_cache",
    }
)


def _is_dotenv_file(path: Path) -> bool:
    return path.is_file() and (path.name == ".env" or fnmatch(path.name, ".env.*"))


def _walk_for_dotenv(root: Path) -> list[Path]:
    """Depth-unlimited walk; prune EXCLUDE_DIRS at every level."""
    hits: list[Path] = []
    stack: list[Path] = [root]
    while stack:
        current = stack.pop()
        try:
            entries = list(current.iterdir())
        except (PermissionError, FileNotFoundError):
            continue
        for entry in entries:
            if entry.is_symlink():
                continue  # don't chase symlinks — avoids infinite loops
            if entry.is_dir():
                if entry.name in EXCLUDE_DIRS:
                    continue
                stack.append(entry)
            elif _is_dotenv_file(entry):
                hits.append(entry)
    return hits


def test_no_dotenv_files_in_workspace() -> None:
    hits = _walk_for_dotenv(REPO_ROOT)
    assert not hits, (
        f"NFR-S1 violation — found {len(hits)} .env / .env.* file(s):\n"
        + "\n".join(f"  - {p.relative_to(REPO_ROOT)}" for p in hits)
        + "\n\nSecrets MUST live only in the OS Keychain "
        "(athena.core.keyring_client). Remove these files or move their "
        "values into keyring via `set_secret` (dev bootstrap) or "
        "Windows Credential Manager / Seahorse (production)."
    )


def test_exclude_lists_stay_in_sync() -> None:
    """The runtime guard and the regression test MUST agree on the core
    exclude set (toolchain + BMAD dirs). The regression test adds cache
    directories (.mypy_cache, .ruff_cache, ...) that are CI-level concerns;
    the runtime guard does not need them because depth-1 coverage doesn't
    reach into caches anyway."""
    from athena.core.settings import _EXCLUDE_DIRS as SETTINGS_EXCLUDE_DIRS

    # Every dir the runtime guard excludes MUST also be excluded here.
    missing_in_regression = SETTINGS_EXCLUDE_DIRS - EXCLUDE_DIRS
    assert not missing_in_regression, (
        f"regression test must exclude everything the runtime guard excludes, "
        f"else CI could fail on a directory that the runtime silently allowed: "
        f"{missing_in_regression}"
    )
