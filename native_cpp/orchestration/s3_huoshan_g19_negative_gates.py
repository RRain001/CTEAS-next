#!/usr/bin/env python3
"""S3-B7 genuine alternate UTC-window acceptance and fail-closed negative gates.

Run only AFTER the exact-case true NOAA P1-P5 source producer and native G19
source-only reader have successfully completed. Mutations are transient,
reversible tests of published control/source bytes, never fabricated weather.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

from native_cpp.orchestration.case_admission import admit_case
from native_cpp.orchestration.plan import ContractError
from native_cpp.orchestration.p6_g19_handoff import prepare_g19, execute_source_preflight


ALT_WINDOW = ("20220601-020000", "20220601-080000")
SOURCE_STATUS = "S3_B6_HUOSHAN_GENUINE_FIVE_SOURCE_NATIVE_G19_PARSED_SCOPED"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def expect_blocked(test_name: str, action, expected: str) -> dict[str, str]:
    try:
        action()
    except (ContractError, ValueError) as exc:
        reason = str(exc)
        if expected not in reason:
            raise AssertionError(f"{test_name}: wrong fail-closed gate: {reason}") from exc
        return {"name": test_name, "status": "EXPECTED_REJECTION",
                "reason": reason[:350]}
    raise AssertionError(test_name + ": altered real source/control was incorrectly admitted")


def run(case_yaml: Path, native: Path) -> dict:
    case = admit_case(case_yaml)
    if (case.research_begin, case.research_end) != ALT_WINDOW:
        raise ValueError("S3-B7 requires the independent June 02:00–08:00 UTC configuration")
    root = case.case_path.parent
    accepted_file = root / "evidence/s3-b6-g19-source-only.json"
    receipt_file = root / "evidence/s3-b0-five-source-preflight.json"
    output = root / "evidence/s3-b7-alt-clock-negative-evidence.json"
    if any(p.is_symlink() or not p.is_file() for p in (accepted_file, receipt_file)):
        raise ValueError("S3-B7 has no accepted same-B0 five-product G19 input")
    if output.exists() or output.is_symlink():
        raise ValueError("S3-B7 result must be created in a new case")
    accepted = json.loads(accepted_file.read_text())
    five = json.loads(receipt_file.read_text())
    if accepted["status"] != SOURCE_STATUS or not accepted["source_only_parsed"]:
        raise ValueError("S3-B7 cannot test without a real successful native C++ parser")
    for key, expected in (
        ("case_yaml_sha256", case.case_sha256),
        ("grid_cmn_sha256", case.grid_sha256),
        ("research_time_sha256", case.time_sha256),
    ):
        if accepted[key] != expected or five[key] != expected:
            raise ValueError("S3-B7 source files do not share exact alternate UTC B0 SHA")
    if not native.is_absolute() or native.is_symlink() or not native.is_file():
        raise ValueError("S3-B7 executable must be the genuine native G19 binary")

    p4 = root / "met/upperair"
    p5 = root / "met/surface/isd_raw"
    plan = prepare_g19(case_yaml, p4, p5, root, native)
    baseline = execute_source_preflight(plan)
    if baseline["status"] != "P6_G19_DYNAMIC_FILE_INPUT_PARSED_NO_PHYSICS_EXECUTED":
        raise AssertionError("real original file source reader does not pass untouched input")

    negatives = []
    deck = root / "run/met/met.inp"
    if deck.is_symlink() or not deck.is_file():
        raise ValueError("S3-B7 authentic CALMET deck missing")
    original_deck = deck.read_bytes()
    # Negative 1: strictly reject altered actual station cardinality metadata.
    text = original_deck.decode("utf-8")
    regex = r"(!\s*NSSTA\s*=\s*)1(\s*!)"
    altered, n = re.subn(regex, lambda m: m.group(1) + "2" + m.group(2), text)
    if n != 1:
        raise ValueError("S3-B7 actual native surface station count is not one")
    try:
        deck.write_bytes(altered.encode("utf-8"))
        negatives.append(expect_blocked(
            "real_MET_deck_surface_station_count_1_to_2",
            lambda: prepare_g19(case_yaml, p4, p5, root, native),
            "met.inp NSSTA differs",
        ))
    finally:
        deck.write_bytes(original_deck)
    if sha(deck.read_bytes()) != sha(original_deck):
        raise AssertionError("genuine MET deck not restored byte-for-byte")

    # Negative 2: reject byte drift in real NOAA-derived published SURF before
    # any native physics. This must be rejected by the original role SHA gate.
    surf = root / "met/surface/final/surf.dat"
    if surf.is_symlink() or not surf.is_file():
        raise ValueError("S3-B7 authentic published SURF missing")
    original_surf = surf.read_bytes()
    if len(original_surf) < 150:
        raise ValueError("S3-B7 suspiciously short original NOAA SURF source")
    corrupted = bytearray(original_surf)
    corrupted[-2] ^= 1
    try:
        surf.write_bytes(corrupted)
        negatives.append(expect_blocked(
            "real_NOAA_published_SURF_source_SHA_drift",
            lambda: execute_source_preflight(plan),
            "source bytes changed after source-plan SHA capture",
        ))
    finally:
        surf.write_bytes(original_surf)
    if sha(surf.read_bytes()) != sha(original_surf):
        raise AssertionError("real SURF source was not restored to original SHA")

    # Negative 3: shared B0 UTC clock must refuse a conflicting research_time
    # even when model/NOAA files and case.yaml are otherwise valid.
    clock = root / "grid/research_time"
    if clock.is_symlink() or not clock.is_file():
        raise ValueError("S3-B7 no actual B0 clock file")
    original_clock = clock.read_bytes()
    wrong_clock = original_clock.replace(b"END:20220601-080000",
                                         b"END:20220601-090000")
    if wrong_clock == original_clock:
        raise ValueError("S3-B7 source B0 clock was not what was admitted")
    try:
        clock.write_bytes(wrong_clock)
        negatives.append(expect_blocked(
            "different_UTC_research_time_cannot_reuse_accepted_B0",
            lambda: admit_case(case_yaml),
            "research_time",
        ))
    finally:
        clock.write_bytes(original_clock)
    if sha(clock.read_bytes()) != sha(original_clock):
        raise AssertionError("real B0 clock not restored to original SHA")

    recovered = execute_source_preflight(
        prepare_g19(case_yaml, p4, p5, root, native))
    if recovered["status"] != baseline["status"] or recovered["roles"] != baseline["roles"]:
        raise AssertionError("true original source G19 input not identical after negative tests")
    case_after = admit_case(case_yaml)
    if (case_after.case_sha256, case_after.grid_sha256, case_after.time_sha256) != (
        case.case_sha256, case.grid_sha256, case.time_sha256):
        raise AssertionError("B0 SHA changed during S3-B7 negatives")

    evidence = {
        "schema": "cteas.s3.b7.alternate_time_and_original_source_negative.v1",
        "status": "S3_B7_REAL_ALT_UTC_G19_POSITIVE_AND_THREE_NEGATIVES_PASS_SCOPED",
        "site": "GENUINE_HUOSHAN_UTM50N_100X100_NOAA_2022",
        "utc": [case.research_begin, case.research_end],
        "case_yaml_sha256": case.case_sha256,
        "grid_cmn_sha256": case.grid_sha256,
        "research_time_sha256": case.time_sha256,
        "five_source_receipt_sha256": sha(receipt_file.read_bytes()),
        "accepted_native_G19_receipt_sha256": sha(accepted_file.read_bytes()),
        "restored_original_met_deck_sha256": sha(deck.read_bytes()),
        "restored_published_original_surf_sha256": sha(surf.read_bytes()),
        "actual_positive_p4": recovered["ordered_upper_station_ids"],
        "actual_positive_p5": recovered["ordered_surface_station_ids"],
        "positive_native_parser": recovered["status"],
        "true_fail_closed_negatives": negatives,
        "original_source_recovery_after_mutation": "PASS",
        "full_S3_final_scope": "REVIEW_REQUIRED",
        "P6_P7_NUMERIC_FIELDS": "NOT_RUN",
        "docker": "DEFERRED",
    }
    output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-yaml", type=Path, required=True)
    parser.add_argument("--native-g19", type=Path, required=True)
    opts = parser.parse_args()
    try:
        result = run(opts.case_yaml, opts.native_g19)
    except (OSError, KeyError, ValueError, ContractError, AssertionError) as exc:
        print(json.dumps({"status": "S3_B7_NEGATIVE_GATE_FAILED",
                          "reason": str(exc)[:600]}), file=sys.stderr)
        return 2
    print(json.dumps({"status": result["status"],
                      "negative_tests": len(result["true_fail_closed_negatives"]),
                      "positive": result["positive_native_parser"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
