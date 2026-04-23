"""Story 1.4 AC-4 Task 4.3 — Trading PC write-scope architectural invariant.

Defends the D1 / #PT-2 contract: Trading PC writes to the six decisions.duckdb
tables (modules_output, decisions, orders, anti_ego_events, labels_f1 via
FeatureStore; pre_trade_ledger via LedgerClient.append). Direct `INSERT INTO
ticks|quotes|news` from Trading PC code is architecturally forbidden — those
tables are Logger PC's exclusive writer zone, surfaced to Trading PC read-only
via Parquet external scan.

Story 1.5 extension — §Invariant #2: `pre_trade_ledger_raw` is the 6th
table, and its sole Python writer is `athena.execution.ledger.client.LedgerClient
.append`. Any `INSERT INTO pre_trade_ledger_raw` string literal that appears
OUTSIDE `packages/athena-execution/athena/execution/ledger/client.py` is
a scope-widening bug. DuckDB 1.x has no row-level trigger (§Invariant #11),
so this AST check + LedgerClient single entry-point are the defense layers.

Gates:
1. `FeatureStore` exposes exactly 5 `insert_*` methods (the ledger is NOT on
   FeatureStore — it lives on a dedicated client). Adding / removing one
   fails loudly so future stories cannot accidentally widen the write scope.
2. `LedgerClient` exposes exactly one `append` method (single entry-point for
   the ledger; Story 6.1 extends the Literal set but keeps the method signature).
3. String literals in feature_query.py / parquet_reader.py contain no
   `INSERT INTO {ticks,quotes,news}` SQL.
4. String literals `INSERT INTO pre_trade_ledger_raw` or
   `UPDATE pre_trade_ledger` / `DELETE FROM pre_trade_ledger` appear nowhere
   in the repo EXCEPT the LedgerClient module itself.
5. parquet_reader.py additionally forbids any INSERT/UPDATE/DELETE verb in
   any literal — it is a pure read path.

Stage-2 regression (no marker). Story 1.9 will promote this to a ruff custom
rule; the AST form here is the MVP defender.
"""

from __future__ import annotations

import ast
import inspect
import re
from pathlib import Path

from athena.execution.ledger import client as ledger_client_module
from athena.execution.ledger.client import LedgerClient
from athena.feature_store import feature_query, parquet_reader
from athena.feature_store.feature_query import FeatureStore

# FeatureStore keeps 5 insert methods — ledger append lives on LedgerClient,
# NOT on FeatureStore (Story 1.5 §Invariant #2). Pushing ledger into
# FeatureStore would blur the write-path audit trail; the two are kept
# separate so Story 1.9 's ruff rule can target `INSERT INTO
# pre_trade_ledger_raw` in any non-LedgerClient file.
EXPECTED_INSERT_METHODS = frozenset(
    {
        "insert_module_output",
        "insert_decision",
        "insert_order",
        "insert_anti_ego_event",
        "insert_label_f1",
    }
)

# Story 1.5 §Invariant #2 — LedgerClient has ONE write method.
EXPECTED_LEDGER_METHODS = frozenset({"append"})

# Relative path of the LedgerClient module (POSIX form) — the only file
# permitted to contain `INSERT INTO pre_trade_ledger_raw` string literals.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_LEDGER_CLIENT_REL = Path("packages/athena-execution/athena/execution/ledger/client.py").as_posix()

# `\s+` tolerates any whitespace (tabs, multi-spaces, newlines) between the
# tokens — a previous regex required single-space and was silently bypassable
# by adding any extra whitespace. `["'`]?` tolerates quoted identifiers
# (`"ticks"`, 'ticks', `` `ticks` ``) which also bypassed the old pattern.
_LOGGER_INSERT_PATTERN = re.compile(
    r"""\bINSERT\s+INTO\s+["'`]?(ticks|quotes|news)["'`]?\b""",
    re.IGNORECASE,
)
_ANY_WRITE_PATTERN = re.compile(
    r"\b(INSERT|UPDATE|DELETE)\s+(INTO|FROM|SET)\b",
    re.IGNORECASE,
)

# Story 1.5 §Invariant #2 — mutations against the ledger. `_raw` suffix covers
# the physical table; `pre_trade_ledger` (view) writes are also caught
# because UPDATE/DELETE on a view ultimately resolves to the raw table, and
# DuckDB actually raises a catalog error against views but we still forbid
# the literal to prevent confusing code from shipping.
_LEDGER_WRITE_PATTERN = re.compile(
    r"""\b(INSERT\s+INTO|UPDATE|DELETE\s+FROM)\s+["'`]?pre_trade_ledger(_raw)?["'`]?\b""",
    re.IGNORECASE,
)


