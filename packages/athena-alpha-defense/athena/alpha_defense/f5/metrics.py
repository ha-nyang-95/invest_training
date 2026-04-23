"""Prometheus textfile-collector emitter for F5 readonly-mount state.

Story 1.6 AC-1 / Source-of-Truth Invariant #11. Metric naming follows
architecture.md line 430 (`athena_<component>_<metric>` pattern):

  * athena_readonly_mount_state{state="LOCKED|UNLOCKED|PARTIAL"} 1
  * athena_readonly_mount_last_transition_timestamp_seconds <unix>
  * athena_readonly_mount_last_lock_success_timestamp_seconds <unix>
  * athena_readonly_mount_last_unlock_success_timestamp_seconds <unix>

Atomic write pattern (Story 1.5 Task 3.2): `tmp + os.replace`. Node exporter's
textfile collector scrapes the final path concurrently and must never see a
half-written file.
"""

from __future__ import annotations

import math
import os
import time
from datetime import datetime
from pathlib import Path

from athena.alpha_defense.f5.readonly_mount import MountState

# Mirrors `scripts/emit_logger_sync_metric.py` — keep tmp suffix short and
# PID-tagged so concurrent emits do not race the same temp name.
_TMP_SUFFIX_TEMPLATE = ".{pid}.tmp"

# Replace retry budget for Windows dev hosts where another in-flight replace
# can briefly block. On Linux prod (systemd ExecStopPost) this loop is a no-op.
_REPLACE_RETRIES = 10
_REPLACE_BACKOFF_SECONDS = 0.05

# When previous textfile is missing or unparseable, we have no baseline and
# emit 0 — Prometheus alert rules (Story 1.9) treat 0 as "no recent success"
# and fire after a configured age threshold.
_NO_PREVIOUS_TIMESTAMP = 0


def _to_unix_seconds(ts: datetime | None) -> int:
    if ts is None:
        return _NO_PREVIOUS_TIMESTAMP
    if ts.tzinfo is None:
        raise ValueError(
            "emit_readonly_mount_metric: timestamps must be timezone-aware. "
            "Pass datetime.now(UTC) or LockTransition.timestamp_utc directly."
        )
    seconds = ts.timestamp()
    if not math.isfinite(seconds):
        # Defensive: a bogus float would render as `nan` / `inf` and node_exporter
        # would silently drop the entire scrape.
        return _NO_PREVIOUS_TIMESTAMP
    return int(seconds)


def _read_prev_timestamp(output_path: Path, metric_prefix: str) -> int:
    """Read prior `<metric_prefix> <unix>` line so failed transitions preserve
    the last known good timestamp (mirrors Story 1.4 last_success preservation).
    """
    if not output_path.exists():
        return _NO_PREVIOUS_TIMESTAMP
    try:
        for line in output_path.read_text(encoding="utf-8").splitlines():
            if line.startswith(metric_prefix + " "):
                return int(float(line.split()[1]))
    except (OSError, ValueError):
        return _NO_PREVIOUS_TIMESTAMP
    return _NO_PREVIOUS_TIMESTAMP


def _render_body(
    *,
    state: MountState,
    last_transition: int,
    last_lock_success: int,
    last_unlock_success: int,
) -> str:
    state_lines: list[str] = []
    # Emit one gauge line per possible state value with 1 set for the active
    # one and 0 for the others. This shape lets PromQL boolean filters work
    # cleanly: `athena_readonly_mount_state{state="LOCKED"} == 1`.
    for member in MountState:
        value = 1 if member is state else 0
        state_lines.append(f'athena_readonly_mount_state{{state="{member.value}"}} {value}')
    # The Prometheus textfile format requires `# HELP <name> <text>` and
    # `<name> <value>` on a single line each — the metric name cannot be
    # wrapped. Names here are intentionally verbose per the Story 1.6
    # naming SSOT (Invariant #11), so a few lines exceed E501.
    return (
        "# HELP athena_readonly_mount_state Current state of /var/lib/athena/policy.\n"
        "# TYPE athena_readonly_mount_state gauge\n" + "\n".join(state_lines) + "\n"
        "# HELP athena_readonly_mount_last_transition_timestamp_seconds Unix ts of last transition.\n"  # noqa: E501
        "# TYPE athena_readonly_mount_last_transition_timestamp_seconds gauge\n"
        f"athena_readonly_mount_last_transition_timestamp_seconds {last_transition}\n"
        "# HELP athena_readonly_mount_last_lock_success_timestamp_seconds Unix ts of last lock.\n"  # noqa: E501
        "# TYPE athena_readonly_mount_last_lock_success_timestamp_seconds gauge\n"
        f"athena_readonly_mount_last_lock_success_timestamp_seconds {last_lock_success}\n"
        "# HELP athena_readonly_mount_last_unlock_success_timestamp_seconds Unix ts of last unlock.\n"  # noqa: E501
        "# TYPE athena_readonly_mount_last_unlock_success_timestamp_seconds gauge\n"
        f"athena_readonly_mount_last_unlock_success_timestamp_seconds {last_unlock_success}\n"
    )


def emit_readonly_mount_metric(
    *,
    state: MountState,
    last_transition_ts: datetime | None,
    output_path: Path,
    successful_action: str | None = None,
) -> None:
    """Write the readonly-mount textfile collector .prom atomically.

    Parameters:
      state — aggregate result of the most recent transition (or the current
              `status()` reading on a no-op refresh).
      last_transition_ts — when the transition happened (UTC). None means
              "no transition this call" — caller is just refreshing state.
      output_path — final .prom file (e.g.
              `/var/lib/node_exporter/textfile_collector/athena_readonly_mount.prom`).
      successful_action — "lock" or "unlock" iff the call corresponds to a
              successful transition; None preserves the prior values for both
              last_lock/last_unlock_success metrics. Failed transitions pass
              None so the alert rule on stale lock_success keeps firing until
              a real success lands.
    """
    transition_unix = _to_unix_seconds(last_transition_ts)
    prev_lock = _read_prev_timestamp(
        output_path, "athena_readonly_mount_last_lock_success_timestamp_seconds"
    )
    prev_unlock = _read_prev_timestamp(
        output_path, "athena_readonly_mount_last_unlock_success_timestamp_seconds"
    )
    if successful_action == "lock":
        last_lock = transition_unix or prev_lock
        last_unlock = prev_unlock
    elif successful_action == "unlock":
        last_lock = prev_lock
        last_unlock = transition_unix or prev_unlock
    else:
        last_lock = prev_lock
        last_unlock = prev_unlock

    body = _render_body(
        state=state,
        last_transition=transition_unix,
        last_lock_success=last_lock,
        last_unlock_success=last_unlock,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = output_path.with_suffix(output_path.suffix + _TMP_SUFFIX_TEMPLATE.format(pid=os.getpid()))
    tmp.write_text(body, encoding="utf-8")
    for attempt in range(_REPLACE_RETRIES):
        try:
            tmp.replace(output_path)
            return
        except PermissionError:
            if attempt == _REPLACE_RETRIES - 1:
                raise
            time.sleep(_REPLACE_BACKOFF_SECONDS)
