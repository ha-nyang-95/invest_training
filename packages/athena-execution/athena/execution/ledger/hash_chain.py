"""SHA-256 entry-hash chain for pre_trade_ledger (and future anti_ego_events).

Source-of-truth: Story 1.5 AC-2 / §Invariant #3, #4.

The input layout is deliberately more than the epics.md narrative
`SHA256(payload_json || policy_version_git_sha)` — we fold `event_type` and
`user_id` into the hash as well so that:
* a payload replay under a different event_type (genesis → schema transition)
  cannot collide with a legitimate entry,
* a future multi-user (V1.1+) enabled ledger cannot silently mix user_id=1
  and user_id=2 chains.

The extension is documented in Dev Notes §Invariant #3 and in the Change Log.
Fields are joined with the `\x00` null byte. U+0000 is technically a valid
UTF-8 code point (encoded as a single `\x00` byte), so the separator is not
universally unambiguous — the concatenation is only unambiguous because
each of the hashed components, by construction, cannot contain a raw NUL:

* `payload_json` comes exclusively from `canonical_json` (= `json.dumps`),
  which escapes U+0000 as the 6-char sequence `\\u0000` rather than emitting
  a raw NUL byte. See the `canonical_json` docstring.
* `policy_version_git_sha` is 40-char lowercase hex (git SHA) — no NUL.
* `event_type` is a `LedgerEventTypeV1` Literal (`genesis` /
  `schema_segment_transition`) — no NUL.
* `user_id` is `str(int)` — digits only, no NUL.
* `prev_hash` is 64-char lowercase hex or empty string — no NUL.

A future Story that widens `event_type` (Story 6.1) or `payload_json`
serialization MUST preserve this no-raw-NUL invariant or switch to a
length-prefixed framing.

Canonical JSON is the single serialization path. Every future Story (3.1,
6.1, 6.2) that computes or verifies ledger hashes MUST call `canonical_json`
rather than re-implementing its own `json.dumps`.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

HASH_PLACEHOLDER: str = "0" * 64
"""Sentinel reserved for unit tests only — MUST NOT appear as a persisted
`this_hash` value. Regression grep (Task 2.3 scenario 8) enforces this."""


def canonical_json(payload: dict[str, Any]) -> str:
    """Deterministic JSON — sort_keys + minimal separators + default=str.

    `default=str` lets Decimal / datetime / UUID serialize without requiring
    callers to pre-convert. Hash reproducibility depends on every serializer
    agreeing bit-for-bit, so all ledger payload serialization MUST go through
    this function — do NOT call `json.dumps` directly from ledger code.
    """
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def compute_entry_hash(
    *,
    prev_hash: str | None,
    payload_json: str,
    policy_version_git_sha: str,
    event_type: str,
    user_id: int,
) -> str:
    """Entry hash — input order and separator are part of the specification.

    Genesis (prev_hash=None):
        SHA256(b"" || payload_json || policy_version_git_sha || event_type || user_id)
    Non-genesis:
        SHA256(prev_hash || payload_json || policy_version_git_sha || event_type || user_id)

    Separator: b"\\x00". U+0000 is valid UTF-8, but by module-level
    construction (see module docstring) none of the hashed components can
    contain a raw NUL — `canonical_json` escapes U+0000 as "\\u0000", hex
    fields are `[0-9a-f]`, `event_type` is a constrained Literal, and
    `user_id` is digits-only — so the concatenation is unambiguous without
    length prefixes.
    """
    sep = b"\x00"
    prev = (prev_hash or "").encode("ascii")
    body = sep.join(
        [
            prev,
            payload_json.encode("utf-8"),
            policy_version_git_sha.encode("ascii"),
            event_type.encode("utf-8"),
            str(user_id).encode("ascii"),
        ]
    )
    return hashlib.sha256(body).hexdigest()


__all__ = ["HASH_PLACEHOLDER", "canonical_json", "compute_entry_hash"]
