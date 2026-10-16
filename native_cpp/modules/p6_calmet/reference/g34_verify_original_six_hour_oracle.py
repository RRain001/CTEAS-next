#!/usr/bin/env python3
"""G34A: verify an independent original CALMET six-hour oracle.

This validates ORIGINAL-vs-ORIGINAL first-hour causal stability and the
subsequent five actual original 45-field output groups. It does NOT assert
native C++ 6h scientific parity; that is a separate blocking G34B gate.
Neither original file may come from the native P6F candidate.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path

from g31_extract_original_science_hour import layout


def utc_clock(code: int, second: int) -> dt.datetime:
    year = code // 100000
    day = (code // 100) % 1000
    hour = code % 100
    if not 2000 <= year <= 2100 or not 1 <= day <= 366 or not 0 <= hour <= 24:
        raise ValueError(f"G34A invalid literal CALMET clock {code} {second}")
    if not 0 <= second <= 3600:
        raise ValueError(f"G34A invalid original seconds {second}")
    return dt.datetime(year, 1, 1, tzinfo=dt.timezone.utc) + dt.timedelta(
        days=day - 1, hours=hour, seconds=second
    )


def inspect(one: Path, six: Path) -> dict:
    if one.resolve() == six.resolve():
        raise ValueError("G34A same original output file used for 1h and 6h")
    single = layout(one, "G34A_literal_original_one_hour")
    multiple = layout(six, "G34A_literal_original_six_hours")
    if len(single["groups"]) != 1 or len(multiple["groups"]) != 6:
        raise ValueError("G34A requires exactly 1 and 6 genuine original 45-field groups")
    if single["static"] != multiple["static"]:
        raise ValueError("G34A original 1h/6h physical static records differ")
    first = single["groups"][0]
    if tuple(x[5] for x in first) != tuple(x[5] for x in multiple["groups"][0]):
        raise ValueError("G34A original first-hour 45 field payloads changed with run horizon")

    ranges = []
    for group in multiple["groups"]:
        a, asec, b, bsec = group[0][1:5]
        start, end = utc_clock(a, asec), utc_clock(b, bsec)
        if end - start != dt.timedelta(hours=1):
            raise ValueError(f"G34A non-hourly original output interval: {a} {asec} {b} {bsec}")
        if ranges and ranges[-1][1] != start:
            raise ValueError(f"G34A original multi-hour gap/overlap at {start.isoformat()}")
        ranges.append((start, end))
    if multiple["groups"][0][0][1:5] != first[0][1:5]:
        raise ValueError("G34A original single/multihour first clock disagrees")
    return {
        "status": "PASS_ORIGINAL_SIX_HOUR_ORACLE_ONLY",
        "scope": "literal original 2SS/2US CALMET 6h output and original-vs-original first-hour causal stability; C++ 6h 45-field parity NOT TESTED",
        "one_hour_original_sha256": hashlib.sha256(one.read_bytes()).hexdigest(),
        "six_hour_original_sha256": hashlib.sha256(six.read_bytes()).hexdigest(),
        "original_hour_count": 6,
        "fields_per_hour": 45,
        "first_hour_original_real4_record_bytes": "BIT_IDENTICAL",
        "source_hour_ranges_utc": [[a.isoformat(), b.isoformat()] for a, b in ranges],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--one-hour", type=Path, required=True)
    parser.add_argument("--six-hour", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    try:
        evidence = inspect(args.one_hour, args.six_hour)
    except Exception as error:
        evidence = {"status": "BLOCKED", "reason": str(error),
                    "scope": "G34A original-only; no native C++ multi-hour science"}
        args.out.write_text(json.dumps(evidence, indent=2) + "\n")
        raise
    args.out.write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
