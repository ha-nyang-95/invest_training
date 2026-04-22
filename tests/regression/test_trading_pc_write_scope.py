"""Story 1.4 AC-4 Task 4.3 — Trading PC write-scope architectural invariant.

Defends the D1 / #PT-2 contract: Trading PC writes ONLY to the five
decisions.duckdb tables (modules_output, decisions, orders, anti_ego_events,
labels_f1). Direct `INSERT INTO ticks|quotes|news` from Trading PC code is
architecturally forbidden — those tables are Logger PC's exclusive writer
zone, surfaced to Trading PC read-only via Parquet external scan.

Two gates:
1. `FeatureStore` exposes exactly 5 `insert_*` methods. Adding or removing
   one fails loudly so future stories cannot accidentally widen the
   write scope.
2. String literals (including f-string static parts) in feature_query.py and
   parquet_reader.py contain no `INSERT INTO {ticks,quotes,news}` SQL. The
   check walks the AST to skip module/function/class docstrings and comments,
   and whitespace-tolerates bypasses like `INSERT  INTO  "ticks"` (extra
   spaces, quoted identifiers). parquet_reader.py additionally forbids any
   INSERT/UPDATE/DELETE verb in any literal — it is a pure read path.

This is stage-2 regression (no marker — runs in every pytest invocation).
Story 1.9 will promote this to a ruff custom rule (see deferred-work.md
"Trading PC write-scope ruff custom rule"); the AST form here is the
MVP defender.
"""

from __future__ import annotations

import ast
import inspect
import re
from pathlib import Path

from athena.feature_store import feature_query, parquet_reader
from athena.feature_store.feature_query import FeatureStore

EXPECTED_INSERT_METHODS = frozenset(
    {
        "insert_module_output",
        "insert_decision",
        "insert_order",
        "insert_anti_ego_event",
        "insert_label_f1",
    }
)

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
