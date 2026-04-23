"""systemd ExecStopPost hook for athena-readonly-mount-{lock,unlock}.service.

Story 1.6 AC-2 Task 2.4. Translates `--exit-code` + `--action` into the
right MountState + successful_action arguments to
`athena.alpha_defense.f5.metrics.emit_readonly_mount_metric`.

systemd populates `$EXIT_STATUS` for ExecStopPost only; passing this from
ExecStartPost would resolve to an empty string. The wrapper accepts an
empty / non-numeric exit code and degrades to a sentinel rather than
crashing the metric emit (mirrors scripts/emit_logger_sync_metric.py).
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, cast

from athena.alpha_defense.f5.metrics import emit_readonly_mount_metric
from athena.alpha_defense.f5.readonly_mount import MountState

# An ExecStartPre exit-1 (non-trading day skip) is whitelisted via
# SuccessExitStatus=0 1 in the unit, so systemd reports $EXIT_STATUS=0 for
# the unit overall — but ExecStartPre's own non-zero short-circuits ExecStart.
# We treat exit 0 = transitioned, anything else = no-op / failure (mount
# state stays at whatever the prior emit recorded).
_SUCCESS_EXIT = 0
_UNKNOWN_EXIT = -1


def _parse_exit_code(raw: str) -> int:
    stripped = raw.strip()
    if not stripped:
        return _UNKNOWN_EXIT
    try:
        return int(stripped)
    except ValueError:
        # Non-numeric $EXIT_STATUS would crash argparse; treat as unknown so
        # the metric still lands and observability picks up "exit -1" alerts.
        return _UNKNOWN_EXIT


def _state_for(action: str, exit_code: int) -> MountState:
    """Translate (action, exit) → resulting MountState.

    On a non-success exit we cannot positively assert PARTIAL vs PRE-state
    without re-running `f5 status`; PARTIAL is the safe pessimistic guess
    so Story 1.9 alert rules will fire and the operator can investigate.
    """
    if exit_code != _SUCCESS_EXIT:
        return MountState.PARTIAL
    if action == "lock":
        return MountState.LOCKED
    return MountState.UNLOCKED


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="emit_readonly_mount_metric",
        description="Translate systemd ExecStopPost args to f5.metrics.emit_readonly_mount_metric.",
    )
    parser.add_argument("--action", choices=["lock", "unlock"], required=True)
    parser.add_argument("--exit-code", type=_parse_exit_code, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    state = _state_for(args.action, args.exit_code)
    successful_action: Literal["lock", "unlock"] | None = (
        cast(Literal["lock", "unlock"], args.action) if args.exit_code == _SUCCESS_EXIT else None
    )
    emit_readonly_mount_metric(
        state=state,
        last_transition_ts=datetime.now(UTC),
        output_path=args.output,
        successful_action=successful_action,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
