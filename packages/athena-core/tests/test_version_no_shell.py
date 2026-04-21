"""AST inspection: athena.core.version MUST NOT call shell at runtime (AR-COM4 / AC-5).

The Hatchling build hook (packages/athena-core/hatch_build.py) is the ONLY
sanctioned source of git SHA. Any runtime invocation of forbidden modules
violates the principle of "런타임 shell 호출 overhead 0".

This test inspects the AST (not raw source text) so that documentation
mentioning these names — e.g. in docstrings — does not produce false positives.
"""

from __future__ import annotations

import ast
from pathlib import Path

VERSION_FILE: Path = Path(__file__).resolve().parent.parent / "athena" / "core" / "version.py"

FORBIDDEN_TOPLEVEL_MODULES = frozenset({"subprocess", "shutil"})

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


def _collect_dotted_calls(tree: ast.AST) -> list[str]:
    """Walk ast.Call nodes; report `<Name>.<attr>` patterns (e.g. subprocess.run, os.popen)."""
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            attr = node.func
            if isinstance(attr.value, ast.Name):
                found.append(f"{attr.value.id}.{attr.attr}")
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


def test_version_module_has_no_forbidden_calls() -> None:
    tree = ast.parse(VERSION_FILE.read_text(encoding="utf-8"))
    calls = _collect_dotted_calls(tree)
    violations = [call for call in calls if call in FORBIDDEN_DOTTED_CALLS]
    assert not violations, (
        f"athena.core.version contains forbidden call patterns {violations}; "
        f"per AR-COM4, runtime shell invocation is banned."
    )
