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
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from athena.feature_store.duckdb_client import open_logger_duckdb
from athena.feature_store.parquet_shard import (
    ShardDriftError,
    ShardOverwriteError,
    export_hour_shard,
)


def parse_hour(spec: str) -> datetime:
    """Accept `YYYY-MM-DDTHH` (UTC implicit) or `now-<N>` (N hours ago, UTC)."""
    if spec.startswith("now-"):
        offset_h = int(spec.split("-", 1)[1])
        now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
        return now - timedelta(hours=offset_h)
    if len(spec) == 13 and spec[10] == "T":
        spec = spec + ":00:00+00:00"
    dt = datetime.fromisoformat(spec)
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

    hour = parse_hour(args.hour)
    mode: str = "check" if args.check_only else "fail"
    tables = [t.strip() for t in args.tables.split(",") if t.strip()]

    per_table_count: dict[str, int] = {}
    total_bytes = 0
    total_duration = 0.0
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
