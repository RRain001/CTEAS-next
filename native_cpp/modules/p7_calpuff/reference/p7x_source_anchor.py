#!/usr/bin/env python3
"""P7X: pin the inline COMP step-integration spans of the vendor.

The step integration lives inside `subroutine comp` and cannot be extracted as a
unit, so its spans are pinned by line number AND content hash: `--check` fails if
the vendor file's lines at those numbers no longer hash the same, so the oracle
comparison can never silently drift from a different vendor revision.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib

VENDOR_SUBDIR = "engine/vendor/src/CALPUFF_v7.2.1_L150618"
VENDOR_SOURCE = "calpuff.for"

# name -> (first_line, last_line) in calpuff.for, 1-based inclusive.
SPANS = {
    "cadence_old_puff": (10136, 10147),
    "cadence_new_puff": (10158, 10318),
    "substep_length": (10548, 10582),
    "position_update": (10607, 10619),
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def extract(vendor: pathlib.Path) -> dict:
    raw = (vendor / VENDOR_SOURCE).read_bytes()
    lines = raw.decode("latin-1").splitlines()
    spans = {}
    for name, (first, last) in SPANS.items():
        if first < 1 or last > len(lines):
            raise SystemExit(f"P7X: span {name} is outside {VENDOR_SOURCE}")
        body = "\n".join(lines[first - 1:last]) + "\n"
        spans[name] = {
            "first_line": first,
            "last_line": last,
            "lines": last - first + 1,
            "sha256": sha256_bytes(body.encode("latin-1")),
        }
    return {
        "gate": "P7X_STEP_INTEGRATION_SOURCE_ANCHOR",
        "vendor_source": VENDOR_SOURCE,
        "vendor_source_sha256": sha256_bytes(raw),
        "located_by": "inline COMP spans pinned by line number and content hash",
        "spans": spans,
        "ported": {"sampling_cadence": True, "substep_length": True, "position_update": True},
        "not_ported": ["the vertical position update (SETPUF's ze1)", "the dispersion update"],
        "not_modified": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=pathlib.Path,
                        default=pathlib.Path(__file__).resolve().parents[4])
    parser.add_argument("--manifest", type=pathlib.Path)
    parser.add_argument("--check", type=pathlib.Path)
    args = parser.parse_args()
    manifest = extract(args.repo_root / VENDOR_SUBDIR)
    if args.manifest:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json.dumps(manifest, indent=2) + "\n")
    if args.check:
        pinned = json.loads(args.check.read_text())
        if pinned != manifest:
            raise SystemExit("P7X step-integration source drift: re-audit before trusting "
                             "the oracle")
        print("P7X_SOURCE_ANCHOR=PASS spans=" + ",".join(sorted(manifest["spans"])))
    print("P7X_VENDOR_SHA256=" + manifest["vendor_source_sha256"])
    for name, info in manifest["spans"].items():
        print(f"P7X_SPAN {name:18s} lines={info['first_line']}-{info['last_line']} "
              f"sha256={info['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
