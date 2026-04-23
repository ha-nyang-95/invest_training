"""KRX trading-day predicate — Story 1.6 AC-2 Task 2.3.

Used as systemd `ExecStartPre=` for athena-readonly-mount-{lock,unlock}.service.

Exit codes:
  0  today (or `--as-of`) IS a KRX trading day → proceed with lock/unlock.
  1  today is a weekend, KR public holiday, or operator-listed extra-closed
     day → skip. The systemd service whitelists exit 1 via SuccessExitStatus
     so the journal stays clean.

The `holidays` library (>=0.50) auto-tracks 공휴일법 amendments + 대체공휴일
without us having to maintain a hardcoded TOML. KRX 임시 휴장 (자연재해 등
short-notice closures) are NOT in `holidays` by design — pass them via
`--extra-closed-days-file`, one ISO date per line.

KRX holiday source for the operator: https://open.krx.co.kr/contents/OPN/04/04020100/OPN04020100.jsp
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import holidays


def _parse_iso_date(raw: str) -> date:
    return date.fromisoformat(raw.strip())


def _load_extra_closed_days(path: Path | None) -> set[date]:
    """Operator-supplied ad-hoc closures (KRX 임시 휴장).

    File format: one ISO-8601 date per line; blank lines and lines starting
    with `#` are ignored. Missing file → empty set (the override is optional).
    """
    if path is None or not path.exists():
        return set()
    out: set[date] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        try:
            out.add(_parse_iso_date(stripped))
        except ValueError:
            # One bad line should not silently exclude all overrides — keep
            # parsing but write a journal-visible warning to stderr.
            print(
                f"check_trading_day: skipping malformed line in {path}: {stripped!r}",
                file=sys.stderr,
            )
    return out


def _classify(
    today: date, *, kr_holidays: holidays.HolidayBase, extra_closed: set[date]
) -> tuple[str, str]:
    """Return (decision, reason). decision ∈ {'trade', 'skip'}."""
    if today.weekday() >= 5:
        return "skip", "weekend"
    if today in kr_holidays:
        return "skip", "holiday"
    if today in extra_closed:
        return "skip", "extra_closed"
    return "trade", "trading_day"


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="check_trading_day",
        description="Exit 0 if today (or --as-of) is a KRX trading day; exit 1 if weekend/holiday.",
    )
    p.add_argument(
        "--as-of",
        type=_parse_iso_date,
        default=None,
        help="Override 'today' for tests / replay. Format: YYYY-MM-DD.",
    )
    p.add_argument(
        "--extra-closed-days-file",
        type=Path,
        default=Path("/etc/athena/extra_closed_days.txt"),
        help="Path to file listing ad-hoc KRX closures (one ISO date per line).",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    today = args.as_of if args.as_of is not None else date.today()  # noqa: DTZ011 — local date intentional
    # `country_holidays` is the typed factory; the `holidays.KR` shorthand
    # is dynamically generated and not visible to mypy.
    kr = holidays.country_holidays("KR", years=today.year)
    extra = _load_extra_closed_days(args.extra_closed_days_file)
    decision, reason = _classify(today, kr_holidays=kr, extra_closed=extra)

    payload = {
        "decision": decision,
        "date": today.isoformat(),
        "reason": reason,
    }
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if decision == "trade" else 1


if __name__ == "__main__":  # pragma: no cover — script entrypoint
    raise SystemExit(main())
