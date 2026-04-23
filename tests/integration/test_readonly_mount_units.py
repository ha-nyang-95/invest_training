"""Story 1.6 AC-2 Task 2.7 — F5 readonly-mount systemd unit + sudoers tests.

Two tiers:
  * Static (configparser, runs everywhere): unit ini sections, OnCalendar,
    Persistent=false, ExecStart wiring, ExecStopPost emits metric, etc.
  * WSL2 / Linux only (`systemd-analyze verify`, `visudo -cf`,
    `install.sh DRY_RUN=1`): full syntactic validation.
"""

from __future__ import annotations

import configparser
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parents[2]
UNIT_DIR = REPO_ROOT / "infra" / "systemd"
SUDOERS_DROPIN = UNIT_DIR / "sudoers.d" / "athena-readonly-mount"
INSTALLER = UNIT_DIR / "athena-readonly-mount.install.sh"

LOCK_SERVICE = UNIT_DIR / "athena-readonly-mount-lock.service"
LOCK_TIMER = UNIT_DIR / "athena-readonly-mount-lock.timer"
UNLOCK_SERVICE = UNIT_DIR / "athena-readonly-mount-unlock.service"
UNLOCK_TIMER = UNIT_DIR / "athena-readonly-mount-unlock.timer"
INOTIFY_SCAFFOLD = UNIT_DIR / "athena-inotify-watcher.service"

ALL_UNITS = (LOCK_SERVICE, LOCK_TIMER, UNLOCK_SERVICE, UNLOCK_TIMER, INOTIFY_SCAFFOLD)
SKIPIF_WINDOWS = pytest.mark.skipif(
    sys.platform == "win32",
    reason="systemd-analyze / visudo / bash install.sh are Linux-only — WSL2 required",
)


def _parse_unit(path: Path) -> configparser.ConfigParser:
    cp = configparser.ConfigParser(strict=False, interpolation=None)
    cp.read(path, encoding="utf-8")
    return cp


# ---------------------------------------------------------------------------
# Static checks — run on every platform (CI stage-3 marker only).


def test_lock_service_runs_chattr_via_python_module() -> None:
    cp = _parse_unit(LOCK_SERVICE)
    exec_start = cp.get("Service", "ExecStart")
    assert "athena.alpha_defense.f5" in exec_start
    assert exec_start.rstrip().endswith(" lock")
    # ExecStartPre routes through check_trading_day so weekend/holiday skips.
    assert "check_trading_day.py" in cp.get("Service", "ExecStartPre")


def test_unlock_service_is_symmetric_to_lock() -> None:
    cp = _parse_unit(UNLOCK_SERVICE)
    exec_start = cp.get("Service", "ExecStart")
    assert exec_start.rstrip().endswith(" unlock")
    assert "check_trading_day.py" in cp.get("Service", "ExecStartPre")


def test_both_services_emit_metric_in_exec_stop_post() -> None:
    """ExecStopPost is the only phase where systemd populates `$EXIT_STATUS`
    (per systemd.service(5)). Mirrors Story 1.4 review-flip fix."""
    for unit in (LOCK_SERVICE, UNLOCK_SERVICE):
        cp = _parse_unit(unit)
        assert cp.has_option("Service", "ExecStopPost"), f"{unit.name} missing ExecStopPost"
        exec_stop_post = cp.get("Service", "ExecStopPost")
        assert "emit_readonly_mount_metric.py" in exec_stop_post
        assert "$EXIT_STATUS" in exec_stop_post


def test_lock_timer_fires_at_kst_open_only_on_weekdays() -> None:
    cp = _parse_unit(LOCK_TIMER)
    assert cp.get("Timer", "OnCalendar") == "Mon..Fri 09:00"
    # Persistent=false — see Story 1.6 Invariant #6 for rationale.
    assert cp.get("Timer", "Persistent") == "false"
    assert cp.get("Install", "WantedBy") == "timers.target"
    assert cp.get("Unit", "Requires") == "athena-readonly-mount-lock.service"


def test_unlock_timer_fires_at_kst_close_only_on_weekdays() -> None:
    cp = _parse_unit(UNLOCK_TIMER)
    assert cp.get("Timer", "OnCalendar") == "Mon..Fri 15:30"
    assert cp.get("Timer", "Persistent") == "false"


def test_services_treat_skip_exit_1_as_success() -> None:
    """SuccessExitStatus=0 1 means check_trading_day.py exit 1 (non-trading
    day) does NOT trip Restart= or alert rules — see Invariant #5."""
    for unit in (LOCK_SERVICE, UNLOCK_SERVICE):
        cp = _parse_unit(unit)
        assert cp.get("Service", "SuccessExitStatus").strip() == "0 1"


