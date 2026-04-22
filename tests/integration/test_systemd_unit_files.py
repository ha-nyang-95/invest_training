"""Story 1.4 AC-3 Task 3.5 — systemd unit ini parsing + installer dry-run tests.

Validates the two unit files we ship are well-formed and that the installer
script's DRY_RUN=1 mode prints the planned actions without invoking sudo.
"""

from __future__ import annotations

import configparser
import os
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parents[2]
UNIT_DIR = REPO_ROOT / "infra" / "systemd"
SERVICE_FILE = UNIT_DIR / "athena-logger-sync.service"
TIMER_FILE = UNIT_DIR / "athena-logger-sync.timer"
INSTALLER = REPO_ROOT / "scripts" / "install_logger_sync_unit.sh"


def _parse_unit(path: Path) -> configparser.ConfigParser:
    # systemd unit files use ini-like syntax; `configparser` with strict=False
    # handles the `=` separators and duplicate keys (e.g. multiple ExecStartPost).
    cp = configparser.ConfigParser(strict=False, interpolation=None)
    cp.read(path, encoding="utf-8")
    return cp


def test_service_file_has_required_sections() -> None:
    cp = _parse_unit(SERVICE_FILE)
    assert {"Unit", "Service", "Install"} <= set(cp.sections())


def test_service_exec_start_is_rsync_with_logger_pc_source() -> None:
    cp = _parse_unit(SERVICE_FILE)
    exec_start = cp.get("Service", "ExecStart")
    assert exec_start.startswith("/usr/bin/rsync")
    assert "logger-pc:/data/parquet/" in exec_start
    assert "/data/parquet/" in exec_start
    # --partial for transient-resume, --timeout bounds stuck connections
    assert "--partial" in exec_start
    assert "--timeout=30" in exec_start


def test_service_exec_start_has_bounded_delete() -> None:
    """Review-flip fix: --delete-after propagates Logger PC retention
    eviction without unbounded blast radius. --max-delete caps accidental
    mass-wipe so a Logger PC empty-directory misconfiguration cannot
    silently nuke the Trading PC cache."""
    cp = _parse_unit(SERVICE_FILE)
    exec_start = cp.get("Service", "ExecStart")
    assert "--delete-after" in exec_start
    assert "--max-delete=" in exec_start


def test_service_emits_metric_from_exec_stop_post_not_start_post() -> None:
    """Review-flip fix: $EXIT_STATUS is populated by systemd ONLY in
    ExecStopPost= (systemd.service(5)). ExecStartPost= leaves the variable
    empty — the metric emitter would then write exit_code=-1 on every run
    regardless of the rsync outcome. See emit_logger_sync_metric.py
    `_parse_exit_code` for the empty-string sentinel."""
    cp = _parse_unit(SERVICE_FILE)
    assert cp.has_option("Service", "ExecStopPost"), (
        "emit_logger_sync_metric.py must run under ExecStopPost= to capture $EXIT_STATUS"
    )
    exec_stop_post = cp.get("Service", "ExecStopPost")
    assert "emit_logger_sync_metric.py" in exec_stop_post
    assert "$EXIT_STATUS" in exec_stop_post
    # And NOT under ExecStartPost=
    if cp.has_option("Service", "ExecStartPost"):
        exec_start_post = cp.get("Service", "ExecStartPost")
        assert "emit_logger_sync_metric.py" not in exec_start_post, (
            "emit_logger_sync_metric.py must not run under ExecStartPost= "
            "(silent $EXIT_STATUS void); use ExecStopPost= instead"
        )


def test_service_success_exit_status_covers_transients() -> None:
    cp = _parse_unit(SERVICE_FILE)
    # exit 0=success, 23/24=partial, 30=timeout — all swallowed so next
    # timer catches up. 1/11/12 etc. remain failures.
    assert cp.get("Service", "SuccessExitStatus").strip() == "0 23 24 30"


def test_service_runs_as_khuk0() -> None:
    cp = _parse_unit(SERVICE_FILE)
    assert cp.get("Service", "User") == "khuk0"
    assert cp.get("Service", "Group") == "khuk0"


def test_timer_fires_every_60s() -> None:
    cp = _parse_unit(TIMER_FILE)
    assert cp.get("Timer", "OnUnitActiveSec") == "60s"
    assert cp.get("Timer", "Persistent") == "true"
    assert cp.get("Install", "WantedBy") == "timers.target"


def test_timer_requires_service() -> None:
    cp = _parse_unit(TIMER_FILE)
    assert cp.get("Unit", "Requires") == "athena-logger-sync.service"


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash not available (Windows CI)")
def test_installer_dry_run_prints_plan_without_sudo() -> None:
    env = {**os.environ, "DRY_RUN": "1"}
    # Resolve bash explicitly: on Windows, bare "bash" in subprocess can hit
    # the WSL shim (C:\Windows\System32\bash.exe) which hangs here. We want
    # git-bash from PATH via shutil.which.
    bash_exe = shutil.which("bash")
    assert bash_exe is not None
    # Pass the script as a path relative to cwd — git-bash does not accept
    # C:\... backslashes directly.
    proc = subprocess.run(
        [bash_exe, "scripts/install_logger_sync_unit.sh"],
        env=env,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
    # 2 unit-copy lines + 1 daemon-reload + 1 enable --now = 4 [dry-run] markers
    dry_run_lines = [line for line in proc.stdout.splitlines() if "[dry-run]" in line]
    assert len(dry_run_lines) == 4
    # No sudo invocations in dry-run mode (the script guards with the early-return)
    assert "sudo" not in proc.stdout
