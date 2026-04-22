"""Hourly append-only Parquet shard export from features_logger.duckdb.

Source: Story 1.4 AC-2; architecture.md#D1 (hot DuckDB + cold Parquet + rsync),
#Naming-Patterns line 412 (`{table}/year=YYYY/month=MM/day=DD/hour=HH/symbol=XXX.parquet`).

Runs on Logger PC. Called once per hour (XX:01 cron) for the prior UTC hour.
One parquet file per (table, symbol) pair per hour; empty symbols skipped. News
rows with `symbol IS NULL` land under the literal `symbol=__NULL__` partition.

Idempotency contract:
- mode="fail"  — re-calling with data already written raises ShardOverwriteError.
- mode="check" — re-writes to tmp + reads existing, compares dataframes for
  data equality. Drift raises ShardDriftError with the existing file's SHA-256
  in context for the operator.

Architectural invariant #4: once a shard is written, it is immutable. Forced
regeneration requires manual file deletion + re-run (audit-evident).
"""

from __future__ import annotations

import hashlib
import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Literal

import duckdb
import polars as pl
from pydantic import BaseModel, ConfigDict

_SYMBOL_NULL_SENTINEL = "__NULL__"
# Legal symbol character class — conservative. KRX tickers are 6-digit numeric
# today, but accepting alnum + `_` + `-` covers future cross-market expansion
# without permitting filesystem-hostile bytes (`/`, `\`, `:`, NUL, path
# separators, glob metacharacters). Length cap 32 prevents pathological
# filename blowup.
_SYMBOL_VALID_RE = re.compile(r"^[A-Za-z0-9_\-]{1,32}$")


def _validate_symbol(sym: str) -> None:
    """Reject symbols that would collide with the NULL sentinel or produce
    unsafe filesystem paths. Runs per-export on every unique symbol in the
    hour's dataset — upstream DTO validation (NOT NULL, min_length=1) guards
    against NULL/empty, but does not bound characters."""
    if sym == _SYMBOL_NULL_SENTINEL:
        raise ValueError(
            f"Symbol literal collides with NULL sentinel {_SYMBOL_NULL_SENTINEL!r}; "
            "adversarial row or mis-configured DTO"
        )
    if not _SYMBOL_VALID_RE.match(sym):
        raise ValueError(
            f"Symbol contains unsupported characters: {sym!r}; "
            f"allowed pattern {_SYMBOL_VALID_RE.pattern}"
        )


_TIME_COL: dict[str, str] = {
    "ticks": "timestamp",
    "quotes": "timestamp",
    "news": "published_at_utc",
}


class ShardExportResult(BaseModel):
    """Result of one export_hour_shard call (one table, one hour)."""

    model_config = ConfigDict(frozen=True)

    table: str
    hour_utc: datetime
    files_written: int
    files_matched: int
    bytes_written: int
    symbols: tuple[str, ...]
    duration_seconds: float


class ShardError(Exception):
    """Base class for shard-export errors. Subclasses set a stable error_code."""

    error_code: str = "SHARD_UNKNOWN"

    def __init__(self, message: str, **context: Any) -> None:
        super().__init__(message)
        self.context: dict[str, Any] = context


class ShardOverwriteError(ShardError):
    """Raised in mode='fail' when a shard file already exists at the target path.

    Defends architecture.md invariant: prior-hour files are never modified.
    """

    error_code = "SHARD_ALREADY_EXISTS"


class ShardDriftError(ShardError):
    """Raised in mode='check' when existing shard data differs from fresh query."""

    error_code = "SHARD_DRIFT"


def _partition_dir(out_root: Path, table: str, hour: datetime) -> Path:
    return (
        out_root
        / table
        / f"year={hour.year:04d}"
        / f"month={hour.month:02d}"
        / f"day={hour.day:02d}"
        / f"hour={hour.hour:02d}"
    )


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _data_equals(existing: pl.DataFrame, fresh: pl.DataFrame) -> bool:
    """Order-insensitive, column-order-insensitive data comparison.

    Parquet file bytes are not deterministic across writes (row-group metadata,
    writer version). The semantic contract of mode='check' is data identity,
    which we verify by reading the existing shard back and comparing sorted
    frames column-by-column.

    Robustness notes:
    - `null_equal=True`: two NULLs at the same cell compare equal (Polars
      default treats NULL != NULL per SQL semantics — wrong for shard parity).
    - `nulls_last=True` on sort: stable, platform-independent null ordering.
    - Row-count prefilter: short-circuits a common drift class (one frame has
      a duplicate or dropped row) that sort+equals alone can miss if the
      sort keys collide.
    """
    cols = sorted(existing.columns)
    if sorted(fresh.columns) != cols:
        return False
    if existing.height != fresh.height:
        return False
    e = existing.select(cols).sort(cols, nulls_last=True)
    f = fresh.select(cols).sort(cols, nulls_last=True)
    return e.equals(f, null_equal=True)


