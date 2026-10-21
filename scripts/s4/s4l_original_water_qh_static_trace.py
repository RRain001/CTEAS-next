#!/usr/bin/env python3
"""Source-pinned original CALMET water QH lifetime discovery, NOT physics admission.

The independent full original HEATFX Fortran-vs-C++ numeric test is a separate
mandatory CI step. This script inspects untouched source ONLY, recording call
sites and candidate QH state owners without asserting a fictitious real-site
prior-hour initialization or sharing vendor source text in its JSON artifact.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

BLOB = "437f43bb7f0e51a1919e56664663e1a046986ed0"


def verify(path: Path) -> dict:
    content = path.read_bytes()
    blob = subprocess.run(
        ["git", "hash-object", str(path)], check=True, capture_output=True, text=True
    ).stdout.strip()
    if blob != BLOB:
        raise ValueError("Original unmodified CALMET 6.5.0 exact Git blob changed")
    text = content.decode("utf-8")
    lines = text.splitlines()

    # Original fixed form: only actual source statements, not comment markers.
    def code(line: str) -> str:
        if not line or line[0] in "*cC!":
            return ""
        return line[6:].strip().lower() if len(line) >= 7 else ""

    statements = [(i + 1, code(line)) for i, line in enumerate(lines)]
    calls = {name: [i for i, statement in statements if re.search(
        rf"\bcall\s+{name}\s*\(", statement
    )] for name in ("heatfx", "elustr", "setup", "setcom", "mixht")}
    routine = {name: [i for i, statement in statements if re.search(
        rf"^subroutine\s+{name}\s*\(", statement
    )] for name in ("heatfx", "elustr")}
    if len(routine["heatfx"]) != 1 or not calls["heatfx"] or not calls["elustr"]:
        raise ValueError("CALMET pinned original HEATFX/ELUSTR structure missing")
    # Guard against falsely treating names like QH0/QQH as actual QH state.
    qh = [i for i, statement in statements if re.search(r"(?<![a-z0-9_])qh\s*\(", statement)]
    water = [i for i, statement in statements if ("iwat1" in statement or "iwat2" in statement)]
    if len(qh) < 10 or len(water) < 5:
        raise ValueError("CALMET original water-QH evidence structure truncated")
    first = routine["heatfx"][0]
    following = [i for i, statement in statements if i > first and
                 re.search(r"^subroutine\s+\w+\s*\(", statement)]
    if not following:
        raise ValueError("Original HEATFX following routine absent")
    heat_end = min(following)
    in_heat = [(i, s) for i, s in statements if first <= i < heat_end]
    heat_water = [i for i, s in in_heat if "iwat1" in s or "iwat2" in s]
    heat_qh = [i for i, s in in_heat if re.search(r"(?<![a-z0-9_])qh\s*\(", s)]
    if not heat_water or not heat_qh:
        raise ValueError("HEATFX water/ QH branch could not be identified")

    # Preserve line references / counts only, not source lines, in an artifact.
    result = {
        "status": "S4L_PINNED_FORTRAN_QH_SOURCE_LIFETIME_AUDIT_PASS_SCOPED",
        "original_git_blob": blob,
        "original_sha256": hashlib.sha256(content).hexdigest(),
        "original_line_count": len(lines),
        "original_heatfx_routine": {"first_line": first, "following_subroutine_line": heat_end,
                                     "water_branch_lines": heat_water,
                                     "qh_reference_lines": heat_qh},
        "call_site_lines": calls,
        "global_qh_reference_count": len(qh),
        "global_water_control_reference_count": len(water),
        "real_water_qh_initialization_and_previous_hour_provenance": "UNRESOLVED",
        "heating_full_2022_2ss1us_source_clock": "NOT_REPLAYED_IN_ISOLATED_HEATFX_FIXTURE",
        "original_vs_cpp_real_hour_water_downstream_elustr_45_fields": "NOT_RUN",
        "g26_physics_admission": "NOT_ACCEPTED",
    }
    # Console-only inspectable lines; do not upload or commit original source.
    print("S4L_SOURCE_HEATFX_ORIGINAL_LINES", first, heat_end)
    for name in ("heatfx", "elustr", "setup", "setcom", "mixht"):
        print("S4L_ORIGINAL_CALLS", name, calls[name][:30])
    print("S4L_SOURCE_WATER_CONTROL_IN_HEATFX", heat_water)
    print("S4L_ORIGINAL_HEATFX_QH_REFERENCES", heat_qh)
    print("S4L_SOURCE_INSPECTION_BEGIN")
    for i, line in enumerate(lines, start=1):
        if (first <= i < heat_end and (
                i in heat_water or i in heat_qh or
                any(abs(i - j) <= 2 for j in heat_water)
        )):
            print(f"L{i}: {line.rstrip()}")
    print("S4L_SOURCE_INSPECTION_END")
    return result


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--vendor", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    result = verify(a.vendor)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("S4L_QH_WATER_ORIGINAL_SOURCE_PINNED=PASS_SOURCE_ONLY")


if __name__ == "__main__":
    main()
