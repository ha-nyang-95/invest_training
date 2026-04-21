"""Test isolation for athena-core test suite.

Autouse fixture rationale (Story 1.2 review 2026-04-22, P10):

- Clears all `ATHENA_*` env vars before each test so `Settings()` defaults
  are not polluted by the developer's shell (`test_settings_defaults` used
  to break on machines with `ATHENA_ENVIRONMENT=prod` exported).
- Clears `get_settings()`'s lru_cache before AND after each test so a cached
  singleton from a prior test cannot mask a later test's env-override setup.

The autouse fixture composes with per-test `monkeypatch.setenv(...)` calls:
pytest shares one `MonkeyPatch` instance per test function, so the autouse
delenv registers its undo first and each test's setenv layers on top.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest


@pytest.fixture(autouse=True)
def _isolate_athena_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for key in list(os.environ):
        if key.startswith("ATHENA_"):
            monkeypatch.delenv(key, raising=False)

    from athena.core.settings import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
