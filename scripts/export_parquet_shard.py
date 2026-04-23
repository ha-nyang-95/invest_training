"""CLI wrapper for hourly Parquet shard export (Logger PC cron, Story 1.4 AC-2).

Usage:
    uv run python scripts/export_parquet_shard.py \
        --duckdb data/duckdb/features_logger.duckdb \
        --out-root data/parquet \
        --hour 2026-04-21T09 \
        --tables ticks,quotes,news

`--hour` is always UTC. Accepts `YYYY-MM-DDTHH` (implicit :00:00Z) or
`now-<N>` where N is hours-ago. `--check-only` compares existing shards
against a fresh re-query; drift exits 1 with error_code=SHARD_DRIFT.

Standard output contract (observability, Story 1.9 parses this):
    {"hour": "...", "tables": {"ticks": 3, ...}, "bytes": N, "duration_seconds": N}

Standard error contract on failure:
    {"error_code": "SHARD_ALREADY_EXISTS" | "SHARD_DRIFT", "path": "...", ...}
"""

from __future__ import annotations

import argparse
import json
import re
import signal
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import FrameType

import duckdb
from athena.feature_store.duckdb_client import open_logger_duckdb
from athena.feature_store.parquet_shard import (
    ShardDriftError,
    ShardOverwriteError,
    export_hour_shard,
)

_VALID_TABLES = frozenset({"ticks", "quotes", "news"})
# `YYYY-MM-DDTHH` — pre-validated before handing to fromisoformat so malformed
# specs produce a structured SHARD_BAD_HOUR JSON error instead of a raw traceback.
_HOUR_ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}$")
# `now-<N>` — N must be >= 1; N=0 would target the currently-incomplete hour
# and N<0 (from the `now--5` typo) would silently target the future.
_NOW_OFFSET_RE = re.compile(r"^now-(\d+)$")


