"""Story 1.5 Task 3.5 — monthly_ledger_chain CLI integration (AC-3 "And").

Stage-3 (`@pytest.mark.integration`) — subprocess + DuckDB file + tmp_path.

Covers AC-3 And 1-5:
1. Successful invocation writes both the local + S3-placeholder file with
   bitwise-identical contents.
2. Re-running against an existing chmod-444 target succeeds (the script
   widens the mode before `os.replace`, both on Linux and Windows).
3. `--month 13` fails via argparse with exit 2.
4. `--prev-segment-hash <hex>` is reflected verbatim in the output JSON.
5. Output JSON carries every required key.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from athena.execution.ledger import LedgerClient
from athena.feature_store.duckdb_client import open_decisions_duckdb

pytestmark = pytest.mark.integration

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "scripts" / "monthly_ledger_chain.py"


def _seed_db(db_path: Path) -> tuple[int, int]:
    """Return (year, month) of the genesis row so tests can target a
    non-empty month."""
    with open_decisions_duckdb(db_path) as conn:
        LedgerClient(conn)
        row = conn.execute(
            "SELECT EXTRACT(year FROM created_at_utc), EXTRACT(month FROM created_at_utc) "
            "FROM pre_trade_ledger WHERE id = 1"
        ).fetchone()
        assert row is not None
        return int(row[0]), int(row[1])


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [sys.executable, str(_SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(_REPO_ROOT),
    )


def test_cli_writes_bitwise_identical_local_and_s3_files(tmp_path: Path) -> None:
    db_path = tmp_path / "decisions.duckdb"
    year, month = _seed_db(db_path)
    out_local = tmp_path / "external" / f"year={year}" / f"month={month:02d}" / "segment_hash.json"
    out_s3 = (
        tmp_path
        / "s3"
        / "ledger"
        / "user_id=1"
        / f"year={year}"
        / f"month={month:02d}"
        / "segment_hash.json"
    )
    result = _run(
        [
            "--db",
            str(db_path),
            "--year",
            str(year),
            "--month",
            str(month),
            "--out-local",
            str(out_local),
            "--s3-placeholder",
            str(out_s3),
        ]
    )
    assert result.returncode == 0, result.stderr
    assert out_local.exists() and out_s3.exists()
    assert out_local.read_bytes() == out_s3.read_bytes()
    body = json.loads(out_local.read_text(encoding="utf-8"))
    assert body["entry_count"] == 1
    assert body["first_id"] == 1
    assert body["last_id"] == 1


def test_cli_rerun_over_readonly_target_succeeds(tmp_path: Path) -> None:
    db_path = tmp_path / "decisions.duckdb"
    year, month = _seed_db(db_path)
    out_local = tmp_path / "external" / "segment_hash.json"
    args = [
        "--db",
        str(db_path),
        "--year",
        str(year),
        "--month",
        str(month),
        "--out-local",
        str(out_local),
    ]
    first = _run(args)
    assert first.returncode == 0, first.stderr
    assert (out_local.stat().st_mode & 0o222) == 0  # read-only (no write bits)
    second = _run(args)
    assert second.returncode == 0, (
        f"Re-run over chmod-444 target failed unexpectedly:\n{second.stderr}"
    )
    # Reset mode to 0o644 so pytest tmp_path cleanup can delete the file on
    # Windows (read-only files cannot be removed without widening the mode).
    out_local.chmod(0o644)


def test_cli_month_13_fails_with_argparse_exit_code() -> None:
    result = _run(
        [
            "--db",
            "unused.duckdb",
            "--year",
            "2026",
            "--month",
            "13",
            "--out-local",
            "unused.json",
        ]
    )
    assert result.returncode == 2


def test_cli_reflects_prev_segment_hash_in_output(tmp_path: Path) -> None:
    db_path = tmp_path / "decisions.duckdb"
    year, month = _seed_db(db_path)
    out_local = tmp_path / "external" / "segment_hash.json"
    prev = "deadbeef" * 8  # 64 chars
    result = _run(
        [
            "--db",
            str(db_path),
            "--year",
            str(year),
            "--month",
            str(month),
            "--prev-segment-hash",
            prev,
            "--out-local",
            str(out_local),
        ]
    )
    assert result.returncode == 0, result.stderr
    body = json.loads(out_local.read_text(encoding="utf-8"))
    assert body["prev_segment_hash"] == prev
    # Tidy up for Windows tmp_path removal.
    out_local.chmod(0o644)


def test_cli_output_json_contains_all_required_keys(tmp_path: Path) -> None:
    db_path = tmp_path / "decisions.duckdb"
    year, month = _seed_db(db_path)
    out_local = tmp_path / "external" / "segment_hash.json"
    result = _run(
        [
            "--db",
            str(db_path),
            "--year",
            str(year),
            "--month",
            str(month),
            "--out-local",
            str(out_local),
        ]
    )
    assert result.returncode == 0, result.stderr
    body = json.loads(out_local.read_text(encoding="utf-8"))
    expected_keys = {
        "month",
        "segment_hash",
        "prev_segment_hash",
        "entry_count",
        "first_id",
        "last_id",
        "computed_at_utc",
        "policy_version_git_sha",
    }
    assert set(body.keys()) == expected_keys
    out_local.chmod(0o644)
    # Touch the env var guard (unused but keeps linters from complaining about
    # the `os` import when the Windows-only path below is not exercised).
    _ = os.environ.get("TMPDIR")
