"""CLI tests — `python -m athena.alpha_defense.f5 ...`. Story 1.6 AC-1 Task 1.7.

All scenarios use --dry-run so no real chattr / sudo invocation is required;
SubprocessChattrExecutor is exercised by the WSL2 E2E tests in Task 3.1.
"""

from __future__ import annotations

import io
import json
from collections.abc import Sequence

import pytest
from athena.alpha_defense.f5.cli import main


def _run(argv: Sequence[str]) -> tuple[int, str]:
    buf = io.StringIO()
    code = main(argv, stream=buf)
    return code, buf.getvalue()


def test_status_dry_run_returns_unlocked_initially() -> None:
    code, stdout = _run(["--dry-run", "status"])
    assert code == 0

    payload = json.loads(stdout.strip().splitlines()[-1])
    assert payload["state"] == "UNLOCKED"
    assert payload["checked_paths"] == [
        "/var/lib/athena/policy/policy.toml",
        "/var/lib/athena/policy/flag_registry.toml",
    ]
    assert "as_of_utc" in payload


def test_lock_dry_run_emits_dry_run_prefix_and_target_paths() -> None:
    code, stdout = _run(["--dry-run", "lock"])
    assert code == 0

    # [dry-run] prefix lines: 1 header + 2 per-path = 3 lines minimum.
    dry_lines = [line for line in stdout.splitlines() if line.startswith("[dry-run]")]
    assert len(dry_lines) >= 3
    assert any("UNLOCKED -> LOCKED" in line for line in dry_lines)
    assert any("/var/lib/athena/policy/policy.toml" in line for line in dry_lines)
    assert any("/var/lib/athena/policy/flag_registry.toml" in line for line in dry_lines)

    # Final JSON payload — last non-dry line.
    json_line = [line for line in stdout.splitlines() if not line.startswith("[dry-run]")][-1]
    payload = json.loads(json_line)
    assert payload["transition"] == "lock"
    assert payload["new_state"] == "LOCKED"


def test_unlock_dry_run_is_symmetric_to_lock() -> None:
    # Note: each `_run` constructs a fresh DryRunChattrExecutor, so the prior
    # state is UNLOCKED again. The transition reports UNLOCKED -> UNLOCKED with
    # per_file_results "already" — still exit 0 (target reached).
    code, stdout = _run(["--dry-run", "unlock"])
    assert code == 0

    json_line = [line for line in stdout.splitlines() if not line.startswith("[dry-run]")][-1]
    payload = json.loads(json_line)
    assert payload["transition"] == "unlock"
    assert payload["new_state"] == "UNLOCKED"


def test_invalid_subcommand_returns_exit_2(capsys: pytest.CaptureFixture[str]) -> None:
    # argparse calls sys.exit(2) on bad subcommand; main() raises SystemExit
    # before returning, so we wrap and check the code.
    with pytest.raises(SystemExit) as exc_info:
        main(["totally-not-a-subcommand"])
    assert exc_info.value.code == 2

    captured = capsys.readouterr()
    # argparse error message goes to stderr.
    assert "invalid choice" in captured.err or "argument" in captured.err
