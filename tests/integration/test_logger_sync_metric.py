"""Story 1.4 AC-5 Task 5.4 — textfile-collector metric emitter tests.

Five scenarios: success with new last_success, transient exit (23) still
updates last_success, hard failure preserves prior last_success + bumps
exit_code, missing output dir is auto-created, and atomic rename under
rapid consecutive calls.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "emit_logger_sync_metric.py"


def _emit(output: Path, exit_code: int, duration: float = 0.0) -> None:
    # errors="replace" hardens against rare cp949 bytes on the Windows pipe
    # (pytest under concurrent threads occasionally sees a mixed-codec chunk);
    # we only read subprocess stdout/stderr on failure, so lossy decode is fine.
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--exit-code",
            str(exit_code),
            "--duration",
            str(duration),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    assert proc.returncode == 0, f"stdout={proc.stdout!r} stderr={proc.stderr!r}"


def _parse_metric(output: Path, name: str) -> float:
    for line in output.read_text(encoding="utf-8").splitlines():
        if line.startswith(f"{name} "):
            return float(line.split()[1])
    raise AssertionError(f"metric {name} not found in {output}")


def test_success_updates_last_success(tmp_path: Path) -> None:
    out = tmp_path / "athena_logger_sync.prom"
    before = int(time.time())
    _emit(out, exit_code=0, duration=4.2)
    after = int(time.time())
    last_success = _parse_metric(out, "athena_logger_sync_last_success_seconds")
    assert before - 1 <= last_success <= after + 1
    assert _parse_metric(out, "athena_logger_sync_last_exit_code") == 0
    assert _parse_metric(out, "athena_logger_sync_duration_seconds") == pytest.approx(4.2)


def test_transient_exit_23_counts_as_success(tmp_path: Path) -> None:
    out = tmp_path / "m.prom"
    _emit(out, exit_code=0, duration=1.0)
    first_success = _parse_metric(out, "athena_logger_sync_last_success_seconds")
    time.sleep(1.1)
    _emit(out, exit_code=23, duration=2.0)
    second_success = _parse_metric(out, "athena_logger_sync_last_success_seconds")
    assert second_success > first_success
    assert _parse_metric(out, "athena_logger_sync_last_exit_code") == 23


def test_hard_failure_preserves_prior_last_success(tmp_path: Path) -> None:
    out = tmp_path / "m.prom"
    _emit(out, exit_code=0, duration=1.0)
    success_before_fail = _parse_metric(out, "athena_logger_sync_last_success_seconds")
    time.sleep(1.1)
    _emit(out, exit_code=12, duration=0.5)
    assert _parse_metric(out, "athena_logger_sync_last_success_seconds") == success_before_fail
    assert _parse_metric(out, "athena_logger_sync_last_exit_code") == 12


def test_missing_output_dir_auto_created(tmp_path: Path) -> None:
    out = tmp_path / "nested" / "deep" / "m.prom"
    _emit(out, exit_code=0, duration=0.1)
    assert out.exists()


def test_empty_exit_code_records_sentinel_and_exits_zero(tmp_path: Path) -> None:
    """Review-flip fix: when systemd expands $EXIT_STATUS in a context where
    the variable is unset (historical ExecStartPost= misuse, manual
    systemd-run invocation, unit config churn), the arg arrives as the
    empty string. Previously `int('')` raised and the emit step itself
    failed — metric file never landed, alert never updated. Now the empty
    string maps to the -1 sentinel so the exit_code gauge still reflects
    an anomalous state."""
    out = tmp_path / "m.prom"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--exit-code",
            "",  # empty string — systemd variable expansion void
            "--duration",
            "0",
            "--output",
            str(out),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert proc.returncode == 0, f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
    assert _parse_metric(out, "athena_logger_sync_last_exit_code") == -1


def test_concurrent_writes_never_leave_torn_file(tmp_path: Path) -> None:
    # node_exporter's textfile scraper polls concurrently — the script writes
    # tmp + replace, so every observed state must be a complete metric set.
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(exist_ok=True)
    out = tmp_path / "concurrent.prom"
    _emit(out, exit_code=0, duration=0.0)

    def spin() -> None:
        for ec in (0, 23, 12, 0, 24):
            _emit(out, exit_code=ec, duration=0.0)

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda _: spin(), range(4)))

    # After the storm, the file is valid: contains all three HELP lines exactly once
    text = out.read_text(encoding="utf-8")
    for gauge in (
        "athena_logger_sync_last_success_seconds",
        "athena_logger_sync_last_exit_code",
        "athena_logger_sync_duration_seconds",
    ):
        assert text.count(f"# HELP {gauge}") == 1, f"torn file: {gauge}"
