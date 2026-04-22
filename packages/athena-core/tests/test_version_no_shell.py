"""AST inspection: athena.core.version MUST NOT call shell at runtime (AR-COM4 / AC-5).

The Hatchling build hook (packages/athena-core/hatch_build.py) is the ONLY
sanctioned source of git SHA. Any runtime invocation of forbidden modules
violates the principle of "런타임 shell 호출 overhead 0".

This test inspects the AST (not raw source text) so that documentation
mentioning these names — e.g. in docstrings — does not produce false positives.

Defense-in-depth:
1. Forbidden top-level imports (`import subprocess`, `import shutil`).
2. Forbidden `from os import <callable>` aliases (closes `from os import system` bypass).
3. Forbidden dotted calls (`subprocess.run`, `os.system`, ...).
4. Forbidden bare-name calls (`system(...)`, `popen(...)`) that can be set up via
   `from os import system` and would otherwise escape the dotted-call check.
"""

from __future__ import annotations

import ast
from pathlib import Path

VERSION_FILE: Path = Path(__file__).resolve().parent.parent / "athena" / "core" / "version.py"

FORBIDDEN_TOPLEVEL_MODULES = frozenset({"subprocess", "shutil"})

# `from os import <name>` for any of these attributes is treated as equivalent
# to an `os.<name>` runtime call — it bypasses the dotted-call check otherwise.
FORBIDDEN_FROM_OS = frozenset(
    {
        "system",
        "popen",
        "execv",
        "execve",
        "execl",
        "execle",
        "execlp",
        "execlpe",
        "execvp",
        "execvpe",
        "spawnl",
        "spawnle",
        "spawnlp",
        "spawnlpe",
        "spawnv",
        "spawnve",
        "spawnvp",
        "spawnvpe",
    }
)

FORBIDDEN_DOTTED_CALLS = frozenset(
    {
        "subprocess.run",
        "subprocess.Popen",
        "subprocess.call",
        "subprocess.check_call",
        "subprocess.check_output",
        "os.popen",
        "os.system",
        "os.execv",
        "os.execve",
        "os.spawnl",
        "os.spawnv",
    }
)

# Bare-name call set (triggered by `from <module> import <name>; <name>(...)`).
# "run" is excluded because it is too common a method name (pytest.run, app.run, ...)
# and would produce false positives in legitimate code. The import check above
# already prevents `from subprocess import run` because `subprocess` is forbidden.
FORBIDDEN_BARE_CALLS = frozenset(
    {
        "system",
        "popen",
        "execv",
        "execve",
        "execl",
        "execle",
        "execlp",
        "execlpe",
        "execvp",
        "execvpe",
        "spawnl",
        "spawnle",
        "spawnlp",
        "spawnlpe",
        "spawnv",
        "spawnve",
        "spawnvp",
        "spawnvpe",
    }
)


def _collect_imports(tree: ast.AST) -> list[str]:
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module is not None:
                found.append(node.module)
    return found


def _collect_os_from_aliases(tree: ast.AST) -> list[str]:
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "os":
            for alias in node.names:
                found.append(alias.name)
    return found


def _collect_dotted_calls(tree: ast.AST) -> list[str]:
    """Walk ast.Call nodes; report `<Name>.<attr>` patterns (e.g. subprocess.run, os.popen)."""
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            attr = node.func
            if isinstance(attr.value, ast.Name):
                found.append(f"{attr.value.id}.{attr.attr}")
    return found


def _collect_bare_name_calls(tree: ast.AST) -> list[str]:
    """Walk ast.Call nodes; report bare `<Name>(...)` callee identifiers."""
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            found.append(node.func.id)
    return found


def test_version_file_exists() -> None:
    assert VERSION_FILE.is_file(), f"expected {VERSION_FILE} to exist"


def test_version_module_has_no_forbidden_imports() -> None:
    tree = ast.parse(VERSION_FILE.read_text(encoding="utf-8"))
    imports = _collect_imports(tree)
    violations = [imp for imp in imports if imp.split(".")[0] in FORBIDDEN_TOPLEVEL_MODULES]
    assert not violations, (
        f"athena.core.version imports forbidden modules {violations}; "
        f"per AR-COM4, only the Hatchling build hook may invoke shell."
    )


def test_version_module_has_no_forbidden_from_os_aliases() -> None:
    tree = ast.parse(VERSION_FILE.read_text(encoding="utf-8"))
    aliases = _collect_os_from_aliases(tree)
    violations = [a for a in aliases if a in FORBIDDEN_FROM_OS]
    assert not violations, (
        f"athena.core.version uses `from os import {violations}`; these aliases are "
        f"equivalent to runtime shell calls and bypass the dotted-call check."
    )


def test_version_module_has_no_forbidden_calls() -> None:
    tree = ast.parse(VERSION_FILE.read_text(encoding="utf-8"))
    calls = _collect_dotted_calls(tree)
    violations = [call for call in calls if call in FORBIDDEN_DOTTED_CALLS]
    assert not violations, (
        f"athena.core.version contains forbidden call patterns {violations}; "
        f"per AR-COM4, runtime shell invocation is banned."
    )


def test_version_module_has_no_forbidden_bare_calls() -> None:
    tree = ast.parse(VERSION_FILE.read_text(encoding="utf-8"))
    bare = _collect_bare_name_calls(tree)
    violations = [name for name in bare if name in FORBIDDEN_BARE_CALLS]
    assert not violations, (
        f"athena.core.version contains bare-name calls {violations} that match "
        f"forbidden shell callables; adversarial `from os import system; system(...)` "
        f"bypass is blocked here."
    )