def export_hour_shard(
    conn: duckdb.DuckDBPyConnection,
    table: str,
    hour_utc_start: datetime,
    out_root: Path,
    *,
    mode: Literal["fail", "check"] = "fail",
) -> ShardExportResult:
    """Export one (table, hour) slice as per-symbol Parquet files under out_root."""
    if table not in _TIME_COL:
        raise ValueError(f"Unknown table {table!r}; expected one of {sorted(_TIME_COL)}")
    # Guard against naive datetimes: DuckDB binds a naive python datetime as a
    # plain TIMESTAMP (session-TZ interpreted) against a TIMESTAMPTZ column, so
    # a KST-host call with naive input silently shifts the window by 9h and
    # returns zero rows — data loss invisible until the downstream query.
    if hour_utc_start.tzinfo is None or hour_utc_start.tzinfo.utcoffset(hour_utc_start) is None:
        raise ValueError("hour_utc_start must be timezone-aware (UTC); naive datetime forbidden")

    t0 = time.perf_counter()
    hour_end = hour_utc_start + timedelta(hours=1)
    time_col = _TIME_COL[table]

    # `table` and `time_col` both come from the fixed _TIME_COL whitelist above,
    # so the f-string cannot be user-controlled SQL. Parameter binding is used
    # for the time range bounds (DuckDB handles TIMESTAMPTZ as a bind parameter).
    df = conn.execute(
        f"SELECT * FROM {table} "  # noqa: S608
        f'WHERE "{time_col}" >= ? AND "{time_col}" < ? '
        f'ORDER BY symbol NULLS LAST, "{time_col}"',
        [hour_utc_start, hour_end],
    ).pl()

    partition_dir = _partition_dir(out_root, table, hour_utc_start)
    if df.is_empty():
        return ShardExportResult(
            table=table,
            hour_utc=hour_utc_start,
            files_written=0,
            files_matched=0,
            bytes_written=0,
            symbols=(),
            duration_seconds=time.perf_counter() - t0,
        )

    files_written = 0
    files_matched = 0
    bytes_written = 0
    symbols_written: list[str] = []

    unique_syms = df.select("symbol").unique(maintain_order=True).get_column("symbol").to_list()
    for sym_value in unique_syms:
        sub_df = (
            df.filter(pl.col("symbol").is_null())
            if sym_value is None
            else df.filter(pl.col("symbol") == sym_value)
        )
        if sub_df.is_empty():
            continue
        if sym_value is None:
            part_sym = _SYMBOL_NULL_SENTINEL
        else:
            part_sym = str(sym_value)
            _validate_symbol(part_sym)
        out_file = partition_dir / f"symbol={part_sym}.parquet"

        if out_file.exists():
            if mode == "fail":
                raise ShardOverwriteError(
                    f"Shard already exists: {out_file}",
                    path=str(out_file),
                    existing_sha256=_sha256_file(out_file),
                )
            existing = pl.read_parquet(out_file)
            if _data_equals(existing, sub_df):
                files_matched += 1
                continue
            raise ShardDriftError(
                f"Shard data drift: {out_file}",
                path=str(out_file),
                existing_sha256=_sha256_file(out_file),
            )

        out_file.parent.mkdir(parents=True, exist_ok=True)
        # Atomic write: if the Logger PC is killed mid-write (power cut, OOM,
        # systemd timeout) a direct write to `out_file` leaves a truncated
        # Parquet behind, and the next hour's mode='fail' call sees it as
        # SHARD_ALREADY_EXISTS — permanently blocking that hour's export
        # until an operator deletes the corrupt file. rsync may also ship
        # the truncated file onward. Writing to a PID-suffixed tmp file
        # then atomically renaming keeps `out_file.exists()` false until
        # the Parquet is valid. See emit_logger_sync_metric.py for the
        # same pattern on the observability side.
        tmp_file = out_file.with_suffix(f"{out_file.suffix}.tmp.{os.getpid()}")
        try:
            sub_df.write_parquet(tmp_file, compression="zstd", compression_level=3)
            tmp_file.replace(out_file)
        except BaseException:
            tmp_file.unlink(missing_ok=True)
            raise
        files_written += 1
        bytes_written += out_file.stat().st_size
        symbols_written.append(part_sym)

    return ShardExportResult(
        table=table,
        hour_utc=hour_utc_start,
        files_written=files_written,
        files_matched=files_matched,
        bytes_written=bytes_written,
        symbols=tuple(symbols_written),
        duration_seconds=time.perf_counter() - t0,
    )
