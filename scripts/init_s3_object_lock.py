"""Initialise an S3 (or S3-compatible) bucket with Object Lock Compliance mode.

Story 1.5 AC-5. V1.0 pins Compliance + 5-year retention; Story 1.10 wires
this to a real bucket + credentials, Story 6.2 handles per-object retention.

`--dry-run` prints the plan without invoking boto3, so this script can be
exercised in CI / integration tests without AWS credentials. The real boto3
path fetches credentials from OS Keychain (SecretName.S3_ACCESS_KEY_ID /
S3_SECRET_ACCESS_KEY) — plaintext `.env` is forbidden by NFR-S1.
"""

from __future__ import annotations

import argparse
import sys

from athena.execution.ledger.backup import ObjectLockConfig


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Initialise S3 bucket with Object Lock Compliance")
    ap.add_argument(
        "--endpoint-url",
        default=None,
        help="MinIO/localstack endpoint (http://localhost:9000). None = real AWS.",
    )
    ap.add_argument("--bucket", required=True)
    ap.add_argument("--region", default="ap-northeast-2")
    ap.add_argument("--retention-years", type=int, default=5)
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Print plan without any SDK call — no credentials required.",
    )
    args = ap.parse_args(argv)

    cfg = ObjectLockConfig(
        bucket=args.bucket,
        region=args.region,
        retention_years=args.retention_years,
    )

    if args.dry_run:
        print("[dry-run] Would create_bucket + put_object_lock_configuration:")
        print(f"  endpoint_url={args.endpoint_url}")
        print(f"  bucket={cfg.bucket}  region={cfg.region}")
        print(f"  Object Lock: mode={cfg.mode}, retention_days={cfg.retention_years * 365}")
        return 0

    try:
        import boto3  # type: ignore[import-untyped]
        from athena.core.keyring_client import SecretName, get_secret
    except ImportError as exc:
        print(f"ERROR: boto3 / keyring_client import failed: {exc}", file=sys.stderr)
        return 1

    try:
        aws_key = get_secret(SecretName.S3_ACCESS_KEY_ID)
        aws_secret = get_secret(SecretName.S3_SECRET_ACCESS_KEY)
    except Exception as exc:  # noqa: BLE001 — exit-code boundary
        print(
            f"ERROR: OS Keychain missing S3_ACCESS_KEY_ID / S3_SECRET_ACCESS_KEY ({exc})",
            file=sys.stderr,
        )
        return 2

    s3 = boto3.client(
        "s3",
        endpoint_url=args.endpoint_url,
        region_name=cfg.region,
        aws_access_key_id=aws_key,
        aws_secret_access_key=aws_secret,
    )
    try:
        s3.create_bucket(
            Bucket=cfg.bucket,
            CreateBucketConfiguration={"LocationConstraint": cfg.region},
            ObjectLockEnabledForBucket=True,
        )
    except s3.exceptions.BucketAlreadyOwnedByYou:
        print(f"NOTE: bucket {cfg.bucket} already exists — continuing")
    s3.put_object_lock_configuration(
        Bucket=cfg.bucket,
        ObjectLockConfiguration={
            "ObjectLockEnabled": "Enabled",
            "Rule": {
                "DefaultRetention": {
                    "Mode": cfg.mode,
                    "Days": cfg.retention_years * 365,
                }
            },
        },
    )
    s3.put_bucket_versioning(
        Bucket=cfg.bucket,
        VersioningConfiguration={"Status": "Enabled"},
    )
    print(f"[ok] bucket={cfg.bucket} Object Lock Compliance {cfg.retention_years}년 활성")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
