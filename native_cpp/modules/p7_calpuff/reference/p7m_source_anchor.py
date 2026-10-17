#!/usr/bin/env python3
"""P7M: pin the CTSG kernel units and stage them for the unmodified-source oracle.

The units are located exactly like P7K does (routine-header scan, no plain-name
patterns), so the spans of the units P7K already pinned are cross-checked
against `p7k_source_anchor.json`; the two units P7K did not cover (`ireg`,
`sigma`) and the `erfdif` dependency of PUFFC are located here as well. The
manifest also records a machine check of the vendor /CONST/ initialisation:
`rt2pi` is declared in const.puf but CTINIT never sets it and no DATA statement
in a routine that includes const.puf writes it, so the vendor evaluates the
"puff mixed in the vertical" branch of LOWER/PUFFC as RT2PI*sz/zlid = 0.

`--stage DIR` writes the extracted spans as `vendor_<unit>.f` plus the
hand-written driver, and copies every vendor `*.puf` include into DIR.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import shutil

VENDOR_SUBDIR = "engine/vendor/src/CALPUFF_v7.2.1_L150618"
VENDOR_SOURCE = "calpuff.for"

# Units compiled UNMODIFIED into the oracle, in build order.
TARGETS = ("munu", "bi", "bji", "bjil", "ireg", "rotate", "erfdif", "sigma", "ctrec", "puffc",
           "lower", "ctsg")

# Units located and pinned but NOT compiled into the oracle: CTINIT is the only
# place the vendor initializes /CONST/, so its span is the direct evidence that
# RT2PI is never set.
LOCATED_ONLY = ("ctinit",)

# Spans already pinned by P7K; a mismatch means the vendor file drifted.
P7K_SHARED = ("munu", "bi", "bji", "bjil", "rotate", "ctrec", "puffc", "lower", "ctsg")

END_KEYWORDS = {"do", "if", "where", "select", "selectcase", "type", "block", "module", "program",
                "subroutine", "function", "associate", "forall", "critical", "enum", "interface",
                "team", "parallel"}
HEADER = re.compile(r"^\s{0,6}(?:real|integer|logical|double\s+precision)?\s*"
                    r"(?:function|subroutine)\s+([a-z0-9_]+)\s*\(?", re.IGNORECASE)
TERMINATOR = re.compile(r"^      end(?![a-zA-Z])\s*(\S.*)?$", re.IGNORECASE)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def headers(lines: list[str]) -> dict[str, list[int]]:
    found: dict[str, list[int]] = {}
    for index, line in enumerate(lines):
        match = HEADER.match(line)
        if match:
            found.setdefault(match.group(1).lower(), []).append(index)
    return found


def enclosing_units(lines: list[str]) -> dict[int, str]:
    """Map every line index to the name of the routine that encloses it."""
    found = headers(lines)
    owner: dict[int, str] = {}
    ordered = sorted((index, name) for name, hits in found.items() for index in hits)
    current = "<none>"
    cursor = 0
    for index in range(len(lines)):
        while cursor < len(ordered) and ordered[cursor][0] <= index:
            current = ordered[cursor][1]
            cursor += 1
        owner[index] = current
    return owner


def locate(lines: list[str], found: dict[str, list[int]], names: tuple[str, ...]) -> dict:
    units: dict[str, dict] = {}
    for name in names:
        hits = found.get(name, [])
        if len(hits) != 1:
            raise SystemExit(f"P7M: unit {name} has {len(hits)} header matches, expected one")
        start = hits[0]
        end = None
        for index in range(start + 1, len(lines)):
            match = TERMINATOR.match(lines[index])
            if not match:
                continue
            remainder = (match.group(1) or "").strip().split()
            if remainder and remainder[0].lower() in END_KEYWORDS:
                continue
            end = index
            break
        if end is None:
            raise SystemExit(f"P7M: unit {name} has no terminator")
        body = "\n".join(lines[start:end + 1]) + "\n"
        calls = sorted({call.lower() for call in re.findall(r"\bcall\s+([a-z0-9_]+)", body,
                                                            re.IGNORECASE)})
        units[name] = {
            "first_line": start + 1,
            "last_line": end + 1,
            "lines": end - start + 1,
            "sha256": sha256_bytes(body.encode("latin-1")),
            "calls": calls,
        }
    return units


CLOSURE_TARGETS = ("ctsg", "ctpar", "upper", "lower", "puffc", "flopuff", "path", "path0")

# Units referenced as FUNCTIONS (`x = name(...)`), which a `call` scan misses.
FUNCTION_REFERENCES = ("vcbar", "vcoup")


def call_closure(lines: list[str], owner: dict[int, str]) -> dict:
    """Who calls each CTSG-closure unit (the P7L `flopuff` question)."""
    callers: dict[str, list[str]] = {name: [] for name in CLOSURE_TARGETS}
    for index, line in enumerate(lines):
        match = re.search(r"\bcall\s+([a-z0-9_]+)", line, re.IGNORECASE)
        if not match:
            continue
        callee = match.group(1).lower()
        if callee in callers:
            caller = owner[index]
            if caller not in callers[callee]:
                callers[callee].append(caller)
    return {name: sorted(names) for name, names in callers.items()}


def function_reference_callers(lines: list[str], owner: dict[int, str]) -> dict:
    """Enclosing units that reference each FUNCTION_REFERENCES unit as a function."""
    result: dict[str, list[str]] = {name: [] for name in FUNCTION_REFERENCES}
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped[0] in "cC*!":
            continue
        lowered = stripped.lower()
        if lowered.startswith(("real", "integer", "logical", "double", "function", "subroutine",
                               "external", "data", "common")):
            continue
        for name in FUNCTION_REFERENCES:
            if re.search(rf"\b{name}\s*\(", lowered):
                caller = owner[index]
                if caller not in result[name]:
                    result[name].append(caller)
    return {name: sorted(names) for name, names in result.items()}


def const_initialisation_check(lines: list[str], owner: dict[int, str],
                               found: dict[str, list[int]]) -> dict:
    """The /CONST/ RT2PI quirk: no unit that includes const.puf initialises it."""
    starts = sorted((index, name) for name, hits in found.items() for index in hits)
    routines_with_const: set[str] = set()
    for position, (start, name) in enumerate(starts):
        stop = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
        for index in range(start, stop):
            if "include 'const.puf'" in lines[index].lower():
                routines_with_const.add(name)
                break
    occurrences = []
    initialised_by: set[str] = set()
    for index, line in enumerate(lines):
        if "rt2pi" not in line.lower():
            continue
        stripped = line.strip()
        unit = owner[index]
        writer = bool(re.match(r"^\s*data\b", stripped, re.IGNORECASE)) or bool(
            re.search(r"\brt2pi\s*=", stripped, re.IGNORECASE))
        occurrences.append({"line": index + 1, "unit": unit, "writer": writer})
        if writer:
            initialised_by.add(unit)
    writers_in_const = sorted(initialised_by & routines_with_const)
    return {
        "rt2pi_writers": sorted(initialised_by),
        "rt2pi_occurrences": occurrences,
        "units_including_const_puf": sorted(routines_with_const),
        "rt2pi_written_by_a_const_puf_unit": writers_in_const,
        "vendor_rt2pi_initialised": bool(writers_in_const),
        "note": ("CTINIT (calpuff.for L22412-22434) sets every /CONST/ value except RT2PI; "
                 "no DATA statement in a unit that includes const.puf writes it, so the vendor "
                 "LOWER/PUFFC branch 'fz = rt2pi*sz/zlid' evaluates to zero at run time."),
    }


def extract(vendor: pathlib.Path) -> tuple[dict, dict[str, str]]:
    raw = (vendor / VENDOR_SOURCE).read_bytes()
    lines = raw.decode("latin-1").splitlines()
    found = headers(lines)
    owner = enclosing_units(lines)
    units = locate(lines, found, TARGETS)
    located_only = locate(lines, found, LOCATED_ONLY)
    const_quirk = const_initialisation_check(lines, owner, found)
    ctinit_span = (lines[located_only["ctinit"]["first_line"] - 1:
                         located_only["ctinit"]["last_line"]])
    const_quirk["ctinit_span"] = located_only["ctinit"]
    const_quirk["ctinit_sets_rt2pi"] = any("rt2pi" in line.lower() for line in ctinit_span)
    if const_quirk["ctinit_sets_rt2pi"] or const_quirk["vendor_rt2pi_initialised"]:
        raise SystemExit("P7M: the vendor /CONST/ RT2PI quirk no longer holds - re-audit")
    manifest: dict = {
        "gate": "P7M_CTSG_KERNEL_SOURCE_ANCHOR",
        "vendor_source": VENDOR_SOURCE,
        "vendor_source_sha256": sha256_bytes(raw),
        "located_by": "routine-header scan (identical to p7k_source_anchor.py)",
        "units": units,
        "located_only": located_only,
        "ported": {"munu": True, "bi": True, "bji": True, "bjil": True, "ireg": True,
                   "rotate": True, "sigma": True, "ctrec": True, "puffc": True, "lower": True,
                   "ctsg": True},
        "not_ported": ["ctpar", "upper", "flopuff"],
        "call_closure": call_closure(lines, owner),
        "function_reference_callers": function_reference_callers(lines, owner),
        "const_initialisation": const_quirk,
        "vendor_include_sha256": {
            path.name: sha256_bytes(path.read_bytes())
            for path in sorted(vendor.glob("*.puf"))
        },
        "not_modified": True,
    }
    spans = {name: "\n".join(lines[info["first_line"] - 1:info["last_line"]]) + "\n"
             for name, info in units.items()}
    return manifest, spans


def stage(vendor: pathlib.Path, output: pathlib.Path, manifest: dict,
          spans: dict[str, str]) -> None:
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    for name, text in spans.items():
        (output / f"vendor_{name}.f").write_bytes(text.encode("latin-1"))
    driver = pathlib.Path(__file__).with_name("p7m_oracle_driver.f")
    shutil.copy2(driver, output / driver.name)
    for include in manifest["vendor_include_sha256"]:
        shutil.copy2(vendor / include, output / include)
    (output / "p7m_source_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=pathlib.Path,
                        default=pathlib.Path(__file__).resolve().parents[4])
    parser.add_argument("--manifest", type=pathlib.Path)
    parser.add_argument("--check", type=pathlib.Path)
    parser.add_argument("--stage", type=pathlib.Path)
    args = parser.parse_args()
    vendor = args.repo_root / VENDOR_SUBDIR
    manifest, spans = extract(vendor)
    if args.manifest:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json.dumps(manifest, indent=2) + "\n")
    if args.stage:
        stage(vendor, args.stage, manifest, spans)
        print(f"P7M_SOURCE_STAGE={args.stage}")
    if args.check:
        pinned = json.loads(args.check.read_text())
        if pinned != manifest:
            raise SystemExit("P7M CTSG kernel source drift: re-audit before trusting the oracle")
        p7k = json.loads((args.check.parent / "p7k_source_anchor.json").read_text())
        for name in P7K_SHARED:
            mine = manifest["units"][name]
            theirs = p7k["units"][name]
            if (mine["first_line"], mine["last_line"], mine["sha256"]) != (
                    theirs["first_line"], theirs["last_line"], theirs["sha256"]):
                raise SystemExit(f"P7M: unit {name} disagrees with the P7K pin")
        print("P7M_SOURCE_ANCHOR=PASS units=" + ",".join(sorted(manifest["units"])))
        print(f"P7M_P7K_CROSSCHECK=PASS units={len(P7K_SHARED)}")
    print("P7M_VENDOR_SHA256=" + manifest["vendor_source_sha256"])
    print("P7M_CONST_RT2PI_INITIALISED_BY_VENDOR=" +
          ("true" if manifest["const_initialisation"]["vendor_rt2pi_initialised"] else "false"))
    closure = manifest["call_closure"]
    print("P7M_CALL_CLOSURE flopuff<-" + ",".join(closure["flopuff"]) + " upper<-" +
          ",".join(closure["upper"]) + " path<-" + ",".join(closure["path"]))
    for name, info in manifest["units"].items():
        print(f"P7M_UNIT {name:6s} lines={info['first_line']}-{info['last_line']} "
              f"sha256={info['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
