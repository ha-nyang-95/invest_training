"""Story 1.3 Task 4.3 — CI stage-7 paper-replay marker gate.

Checks that a lightweight tag `paper-replay-ok/<short_sha>` exists for the
current `policy:` HEAD commit. Non-policy commits exit 0 without inspecting
tags. Exit 1 with a JSON payload on stderr when the marker is missing.

Tag generation is deferred to Epic 8 Story 8.5. Local bootstrap is documented
in `docs/operating_playbook.md` § "Story 1.3 Task 4.6 — Paper Replay Marker".
"""

from __future__ import annotations

import json
import re
import subprocess
import sys

POLICY_PREFIX = re.compile(r"^policy:")


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


def main() -> int:
    if not POLICY_PREFIX.search(head_subject()):
        return 0
    short = _run_git("rev-parse", "--short", "HEAD")
    tag = f"paper-replay-ok/{short}"
    tags = _run_git("tag", "--list", tag).splitlines()
    if tag in tags:
        return 0
    payload = {
        "error_code": "PAPER_REPLAY_MISSING",
        "head_sha": short,
        "expected_tag": tag,
    }
    print(json.dumps(payload), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
