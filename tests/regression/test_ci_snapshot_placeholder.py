"""Story 1.3 Task 3.3 — CI stage-4 snapshot placeholder.

Explicit skip so stage-4 exits 0 without fixtures. Epic 2 Story 2.1 populates
the historical-failure S_entry fixture and removes this skip.
"""

from __future__ import annotations

import pytest


@pytest.mark.snapshot
def test_snapshot_fixture_pending() -> None:
    pytest.skip("SNAPSHOT_FIXTURE_MISSING — Epic 2 Story 2.1 populates fixture")
