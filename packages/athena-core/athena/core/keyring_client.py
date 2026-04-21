"""OS Keychain 단일 진입점 — `get_secret` / `set_secret` + 14-secret registry.

Source-of-truth: PRD#NFR-S1 (line 1020, `.env` forever forbidden), PRD#NFR-S2
(line 1021, KIS order/query key separation), architecture.md#D7 (line 295,
keyring auto-backend), architecture.md#AR-SEC1.

All API keys, broker credentials, account numbers, and backup passphrases
MUST be fetched through this module. Backend selection is automatic
(wincred on Windows, Secret Service / libsecret on Linux). `.env` files and
plain-text environment variables are BANNED — see `athena.core.settings`
for the `.env` runtime guard.

CRITICAL (AR-COM4 mirror — Story 1.2 Task 2.3 enforces via AST inspection):
This module MUST NOT call subprocess, os.popen, os.system, or shutil at
runtime. Backend selection is delegated to the `keyring` library, which
handles OS primitives internally.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

import keyring
from athena.core.errors import MissingSecretError

KEYRING_SERVICE: Final[str] = "athena"


class SecretName(StrEnum):
    """14 frozen secret IDs — Change Control required to add/rename (NFR-M3).

    Grouping follows architecture.md Integration Points (lines 1017-1028) and
    PRD NFR-S2 (order/query key physical separation).
    """

    # KIS broker — order credentials (NFR-S2: physically separate from query)
    KIS_ORDER_APP_KEY = "KIS_ORDER_APP_KEY"
    KIS_ORDER_APP_SECRET = "KIS_ORDER_APP_SECRET"
    KIS_ORDER_ACCOUNT_NUMBER = "KIS_ORDER_ACCOUNT_NUMBER"

    # KIS broker — query-only credentials (read-only quote/snapshot access)
    KIS_QUERY_APP_KEY = "KIS_QUERY_APP_KEY"
    KIS_QUERY_APP_SECRET = "KIS_QUERY_APP_SECRET"

    # DART (corporate disclosure feed) — FR2
    DART_API_KEY = "DART_API_KEY"

    # LLM vendors — M13 two-stage narrative analysis
    HYPERCLOVA_API_KEY = "HYPERCLOVA_API_KEY"
    SOLAR_PRO_API_KEY = "SOLAR_PRO_API_KEY"

    # Notification channels — heartbeat + kill-switch alerts
    TELEGRAM_BOT_TOKEN = "TELEGRAM_BOT_TOKEN"
    KAKAOWORK_WEBHOOK_URL = "KAKAOWORK_WEBHOOK_URL"

    # Offsite backup — S3 + SSE-C envelope
    S3_ACCESS_KEY_ID = "S3_ACCESS_KEY_ID"
    S3_SECRET_ACCESS_KEY = "S3_SECRET_ACCESS_KEY"
    S3_SSE_C_KEY = "S3_SSE_C_KEY"

    # Local encrypted-disk passphrase (external backup drive, Story 1.10)
    LUKS_PASSPHRASE = "LUKS_PASSPHRASE"


def get_secret(name: SecretName | str) -> str:
    """Fetch a secret from the OS Keychain.

    The raw value is returned ONLY to the caller. Callers must never print,
    log, or otherwise persist the return value outside of in-memory transient
    usage (architecture.md#NFR-S1 mapping, line 1009).

    Empty-string values (`""`) are treated the same as missing — a keyring
    entry cleared to zero length cannot authenticate anything downstream, so
    we surface the clear `MissingSecretError` rather than letting a silent
    empty string propagate to a brittle HTTP 401 later.

    Keyring backend failure (no Secret Service on headless WSL, daemon crash,
    etc.) propagates `keyring.errors.KeyringError` unchanged by design — this
    is an infrastructure / setup failure and Athena's Kill-Switch philosophy
    prefers process death with the root cause preserved over silently folding
    it into the `MissingSecretError` contract.

    Raises:
        MissingSecretError: when the key is absent OR stored as an empty
            string. Message format is fixed by AC-2: `f"{name} not in OS Keychain"`.
        keyring.errors.KeyringError: when the backend itself is unavailable.
    """
    value = keyring.get_password(KEYRING_SERVICE, str(name))
    if not value:
        raise MissingSecretError(f"{name} not in OS Keychain")
    return value


def set_secret(name: SecretName | str, value: str) -> None:
    """Store a secret in the OS Keychain — dev bootstrap only.

    Production secrets MUST be set via OS-native UI: Windows Credential
    Manager (`cmdkey /add:athena`) or Seahorse / `secret-tool store` on Linux.
    Never use this helper inside a shell one-liner that persists to PS1 /
    bash history — the value will be captured in history files and defeats
    the keyring's purpose.
    """
    keyring.set_password(KEYRING_SERVICE, str(name), value)


__all__ = ["KEYRING_SERVICE", "SecretName", "get_secret", "set_secret"]
