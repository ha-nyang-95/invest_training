"""Story 1.3 Task 4.2 — CI stage-6 72h policy cooling gate.

Exit 0 on non-policy HEAD commit or when the previous `policy:` merge is
>= 72h old. Exit 1 with a JSON payload on stderr when the cooling window has
not elapsed. Time source is wrapped in `_now_utc()` so tests can monkeypatch
without `freezegun`; there is intentionally no environment override to prevent
silent bypass.

FR57 / NFR-R5 enforcement. Invoked from `.github/workflows/ci.yml`
stage-6-cooling-gate.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import UTC, datetime, timedelta

POLICY_PREFIX = re.compile(r"^policy:")
COOLING_WINDOW = timedelta(hours=72)


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        check=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def head_subject() -> str:
    return _run_git("log", "-1", "--pretty=%s", "HEAD")


def prev_policy_commit_ts() -> datetime | None:
    """Return the most recent `policy:` commit timestamp excluding HEAD.

    Returns None when the repo has no prior `policy:` commit (genesis case)
    or only one commit in total.
    """
    try:
        out = _run_git(
            "log",
            "--pretty=%H%x09%ct",
            "--grep=^policy:",
            "-E",
            "HEAD~1",
        )
    except subprocess.CalledProcessError:
        return None
    if not out:
        return None
    first_line = out.splitlines()[0]
    _, ts = first_line.split("\t")
    return datetime.fromtimestamp(int(ts), tz=UTC)


def main() -> int:
    subject = head_subject()
    if not POLICY_PREFIX.search(subject):
        return 0
    prev_ts = prev_policy_commit_ts()
    if prev_ts is None:
        return 0
    elapsed = _now_utc() - prev_ts
    if elapsed >= COOLING_WINDOW:
        return 0
    remaining = (COOLING_WINDOW - elapsed).total_seconds() / 3600
    payload = {
        "error_code": "POLICY_NOT_COOLED",
        "prev_policy_ts_utc": prev_ts.isoformat(),
        "cooling_remaining_hours": round(remaining, 2),
    }
    print(json.dumps(payload), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
