"""F5 readonly-mount CLI — `python -m athena.alpha_defense.f5 {lock,unlock,status}`.

Story 1.6 AC-1 Task 1.4. Used by:
  * systemd `ExecStart=` for `athena-readonly-mount-lock.service` (Task 2.1)
  * operator manual recovery (operating_playbook.md `## Story 1.6`)
  * developer dry-run preview on Windows / non-WSL2 hosts

Exit codes:
  0  success — transitioned to or already at the requested state.
  1  failure — chattr returned non-zero, sudoers misconfigured, or partial state.
  2  usage error — bad subcommand / missing args (argparse default).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import TextIO

from athena.alpha_defense.f5.readonly_mount import (
    ChattrExecutor,
    DryRunChattrExecutor,
    LockTransition,
    MountState,
    ReadonlyMountController,
    SubprocessChattrExecutor,
)

_DRY_RUN_PREFIX = "[dry-run]"


def _build_executor(*, dry_run: bool) -> ChattrExecutor:
    return DryRunChattrExecutor() if dry_run else SubprocessChattrExecutor()


def _serialize_transition(transition: LockTransition) -> dict[str, object]:
    return {
        "transition": transition.transition,
        "previous_state": transition.previous_state.value,
        "new_state": transition.new_state.value,
        "timestamp_utc": transition.timestamp_utc.isoformat(),
        "target_paths": [str(p) for p in transition.target_paths],
        "per_file_results": {str(p): r for p, r in transition.per_file_results.items()},
        "error_message": transition.error_message,
    }


def _exit_code_for_state(state: MountState, expected: MountState) -> int:
    if state is expected:
        return 0
    return 1


def _print_dry_run_intent(
    *, transition: LockTransition, target_state: MountState, stream: TextIO
) -> None:
    """Echo a `[dry-run]` summary so operators can preview a `lock` / `unlock`
    without checking the JSON payload byte by byte.
    """
    stream.write(
        f"{_DRY_RUN_PREFIX} {transition.transition} "
        f"{transition.previous_state.value} -> {target_state.value}\n"
    )
    for path in transition.target_paths:
        result = transition.per_file_results.get(path, "skipped")
        stream.write(f"{_DRY_RUN_PREFIX}   {path} -> {result}\n")


def _cmd_lock(*, executor: ChattrExecutor, dry_run: bool, stream: TextIO) -> int:
    controller = ReadonlyMountController(executor)
    transition = controller.lock()
    if dry_run:
        _print_dry_run_intent(transition=transition, target_state=MountState.LOCKED, stream=stream)
    stream.write(json.dumps(_serialize_transition(transition), ensure_ascii=False) + "\n")
    return _exit_code_for_state(transition.new_state, MountState.LOCKED)


def _cmd_unlock(*, executor: ChattrExecutor, dry_run: bool, stream: TextIO) -> int:
    controller = ReadonlyMountController(executor)
    transition = controller.unlock()
    if dry_run:
        _print_dry_run_intent(
            transition=transition, target_state=MountState.UNLOCKED, stream=stream
        )
    stream.write(json.dumps(_serialize_transition(transition), ensure_ascii=False) + "\n")
    return _exit_code_for_state(transition.new_state, MountState.UNLOCKED)


def _cmd_status(*, executor: ChattrExecutor, stream: TextIO) -> int:
    controller = ReadonlyMountController(executor)
    state = controller.status()
    payload = {
        "state": state.value,
        "checked_paths": [str(p) for p in controller.protected_paths],
        "as_of_utc": datetime.now(UTC).isoformat(),
    }
    stream.write(json.dumps(payload, ensure_ascii=False) + "\n")
    # status is a read; PARTIAL is informational, not a failure here. Operators
    # rely on exit 0 to script `... status && echo ok`.
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m athena.alpha_defense.f5",
        description=(
            "F5 readonly-mount controller — chattr +i / -i for "
            "/var/lib/athena/policy/{policy,flag_registry}.toml."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Use DryRunChattrExecutor; no real chattr / sudo invocation.",
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="{lock,unlock,status}")
    sub.add_parser("lock", help="chattr +i on protected paths (idempotent).")
    sub.add_parser("unlock", help="chattr -i on protected paths (idempotent).")
    sub.add_parser("status", help="Report aggregate MountState as JSON.")
    return parser


def main(argv: Sequence[str] | None = None, *, stream: TextIO | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    out = stream if stream is not None else sys.stdout
    executor = _build_executor(dry_run=args.dry_run)
    if args.command == "lock":
        return _cmd_lock(executor=executor, dry_run=args.dry_run, stream=out)
    if args.command == "unlock":
        return _cmd_unlock(executor=executor, dry_run=args.dry_run, stream=out)
    if args.command == "status":
        return _cmd_status(executor=executor, stream=out)
    # argparse `required=True` already catches missing subcommand; this branch
    # is unreachable but keeps mypy honest about return paths.
    parser.error(f"unknown command: {args.command!r}")


if __name__ == "__main__":  # pragma: no cover — module entry point
    raise SystemExit(main())
