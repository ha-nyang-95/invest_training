"""Unit tests for ReadonlyMountController + ChattrExecutor Protocol — Story 1.6 AC-1.

7 scenarios per the AC:
  1. lock() from UNLOCKED with both paths writable → LOCKED + per_file all "ok".
  2. Second lock() → all "already" (idempotent).
  3. lock() then unlock() → UNLOCKED + per_file all "ok".
  4. Executor raises on second path → PARTIAL + per_file_results[bad]="error".
  5. Recovery: a second lock() after PARTIAL → first path "already", second retried.
  6. PurePosixPath outside /var/lib/athena/policy/ → ValueError.
  7. status() returns LOCKED / UNLOCKED / PARTIAL correctly aggregated.
"""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any

import pytest
from athena.alpha_defense.f5.readonly_mount import (
    LockTransition,
    MountState,
    ReadonlyMountController,
)


class FakeChattrExecutor:
    """In-memory chattr fake — Protocol-compatible with ChattrExecutor.

    `fail_on_set` / `fail_on_clear` allow targeted failure injection per path
    so partial-state scenarios are deterministic.
    """

    def __init__(
        self,
        *,
        initial: dict[PurePosixPath, bool] | None = None,
        fail_on_set: set[PurePosixPath] | None = None,
        fail_on_clear: set[PurePosixPath] | None = None,
    ) -> None:
        self.state: dict[PurePosixPath, bool] = dict(initial or {})
        self.fail_on_set: set[PurePosixPath] = set(fail_on_set or set())
        self.fail_on_clear: set[PurePosixPath] = set(fail_on_clear or set())
        self.calls: list[tuple[str, PurePosixPath]] = []

    def set_immutable(self, path: PurePosixPath) -> None:
        self.calls.append(("set", path))
        if path in self.fail_on_set:
            raise PermissionError(f"injected failure: cannot set immutable on {path}")
        self.state[path] = True

    def clear_immutable(self, path: PurePosixPath) -> None:
        self.calls.append(("clear", path))
        if path in self.fail_on_clear:
            raise PermissionError(f"injected failure: cannot clear immutable on {path}")
        self.state[path] = False

    def is_immutable(self, path: PurePosixPath) -> bool:
        return self.state.get(path, False)


PATH_A = PurePosixPath("/var/lib/athena/policy/policy.toml")
PATH_B = PurePosixPath("/var/lib/athena/policy/flag_registry.toml")


def _controller(
    executor: Any,
    paths: tuple[PurePosixPath, ...] = (PATH_A, PATH_B),
) -> ReadonlyMountController:
    return ReadonlyMountController(executor, protected_paths=paths)


def test_lock_from_unlocked_marks_both_paths_ok() -> None:
    fake = FakeChattrExecutor()
    transition = _controller(fake).lock()

    assert isinstance(transition, LockTransition)
    assert transition.transition == "lock"
    assert transition.previous_state is MountState.UNLOCKED
    assert transition.new_state is MountState.LOCKED
    assert transition.per_file_results == {PATH_A: "ok", PATH_B: "ok"}
    assert fake.state == {PATH_A: True, PATH_B: True}
    assert transition.error_message is None


def test_second_lock_is_idempotent_no_chattr_calls() -> None:
    fake = FakeChattrExecutor(initial={PATH_A: True, PATH_B: True})
    transition = _controller(fake).lock()

    assert transition.previous_state is MountState.LOCKED
    assert transition.new_state is MountState.LOCKED
    assert transition.per_file_results == {PATH_A: "already", PATH_B: "already"}
    # Only the is_immutable probes should appear — no set_immutable calls.
    assert all(kind != "set" for kind, _ in fake.calls)


def test_unlock_after_lock_clears_both_paths() -> None:
    fake = FakeChattrExecutor(initial={PATH_A: True, PATH_B: True})
    transition = _controller(fake).unlock()

    assert transition.transition == "unlock"
    assert transition.previous_state is MountState.LOCKED
    assert transition.new_state is MountState.UNLOCKED
    assert transition.per_file_results == {PATH_A: "ok", PATH_B: "ok"}
    assert fake.state == {PATH_A: False, PATH_B: False}


