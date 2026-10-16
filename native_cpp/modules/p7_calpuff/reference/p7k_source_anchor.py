#!/usr/bin/env python3
"""P7K: locate the CTSG kernel units by call site and pin their spans.

The earlier P7I anchor script found QATR/TFAC/ROTATE with plain-name patterns;
the remaining CTSG kernel units are located here by scanning every vendor
routine header (any `function`/`subroutine` declaration, with optional type
prefix and flexible indentation), recording the exact span, SHA-256 and the
call closure of each unit. `--check` fails when any of them drifts, so the next
port round starts from verified spans.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re

VENDOR_SUBDIR = "engine/vendor/src/CALPUFF_v7.2.1_L150618"
VENDOR_SOURCE = "calpuff.for"
TARGETS = ("munu", "bi", "bji", "bjil", "flopuff", "ctpar", "puffc", "ctsg", "ctrec", "lower",
           "upper", "rotate", "qatr", "tfac")
END_KEYWORDS = {"do", "if", "where", "select", "selectcase", "type", "block", "module", "program",
                "subroutine", "function", "associate", "forall", "critical", "enum", "interface",
                "team", "parallel"}
HEADER = re.compile(r"^\s{0,6}(?:real|integer|logical|double\s+precision)?\s*"
                    r"(?:function|subroutine)\s+([a-z0-9_]+)\s*\(?", re.IGNORECASE)


def locate(vendor: pathlib.Path) -> dict:
    source = vendor / VENDOR_SOURCE
    raw = source.read_bytes()
    lines = raw.decode("latin-1").splitlines()
    headers: dict[str, list[int]] = {}
    for index, line in enumerate(lines):
        match = HEADER.match(line)
        if match:
            headers.setdefault(match.group(1).lower(), []).append(index)
    units: dict[str, dict] = {}
    for name in TARGETS:
        hits = headers.get(name, [])
        if len(hits) != 1:
            raise SystemExit(f"P7K: unit {name} has {len(hits)} header matches, expected one")
        start = hits[0]
        end = None
        for index in range(start + 1, len(lines)):
            match = re.match(r"^      end(?![a-zA-Z])\s*(\S.*)?$", lines[index], re.IGNORECASE)
            if not match:
                continue
            remainder = (match.group(1) or "").strip().split()
            if remainder and remainder[0].lower() in END_KEYWORDS:
                continue
            end = index
            break
        if end is None:
            raise SystemExit(f"P7K: unit {name} has no terminator")
        body = "\n".join(lines[start:end + 1]) + "\n"
        calls = sorted({call.lower() for call in re.findall(r"\bcall\s+([a-z0-9_]+)", body, re.IGNORECASE)})
        units[name] = {
            "first_line": start + 1,
            "last_line": end + 1,
            "lines": end - start + 1,
            "sha256": hashlib.sha256(body.encode("latin-1")).hexdigest(),
            "calls": calls,
        }
    return {
        "gate": "P7K_CTSG_KERNEL_SOURCE_LOCATION",
        "vendor_source": VENDOR_SOURCE,
        "vendor_source_sha256": hashlib.sha256(raw).hexdigest(),
        "located_by": "call-site scan over the vendor routine headers (no plain-name patterns)",
        "units": units,
        "ported": {"rotate": True, "qatr": True, "tfac": True},
        "open": ["munu", "bi", "bji", "bjil", "flopuff", "ctpar", "puffc", "ctsg", "ctrec", "lower",
                 "upper"],
        "note": "The located spans, hashes and call closures are the entry point for the CTSG kernel "
                "port; none of the open units is ported yet.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=pathlib.Path,
                        default=pathlib.Path(__file__).resolve().parents[4])
    parser.add_argument("--check", type=pathlib.Path)
    args = parser.parse_args()
    manifest = locate(args.repo_root / VENDOR_SUBDIR)
    if args.check:
        pinned = json.loads(args.check.read_text())
        if pinned != manifest:
            raise SystemExit("P7K CTSG kernel unit drift: spans/hashes differ from the pinned manifest")
        print("P7K_CTSG_KERNEL_LOCATION=PASS units=" + ",".join(sorted(manifest["units"])))
    for name, info in sorted(manifest["units"].items()):
        print(f"P7K_UNIT {name:8s} lines={info['first_line']}-{info['last_line']} "
              f"sha256={info['sha256'][:16]} calls={','.join(info['calls']) or '-'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
