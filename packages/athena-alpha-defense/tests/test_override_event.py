"""OverrideAttemptEvent contract tests — Story 1.6 AC-4 Task 4.3.

Story 3.5 emits this dataclass; Story 3.1 persists `dataclasses.asdict(event)`
into the `anti_ego_events` SHA-256 chain. Both downstreams require:
  * `attempted_at_utc` is timezone-aware (canonical JSON requires
     deterministic ISO-8601 with offset).
  * `target_path` is under `/var/lib/athena/policy/` (watcher invariant).
  * `dataclasses.asdict` returns a dict that can be JSON-serialised with
     `default=str` (no exotic types).
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import PurePosixPath

import pytest
from athena.alpha_defense.f5.override_event import OverrideAttemptEvent


def _valid_event() -> OverrideAttemptEvent:
    return OverrideAttemptEvent(
        attempted_at_utc=datetime(2026, 4, 23, 12, 30, tzinfo=UTC),
        target_path=PurePosixPath("/var/lib/athena/policy/policy.toml"),
        inotify_event_mask="IN_MODIFY",
        attempter_uid=1000,
        attempter_pid=12345,
        mount_state_at_attempt="LOCKED",
    )


def test_naive_datetime_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        OverrideAttemptEvent(
            attempted_at_utc=datetime(2026, 4, 23, 12, 30),  # noqa: DTZ001 — naive intentional
            target_path=PurePosixPath("/var/lib/athena/policy/policy.toml"),
            inotify_event_mask="IN_MODIFY",
            attempter_uid=0,
            attempter_pid=None,
            mount_state_at_attempt="LOCKED",
        )


def test_target_path_outside_protected_root_rejected() -> None:
    with pytest.raises(ValueError, match="/var/lib/athena/policy"):
        OverrideAttemptEvent(
            attempted_at_utc=datetime(2026, 4, 23, 12, 30, tzinfo=UTC),
            target_path=PurePosixPath("/etc/passwd"),
            inotify_event_mask="IN_MODIFY",
            attempter_uid=1000,
            attempter_pid=12345,
            mount_state_at_attempt="LOCKED",
        )


def test_target_path_with_dotdot_rejected() -> None:
    """Post-CR fix (2026-04-23): `str(path).startswith("/var/lib/athena/policy/")`
    previously admitted paths containing `..` because `PurePosixPath` does
    not normalise segments. Explicit `..` rejection is now required.
    """
    with pytest.raises(ValueError, match=r"'\.\.'"):
        OverrideAttemptEvent(
            attempted_at_utc=datetime(2026, 4, 23, 12, 30, tzinfo=UTC),
            target_path=PurePosixPath("/var/lib/athena/policy/../../../etc/shadow"),
            inotify_event_mask="IN_MODIFY",
            attempter_uid=1000,
            attempter_pid=12345,
            mount_state_at_attempt="LOCKED",
        )


def test_asdict_is_json_serialisable_with_default_str() -> None:
    event = _valid_event()
    payload = asdict(event)
    # `default=str` is what Story 3.1 will use for canonical JSON serialisation
    # before SHA-256 hashing. The whole point of this contract test is that
    # this serialisation does not raise.
    rendered = json.dumps(payload, ensure_ascii=False, default=str, sort_keys=True)
    parsed = json.loads(rendered)
    assert parsed["target_path"] == "/var/lib/athena/policy/policy.toml"
    assert parsed["mount_state_at_attempt"] == "LOCKED"
    # `default=str` on a datetime yields `"2026-04-23 12:30:00+00:00"` (the
    # built-in repr). Story 3.1 will prefer `.isoformat()` explicitly, but
    # the round-trip guarantee the contract offers here is just "no exotic
    # types, default=str never raises, UTC offset preserved as +00:00".
    assert "2026-04-23" in parsed["attempted_at_utc"]
    assert "+00:00" in parsed["attempted_at_utc"]
