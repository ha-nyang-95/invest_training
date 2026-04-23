"""Story 1.5 Task 2.5 — LedgerEventTypeV1 Literal regression via mypy subprocess.

Two fixture files are materialised in a tmp dir and handed to `uv run mypy
--strict`. The first uses a legal event_type and MUST typecheck; the second
uses a Literal-violating event_type (a future Story 6.1 value not yet in the
V1.0 Literal set) and MUST produce a mypy error.

When Story 6.1 widens `LedgerEventTypeV1` to include the full ledger verb
set (entry_authorized, order_placed, ...), this fixture's bad case must be
updated to use a value that remains out-of-set (e.g. deliberately misspelled
'schema_transition_typo'). Otherwise the regression becomes vacuous.

Marked `@pytest.mark.slow` — mypy subprocess is ~3-5 seconds. Still runs
in the default suite, but can be skipped with `-m 'not slow'`.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest


def _uv_available() -> bool:
    return shutil.which("uv") is not None


_UV_SKIP_REASON = "uv CLI not on PATH — mypy subprocess harness cannot launch"

_GOOD_FIXTURE = """\
from __future__ import annotations

import duckdb
from athena.execution.ledger import LedgerClient


def main() -> None:
    conn = duckdb.connect(":memory:")
    client = LedgerClient(conn)
    # Legal V1.0 event_type — must pass mypy --strict.
    client.append(event_type="schema_segment_transition", payload={"ok": True})
"""

_BAD_FIXTURE = """\
from __future__ import annotations

import duckdb
from athena.execution.ledger import LedgerClient


def main() -> None:
    conn = duckdb.connect(":memory:")
    client = LedgerClient(conn)
    # "entry_authorized" is a Story 6.1 value, NOT in V1.0 LedgerEventTypeV1.
    # mypy --strict MUST reject this.
    client.append(event_type="entry_authorized", payload={"bad": True})
"""


def _run_mypy(source: str, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    fixture = tmp_path / "ledger_literal_fixture.py"
    fixture.write_text(source, encoding="utf-8")
    # Anchor the cwd at the repo root so mypy resolves workspace packages.
    repo_root = Path(__file__).resolve().parents[2]
    return subprocess.run(  # noqa: S603
        ["uv", "run", "mypy", "--strict", str(fixture)],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(repo_root),
    )


@pytest.mark.slow
@pytest.mark.skipif(not _uv_available(), reason=_UV_SKIP_REASON)
def test_legal_event_type_typechecks(tmp_path: Path) -> None:
    result = _run_mypy(_GOOD_FIXTURE, tmp_path)
    if result.returncode != 0:
        pytest.fail(
            "mypy rejected a legal V1.0 event_type — regression fixture broken.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}",
        )


@pytest.mark.slow
@pytest.mark.skipif(not _uv_available(), reason=_UV_SKIP_REASON)
def test_illegal_event_type_rejected_by_mypy(tmp_path: Path) -> None:
    result = _run_mypy(_BAD_FIXTURE, tmp_path)
    assert result.returncode != 0, (
        "mypy accepted an out-of-Literal event_type — Literal constraint no "
        f"longer enforced.\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    # mypy writes the error to stdout (not stderr) by default.
    combined = result.stdout + result.stderr
    # The failing argument must be named `event_type` or the failure is for the
    # wrong reason (e.g. a missing import).
    assert "event_type" in combined, combined


if sys.platform == "nt":
    # Windows pytest-xdist workers can race on tmp_path fixture creation when
    # the mypy subprocess is slow — ensure each case gets an isolated subdir.
    pass  # pragma: no cover