def parse_hour(spec: str) -> datetime:
    """Accept `YYYY-MM-DDTHH` (UTC implicit) or `now-<N>` (N hours ago, UTC).

    Rejects invalid specs with a clear ValueError so main() can translate to
    the SHARD_BAD_HOUR JSON contract. Previously `int("abc")` and `now-0` both
    escaped as raw tracebacks or silent no-ops.
    """
    if m := _NOW_OFFSET_RE.match(spec):
        offset_h = int(m.group(1))
        if offset_h < 1:
            raise ValueError(
                f"--hour now-<N> requires N>=1 (current hour is incomplete); got {spec!r}"
            )
        now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
        return now - timedelta(hours=offset_h)
    if _HOUR_ISO_RE.match(spec):
        spec = spec + ":00:00+00:00"
    try:
        dt = datetime.fromisoformat(spec)
    except ValueError as exc:
        raise ValueError(
            f"--hour must be `YYYY-MM-DDTHH` or `now-<N>` (N>=1); got {spec!r}"
        ) from exc
    if dt.tzinfo is None:
        raise ValueError(f"--hour must be UTC-aware or `YYYY-MM-DDTHH`; got {spec!r}")
    return dt.astimezone(UTC)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Export hourly Parquet shards from features_logger.duckdb"
    )
    ap.add_argument("--duckdb", type=Path, required=True, help="Path to features_logger.duckdb")
    ap.add_argument("--out-root", type=Path, required=True, help="Parquet root (e.g. data/parquet)")
    ap.add_argument("--hour", required=True, help="UTC hour: `2026-04-21T09` or `now-1`")
    ap.add_argument(
        "--tables",
        default="ticks,quotes,news",
        help="Comma-separated subset of {ticks,quotes,news}",
    )
    ap.add_argument(
        "--check-only",
        action="store_true",
        help="Compare existing shards against fresh query; no writes. Drift = exit 1.",
    )
    args = ap.parse_args()

    try:
        hour = parse_hour(args.hour)
    except ValueError as exc:
        sys.stderr.write(json.dumps({"error_code": "SHARD_BAD_HOUR", "detail": str(exc)}) + "\n")
        return 2

    mode: str = "check" if args.check_only else "fail"
    tables = [t.strip() for t in args.tables.split(",") if t.strip()]
    invalid = sorted(set(tables) - _VALID_TABLES)
    if invalid:
        # Validate all table names up-front so a typo cannot leave us with
        # ticks exported + quotes aborted mid-loop (partial state that would
        # hit SHARD_ALREADY_EXISTS on retry).
        sys.stderr.write(
            json.dumps(
                {
                    "error_code": "SHARD_BAD_TABLES",
                    "invalid": invalid,
                    "allowed": sorted(_VALID_TABLES),
                }
            )
            + "\n"
        )
        return 2

    per_table_count: dict[str, int] = {}
    total_bytes = 0
    total_duration = 0.0

    # SIGTERM handler — systemd oneshot with TimeoutStartSec may kill the
    # export mid-loop at the hour boundary. Emit a partial-state JSON to
    # stderr so Story 1.9 observability distinguishes "killed" from "no run".
    # Windows main-thread-only + systemd is the production target; the
    # setup is best-effort and swallows setup errors silently.
    def _on_sigterm(_signum: int, _frame: FrameType | None) -> None:
        sys.stderr.write(
            json.dumps(
                {
                    "error_code": "SHARD_INTERRUPTED",
                    "hour": hour.isoformat(),
                    "tables_partial": per_table_count,
                    "bytes_partial": total_bytes,
                    "duration_partial_seconds": total_duration,
                }
            )
            + "\n"
        )
        raise SystemExit(130)

    try:
        signal.signal(signal.SIGTERM, _on_sigterm)
    except (AttributeError, ValueError, OSError):
        # Non-main thread or unsupported-signal platform: skip the handler.
        pass

    try:
        with open_logger_duckdb(args.duckdb) as conn:
            for table in tables:
                shard_result = export_hour_shard(
                    conn,
                    table,
                    hour,
                    args.out_root,
                    mode=mode,  # type: ignore[arg-type]
                )
                per_table_count[table] = (
                    shard_result.files_matched if args.check_only else shard_result.files_written
                )
                total_bytes += shard_result.bytes_written
                total_duration += shard_result.duration_seconds
    except (ShardOverwriteError, ShardDriftError) as exc:
        sys.stderr.write(json.dumps({"error_code": exc.error_code, **exc.context}) + "\n")
        return 1
    except duckdb.IOException as exc:
        # Logger daemon + hourly cron collision on the DuckDB single-writer
        # lock. Distinguishes from a "real" shard error (exit 1) so the
        # operator can retry vs page someone.
        sys.stderr.write(
            json.dumps({"error_code": "DB_LOCKED", "path": str(args.duckdb), "detail": str(exc)})
            + "\n"
        )
        return 3
    except Exception as exc:  # noqa: BLE001 — top-level contract
        # Catch-all so disk-full, polars OOM, permission denied, network
        # partition, etc. surface as structured JSON rather than raw traceback.
        # Story 1.9 observability (textfile_collector parser) depends on this
        # contract to classify failure.
        sys.stderr.write(
            json.dumps(
                {
                    "error_code": "SHARD_UNEXPECTED",
                    "type": type(exc).__name__,
                    "detail": str(exc),
                }
            )
            + "\n"
        )
        return 4

    if args.check_only:
        sys.stdout.write(
            json.dumps(
                {
                    "check": "identical",
                    "hour": hour.isoformat(),
                    "files": sum(per_table_count.values()),
                }
            )
            + "\n"
        )
    else:
        sys.stdout.write(
            json.dumps(
                {
                    "hour": hour.isoformat(),
                    "tables": per_table_count,
                    "bytes": total_bytes,
                    "duration_seconds": total_duration,
                }
            )
            + "\n"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
