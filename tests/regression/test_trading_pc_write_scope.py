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
2. Source text of feature_query.py and parquet_reader.py contains no
   `INSERT INTO {ticks,quotes,news}` (and parquet_reader.py has no
   INSERT/UPDATE/DELETE at all — it is a read path).

This is stage-2 regression (no marker — runs in every pytest invocation).
Story 1.9 will promote this to a ruff custom rule; the grep form here is
the MVP defender.
"""

from __future__ import annotations

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


def _source(module_file: str) -> str:
    return Path(module_file).read_text(encoding="utf-8")


def test_feature_query_does_not_write_logger_tables() -> None:
    source = _source(feature_query.__file__)
    pattern = re.compile(r"\bINSERT\s+INTO\s+(ticks|quotes|news)\b", re.IGNORECASE)
    assert not pattern.search(source), (
        "feature_query.py must not INSERT into ticks/quotes/news (Logger-owned tables)"
    )


def test_parquet_reader_has_no_write_statements() -> None:
    source = _source(parquet_reader.__file__)
    # `read_parquet` itself contains `read` — exclude it. Also filter out
    # comments. Simple regex for SQL verbs at word boundary.
    forbidden = re.compile(r"\b(INSERT|UPDATE|DELETE)\s+(INTO|FROM|SET)\b", re.IGNORECASE)
    assert not forbidden.search(source), (
        "parquet_reader.py is the read path — it must not contain INSERT/UPDATE/DELETE"
    )
