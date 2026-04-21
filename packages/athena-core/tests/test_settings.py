"""Unit tests for athena.core.settings (Story 1.2 AC-3).

`.env` guard is exercised with tmp_path to avoid polluting the real
workspace. Secret accessors are verified with keyring monkeypatching —
never touch the real OS Keychain.
"""

from __future__ import annotations

from pathlib import Path

import keyring as keyring_lib
import pytest
from athena.core.keyring_client import KEYRING_SERVICE, SecretName
from athena.core.settings import (
    Settings,
    _ensure_no_dotenv_files,
    get_settings,
)
from pydantic import ValidationError

# ---------- Settings defaults & frozen contract ----------


def test_settings_defaults() -> None:
    s = Settings()
    assert s.environment == "paper", "default must be paper to prevent accidental prod trades"
    assert s.app_log_level == "INFO"


def test_settings_is_frozen() -> None:
    s = Settings()
    with pytest.raises(ValidationError):
        s.environment = "prod"  # type: ignore[misc]


def test_settings_forbids_extra_kwargs() -> None:
    """extra='forbid' rejects unknown constructor args — fails fast on typos
    in tests or dev harnesses. Note: pydantic-settings silently ignores env
    vars that don't match a declared field; model-level `forbid` governs
    direct kwargs, not the env surface (that is enforced by the field set)."""
    with pytest.raises(ValidationError, match=r"[Ee]xtra"):
        Settings(unknown_field="x")  # type: ignore[call-arg]


def test_settings_accepts_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ATHENA_ENVIRONMENT", "prod")
    assert Settings().environment == "prod"


def test_settings_log_level_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ATHENA_APP_LOG_LEVEL", "DEBUG")
    assert Settings().app_log_level == "DEBUG"


def test_settings_rejects_invalid_environment_literal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ATHENA_ENVIRONMENT", "staging")
    with pytest.raises(ValidationError):
        Settings()


# ---------- .env guard ----------


@pytest.mark.parametrize(
    "filename",
    [".env", ".env.local", ".env.production", ".env.test", ".env.development"],
)
def test_dotenv_guard_raises_on_root_env(tmp_path: Path, filename: str) -> None:
    (tmp_path / filename).write_text("SECRET=x", encoding="utf-8")
    with pytest.raises(SystemExit, match=r"\.env usage forbidden by NFR-S1"):
        _ensure_no_dotenv_files(tmp_path)


def test_dotenv_guard_raises_on_depth_one_subdir(tmp_path: Path) -> None:
    subdir = tmp_path / "packages"
    subdir.mkdir()
    (subdir / ".env").write_text("SECRET=x", encoding="utf-8")
    with pytest.raises(SystemExit, match=r"\.env usage forbidden by NFR-S1"):
        _ensure_no_dotenv_files(tmp_path)


def test_dotenv_guard_excludes_venv_and_bmad(tmp_path: Path) -> None:
    for excluded in (".venv", ".git", "_bmad", "_bmad-output", "build", "dist", "__pycache__"):
        (tmp_path / excluded).mkdir()
        (tmp_path / excluded / ".env").write_text("ignored", encoding="utf-8")
    # Must return silently — no exception.
    _ensure_no_dotenv_files(tmp_path)


def test_dotenv_guard_does_not_recurse_deeper_than_1(tmp_path: Path) -> None:
    """Depth-2 `.env` is NOT detected at import time by design (performance +
    false-positive reduction). The CI-level regression test covers full-tree."""
    deep = tmp_path / "a" / "b"
    deep.mkdir(parents=True)
    (deep / ".env").write_text("SECRET=x", encoding="utf-8")
    _ensure_no_dotenv_files(tmp_path)  # must not raise


def test_dotenv_guard_ignores_env_example(tmp_path: Path) -> None:
    """`.env.example` without content matching `.env.*` glob is still blocked —
    our guard explicitly forbids ANY .env.* variant to kill the template bait."""
    (tmp_path / ".env.example").write_text("PLACEHOLDER=x", encoding="utf-8")
    with pytest.raises(SystemExit, match=r"\.env usage forbidden by NFR-S1"):
        _ensure_no_dotenv_files(tmp_path)


def test_dotenv_guard_returns_on_clean_tree(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("hi", encoding="utf-8")
    (tmp_path / "packages").mkdir()
    (tmp_path / "packages" / "foo.py").write_text("x=1", encoding="utf-8")
    _ensure_no_dotenv_files(tmp_path)  # no exception


def test_dotenv_guard_handles_nonexistent_root(tmp_path: Path) -> None:
    _ensure_no_dotenv_files(tmp_path / "does-not-exist")  # no exception


# ---------- get_settings singleton ----------


def test_get_settings_is_singleton() -> None:
    get_settings.cache_clear()
    a = get_settings()
    b = get_settings()
    assert a is b


# ---------- Secret accessor delegation + no-caching ----------


def test_secret_accessor_delegates_to_keyring(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str] = {}

    def fake_get(service: str, username: str) -> str:
        captured["service"] = service
        captured["username"] = username
        return "fake-value"

    monkeypatch.setattr(keyring_lib, "get_password", fake_get)
    assert Settings().kis_order_app_key() == "fake-value"
    assert captured["service"] == KEYRING_SERVICE
    assert captured["username"] == SecretName.KIS_ORDER_APP_KEY.value


def test_secret_accessor_does_not_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """Each call MUST re-hit keyring — memory lifetime minimisation."""
    counter = {"n": 0}

    def counting_get(service: str, username: str) -> str:
        counter["n"] += 1
        return f"v{counter['n']}"

    monkeypatch.setattr(keyring_lib, "get_password", counting_get)
    s = Settings()
    v1 = s.dart_api_key()
    v2 = s.dart_api_key()
    assert counter["n"] == 2, "accessor must re-fetch on every call"
    assert v1 == "v1"
    assert v2 == "v2"


def test_all_14_secret_accessors_exist() -> None:
    """Every SecretName member must have a corresponding Settings method."""
    expected_methods = {member.value.lower() for member in SecretName}
    actual_methods = {
        name
        for name in dir(Settings)
        if not name.startswith("_") and callable(getattr(Settings, name))
    }
    missing = expected_methods - actual_methods
    assert not missing, f"Settings is missing accessor methods for: {missing}"


def test_secret_accessor_raises_when_secret_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """MissingSecretError bubbles up through the accessor — no swallowing."""
    from athena.core.errors import MissingSecretError

    monkeypatch.setattr(keyring_lib, "get_password", lambda s, u: None)
    with pytest.raises(MissingSecretError, match=r"TELEGRAM_BOT_TOKEN"):
        Settings().telegram_bot_token()
