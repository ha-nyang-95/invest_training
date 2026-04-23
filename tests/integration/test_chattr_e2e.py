"""Story 1.6 AC-3 — real chattr E2E on WSL2 ext4.

Prerequisites (operator-side, only on Trading PC WSL2 self-hosted runner):
  * WSL2 Ubuntu 24.04+ with `/usr/sbin/chattr` and `/usr/bin/lsattr` installed.
  * sudoers NOPASSWD drop-in installed via
    `infra/systemd/athena-readonly-mount.install.sh` so `sudo chattr` runs
    non-interactively.
  * tmp_path resolves to ext4 (WSL2 home is ext4 by default).

These tests intentionally call the real `SubprocessChattrExecutor`. On
Windows + non-Linux dev hosts they skip — the unit-level `FakeChattrExecutor`
suite (test_readonly_mount.py) covers the same logic deterministically.

The tests do NOT touch /var/lib/athena/policy/ — every protected_paths arg
goes through tmp_path, and the path validator in ReadonlyMountController
is patched out for these isolated tmp paths via a controller subclass.
"""

from __future__ import annotations

import errno
import os
import subprocess
import sys
from pathlib import PurePosixPath
from typing import Any

import pytest
from athena.alpha_defense.f5.readonly_mount import (
    MountState,
    ReadonlyMountController,
    SubprocessChattrExecutor,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        sys.platform == "win32",
        reason="chattr/lsattr are Linux-only — WSL2 ext4 required",
    ),
]


def _ensure_chattr_available() -> None:
    """Skip (rather than fail) when chattr is missing — non-WSL2 Linux CI."""
    if not os.path.exists("/usr/sbin/chattr"):
        pytest.skip("/usr/sbin/chattr missing — WSL2 Ubuntu prerequisite unmet")


