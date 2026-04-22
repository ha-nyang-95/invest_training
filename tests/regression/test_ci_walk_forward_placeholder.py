"""Story 1.3 Task 3.4 — CI stage-5 walk-forward placeholder.

Explicit skip so stage-5 exits 0 without a runner. Epic 8 Story 8.3 implements
`scripts/walk_forward_runner.py` and removes this skip.
"""

from __future__ import annotations

import pytest


@pytest.mark.walk_forward
def test_walk_forward_runner_pending() -> None:
    pytest.skip("WALK_FORWARD_RUNNER_NOT_IMPLEMENTED — Epic 8 Story 8.3")
