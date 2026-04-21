"""Unit tests for athena.core.keyring_client (Story 1.2 AC-2).

All keyring backend calls are monkeypatched — tests MUST NOT write to the
real OS Keychain. A stray real write would leave dev-PC residue that could
survive across sessions and contaminate subsequent test runs.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Any

import keyring as keyring_lib
import pytest
from athena.core.errors import MissingSecretError
from athena.core.keyring_client import (
    KEYRING_SERVICE,
    SecretName,
    get_secret,
    set_secret,
)


@pytest.fixture
def fake_store(monkeypatch: pytest.MonkeyPatch) -> Iterator[dict[tuple[str, str], str]]:
    """In-memory substitute for keyring.get_password / set_password."""
    store: dict[tuple[str, str], str] = {}

    def fake_get(service: str, username: str) -> str | None:
        return store.get((service, username))

    def fake_set(service: str, username: str, value: str) -> None:
        store[(service, username)] = value

    monkeypatch.setattr(keyring_lib, "get_password", fake_get)
    monkeypatch.setattr(keyring_lib, "set_password", fake_set)
    yield store


def test_get_secret_returns_value(fake_store: dict[tuple[str, str], str]) -> None:
    fake_store[(KEYRING_SERVICE, "KIS_ORDER_APP_KEY")] = "val"
    assert get_secret(SecretName.KIS_ORDER_APP_KEY) == "val"


def test_get_secret_uses_athena_service(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def spy(service: str, username: str) -> str:
        captured["service"] = service
        captured["username"] = username
        return "v"

    monkeypatch.setattr(keyring_lib, "get_password", spy)
    get_secret(SecretName.DART_API_KEY)
    assert captured["service"] == "athena"
    assert captured["username"] == "DART_API_KEY"


def test_get_secret_raises_missing_error(fake_store: dict[tuple[str, str], str]) -> None:
    del fake_store  # empty store — nothing to fetch
    with pytest.raises(
        MissingSecretError,
        match=r"^KIS_ORDER_APP_KEY not in OS Keychain$",
    ):
        get_secret(SecretName.KIS_ORDER_APP_KEY)


def test_get_secret_accepts_raw_str(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def spy(service: str, username: str) -> str:
        captured["username"] = username
        return "x"

    monkeypatch.setattr(keyring_lib, "get_password", spy)
    assert get_secret("CUSTOM_NAME") == "x"
    assert captured["username"] == "CUSTOM_NAME"


def test_set_secret_calls_keyring_set_password(fake_store: dict[tuple[str, str], str]) -> None:
    set_secret(SecretName.DART_API_KEY, "secret")
    assert fake_store[(KEYRING_SERVICE, "DART_API_KEY")] == "secret"


def test_set_secret_accepts_raw_str(fake_store: dict[tuple[str, str], str]) -> None:
    set_secret("CUSTOM_KEY", "val")
    assert fake_store[(KEYRING_SERVICE, "CUSTOM_KEY")] == "val"


def test_secret_name_registry_size_and_format() -> None:
    assert len(SecretName) == 14, "SecretName registry is frozen at 14 IDs (Story 1.2 AC-2)"

    value_re = re.compile(r"^[A-Z][A-Z0-9_]*$")
    for member in SecretName:
        assert value_re.fullmatch(member.value), (
            f"SecretName.{member.name} value {member.value!r} violates SCREAMING_SNAKE_CASE"
        )

    kis_members = [m for m in SecretName if m.value.startswith("KIS_")]
    assert len(kis_members) == 5, "expected 5 KIS secrets (3 order + 2 query), per NFR-S2"

    other_members = [m for m in SecretName if not m.value.startswith("KIS_")]
    assert len(other_members) == 9, "expected 9 non-KIS secrets (14 total - 5 KIS)"


def test_secret_name_order_query_separation() -> None:
    """NFR-S2 physical separation: order/query keys are distinct IDs."""
    assert SecretName.KIS_ORDER_APP_KEY != SecretName.KIS_QUERY_APP_KEY
    assert SecretName.KIS_ORDER_APP_SECRET != SecretName.KIS_QUERY_APP_SECRET


def test_keyring_service_frozen() -> None:
    assert KEYRING_SERVICE == "athena", "service name is frozen; change = Change Control"


def test_secret_name_str_conversion_equals_value() -> None:
    """StrEnum invariant — ensures `str(SecretName.X) == "X"` for keyring key use."""
    assert str(SecretName.KIS_ORDER_APP_KEY) == "KIS_ORDER_APP_KEY"