def test_services_run_as_khuk0_not_root() -> None:
    """User=khuk0 + sudoers NOPASSWD is the chosen sudo boundary
    (Story 1.6 Invariant #8)."""
    for unit in (LOCK_SERVICE, UNLOCK_SERVICE):
        cp = _parse_unit(unit)
        assert cp.get("Service", "User") == "khuk0"
        assert cp.get("Service", "Group") == "khuk0"


def test_inotify_watcher_is_scaffold_with_no_install_section() -> None:
    """Story 1.6 must NOT enable the inotify watcher; Story 3.5 owns activation."""
    cp = _parse_unit(INOTIFY_SCAFFOLD)
    assert "Install" not in cp.sections(), (
        "athena-inotify-watcher.service is a scaffold and must not declare [Install]"
    )
    # ExecStart is a placeholder; the assertion is that it parses, not what it does.
    assert cp.has_option("Service", "ExecStart")


def test_sudoers_dropin_lists_only_specific_chattr_commands_no_wildcards() -> None:
    body = SUDOERS_DROPIN.read_text(encoding="utf-8")
    cmd_lines = [line for line in body.splitlines() if line.startswith("khuk0")]
    # 2 protected files × {+i, -i} = 4 entries (Invariant #7).
    assert len(cmd_lines) == 4
    for line in cmd_lines:
        assert "/usr/sbin/chattr" in line
        assert "NOPASSWD:" in line
        # Hard ban on wildcards — Invariant #7.
        assert "*" not in line.split("NOPASSWD:")[1]


# ---------------------------------------------------------------------------
# WSL2 / Linux-only tests.


@SKIPIF_WINDOWS
def test_systemd_analyze_verify_passes_on_all_units() -> None:
    if shutil.which("systemd-analyze") is None:
        pytest.skip("systemd-analyze not available")
    for unit in ALL_UNITS:
        proc = subprocess.run(  # noqa: S603 — known argv list
            ["systemd-analyze", "verify", str(unit)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
        )
        assert proc.returncode == 0, (
            f"systemd-analyze verify failed on {unit.name}: "
            f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
        )


@SKIPIF_WINDOWS
def test_systemd_analyze_calendar_resolves_to_weekday_kst_open() -> None:
    if shutil.which("systemd-analyze") is None:
        pytest.skip("systemd-analyze not available")
    proc = subprocess.run(  # noqa: S603
        ["systemd-analyze", "calendar", "Mon..Fri 09:00"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
        check=False,
    )
    assert proc.returncode == 0
    # `Next elapse:` line must mention 09:00 — exact day depends on when
    # tests run, so we don't pin it.
    assert "09:00" in proc.stdout


@SKIPIF_WINDOWS
def test_visudo_validates_sudoers_dropin() -> None:
    if shutil.which("visudo") is None:
        pytest.skip("visudo not available")
    proc = subprocess.run(  # noqa: S603
        ["visudo", "-cf", str(SUDOERS_DROPIN)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
        check=False,
    )
    assert proc.returncode == 0, f"visudo -cf failed: {proc.stdout!r} {proc.stderr!r}"


@SKIPIF_WINDOWS
def test_install_sh_dry_run_lists_at_least_8_planned_actions() -> None:
    if shutil.which("bash") is None:
        pytest.skip("bash not available")
    env = {**os.environ, "DRY_RUN": "1"}
    proc = subprocess.run(  # noqa: S603
        ["bash", str(INSTALLER)],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, f"install DRY_RUN failed: {proc.stdout!r} {proc.stderr!r}"
    dry_lines = [line for line in proc.stdout.splitlines() if "[dry-run]" in line]
    # Expected dry-run actions (≥ 8): mkdir/seed (2-3) + install 5 units +
    # install sudoers (1) + daemon-reload (1) + enable timers (2).
    assert len(dry_lines) >= 8, f"only {len(dry_lines)} dry-run lines: {dry_lines!r}"


@SKIPIF_WINDOWS
def test_install_sh_is_idempotent_on_dry_run_repeats() -> None:
    """Re-running the installer in DRY_RUN mode must still exit 0 — the
    real-mode `cmp -s` skip path is exercised in the WSL2 E2E flow."""
    if shutil.which("bash") is None:
        pytest.skip("bash not available")
    env = {**os.environ, "DRY_RUN": "1"}
    for _ in range(2):
        proc = subprocess.run(  # noqa: S603
            ["bash", str(INSTALLER)],
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
        )
        assert proc.returncode == 0
