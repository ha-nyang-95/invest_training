"""Story 1.6 AC-2 Task 2.8 — KRX trading-day predicate CLI tests.

5 scenarios per the AC + a malformed-extra-line resilience scenario:
  1. 신정 (2026-01-01) → exit 1, reason=holiday.
  2. Trading Monday (2026-04-27) → exit 0, decision=trade.
  3. Children's Day (2026-05-05) → exit 1, reason=holiday.
  4. --extra-closed-days-file lists a trading day → exit 1, reason=extra_closed.
  5. Sunday (2026-04-26) → exit 1, reason=weekend.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "check_trading_day.py"


def _run(*args: str) -> tuple[int, dict[str, str]]:
    proc = subprocess.run(  # noqa: S603 — known argv list
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    return proc.returncode, payload


def test_new_year_is_holiday() -> None:
    code, payload = _run("--as-of", "2026-01-01")
    assert code == 1
    assert payload["decision"] == "skip"
    assert payload["reason"] == "holiday"


def test_2026_04_27_monday_is_trading_day() -> None:
    code, payload = _run("--as-of", "2026-04-27")
    assert code == 0
    assert payload["decision"] == "trade"
    assert payload["reason"] == "trading_day"


def test_childrens_day_is_holiday() -> None:
    code, payload = _run("--as-of", "2026-05-05")
    assert code == 1
    assert payload["decision"] == "skip"
    assert payload["reason"] == "holiday"


def test_extra_closed_days_file_overrides_a_trading_day(tmp_path: Path) -> None:
    extra_file = tmp_path / "extra_closed.txt"
    extra_file.write_text(
        "# Operator-supplied KRX 임시 휴장\n2026-04-27\n",
        encoding="utf-8",
    )
    code, payload = _run(
        "--as-of",
        "2026-04-27",
        "--extra-closed-days-file",
        str(extra_file),
    )
    assert code == 1
    assert payload["decision"] == "skip"
    assert payload["reason"] == "extra_closed"


def test_sunday_is_weekend() -> None:
    code, payload = _run("--as-of", "2026-04-26")
    assert code == 1
    assert payload["decision"] == "skip"
    assert payload["reason"] == "weekend"


def test_malformed_extra_lines_do_not_break_parsing(tmp_path: Path) -> None:
    extra_file = tmp_path / "extra_closed.txt"
    extra_file.write_text(
        "# valid blank line below\n\nnot-a-date\n2026-04-27\n",
        encoding="utf-8",
    )
    code, payload = _run(
        "--as-of",
        "2026-04-27",
        "--extra-closed-days-file",
        str(extra_file),
    )
    # Malformed line is ignored; the valid date still triggers skip.
    assert code == 1
    assert payload["reason"] == "extra_closed"
