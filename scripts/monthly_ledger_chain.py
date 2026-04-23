"""Monthly segment-hash CLI — Story 1.5 AC-3 placeholder.

Emits a JSON document describing the chain of entries added in a given
month + uploads (copies) to the LUKS-mounted external SSD path and an
optional S3-shaped placeholder directory. Story 1.10 wires this under
systemd timer (monthly, 03:00 KST); Story 6.2 replaces the `--s3-placeholder`
hop with real boto3 uploads under Object Lock Compliance.

Exit codes:
* 0 on success.
* 1 on DuckDB/compute error (`LEDGER_SEGMENT_COMPUTE_FAILED`).
* 2 reserved for argparse usage errors (argparse produces this automatically).
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path

from athena.core.version import POLICY_VERSION_SHA
from athena.execution.ledger.segment_hash import compute_segment_hash
from athena.feature_store.duckdb_client import open_decisions_duckdb


def _atomic_write_readonly(target: Path, body: str) -> None:
    """Write `body` to `target` atomically and then chmod 0o444.

    Windows `os.replace` refuses to clobber a read-only destination, so if
    the target already exists we first widen its mode back to 0o644 before
    the replace. Linux would accept the clobber regardless, but the pre-step
    is no-op-safe on Linux.

    On Linux we fsync the tmp file + its parent directory before the replace
    so that a crash between `write` and `replace` cannot leave the target
    either missing or zero-length despite the rename having returned. On
    Windows `os.fsync` on a directory fd is not supported, so we skip the
    dir sync — the file-level sync still gives torn-write protection.

    The `.tmp` file is unlinked in a `finally` block on failure so an
    interrupted run does not orphan `.tmp` siblings next to the target.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target.chmod(0o644)
    tmp = target.with_suffix(target.suffix + ".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(body)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(str(tmp), str(target))
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    if os.name != "nt":
        # Parent-dir fsync is POSIX-only; Windows rejects it.
        dir_fd = os.open(str(target.parent), os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    target.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)  # 0o444


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Compute + publish monthly ledger segment hash")
    ap.add_argument("--db", type=Path, required=True)
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--month", type=int, required=True, choices=range(1, 13))
    ap.add_argument("--prev-segment-hash", type=str, default=None)
    ap.add_argument(
        "--out-local",
        type=Path,
        required=True,
        help="LUKS-mounted external SSD target — atomic-write, chmod 444.",
    )
    ap.add_argument(
        "--s3-placeholder",
        type=Path,
        default=None,
        help="S3 bucket-shaped placeholder (Story 6.2 replaces with real boto3).",
    )
    args = ap.parse_args(argv)

    try:
        with open_decisions_duckdb(args.db) as conn:
            result = compute_segment_hash(
                conn,
                year=args.year,
                month=args.month,
                prev_segment_hash=args.prev_segment_hash,
                policy_version_git_sha=POLICY_VERSION_SHA,
            )
    except Exception as exc:  # noqa: BLE001 — exit-code boundary
        print(
            json.dumps(
                {
                    "error_code": "LEDGER_SEGMENT_COMPUTE_FAILED",
                    "error": str(exc),
                }
            ),
            file=sys.stderr,
        )
        return 1

    body = json.dumps(
        {
            "month": result.month,
            "segment_hash": result.segment_hash,
            "prev_segment_hash": result.prev_segment_hash,
            "entry_count": result.entry_count,
            "first_id": result.first_id,
            "last_id": result.last_id,
            "computed_at_utc": result.computed_at_utc,
            "policy_version_git_sha": POLICY_VERSION_SHA,
        },
        sort_keys=True,
        indent=2,
    )

    _atomic_write_readonly(args.out_local, body)

    if args.s3_placeholder is not None:
        _atomic_write_readonly(args.s3_placeholder, body)

    print(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
