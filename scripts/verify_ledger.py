"""Pre-Trade Ledger integrity verifier — Story 1.5 AC-6 substrate.

Walks `pre_trade_ledger` in id-order and, for each row, recomputes the
`this_hash` from stored columns via `compute_entry_hash`. A mismatch is a
silent-tamper signal. With `--prev-segment-json` also supplied, the script
additionally verifies that the current month's `compute_segment_hash` uses
the previous segment's hash as `prev` — giving a one-step continuity check
between consecutive monthly archives.

Exit contract (Story 5.6 / Story 1.9 will later consume):
* exit 0 with stdout JSON `{"verdict": "OK", ...}` → chain intact.
* exit 1 with `"verdict": "CHAIN_BROKEN"` or `"VERIFY_FAILED"` + error detail.

A non-zero exit is the ONLY signal this substrate emits — Prometheus rule
and Global CB hook (Story 1.9 + 5.6) consume the stdout JSON contract.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb
from athena.core.version import POLICY_VERSION_SHA
from athena.execution.ledger.hash_chain import compute_entry_hash
from athena.execution.ledger.segment_hash import compute_segment_hash
from athena.feature_store.duckdb_client import open_decisions_duckdb


def verify_chain(conn: duckdb.DuckDBPyConnection) -> list[dict[str, object]]:
    """Recompute every row's this_hash + check prev_hash continuity.

    Returns a list of mismatch records (empty list means the chain is intact).
    Each record has a `kind` of either `prev_hash_chain_break` or
    `this_hash_mismatch`. The two kinds are orthogonal — a row may raise one,
    the other, or both.
    """
    rows = conn.execute(
        "SELECT id, event_type, policy_version_git_sha, user_id, "
        "payload_json, prev_hash, this_hash FROM pre_trade_ledger ORDER BY id"
    ).fetchall()
    mismatches: list[dict[str, object]] = []
    last_this: str | None = None
    for row in rows:
        eid, ev, psha, uid, pj, prev, this = row
        expected_prev = last_this
        # Genesis is allowed: id=1 + prev=NULL + expected_prev=None.
        is_genesis_ok = eid == 1 and prev is None and expected_prev is None
        if prev != expected_prev and not is_genesis_ok:
            mismatches.append(
                {
                    "id": eid,
                    "kind": "prev_hash_chain_break",
                    "stored_prev": prev,
                    "expected_prev": expected_prev,
                }
            )
        expected_this = compute_entry_hash(
            prev_hash=prev,
            payload_json=pj,
            policy_version_git_sha=psha,
            event_type=ev,
            user_id=uid,
        )
        if this != expected_this:
            mismatches.append(
                {
                    "id": eid,
                    "kind": "this_hash_mismatch",
                    "stored_this": this,
                    "recomputed_this": expected_this,
                }
            )
        last_this = this
    return mismatches


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Verify pre_trade_ledger chain integrity")
    ap.add_argument("--db", type=Path, required=True)
    ap.add_argument(
        "--prev-segment-json",
        type=Path,
        default=None,
        help="Previous month's segment_hash.json — enables continuity check.",
    )
    ap.add_argument("--year", type=int, default=None)
    ap.add_argument("--month", type=int, default=None)
    args = ap.parse_args(argv)

    result: dict[str, object] = {
        "db": str(args.db),
        "verdict": "OK",
        "mismatches": [],
        "segment_continuity": None,
    }

    try:
        with open_decisions_duckdb(args.db) as conn:
            mismatches = verify_chain(conn)
            result["mismatches"] = mismatches
            if mismatches:
                result["verdict"] = "CHAIN_BROKEN"

            if args.prev_segment_json and args.year and args.month:
                prev = json.loads(args.prev_segment_json.read_text(encoding="utf-8"))
                seg = compute_segment_hash(
                    conn,
                    year=args.year,
                    month=args.month,
                    prev_segment_hash=prev["segment_hash"],
                    policy_version_git_sha=POLICY_VERSION_SHA,
                )
                result["segment_continuity"] = {
                    "prev_month": prev["month"],
                    "prev_segment_hash": prev["segment_hash"],
                    "this_segment_hash": seg.segment_hash,
                    "this_month": seg.month,
                }
    except Exception as exc:  # noqa: BLE001 — exit-code boundary
        result["verdict"] = "VERIFY_FAILED"
        result["error"] = str(exc)

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["verdict"] == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
