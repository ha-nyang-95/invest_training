"""Emit Prometheus textfile-collector metrics after each rsync run.

Source: Story 1.4 AC-5 Task 5.1.

Invoked from athena-logger-sync.service's ExecStartPost. Reads the previous
file (if present) to preserve `athena_logger_sync_last_success_seconds` on
failure — Prometheus alert rule `LoggerSyncLagHigh` fires when this value
gets more than 120 seconds behind wall-clock. Writes atomically via
tmp + replace so node_exporter's textfile scraper never sees a torn file.

The `SuccessExitStatus=0 23 24 30` on the service means exits 23/24/30 are
treated as success by systemd (network transient / partial / timeout — the
next timer catches up). This script mirrors that set when deciding whether
to update last_success_seconds.
"""

from __future__ import annotations

import argparse
import math
import os
import time
from pathlib import Path

_SUCCESS_EXIT_CODES = frozenset({0, 23, 24, 30})
_PREV_SUCCESS_PREFIX = "athena_logger_sync_last_success_seconds "
# systemd populates $EXIT_STATUS in ExecStopPost= for Type=oneshot, but if the
# unit aborts before the service phase (dependency failure, `systemd-run`
# manual invocation, non-oneshot call path) the variable expands to empty.
# -1 is the sentinel the rendered metric uses so alerts on
# `athena_logger_sync_last_exit_code != 0` still fire.
_UNKNOWN_EXIT_CODE = -1


def _parse_exit_code(raw: str) -> int:
    """argparse type= hook. Accepts empty string (from an unset $EXIT_STATUS
    expansion) as -1 sentinel rather than raising — otherwise the emit step
    itself would fail and the metric file would never land."""
    stripped = raw.strip()
    if not stripped:
        return _UNKNOWN_EXIT_CODE
    return int(stripped)


def _read_prev_last_success(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith(_PREV_SUCCESS_PREFIX):
                # `int(float(...))` tolerates prior values written in float or
                # scientific notation (unlikely but plausible if a future
                # version emits `time()` directly without rounding); bare
                # `int()` would have crashed and reset last_success to 0,
                # firing LoggerSyncLagHigh immediately after the format drift.
                return int(float(line.split()[1]))
    except (OSError, ValueError):
        return 0
    return 0


def _sanitise_duration(duration: float) -> float:
    """NaN/inf would render as `nan`/`inf` in the Prometheus text format,
    which node_exporter's textfile scraper rejects — silently dropping ALL
    three gauges for that scrape. Clamp to 0.0 so the metric file stays
    valid even if a buggy caller passes garbage."""
    return 0.0 if not math.isfinite(duration) else duration


_STALE_TMP_AGE_SECONDS = 300  # 5 min — long enough that any in-flight emit finished.


def _sweep_stale_tmp_files(target: Path) -> None:
    """Orphan `.<pid>.tmp` files accumulate when a prior emitter crashed
    between write_text() and replace(). Without a sweep, the textfile
    collector directory grows unbounded over months on the Trading PC.

    mtime-guarded: only files older than 5 minutes are removed, so an
    in-flight concurrent emitter's tmp is never unlinked mid-flight.
    """
    parent = target.parent
    if not parent.exists():
        return
    suffix_glob = f"{target.stem}{target.suffix}.*.tmp"
    now = time.time()
    for stale in parent.glob(suffix_glob):
        try:
            if now - stale.stat().st_mtime < _STALE_TMP_AGE_SECONDS:
                continue
            stale.unlink()
        except OSError:
            # Another emitter may be mid-rename — leave the file alone.
            pass


def _render_body(last_success: int, exit_code: int, duration: float) -> str:
    safe_duration = _sanitise_duration(duration)
    return (
        "# HELP athena_logger_sync_last_success_seconds Unix timestamp of last successful rsync.\n"
        "# TYPE athena_logger_sync_last_success_seconds gauge\n"
        f"athena_logger_sync_last_success_seconds {last_success}\n"
        "# HELP athena_logger_sync_last_exit_code Last rsync exit code.\n"
        "# TYPE athena_logger_sync_last_exit_code gauge\n"
        f"athena_logger_sync_last_exit_code {exit_code}\n"
        "# HELP athena_logger_sync_duration_seconds Last rsync duration.\n"
        "# TYPE athena_logger_sync_duration_seconds gauge\n"
        f"athena_logger_sync_duration_seconds {safe_duration}\n"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Emit rsync-sync Prometheus textfile metrics")
    ap.add_argument("--exit-code", type=_parse_exit_code, required=True)
    ap.add_argument("--duration", type=float, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    now_unix = int(time.time())
    is_success = args.exit_code in _SUCCESS_EXIT_CODES
    prev_last_success = _read_prev_last_success(args.output)
    last_success = now_unix if is_success else prev_last_success

    args.output.parent.mkdir(parents=True, exist_ok=True)
    _sweep_stale_tmp_files(args.output)
    body = _render_body(last_success, args.exit_code, args.duration)
    # Atomic write: node_exporter textfile scraper runs concurrently and must
    # never observe a half-written file. Rename is atomic on the same filesystem.
    # PID-suffixed tmp name prevents races if two emitters fire concurrently.
    # Prod target is Linux (systemd ExecStartPost) where os.replace is atomic;
    # on Windows dev hosts the replace can lose a race against another
    # in-flight replace — retry briefly to paper over it.
    tmp = args.output.with_suffix(f"{args.output.suffix}.{os.getpid()}.tmp")
    tmp.write_text(body, encoding="utf-8")
    for attempt in range(10):
        try:
            tmp.replace(args.output)
            break
        except PermissionError:
            if attempt == 9:
                raise
            time.sleep(0.05)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
