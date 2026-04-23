"""F5 readonly-mount controller — chattr +i / -i wrapper for policy files.

Story 1.6 AC-1. Source-of-truth invariants (per story Dev Notes):

* `DEFAULT_PROTECTED_PATHS` is locked to 2 paths under `/var/lib/athena/policy/`
  for V1.0; new policy files (e.g. tax_schedule.toml in Story 6.5) extend the
  tuple via Change Control + sudoers drop-in update.
* All chattr access flows through `ChattrExecutor` Protocol — direct
  `subprocess.run(["chattr", ...])` calls are forbidden so unit tests can
  inject `FakeChattrExecutor` and Story 3.5's inotify watcher can mock state.
* `MountState` is a 3-state StrEnum (`LOCKED` / `UNLOCKED` / `PARTIAL`); PARTIAL
  is the edge case where 2 protected files have diverged immutability.
* `lock()` / `unlock()` are idempotent — already-immutable paths are skipped
  with `per_file_results[p]="already"`, no chattr call. Reason: systemd
  `Restart=on-failure` may double-fire and manual `systemctl start` may collide.
* Partial failure handling: an executor exception on one path leaves the
  others' state intact and returns `MountState.PARTIAL`; the next `lock()`
  retries only the failed paths (recovery path).
* `protected_paths` constructor arg is validated to be under
  `/var/lib/athena/policy/` (architecture.md Gap-3 ext4 path rule). Other
  paths raise `ValueError`.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import PurePosixPath
from typing import ClassVar, Literal, Protocol

# Per-file outcome literal, used for both lock() and unlock().
PerFileResult = Literal["ok", "already", "skipped", "error"]

# chattr targets are always WSL2 ext4 (architecture.md Gap-3 line 1211-1217),
# so the protected-path type is `PurePosixPath` rather than the platform-
# dependent `pathlib.Path`. This keeps `str(path)` forward-slash on Windows
# dev hosts so dry-run JSON output and test assertions match prod semantics
# byte-for-byte.

# Path validation root — architecture.md Gap-3 (line 1211-1217): chattr is
# ext4-only, so protected files must live on WSL2 native ext4, not /mnt/c.
_PROTECTED_ROOT = PurePosixPath("/var/lib/athena/policy")

# subprocess timeout for chattr/lsattr calls. 10s is generous: chattr on a
# single 4KB file completes in <1ms; the budget covers a stuck filesystem
# without hanging the systemd unit indefinitely.
_SUBPROCESS_TIMEOUT_SECONDS = 10

# `lsattr -d <path>` output format: 16-char attr string + space + path.
# 'i' at offset 4 within the attr block means immutable. Parsing the
# attr column is more robust than substring 'i' which would false-positive
# on filenames containing 'i'.
_LSATTR_FLAGS_RE = re.compile(r"^(?P<flags>\S+)\s+\S+")


class ChattrExecutor(Protocol):
    """Strategy abstraction for chattr +i / -i / lsattr.

    Production: `SubprocessChattrExecutor` shells out to `sudo chattr`.
    Tests: `FakeChattrExecutor` keeps a `dict[Path, bool]` in memory.
    CLI dry-run: `DryRunChattrExecutor` echoes intent to stdout without
    mutating real state.

    Story 3.5's inotify watcher will inject mocks via the same Protocol so
    OVERRIDE_ATTEMPT events can be triggered in tests without touching ext4.
    """

    def set_immutable(self, path: PurePosixPath) -> None: ...

    def clear_immutable(self, path: PurePosixPath) -> None: ...

    def is_immutable(self, path: PurePosixPath) -> bool: ...


def _run_sudo_chattr(args: list[str]) -> None:
    """Internal helper — `sudo /usr/sbin/chattr <args>` with hardened invocation.

    Story 1.5 Debug Log #1 (cp949 encoding trap) requires explicit utf-8 +
    errors="replace". sudoers NOPASSWD drop-in restricts the path to
    `/usr/sbin/chattr` with exactly the +i / -i pairs declared in
    `infra/systemd/sudoers.d/athena-readonly-mount` (Task 2.2).
    """
    cmd = ["sudo", "/usr/sbin/chattr", *args]
    subprocess.run(  # noqa: S603 — argv list, no shell, sudoers-pinned binary
        cmd,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=_SUBPROCESS_TIMEOUT_SECONDS,
    )


def _run_lsattr(path: PurePosixPath) -> str:
    """Return raw `lsattr -d <path>` stdout (single line)."""
    result = subprocess.run(  # noqa: S603 — argv list, no shell
        ["/usr/bin/lsattr", "-d", str(path)],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=_SUBPROCESS_TIMEOUT_SECONDS,
    )
    return result.stdout


def _flags_contain_immutable(lsattr_output: str) -> bool:
    """Parse `lsattr -d` output and return True iff the 'i' flag is set.

    Output shape: `----i---------e----- /path/to/file`. The flag column is
    fixed-width but its width has grown across util-linux releases, so we
    match the leading non-whitespace token rather than a fixed offset.
    """
    match = _LSATTR_FLAGS_RE.match(lsattr_output.strip())
    if match is None:
        return False
    return "i" in match.group("flags")


class SubprocessChattrExecutor:
    """Real chattr executor — Linux ext4 only.

    Import succeeds on any platform; the first `set_immutable`/`clear_immutable`
    call on a non-Linux host fails when sudo or chattr is missing. Per Story
    1.6 Architecture Patterns, no import-time platform guard — runtime
    failure is the chosen degradation mode (architecture.md AR-SEC3).
    """

    def set_immutable(self, path: PurePosixPath) -> None:
        _run_sudo_chattr(["+i", str(path)])

    def clear_immutable(self, path: PurePosixPath) -> None:
        _run_sudo_chattr(["-i", str(path)])

    def is_immutable(self, path: PurePosixPath) -> bool:
        return _flags_contain_immutable(_run_lsattr(path))


class DryRunChattrExecutor:
    """CLI `--dry-run` executor — production-side fake that echoes intent.

    Distinct from `FakeChattrExecutor` (tests/conftest.py): this is invoked
    from the CLI when an operator wants to preview lock/unlock without
    privilege escalation. State is held in-memory for the lifetime of the
    process so a `--dry-run lock` followed by `--dry-run status` reports
    LOCKED. The Story 1.5 `init_external_backup.sh` `[dry-run]` prefix
    convention is preserved on stdout.
    """

    def __init__(self) -> None:
        self._state: dict[PurePosixPath, bool] = {}

    def set_immutable(self, path: PurePosixPath) -> None:
        # CLI prints the [dry-run] prefix at the action layer (cli.py); this
        # method only mutates the in-memory state so subsequent is_immutable()
        # queries within the same process return the dry-run intent.
        self._state[path] = True

    def clear_immutable(self, path: PurePosixPath) -> None:
        self._state[path] = False

    def is_immutable(self, path: PurePosixPath) -> bool:
        return self._state.get(path, False)


class MountState(StrEnum):
    """Aggregate state of the protected-path set."""

    LOCKED = "LOCKED"
    UNLOCKED = "UNLOCKED"
    PARTIAL = "PARTIAL"


@dataclass(frozen=True, slots=True)
class LockTransition:
    """Result of a single `lock()` or `unlock()` call.

    Persisted nowhere directly in Story 1.6 — Story 1.9 may surface this
    as a Prometheus event counter and Story 3.1 may persist OVERRIDE_ATTEMPT
    events (separate dataclass `OverrideAttemptEvent`).
    """

    transition: Literal["lock", "unlock"]
    target_paths: tuple[PurePosixPath, ...]
    timestamp_utc: datetime
    previous_state: MountState
    new_state: MountState
    per_file_results: dict[PurePosixPath, PerFileResult] = field(default_factory=dict)
    error_message: str | None = None


def _validate_protected_paths(paths: tuple[PurePosixPath, ...]) -> None:
    """Refuse paths outside `/var/lib/athena/policy/` — enforces architecture.md
    Gap-3 (chattr requires ext4, /mnt/c excluded) and prevents a caller from
    accidentally locking system files like /etc/passwd.
    """
    for p in paths:
        try:
            p.relative_to(_PROTECTED_ROOT)
        except ValueError as exc:
            raise ValueError(
                f"Protected path {p!s} is outside {_PROTECTED_ROOT!s}; "
                "F5 only manages files under the policy root (architecture.md Gap-3)."
            ) from exc


def _classify_state(immutable_count: int, total: int) -> MountState:
    if immutable_count == 0:
        return MountState.UNLOCKED
    if immutable_count == total:
        return MountState.LOCKED
    return MountState.PARTIAL


class ReadonlyMountController:
    """High-level lock/unlock coordinator over the protected-path set.

    Idempotency:
      * `lock()` while already LOCKED → all paths report "already", no chattr.
      * `unlock()` while already UNLOCKED → all paths report "already".
      * Partial state recovers on the next `lock()` (already paths skipped,
        failed paths retried).

    Failure semantics:
      * Per-path executor exceptions are caught and recorded as "error" in
        `per_file_results`; the overall transition still returns and the
        new aggregate state is computed from post-call `is_immutable` reads.
      * `error_message` summarises the first failure for systemd journal /
        Prometheus alerting hooks (Story 1.9).
    """

    DEFAULT_PROTECTED_PATHS: ClassVar[tuple[PurePosixPath, ...]] = (
        PurePosixPath("/var/lib/athena/policy/policy.toml"),
        PurePosixPath("/var/lib/athena/policy/flag_registry.toml"),
    )

    def __init__(
        self,
        executor: ChattrExecutor,
        protected_paths: tuple[PurePosixPath, ...] | None = None,
    ) -> None:
        paths = protected_paths if protected_paths is not None else self.DEFAULT_PROTECTED_PATHS
        if not paths:
            raise ValueError("ReadonlyMountController requires at least one protected path.")
        _validate_protected_paths(paths)
        self._executor = executor
        self._protected_paths = paths

    @property
    def protected_paths(self) -> tuple[PurePosixPath, ...]:
        return self._protected_paths

    def status(self) -> MountState:
        immutable_count = sum(1 for p in self._protected_paths if self._executor.is_immutable(p))
        return _classify_state(immutable_count, len(self._protected_paths))

    def lock(self) -> LockTransition:
        return self._transition(target_immutable=True)

    def unlock(self) -> LockTransition:
        return self._transition(target_immutable=False)

    def _transition(self, *, target_immutable: bool) -> LockTransition:
        previous = self.status()
        per_file: dict[PurePosixPath, PerFileResult] = {}
        first_error: str | None = None

        for path in self._protected_paths:
            currently_immutable = self._executor.is_immutable(path)
            if currently_immutable == target_immutable:
                per_file[path] = "already"
                continue
            try:
                if target_immutable:
                    self._executor.set_immutable(path)
                else:
                    self._executor.clear_immutable(path)
                per_file[path] = "ok"
            except Exception as exc:  # noqa: BLE001 — record + continue
                per_file[path] = "error"
                if first_error is None:
                    first_error = f"{path}: {type(exc).__name__}: {exc}"

        new_state = self.status()
        return LockTransition(
            transition="lock" if target_immutable else "unlock",
            target_paths=self._protected_paths,
            timestamp_utc=datetime.now(UTC),
            previous_state=previous,
            new_state=new_state,
            per_file_results=per_file,
            error_message=first_error,
        )
