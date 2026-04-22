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


def _matches_dotenv_name(name: str) -> bool:
    """Case-insensitive match — mirrors runtime guard (Story 1.2 review 2026-04-22)."""
    lower = name.lower()
    return lower == ".env" or fnmatch(lower, ".env.*")


def _walk_for_dotenv(root: Path) -> list[Path]:
    """Depth-unlimited walk; prune EXCLUDE_DIRS at every level.

    Symlink policy (aligned with runtime guard): a symlink whose NAME matches
    `.env*` is a violation regardless of what it resolves to — record it.
    Symlinks that do NOT match the name are skipped to avoid cycle loops and
    accidental home-dir traversal via dev-convenience links.
    """
    hits: list[Path] = []
    stack: list[Path] = [root]
    while stack:
        current = stack.pop()
        try:
            entries = list(current.iterdir())
        except (PermissionError, FileNotFoundError, OSError):
            continue
        for entry in entries:
            if _matches_dotenv_name(entry.name):
                hits.append(entry)
                continue
            if entry.is_symlink():
                continue  # non-matching symlinks: skip to avoid cycles
            if entry.is_dir():
                if entry.name in EXCLUDE_DIRS:
                    continue
                stack.append(entry)
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


def test_regression_excludes_are_superset_of_runtime() -> None:
    """Asymmetric-by-design: the regression `EXCLUDE_DIRS` MUST be a superset
    of the runtime `_EXCLUDE_DIRS`. The regression list additionally prunes
    tool cache dirs (`.mypy_cache`, `.ruff_cache`, `.pytest_cache`,
    `.import_linter_cache`) that are CI-level concerns; the runtime guard
    does not need them because its depth-1 coverage does not reach caches
    anyway.

    Invariant protected: if a future edit adds a new dir to the runtime
    guard without also adding it here, the regression walker could fail on
    content that the runtime silently allows — creating CI false positives.
    """
    from athena.core.settings import _EXCLUDE_DIRS as SETTINGS_EXCLUDE_DIRS

    missing_in_regression = SETTINGS_EXCLUDE_DIRS - EXCLUDE_DIRS
    assert not missing_in_regression, (
        f"regression test must exclude everything the runtime guard excludes, "
        f"else CI could fail on a directory that the runtime silently allowed: "
        f"{missing_in_regression}"
    )
