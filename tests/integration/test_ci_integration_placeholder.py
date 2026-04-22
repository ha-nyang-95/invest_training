"""Story 1.3 Task 3.2 — CI stage-3 integration placeholder.

Keeps stage-3 from exiting 5 (pytest "no tests collected"). Real J1-J5 broker
integration scenarios land in Epic 4/5.
"""

from __future__ import annotations

import pytest


@pytest.mark.integration
def test_integration_stage_reachable() -> None:
    assert True
