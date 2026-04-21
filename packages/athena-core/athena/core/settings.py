"""Athena runtime Settings — pydantic-settings BaseSettings + `.env` runtime guard.

Source-of-truth: PRD#NFR-S1 (line 1020, `.env` forever forbidden),
architecture.md#D21 (line 361, pydantic-settings BaseSettings), #AR-CFG5.

Two responsibilities, split by concern:
1. `_ensure_no_dotenv_files` — fail-fast guard that prevents the process
   from starting when `.env` / `.env.*` files exist in the workspace root
   or any depth-1 subdirectory (excluding toolchain dirs). Runs at module
   import as a side effect — the first import of anything that transitively
   touches `athena.core.settings` is the enforcement point.
2. `Settings(BaseSettings)` — runtime flags (environment, log level) +
   non-caching secret accessor methods that delegate to `keyring_client`.
   Secret values are fetched on EVERY call to minimize in-memory lifetime.

The `ATHENA_REPO_ROOT` environment variable overrides the auto-detected
repo root for testing (see `_REPO_ROOT` below). Tests should prefer
calling `_ensure_no_dotenv_files(tmp_path)` directly rather than patching
the repo root, to avoid contaminating the cached module state.
"""

from __future__ import annotations

import os
from fnmatch import fnmatch
from functools import lru_cache
from pathlib import Path
from typing import Final, Literal

from athena.core.keyring_client import SecretName, get_secret
from pydantic_settings import BaseSettings, SettingsConfigDict


def _detect_repo_root() -> Path:
    """Walk up from this file to the workspace root, or honour ATHENA_REPO_ROOT."""
    override = os.environ.get("ATHENA_REPO_ROOT")
    if override:
        return Path(override).resolve()
    # settings.py -> athena/core -> athena -> athena-core -> packages -> <REPO_ROOT>
    return Path(__file__).resolve().parents[4]


_REPO_ROOT: Final[Path] = _detect_repo_root()

_EXCLUDE_DIRS: Final[frozenset[str]] = frozenset(
    {
        ".venv",
        ".git",
        "_bmad",
        "_bmad-output",
        "node_modules",
        "build",
        "dist",
        "__pycache__",
    }
)


def _ensure_no_dotenv_files(root: Path) -> None:
    """Fail-fast: abort process if any `.env` / `.env.*` file exists in scope.

    Scope: `root` itself + all depth-1 subdirectories not in `_EXCLUDE_DIRS`.
    Deeper nesting is deliberately out of scope to prevent the walk from
    sweeping over user home dirs in edge scenarios — `.env` is a repo-level
    convention and depth-1 coverage is sufficient. A follow-up regression
    test (`tests/regression/test_no_dotenv_files.py`) walks the entire
    workspace tree for CI-level defence in depth.

    On match: raises `SystemExit(".env usage forbidden by NFR-S1: found <path>")`
    — message format is fixed by AC-3 and exercised by the regression test.
    """
    if not root.is_dir():
        return

    for item in root.iterdir():
        if _is_dotenv_file(item):
            raise SystemExit(f".env usage forbidden by NFR-S1: found {item}")

    for subdir in root.iterdir():
        if not subdir.is_dir() or subdir.name in _EXCLUDE_DIRS:
            continue
        for item in subdir.iterdir():
            if _is_dotenv_file(item):
                raise SystemExit(f".env usage forbidden by NFR-S1: found {item}")


def _is_dotenv_file(path: Path) -> bool:
    return path.is_file() and (path.name == ".env" or fnmatch(path.name, ".env.*"))


# Import-time enforcement: the first thing any athena runtime touches
# is an ImportError / SystemExit if `.env` is present. No escape hatch.
_ensure_no_dotenv_files(_REPO_ROOT)


class Settings(BaseSettings):
    """Runtime flags (non-secret) + secret accessor methods.

    `SettingsConfigDict(env_file=None)` physically disables `.env` parsing
    inside pydantic-settings. The environment variable surface is limited
    to `ATHENA_*` prefix — ONLY for non-secret runtime flags defined as
    class fields below. Secrets are never exposed as fields; they are
    fetched on each method call via `keyring_client.get_secret` and
    returned directly to the caller (no caching, no logging).
    """

    model_config = SettingsConfigDict(
        env_file=None,
        env_prefix="ATHENA_",
        frozen=True,
        extra="forbid",
        case_sensitive=False,
    )

    environment: Literal["prod", "paper"] = "paper"
    app_log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # --- KIS order credentials (NFR-S2) ---
    def kis_order_app_key(self) -> str:
        return get_secret(SecretName.KIS_ORDER_APP_KEY)

    def kis_order_app_secret(self) -> str:
        return get_secret(SecretName.KIS_ORDER_APP_SECRET)

    def kis_order_account_number(self) -> str:
        return get_secret(SecretName.KIS_ORDER_ACCOUNT_NUMBER)

    # --- KIS query-only credentials (NFR-S2 separation) ---
    def kis_query_app_key(self) -> str:
        return get_secret(SecretName.KIS_QUERY_APP_KEY)

    def kis_query_app_secret(self) -> str:
        return get_secret(SecretName.KIS_QUERY_APP_SECRET)

    # --- External data feeds ---
    def dart_api_key(self) -> str:
        return get_secret(SecretName.DART_API_KEY)

    # --- LLM vendors ---
    def hyperclova_api_key(self) -> str:
        return get_secret(SecretName.HYPERCLOVA_API_KEY)

    def solar_pro_api_key(self) -> str:
        return get_secret(SecretName.SOLAR_PRO_API_KEY)

    # --- Notification channels ---
    def telegram_bot_token(self) -> str:
        return get_secret(SecretName.TELEGRAM_BOT_TOKEN)

    def kakaowork_webhook_url(self) -> str:
        return get_secret(SecretName.KAKAOWORK_WEBHOOK_URL)

    # --- Offsite backup (S3 + SSE-C) ---
    def s3_access_key_id(self) -> str:
        return get_secret(SecretName.S3_ACCESS_KEY_ID)

    def s3_secret_access_key(self) -> str:
        return get_secret(SecretName.S3_SECRET_ACCESS_KEY)

    def s3_sse_c_key(self) -> str:
        return get_secret(SecretName.S3_SSE_C_KEY)

    # --- Encrypted backup disk ---
    def luks_passphrase(self) -> str:
        return get_secret(SecretName.LUKS_PASSPHRASE)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton accessor. The Settings INSTANCE is cached; secret values
    are re-fetched from the keyring on every accessor call (no caching)."""
    return Settings()


__all__ = ["Settings", "get_settings"]