def _source(module_file: str) -> str:
    return Path(module_file).read_text(encoding="utf-8")


def _docstring_node_ids(tree: ast.Module) -> set[int]:
    """IDs of the ast.Constant nodes that serve as module/class/function
    docstrings. These are string literals by parse but by intent documentation,
    so they must not count as SQL-bearing code."""
    ids: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.body and isinstance(node.body[0], ast.Expr):
                first = node.body[0].value
                if isinstance(first, ast.Constant) and isinstance(first.value, str):
                    ids.add(id(first))
    return ids


def _collect_code_string_literals(source: str) -> list[str]:
    """String literals appearing as code (not docstrings, not comments).

    Includes the static segments of f-strings (`ast.JoinedStr` → inner
    `ast.Constant` children) so `f"INSERT INTO {tbl}"` is still caught.
    A comment `# INSERT INTO ticks` is a COMMENT token, not an ast.Constant,
    so the AST walk naturally filters it out.
    """
    tree = ast.parse(source)
    docstring_ids = _docstring_node_ids(tree)
    literals: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) in docstring_ids:
                continue
            literals.append(node.value)
        elif isinstance(node, ast.JoinedStr):
            for part in node.values:
                if isinstance(part, ast.Constant) and isinstance(part.value, str):
                    literals.append(part.value)
    return literals


def test_feature_store_has_exactly_five_insert_methods() -> None:
    actual = {
        name
        for name, _ in inspect.getmembers(FeatureStore, predicate=inspect.isfunction)
        if name.startswith("insert_")
    }
    missing = EXPECTED_INSERT_METHODS - actual
    extra = actual - EXPECTED_INSERT_METHODS
    assert not missing, f"Missing allowed insert_* methods: {missing}"
    assert not extra, (
        f"Unexpected insert_* methods (scope creep): {extra}; "
        "if a new table joins the Trading PC write scope, update "
        "EXPECTED_INSERT_METHODS and Story 1.4 Source-of-Truth Invariant #3"
    )


def test_feature_query_does_not_write_logger_tables() -> None:
    literals = _collect_code_string_literals(_source(feature_query.__file__))
    violating = [s for s in literals if _LOGGER_INSERT_PATTERN.search(s)]
    assert not violating, (
        "feature_query.py must not INSERT into ticks/quotes/news "
        f"(Logger-owned tables). Offending literals: {violating!r}"
    )


def test_parquet_reader_has_no_write_statements() -> None:
    literals = _collect_code_string_literals(_source(parquet_reader.__file__))
    violating = [s for s in literals if _ANY_WRITE_PATTERN.search(s)]
    assert not violating, (
        "parquet_reader.py is the read path — it must not contain "
        f"INSERT/UPDATE/DELETE. Offending literals: {violating!r}"
    )


# ─── Detector self-tests: prove the scanner catches known-sneaky bypasses ─
#
# The earlier regex form had documented bypasses: extra whitespace,
# quoted identifiers, and f-string assembly all slipped past. These tests
# pin-down that the AST + widened regex catches each of those shapes so a
# future "simplification" can't silently regress the defender.


def test_detector_catches_whitespace_bypass() -> None:
    # `INSERT  INTO ticks` (two spaces) slipped the old single-space regex
    synth = 'conn.execute("INSERT  INTO ticks VALUES (1)")'
    assert _LOGGER_INSERT_PATTERN.search(synth) is not None


def test_detector_catches_quoted_identifier_bypass() -> None:
    # `INSERT INTO "ticks"` slipped the old unquoted-only regex
    synth = "conn.execute('INSERT INTO \"ticks\" VALUES (1)')"
    assert _LOGGER_INSERT_PATTERN.search(synth) is not None


