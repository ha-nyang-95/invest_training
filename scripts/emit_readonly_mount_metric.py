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
from athena.alpha_defense.f5.readonly_mount import (
    MountState,
    ReadonlyMountController,
    SubprocessChattrExecutor,
)

# Gemini PR #13 review (2026-04-23, HIGH): unit files set
# `SuccessExitStatus=0 1` so that `check_trading_day.py` returning 1 on a
# KRX holiday counts as success. That means `$EXIT_STATUS` is ALWAYS 0 on
# a clean run — it can no longer tell us whether the transition actually
# fired. We read the real filesystem state via ReadonlyMountController
# instead, and only count the run as a "successful_action" when both
# $EXIT_STATUS=0 AND status() matches the requested action.
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


def _actual_state() -> MountState:
    """Read the real MountState via lsattr. On any unexpected failure
    (missing file, sudo denied, ext4 anomaly) we fall back to PARTIAL so
    Story 1.9's alert rule fires — better a false positive than silently
    reporting LOCKED when the mount is in an unknown state.
    """
    try:
        return ReadonlyMountController(SubprocessChattrExecutor()).status()
    except Exception:  # noqa: BLE001 — best-effort observability probe
        return MountState.PARTIAL


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="emit_readonly_mount_metric",
        description="Translate systemd ExecStopPost args to f5.metrics.emit_readonly_mount_metric.",
    )
    parser.add_argument("--action", choices=["lock", "unlock"], required=True)
    parser.add_argument("--exit-code", type=_parse_exit_code, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    state = _actual_state()
    target_state = MountState.LOCKED if args.action == "lock" else MountState.UNLOCKED
    is_actual_success = args.exit_code == _SUCCESS_EXIT and state is target_state
    successful_action: Literal["lock", "unlock"] | None = (
        cast(Literal["lock", "unlock"], args.action) if is_actual_success else None
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
