"""Story 1.3 Task 6.2 — commit-msg hook guarding `policy:` prefix.

When a commit stages any policy file (`config/policy.toml`, `config/flag_registry.toml`,
`packages/athena-core/athena/core/flags.py`), the commit subject must begin
with `policy:`. Missing prefix → exit 1 with an explanatory message.

This hook is a developer-safety net, not an adversarial defence. `--no-verify`
bypass is intentionally out of scope; CI stage-6 cooling gate carries the
adversarial defence line.

Invoked as: `python scripts/check_policy_prefix.py <commit-msg-path>`
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

POLICY_PREFIX = re.compile(r"^policy:")
POLICY_FILES = re.compile(
    r"^(config/policy\.toml|config/flag_registry\.toml|"
    r"packages/athena-core/athena/core/flags\.py)$"
)


def staged_files() -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True,
        text=True,
        check=True,
        encoding="utf-8",
    ).stdout
    return [line for line in out.splitlines() if line]


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: check_policy_prefix.py <commit-msg-path>", file=sys.stderr)
        return 2
    msg_path = Path(sys.argv[1])
    first_line = ""
    if msg_path.exists():
        # `utf-8-sig` transparently strips a UTF-8 BOM that Windows git
        # occasionally prepends to COMMIT_EDITMSG; matches git's own
        # post-cleanup view of the subject by skipping leading blank lines.
        raw = msg_path.read_text(encoding="utf-8-sig").splitlines()
        for line in raw:
            stripped = line.strip()
            if stripped:
                first_line = stripped
                break
    changed = staged_files()
    policy_touched = [f for f in changed if POLICY_FILES.match(f)]
    if not policy_touched:
        return 0
    if POLICY_PREFIX.search(first_line):
        return 0
    print(
        f"policy file(s) changed {policy_touched} but commit message prefix != 'policy:' "
        "— use `git commit -m 'policy: ...'` or revert the policy change.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