def test_detector_catches_f_string_assembly() -> None:
    # `f"INSERT INTO {tbl}"` — the static literal part of an f-string is
    # collected via ast.JoinedStr walk in _collect_code_string_literals.
    # We emulate this by passing the f-string's literal-only shape.
    synth_source = 'tbl = "ticks"\nconn.execute(f"INSERT INTO {tbl} VALUES (1)")\n'
    literals = _collect_code_string_literals(synth_source)
    # The static prefix before the `{tbl}` placeholder is "INSERT INTO " —
    # on its own this is not yet a full violation because the table name is
    # interpolated. The purpose of this test is to prove the collector reaches
    # into f-string statics so a future direct literal bypass like
    # `f"INSERT INTO ticks {where}"` IS caught — verify that shape here:
    full_synth = 'conn.execute(f"INSERT INTO ticks WHERE {cond}")'
    full_literals = _collect_code_string_literals(full_synth)
    assert any(_LOGGER_INSERT_PATTERN.search(lit) for lit in full_literals), (
        f"f-string static-part collection missed the INSERT; got {full_literals!r}"
    )
    # And the partial-prefix case (`INSERT INTO ` alone) legitimately does
    # NOT fire — that is per-design, otherwise we get false positives.
    assert not any(_LOGGER_INSERT_PATTERN.search(lit) for lit in literals)


def test_ledger_client_has_exactly_one_append_method() -> None:
    """Story 1.5 §Invariant #2 — LedgerClient's public write surface is the
    single `append` method. Adding a sibling writer (update/delete/patch)
    fails this assertion — scope-widening the ledger requires a new Story."""
    actual = {
        name
        for name, _ in inspect.getmembers(LedgerClient, predicate=inspect.isfunction)
        if not name.startswith("_")
    }
    missing = EXPECTED_LEDGER_METHODS - actual
    extra = actual - EXPECTED_LEDGER_METHODS
    assert not missing, f"LedgerClient lost its `append` method: {missing}"
    assert not extra, (
        f"LedgerClient gained a new public write method (scope creep): {extra}. "
        "pre_trade_ledger is append-only per NFR-S3. Update Story 1.5 §Invariant #2 "
        "before extending the write surface."
    )


def test_ledger_writes_only_appear_in_ledger_client() -> None:
    """No file outside the LedgerClient module may contain an
    `INSERT INTO pre_trade_ledger_raw` / `UPDATE pre_trade_ledger*` /
    `DELETE FROM pre_trade_ledger*` literal. Tests are allowed an exemption
    (they exercise DB-level failure modes explicitly, e.g. AC-6 tampered
    payload scenario). The allowlist is narrow on purpose — any non-test,
    non-LedgerClient hit is a bug."""
    py_files = [
        p
        for p in _REPO_ROOT.rglob("*.py")
        if ".venv" not in p.parts
        and "_bmad" not in p.parts
        and "_bmad-output" not in p.parts
        and "build" not in p.parts
        and "dist" not in p.parts
    ]
    offenders: list[str] = []
    for path in py_files:
        rel = path.relative_to(_REPO_ROOT).as_posix()
        if rel == _LEDGER_CLIENT_REL:
            continue
        # Tests are allowed — they exercise the forbidden path to prove
        # defense layers fire (AC-6 verify_chain tampered-payload scenario).
        if "/tests/" in "/" + rel or rel.startswith("tests/"):
            continue
        try:
            literals = _collect_code_string_literals(_source(str(path)))
        except SyntaxError:
            continue
        hits = [lit for lit in literals if _LEDGER_WRITE_PATTERN.search(lit)]
        if hits:
            offenders.append(f"{rel}: {hits!r}")
    assert not offenders, "Only LedgerClient may write pre_trade_ledger. Offenders:\n" + "\n".join(
        offenders
    )


def test_ledger_client_module_contains_insert_into_raw() -> None:
    """Positive control — if the file stops containing `INSERT INTO
    pre_trade_ledger_raw`, the negative scan above becomes vacuous. Detect
    that regression by requiring the literal to be present in exactly the
    LedgerClient module."""
    literals = _collect_code_string_literals(_source(ledger_client_module.__file__))
    assert any(_LEDGER_WRITE_PATTERN.search(lit) for lit in literals), (
        "LedgerClient no longer contains an INSERT INTO pre_trade_ledger_raw "
        "literal — the pattern-based regression test above is now vacuous."
    )


def test_detector_skips_docstring_mentioning_pattern() -> None:
    """A docstring that textually contains `INSERT INTO ticks` (for
    documentation purposes) must NOT trigger the detector — the earlier
    raw-source regex had a known false-positive here that the author
    worked around by rephrasing prose (Debug Log #8). The AST walk skips
    module/function/class docstrings explicitly."""
    synth_source = '"""Module docstring mentioning INSERT INTO ticks as a forbidden pattern."""\n'
    literals = _collect_code_string_literals(synth_source)
    # Docstring excluded → no literals to scan → no violations
    violating = [s for s in literals if _LOGGER_INSERT_PATTERN.search(s)]
    assert not violating, f"docstring was scanned as code — false positive: {violating!r}"
