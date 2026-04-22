"""AST inspection: athena.core.keyring_client MUST NOT call shell (Story 1.2 AC-2).

Mirror of `test_version_no_shell.py` — same layered defense, extended to
close reflection-based bypasses surfaced in Story 1.2 review (2026-04-22):

1. Forbidden top-level imports (`import subprocess`, `import shutil`,
   `import importlib`).
2. Forbidden `from os import <callable>` aliases (closes `from os import system`).
3. Forbidden dotted calls (`subprocess.run`, `os.system`, ...).
4. Forbidden bare-name calls (`system(...)`, `popen(...)`, `getattr(...)`,
   `__import__(...)`, `eval(...)`, `exec(...)`, `compile(...)`).

Rationale (architecture.md#NFR-S1 mapping, line 1009): the OS Keychain is
the only sanctioned secret-storage primitive. Any fallback to shell-based
secret retrieval (e.g. `subprocess.run(['security', 'find-generic-password', ...])`)
would bypass the keyring abstraction and defeat cross-platform uniformity.
The reflection ban closes `getattr(__import__('subprocess'), 'run')(...)`
and `eval("__import__('os').system('...')")`-style escapes.
"""

from __future__ import annotations

import ast
from pathlib import Path

KEYRING_CLIENT_FILE: Path = (
    Path(__file__).resolve().parent.parent / "athena" / "core" / "keyring_client.py"
)

# `importlib` is added alongside `subprocess`/`shutil` to block
# `importlib.import_module("subprocess").run(...)` reflection escape.
FORBIDDEN_TOPLEVEL_MODULES = frozenset({"subprocess", "shutil", "importlib"})

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

# Bare-name set — "run" excluded to avoid pytest.run / app.run false positives;
# the module-import ban above already prevents `from subprocess import run`.
# Reflection primitives (`getattr`, `__import__`, `eval`, `exec`, `compile`) are
# blocked wholesale for this module — the keyring client has no legitimate use
# for dynamic attribute or code evaluation, and allowing them reopens the shell
# bypass. If a future change needs reflection, lift the ban with an explicit
# Change Control entry documenting the reason.
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
        "getattr",
        "__import__",
        "eval",
        "exec",
        "compile",
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
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            attr = node.func
            if isinstance(attr.value, ast.Name):
                found.append(f"{attr.value.id}.{attr.attr}")
    return found


def _collect_bare_name_calls(tree: ast.AST) -> list[str]:
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            found.append(node.func.id)
    return found


def test_keyring_client_file_exists() -> None:
    assert KEYRING_CLIENT_FILE.is_file(), f"expected {KEYRING_CLIENT_FILE} to exist"


def test_keyring_client_has_no_forbidden_imports() -> None:
    tree = ast.parse(KEYRING_CLIENT_FILE.read_text(encoding="utf-8"))
    imports = _collect_imports(tree)
    violations = [imp for imp in imports if imp.split(".")[0] in FORBIDDEN_TOPLEVEL_MODULES]
    assert not violations, (
        f"athena.core.keyring_client imports forbidden modules {violations}; "
        f"per architecture.md#NFR-S1 the keyring library is the only sanctioned backend."
    )


def test_keyring_client_has_no_forbidden_from_os_aliases() -> None:
    tree = ast.parse(KEYRING_CLIENT_FILE.read_text(encoding="utf-8"))
    aliases = _collect_os_from_aliases(tree)
    violations = [a for a in aliases if a in FORBIDDEN_FROM_OS]
    assert not violations, (
        f"athena.core.keyring_client uses `from os import {violations}`; aliases "
        f"bypass the dotted-call check and are treated as runtime shell calls."
    )


def test_keyring_client_has_no_forbidden_calls() -> None:
    tree = ast.parse(KEYRING_CLIENT_FILE.read_text(encoding="utf-8"))
    calls = _collect_dotted_calls(tree)
    violations = [call for call in calls if call in FORBIDDEN_DOTTED_CALLS]
    assert not violations, (
        f"athena.core.keyring_client contains forbidden call patterns {violations}; "
        f"runtime shell invocation is banned."
    )


def test_keyring_client_has_no_forbidden_bare_calls() -> None:
    tree = ast.parse(KEYRING_CLIENT_FILE.read_text(encoding="utf-8"))
    bare = _collect_bare_name_calls(tree)
    violations = [name for name in bare if name in FORBIDDEN_BARE_CALLS]
    assert not violations, (
        f"athena.core.keyring_client contains bare-name calls {violations} matching "
        f"forbidden shell callables; adversarial `from os import system; system(...)` blocked."
    )


def test_keyring_client_contains_actual_keyring_calls() -> None:
    """Guard against empty-file / stub regression: the four forbidden-call
    tests above all pass trivially for an empty or gutted `keyring_client.py`
    (zero AST nodes = zero violations). Prove the module actually wires the
    keyring primitives we depend on (Story 1.2 review P13, 2026-04-22)."""
    tree = ast.parse(KEYRING_CLIENT_FILE.read_text(encoding="utf-8"))
    calls = set(_collect_dotted_calls(tree))
    required = {"keyring.get_password", "keyring.set_password"}
    missing = required - calls
    assert not missing, (
        f"athena.core.keyring_client is missing required keyring calls {missing}; "
        f"the no-shell tests would otherwise pass trivially on an empty module."
    )
