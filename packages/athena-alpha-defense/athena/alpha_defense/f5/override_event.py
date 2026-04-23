"""OVERRIDE_ATTEMPT event contract — Story 1.6 AC-4.

Story 3.5 (inotify watcher) emits this dataclass when someone tries to
write/delete a protected file inside the LOCKED window. Story 3.1
(anti_ego_events SHA-256 chain) persists `dataclasses.asdict(event)` as the
canonical-JSON `payload_json` column.

This module is the contract surface only — no inotify code, no DuckDB code.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import PurePosixPath
from typing import Literal

# `/var/lib/athena/policy/` — kept as a string here (no Path coupling) because
# the event contract should validate without importing readonly_mount.py and
# pulling in subprocess. The path is short enough that string compare is fine.
_PROTECTED_ROOT_STR = "/var/lib/athena/policy"

InotifyEventMask = Literal["IN_MODIFY", "IN_ATTRIB", "IN_DELETE", "IN_MOVED_FROM"]
MountStateAtAttempt = Literal["LOCKED", "UNLOCKED", "PARTIAL"]


@dataclass(frozen=True, slots=True)
class OverrideAttemptEvent:
    """A single attempt to mutate a protected policy file.

    Invariants enforced in `__post_init__`:
      * `attempted_at_utc` MUST be timezone-aware. BaseDTO (Story 1.4
        Invariant #1) requires UTC; we mirror that without depending on
        Pydantic so the contract stays import-light.
      * `target_path` MUST live under `/var/lib/athena/policy/`. Any other
        path is a bug in the watcher (it should only watch the protected
        root) and we fail loudly rather than persist garbage.
      * `attempter_uid` is unrestricted in range so root (uid=0) attempts
        also persist — F5 considers root a potential attacker (chattr +i
        blocks root writes too, per architecture.md D9).

    `attempter_pid` is optional because inotify alone cannot identify the
    writing process; a future audit-subsystem integration (V1.1+) may fill
    it in.
    """

    attempted_at_utc: datetime
    target_path: PurePosixPath
    inotify_event_mask: InotifyEventMask
    attempter_uid: int
    attempter_pid: int | None
    mount_state_at_attempt: MountStateAtAttempt

    def __post_init__(self) -> None:
        if self.attempted_at_utc.tzinfo is None:
            raise ValueError(
                "OverrideAttemptEvent.attempted_at_utc must be timezone-aware (UTC). "
                "Naive datetimes break canonical JSON serialization in Story 3.1's "
                "anti_ego_events SHA-256 chain."
            )
        # Post-CR fix (2026-04-23): reject `..` before the prefix check.
        # `PurePosixPath` does not normalise `..`, so `/var/lib/athena/policy/
        # ../../../etc/shadow` would have passed the pre-patch `startswith`
        # guard — the watcher (Story 3.5) should only supply normalised paths
        # anyway, so we fail loudly on any `..` segment.
        if ".." in self.target_path.parts:
            raise ValueError(
                f"OverrideAttemptEvent.target_path={self.target_path!s} contains "
                "'..' traversal segments; inotify watcher must supply normalised paths."
            )
        # str() avoids a Path.relative_to ValueError swallow + re-raise dance —
        # the protected-root prefix check is the same semantics with a clearer
        # error.
        if not str(self.target_path).startswith(_PROTECTED_ROOT_STR + "/"):
            raise ValueError(
                f"OverrideAttemptEvent.target_path={self.target_path!s} is outside "
                f"{_PROTECTED_ROOT_STR}/. The inotify watcher (Story 3.5) should "
                "only watch the protected root."
            )
