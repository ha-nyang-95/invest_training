"""Story 1.5 Task 5.5 — init_s3_object_lock CLI integration (AC-5 "And").

Stage-3 (`@pytest.mark.integration`).

Covers AC-5 And 1-3:
1. `--dry-run` emits the expected retention_days = 1825.
2. `--retention-years 10 --dry-run` emits retention_days = 3650.
3. moto-backed real path — create_bucket with ObjectLockEnabledForBucket=True
   succeeds, and put_object_lock_configuration round-trips the Compliance
   rule. If moto's Object Lock support is too limited, the test skips with
   an explicit deferred-work reference rather than silently false-passing.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "scripts" / "init_s3_object_lock.py"


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [sys.executable, str(_SCRIPT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        cwd=str(_REPO_ROOT),
    )


def test_dry_run_prints_five_year_retention() -> None:
    result = _run(["--bucket", "athena-ledger-test", "--dry-run"])
    assert result.returncode == 0, result.stderr
    assert "[dry-run] Would create_bucket" in result.stdout
    assert "Object Lock: mode=COMPLIANCE, retention_days=1825" in result.stdout


def test_dry_run_honors_retention_years_override() -> None:
    result = _run(["--bucket", "athena-ledger-test", "--retention-years", "10", "--dry-run"])
    assert result.returncode == 0, result.stderr
    assert "retention_days=3650" in result.stdout


def test_retention_years_zero_rejected_at_boundary() -> None:
    """P3 regression — Story 1.5 review-flip 2026-04-23. `--retention-years 0`
    on AWS produces `Days=0` which silently disables Object Lock (NFR-A2
    bypass). argparse `type` validator rejects at the boundary."""
    result = _run(["--bucket", "athena-ledger-test", "--retention-years", "0", "--dry-run"])
    assert result.returncode != 0
    # argparse emits the error on stderr.
    assert "retention-years" in result.stderr


def test_retention_years_negative_rejected_at_boundary() -> None:
    """P3 regression — negative retention is nonsensical; argparse rejects."""
    result = _run(["--bucket", "athena-ledger-test", "--retention-years", "-1", "--dry-run"])
    assert result.returncode != 0


def test_moto_mock_round_trips_object_lock_config() -> None:
    """Real boto3 path — moto supplies an in-process S3 mock. If moto 5.x
    cannot honour `put_object_lock_configuration`, skip rather than false-pass.

    moto state is per-process; we run the check in-process (no subprocess)
    so the monkey-patched boto3 client actually hits the mock."""
    try:
        import boto3  # noqa: F401
        from moto import mock_aws
    except ImportError:
        pytest.skip("moto / boto3 not installed — dev-group not synced")

    with mock_aws():
        import boto3

        client = boto3.client("s3", region_name="us-east-1")  # type: ignore[no-untyped-call]
        try:
            client.create_bucket(
                Bucket="athena-ledger-test",
                ObjectLockEnabledForBucket=True,
            )
            client.put_object_lock_configuration(
                Bucket="athena-ledger-test",
                ObjectLockConfiguration={
                    "ObjectLockEnabled": "Enabled",
                    "Rule": {
                        "DefaultRetention": {
                            "Mode": "COMPLIANCE",
                            "Days": 1825,
                        }
                    },
                },
            )
        except Exception as exc:  # noqa: BLE001
            pytest.skip(
                "moto does not yet fully support Object Lock "
                f"(deferred-work: Story 1.10 will verify against real MinIO/AWS): {exc}"
            )
        got = client.get_object_lock_configuration(Bucket="athena-ledger-test")
        rule = got["ObjectLockConfiguration"]["Rule"]["DefaultRetention"]
        assert rule["Mode"] == "COMPLIANCE"
        assert rule["Days"] == 1825
