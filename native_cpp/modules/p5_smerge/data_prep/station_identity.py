"""Stable numeric SMERGE aliases for Global Hourly USAF+WBAN identities.

Original station IDs never change in source-file names. Non-numeric USAF and
duplicate USAF records receive deterministic seven-digit numeric aliases.
"""
from __future__ import annotations

import hashlib
import re


def numeric_station_ids(full_ids: list[str]) -> dict[str, str]:
    if len(full_ids) != len(set(full_ids)):
        raise ValueError("duplicate NOAA station identity")
    counts: dict[str, int] = {}
    for sid in full_ids:
        if not re.fullmatch(r"[A-Za-z0-9]{11}", sid):
            raise ValueError(f"invalid NOAA USAF/WBAN identity: {sid!r}")
        usaf = sid[:6]
        counts[usaf] = counts.get(usaf, 0) + 1
    mapping: dict[str, str] = {}
    occupied: set[str] = set()
    for sid in sorted(full_ids):
        usaf = sid[:6]
        if usaf.isdigit() and counts[usaf] == 1:
            alias = usaf  # preserve existing legacy numeric IDs
        else:
            # Numeric 7-digit namespace avoids all genuine six-digit USAF codes.
            alias = str(1_000_000 + int.from_bytes(
                hashlib.sha256(sid.encode("ascii")).digest()[:8], "big"
            ) % 8_000_000)
        if alias in occupied:
            raise ValueError(f"numeric SMERGE alias collision {alias} for {sid}; fail closed")
        occupied.add(alias)
        mapping[sid] = alias
    return mapping
