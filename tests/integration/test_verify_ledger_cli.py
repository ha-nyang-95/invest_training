"""Story 1.5 Task 6.4 — verify_ledger CLI integration (AC-6 "And").

Stage-3 (`@pytest.mark.integration`).

Covers AC-6 And 1-4:
1. Clean ledger → exit 0 + verdict "OK".
2. Tampered → exit 1 + verdict "CHAIN_BROKEN" + non-empty mismatches.
3. Missing DB file → exit 1 + verdict "VERIFY_FAILED" + error key.
4. `--prev-segment-json` attaches segment_continuity block to output.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from athena.execution.ledger import LedgerClient
from athena.feature_store.duckdb_client import open_decisions_duckdb

pytestmark = pytest.mark.integration

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "scripts" / "verify_ledger.py"


def _seed(db_path: Path) -> None:
    with open_decisions_duckdb(db_path) as conn:
        client = LedgerClient(conn)
        for i in range(2):
            client.append(event_type="schema_segment_transition", payload={"i": i})


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [sys.executable, str(_SCRIPT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        cwd=str(_REPO_ROOT),
    )


def test_clean_ledger_exits_zero_with_verdict_ok(tmp_path: Path) -> None:
    db_path = tmp_path / "decisions.duckdb"
    _seed(db_path)
    result = _run(["--db", str(db_path)])
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["verdict"] == "OK"
    assert payload["mismatches"] == []


def test_tampered_ledger_exits_one_with_chain_broken(tmp_path: Path) -> None:
    db_path = tmp_path / "decisions.duckdb"
    _seed(db_path)
    with open_decisions_duckdb(db_path) as conn:
        conn.execute(
            "UPDATE pre_trade_ledger_raw SET payload_json = ? WHERE id = 2",
            ['{"tampered":true}'],
        )
    result = _run(["--db", str(db_path)])
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["verdict"] == "CHAIN_BROKEN"
    assert payload["mismatches"], "expected at least one mismatch entry"


def test_missing_db_reports_verify_failed(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist.duckdb"
    result = _run(["--db", str(missing)])
    # open_decisions_duckdb creates the parent dir but an empty duckdb file
    # won't have pre_trade_ledger — the SELECT fails. Accept either failure
    # mode as long as the verdict is non-OK and an error is surfaced.
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["verdict"] == "VERIFY_FAILED"
    assert "error" in payload


def test_prev_segment_json_populates_continuity(tmp_path: Path) -> None:
    db_path = tmp_path / "decisions.duckdb"
    _seed(db_path)
    prev_seg = {
        "month": "2025-12",
        "segment_hash": "cafe" * 16,  # 64 chars
    }
    prev_path = tmp_path / "segment_hash.json"
    prev_path.write_text(json.dumps(prev_seg), encoding="utf-8")

    # Read the genesis row's month so we can target a non-empty window.
    with open_decisions_duckdb(db_path) as conn:
        row = conn.execute(
            "SELECT EXTRACT(year FROM created_at_utc), EXTRACT(month FROM created_at_utc) "
            "FROM pre_trade_ledger WHERE id = 1"
        ).fetchone()
    assert row is not None
    year, month = int(row[0]), int(row[1])

    result = _run(
        [
            "--db",
            str(db_path),
            "--prev-segment-json",
            str(prev_path),
            "--year",
            str(year),
            "--month",
            str(month),
        ]
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["verdict"] == "OK"
    continuity = payload["segment_continuity"]
    assert continuity is not None
    assert continuity["prev_segment_hash"] == prev_seg["segment_hash"]
    assert continuity["prev_month"] == prev_seg["month"]
    assert continuity["this_month"] == f"{year:04d}-{month:02d}"