def _ensure_sudo_chattr_nopasswd() -> None:
    """Probe `sudo -n /usr/sbin/chattr -V` — `-n` fails fast if a password is
    required. Skip rather than block tests on sudoers misconfiguration.
    """
    proc = subprocess.run(  # noqa: S603 — argv list, no shell
        ["sudo", "-n", "/usr/sbin/chattr", "-V"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=5,
        check=False,
    )
    if proc.returncode != 0:
        pytest.skip(
            "sudoers NOPASSWD for /usr/sbin/chattr not configured — "
            "run infra/systemd/athena-readonly-mount.install.sh first"
        )


class _LooseValidationController(ReadonlyMountController):
    """Controller subclass that bypasses the `/var/lib/athena/policy/` path
    validator so we can exercise real chattr against tmp_path-rooted files.

    The validator is a guardrail for production callers; production paths
    are still locked to the protected root via DEFAULT_PROTECTED_PATHS.
    """

    def __init__(self, executor: Any, paths: tuple[PurePosixPath, ...]) -> None:
        self._executor = executor
        self._protected_paths = paths


@pytest.fixture
def policy_files(tmp_path: Any) -> tuple[PurePosixPath, PurePosixPath]:
    _ensure_chattr_available()
    _ensure_sudo_chattr_nopasswd()
    a = tmp_path / "policy.toml"
    b = tmp_path / "flag_registry.toml"
    a.write_text("# tmp policy\n", encoding="utf-8")
    b.write_text("# tmp flag registry\n", encoding="utf-8")
    return PurePosixPath(str(a)), PurePosixPath(str(b))


@pytest.fixture
def controller(
    policy_files: tuple[PurePosixPath, PurePosixPath],
) -> Any:
    ctl = _LooseValidationController(SubprocessChattrExecutor(), policy_files)
    yield ctl
    # Always unlock at teardown so a failed test does not leave tmp_path
    # immutable (tmp_path cleanup itself would otherwise fail with EPERM).
    try:
        ctl.unlock()
    except Exception:  # noqa: BLE001, S110 — best-effort teardown
        pass


def test_lock_then_write_fails_with_eperm(
    controller: Any, policy_files: tuple[PurePosixPath, PurePosixPath]
) -> None:
    a, _b = policy_files
    transition = controller.lock()
    assert transition.new_state is MountState.LOCKED

    # Write attempt: open(..., "w") on Linux returns EPERM when the inode has
    # the immutable flag set, even for the file owner. PermissionError wraps EPERM.
    with pytest.raises(PermissionError) as exc:
        with open(str(a), "w", encoding="utf-8") as fh:
            fh.write("tampered")
    assert exc.value.errno == errno.EPERM

    # Even `sudo rm` fails because immutable blocks unlink.
    rm = subprocess.run(  # noqa: S603
        ["sudo", "-n", "rm", "-f", str(a)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=5,
        check=False,
    )
    assert rm.returncode != 0, "rm -f succeeded on immutable file — chattr +i broken?"

    # Unlock restores write capability.
    controller.unlock()
    with open(str(a), "w", encoding="utf-8") as fh:
        fh.write("post-unlock OK")


def test_idempotent_lock_unlock_cycle(controller: Any) -> None:
    first_lock = controller.lock()
    assert first_lock.new_state is MountState.LOCKED
    second_lock = controller.lock()
    assert second_lock.new_state is MountState.LOCKED
    assert all(v == "already" for v in second_lock.per_file_results.values())

    first_unlock = controller.unlock()
    assert first_unlock.new_state is MountState.UNLOCKED
    second_unlock = controller.unlock()
    assert second_unlock.new_state is MountState.UNLOCKED
    assert all(v == "already" for v in second_unlock.per_file_results.values())


def test_git_revert_blocked_during_lock(
    controller: Any, policy_files: tuple[PurePosixPath, PurePosixPath], tmp_path: Any
) -> None:
    """End-to-end Story 1.6 use case: a git checkout into the locked path
    must fail. We only verify the underlying primitive — `cp -f` on an
    immutable target — because driving git here adds tooling overhead with
    no extra coverage of F5 itself.
    """
    a, _b = policy_files
    controller.lock()
    new_content = tmp_path / "new_policy.toml"
    new_content.write_text("# would-be replacement\n", encoding="utf-8")

    # cp -f against immutable target: cp tries to truncate/overwrite which
    # fails with EPERM. Operators experience the same with `git checkout`.
    cp = subprocess.run(  # noqa: S603
        ["cp", "-f", str(new_content), str(a)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=5,
        check=False,
    )
    assert cp.returncode != 0
    # Original content preserved.
    assert "would-be replacement" not in a.read_text(encoding="utf-8")  # type: ignore[attr-defined]


def test_end_to_end_market_cycle(
    controller: Any, policy_files: tuple[PurePosixPath, PurePosixPath]
) -> None:
    """Story 1.6 hero scenario — full market-day rhythm in one test.

    07:00 UNLOCKED edit → 09:00 lock → 12:00 write rejected → 15:30 unlock
    → 17:00 edit OK.
    """
    a, _b = policy_files
    # 07:00 — UNLOCKED, edit allowed.
    with open(str(a), "w", encoding="utf-8") as fh:
        fh.write("morning edit\n")

    # 09:00 — lock.
    lock_t = controller.lock()
    assert lock_t.new_state is MountState.LOCKED

    # 12:00 — write rejected.
    with pytest.raises(PermissionError):
        with open(str(a), "w", encoding="utf-8") as fh:
            fh.write("intra-day tamper")

    # 15:30 — unlock.
    unlock_t = controller.unlock()
    assert unlock_t.new_state is MountState.UNLOCKED

    # 17:00 — edit allowed again.
    with open(str(a), "w", encoding="utf-8") as fh:
        fh.write("evening edit\n")
    assert a.read_text(encoding="utf-8") == "evening edit\n"  # type: ignore[attr-defined]