def test_partial_failure_returns_partial_state_with_error_message() -> None:
    fake = FakeChattrExecutor(fail_on_set={PATH_B})
    transition = _controller(fake).lock()

    assert transition.previous_state is MountState.UNLOCKED
    assert transition.new_state is MountState.PARTIAL
    assert transition.per_file_results[PATH_A] == "ok"
    assert transition.per_file_results[PATH_B] == "error"
    assert transition.error_message is not None
    assert str(PATH_B) in transition.error_message
    assert fake.state[PATH_A] is True
    assert fake.state.get(PATH_B, False) is False


def test_recovery_lock_after_partial_skips_already_and_retries_failed() -> None:
    # Initial PARTIAL state: A locked, B unlocked.
    fake = FakeChattrExecutor(initial={PATH_A: True, PATH_B: False})
    transition = _controller(fake).lock()

    assert transition.previous_state is MountState.PARTIAL
    assert transition.new_state is MountState.LOCKED
    assert transition.per_file_results == {PATH_A: "already", PATH_B: "ok"}
    # PATH_A must NOT have received a set call this round.
    assert ("set", PATH_A) not in fake.calls
    assert ("set", PATH_B) in fake.calls


def test_path_outside_protected_root_raises_value_error() -> None:
    fake = FakeChattrExecutor()
    with pytest.raises(ValueError, match="/var/lib/athena/policy"):
        ReadonlyMountController(fake, protected_paths=(PurePosixPath("/etc/passwd"),))


def test_dotdot_traversal_path_rejected() -> None:
    """Post-CR fix (2026-04-23): `..` segments must be rejected explicitly —
    `PurePosixPath.relative_to` did not normalise them so paths like
    `/var/lib/athena/policy/../../../etc/shadow` previously passed validation.
    """
    fake = FakeChattrExecutor()
    with pytest.raises(ValueError, match=r"'\.\.'"):
        ReadonlyMountController(
            fake,
            protected_paths=(PurePosixPath("/var/lib/athena/policy/../../../etc/shadow"),),
        )


def test_status_is_resilient_to_probe_exceptions() -> None:
    """Post-CR fix (2026-04-23): `_transition` calls `status()` after the
    per-path loop. An executor whose `is_immutable` raises on a deleted file
    must not crash the whole transition — `status()` treats probe failures
    as "not immutable" for aggregation purposes.
    """

    class FlakyExecutor:
        def __init__(self) -> None:
            self._state: dict[PurePosixPath, bool] = {PATH_A: True}

        def set_immutable(self, path: PurePosixPath) -> None:  # pragma: no cover
            self._state[path] = True

        def clear_immutable(self, path: PurePosixPath) -> None:  # pragma: no cover
            self._state[path] = False

        def is_immutable(self, path: PurePosixPath) -> bool:
            if path == PATH_B:
                raise FileNotFoundError(f"simulated mid-transition deletion of {path}")
            return self._state.get(path, False)

    ctl = _controller(FlakyExecutor())
    # status() must not propagate the FileNotFoundError — PATH_A True + PATH_B
    # probe-fail counts as 1 immutable out of 2 → PARTIAL.
    assert ctl.status() is MountState.PARTIAL


def test_status_aggregates_three_states() -> None:
    # UNLOCKED — neither immutable.
    fake_unlocked = FakeChattrExecutor()
    assert _controller(fake_unlocked).status() is MountState.UNLOCKED

    # LOCKED — both immutable.
    fake_locked = FakeChattrExecutor(initial={PATH_A: True, PATH_B: True})
    assert _controller(fake_locked).status() is MountState.LOCKED

    # PARTIAL — one immutable, one not.
    fake_partial = FakeChattrExecutor(initial={PATH_A: True, PATH_B: False})
    assert _controller(fake_partial).status() is MountState.PARTIAL


def test_str_enum_str_semantics() -> None:
    # Story 1.6 Then-clause: `MountState.LOCKED` etc. must compare equal to
    # their string form so JSON serialization (cli.py) is trivial.
    assert MountState.LOCKED == "LOCKED"
    assert MountState.UNLOCKED == "UNLOCKED"
    assert MountState.PARTIAL == "PARTIAL"
