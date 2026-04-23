"""Prometheus textfile-collector emitter tests — Story 1.6 AC-1 Task 1.8.

3 scenarios per the AC:
  1. emit() writes a .prom file with at least 4 metric lines.
  2. tmp + os.replace is atomic — no half-written final file is observable.
  3. UNLOCKED + successful_action="unlock" pins last_unlock_success_seconds to
     the transition timestamp.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from athena.alpha_defense.f5.metrics import emit_readonly_mount_metric
from athena.alpha_defense.f5.readonly_mount import MountState


def _metric_line(text: str, prefix: str) -> str:
    matches = [line for line in text.splitlines() if line.startswith(prefix)]
    assert matches, f"missing metric {prefix!r} in:\n{text}"
    return matches[-1]


def test_emit_writes_prom_file_with_required_metrics(tmp_path: Path) -> None:
    output = tmp_path / "athena_readonly_mount.prom"
    ts = datetime(2026, 4, 23, 9, 0, 5, tzinfo=UTC)

    emit_readonly_mount_metric(
        state=MountState.LOCKED,
        last_transition_ts=ts,
        output_path=output,
        successful_action="lock",
    )

    body = output.read_text(encoding="utf-8")
    # State gauge: 1 line per MountState member.
    assert 'athena_readonly_mount_state{state="LOCKED"} 1' in body
    assert 'athena_readonly_mount_state{state="UNLOCKED"} 0' in body
    assert 'athena_readonly_mount_state{state="PARTIAL"} 0' in body

    transition_line = _metric_line(body, "athena_readonly_mount_last_transition_timestamp_seconds")
    assert transition_line.endswith(str(int(ts.timestamp())))

    lock_line = _metric_line(body, "athena_readonly_mount_last_lock_success_timestamp_seconds")
    assert lock_line.endswith(str(int(ts.timestamp())))


def test_atomic_write_leaves_no_partial_files_on_success(tmp_path: Path) -> None:
    output = tmp_path / "athena_readonly_mount.prom"
    emit_readonly_mount_metric(
        state=MountState.UNLOCKED,
        last_transition_ts=datetime(2026, 4, 23, 15, 30, tzinfo=UTC),
        output_path=output,
        successful_action="unlock",
    )

    siblings = list(output.parent.iterdir())
    # Only the final file remains — tmp suffix .{pid}.tmp must be replaced.
    assert siblings == [output], f"unexpected leftovers: {siblings}"
    # The first emit also creates the parent dir if needed.
    assert output.exists()


def test_unlock_action_pins_last_unlock_success_to_transition_ts(tmp_path: Path) -> None:
    output = tmp_path / "athena_readonly_mount.prom"
    ts = datetime(2026, 4, 23, 15, 30, 12, tzinfo=UTC)

    emit_readonly_mount_metric(
        state=MountState.UNLOCKED,
        last_transition_ts=ts,
        output_path=output,
        successful_action="unlock",
    )

    body = output.read_text(encoding="utf-8")
    unlock_line = _metric_line(body, "athena_readonly_mount_last_unlock_success_timestamp_seconds")
    transition_line = _metric_line(body, "athena_readonly_mount_last_transition_timestamp_seconds")
    assert unlock_line.endswith(str(int(ts.timestamp())))
    assert transition_line.endswith(str(int(ts.timestamp())))

    # First emit has no prior lock_success → must be 0 (sentinel for alerts).
    lock_line = _metric_line(body, "athena_readonly_mount_last_lock_success_timestamp_seconds")
    assert lock_line.endswith(" 0")


def test_naive_datetime_raises_value_error(tmp_path: Path) -> None:
    output = tmp_path / "athena_readonly_mount.prom"
    with pytest.raises(ValueError, match="timezone-aware"):
        emit_readonly_mount_metric(
            state=MountState.LOCKED,
            last_transition_ts=datetime(2026, 4, 23, 9, 0),  # noqa: DTZ001 — naive intentional
            output_path=output,
            successful_action="lock",
        )
