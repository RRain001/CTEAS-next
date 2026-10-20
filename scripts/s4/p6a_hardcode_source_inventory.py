#!/usr/bin/env python3
"""Issue #40 P6-A: source-anchored inventory of actual P6 portability blockers.

Read-only forensic inventory, not P6 physics. It checks real C++/Python source
anchors and emits bounded JSON evidence. An altered anchor is a BLOCKER until
a new independent numerical/scientific review updates this inventory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]

# Paths point to ACTUAL source/production, not docs or synthetic test fixtures.
# A tuple is (unique anchor, finding ID, ownership, remediation gate).
SPECS = {
    "native_cpp/modules/p6_calmet/include/cteas/p6/p6g_g19_file_backed_case.hpp": [
        ("if(ns<1||nu<1||", "G19_REAL_INPUT_1SS_1US_ALLOWED",
         "INPUT_ONLY_ACCEPTED", "P6B_ADMIT_ORIGINAL_BYTES_NOT_PHYSICS"),
    ],
    "native_cpp/modules/p6_calmet/src/p6g_g20_source_wind1_probe_main.cpp": [
        ("paths.ordered_up_dat.size()<2", "G20_CLI_TWO_UP_REQUIRED",
         "TEST_ONLY_NOT_NEW_SITE", "P6B1_ORIGINAL_1US_WIND1_BRANCH_SCIENCE"),
    ],
    "native_cpp/modules/p6_calmet/include/cteas/p6/p6g_g20_file_backed_wind1_profiles.hpp": [
        ("ns<2||nu<2||ns>6||nu>6||", "G20_PHYSICS_MIN_2SS_2US",
         "TEST_ONLY_NOT_NEW_SITE", "P6B1_REAL_1SS_1US_WIND1_COMPARE_ORIGINAL"),
        ("stations.upper[0].id!=58424||stations.upper[1].id!=58425||",
         "G20_G32E_SYNTHETIC_UP_IDS", "SYNTHETIC_TEST_ONLY",
         "P6B1_ORIGINAL_PREPDI_MISSING_K1_POLICY"),
    ],
    "native_cpp/modules/p6_calmet/include/cteas/p6/p6g_g26_file_backed_g14_diagno_bridge.hpp": [
        ("return {p6::NativeHourSource::Unknown,false};",
         "G26_G14_PRODUCTION_DISABLED", "COMPOSITE_TEST_ONLY",
         "P6B3_REAL_G14_COMMIT_AND_CAUSAL_STATE"),
        ("g20_file_backed_source_wind1_profiles(frame,true)",
         "G26_REQUIRES_G20_TEST_SELECTED_PATH", "COMPOSITE_TEST_ONLY",
         "P6B2_WIND1_FRADJ_STHEOR_INTER2_SOURCE_PARITY"),
    ],
    "native_cpp/modules/p6_calmet/src/realcase_wind_field_main.cpp": [
        ("if(nx!=50||ny!=50||nz!=9)", "P6D_FROZEN_50X50_9LAYERS",
         "FROZEN_HEFEI_PRODUCTION", "P6B2_DYNAMIC_NX_NY_NZ_AND_ALLOCATION"),
        ("args.first_hour>=143", "P6D_FROZEN_143_CLOCK_BOUND",
         "FROZEN_HEFEI_PRODUCTION", "P6B3_DYNAMIC_SUPPORTED_UTC_HOUR_COUNT"),
        ("gamma_grid(2500)", "P6D_STATIC_GAMMA_PLANE_2500",
         "FROZEN_HEFEI_PRODUCTION", "P6B2_DYNAMIC_CELLS_GAMMA"),
        ("blend.observation_weight.assign(22500,1.f)",
         "P6D_FIXED_NINE_LEVEL_OBS_WEIGHT_22500",
         "FROZEN_HEFEI_PRODUCTION", "P6B2_DYNAMIC_VERTICAL_PLANE_MEMORY"),
    ],
    "native_cpp/modules/p6_calmet/src/native_hourly_driver_main.cpp": [
        ("up_58424.dat", "DRIVER_FROZEN_UP_FILE",
         "FROZEN_HEFEI_PRODUCTION", "P6B2_READ_ORDERED_UP_FROM_G19"),
        ('"--upper-i","25","--upper-j","26"', "DRIVER_FROZEN_CGAMMA_SITE_IJ",
         "FROZEN_HEFEI_PRODUCTION", "P6B2_DERIVE_STATION_POSITION"),
        ("o.hours>143", "DRIVER_FROZEN_143H_BOUND",
         "FROZEN_HEFEI_PRODUCTION", "P6B3_DERIVE_B0_TIME_AND_CAUSAL_HOURS"),
        ("constexpr const char* kMetHash=", "DRIVER_ORIGINAL_MET_HASH_LOCK",
         "FROZEN_HEFEI_REFERENCE_OPTION", "P6B3_FORBID_REFERENCED_MET_FOR_NEW_SITE"),
        ("45ULL*50ULL*50ULL*sizeof(float)", "DRIVER_FROZEN_45FIELD_2500_PAYLOAD",
         "FROZEN_HEFEI_PRODUCTION", "P6B3_DYNAMIC_NATIVE_MET_DIMS"),
    ],
    "native_cpp/orchestration/run_p6.py": [
        ("if case_root.name != CASE_ID:", "ORCHESTRATOR_FORBIDS_NEW_SITE",
         "FROZEN_HEFEI_PRODUCTION", "P6B0_TRUE_B0_G19_SHA_PREFLIGHT"),
        ("hours not in (1, 6, 143)", "ORCHESTRATOR_FIXED_CHECKPOINTS",
         "FROZEN_HEFEI_PRODUCTION", "P6B3_CLOCK_DERIVED_SUPPORTED_HOURS"),
        ("case_root / \"run/met/met.dat\"", "ORCHESTRATOR_FROZEN_MET_INPUT_GUARD",
         "CORRECT_SAFETY_INVARIANT", "KEEP_FAIL_CLOSED_NO_OLD_MET_FALLBACK"),
    ],
    "scripts/run_p6_end_to_end.py": [
        ("FROZEN_CELLS = 50 * 50", "REFERENCE_VALIDATOR_50X50_ONLY",
         "FROZEN_HEFEI_FORENSIC_COMPARATOR", "KEEP_143H_REGRESSION_SEPARATE"),
        ("FROZEN_MET_SHA256", "REFERENCE_VALIDATOR_ORIGINAL_MET_HASH",
         "FROZEN_HEFEI_FORENSIC_COMPARATOR", "KEEP_143H_REGRESSION_SEPARATE"),
    ],
}

SEQUENCE = [
    {
        "gate": "P6B0",
        "action": "reuse S3 actual Huoshan 6h G19 and B0 five-source SHA; read true 1SS/1US and reject unbracketed hours",
        "output": "source-only TRUE_INPUT_1SS_1US; no wind fields",
    },
    {
        "gate": "P6B1",
        "action": "extend only existing G20 WIND1 selected 1SS/1US scope using observed original weather and compare original Fortran station-level/cell values",
        "output": "first-hour native U/V grid with original numeric comparison or NOT_ACCEPTED",
    },
    {
        "gate": "P6B2",
        "action": "source-port selected CGAMMA, FRADJ, STHEOR, INTER2 and 50x50 array assumptions in real actual 100x100 case",
        "output": "nonzero first-hour 3D wind, producer-owned SHA, original stage-by-stage evidence",
    },
    {
        "gate": "P6B3",
        "action": "causal P6D-P6E state, P6F full 45-field/hour writer, dynamic hours from supported B0 without injecting frozen MET",
        "output": "actual original-compatible newsite MET.DAT, native science still NOT_ACCEPTED",
    },
    {
        "gate": "P6C",
        "action": "rerun original CALMET on same genuine GEO/UP/SURF and selected options; independently compare every supported hourly 45 fields",
        "output": "P6_NEW_SITE_SCIENCE=PASS_SCOPED only after independently demonstrated numerical tolerance",
    },
    {
        "gate": "P6D",
        "action": "preserve isolated true Hefei 143h regression, unsupported physics fail-closed, deterministic thread/heap and source SHA accounting",
        "output": "S4 P6 science certificate; no precipitation/wet deposition",
    },
]


def audit(repo: Path) -> dict:
    findings = []
    manifests = {}
    for relative, assertions in SPECS.items():
        path = repo / relative
        if not path.is_file() or path.is_symlink():
            raise ValueError("P6A source missing/nonregular: " + relative)
        data = path.read_bytes()
        contents = data.decode("utf-8")
        lines = contents.splitlines()
        manifests[relative] = {"sha256": hashlib.sha256(data).hexdigest(),
                               "source_bytes": len(data)}
        for anchor, name, scope, fix in assertions:
            matches = [(i, line) for i, line in enumerate(lines, 1) if anchor in line]
            if len(matches) != 1:
                raise ValueError(f"P6A {name}: expected exactly 1 ACTUAL code anchor, found {len(matches)}")
            line_number, line = matches[0]
            findings.append({
                "id": name, "path": relative, "source_line": line_number,
                "source_line_sha256": hashlib.sha256(line.encode()).hexdigest(),
                "current_scope": scope, "successor_gate": fix,
                "claim": "REAL_SOURCE_AUDITED_NOT_REMEDIATED",
            })
    required = {"G19_REAL_INPUT_1SS_1US_ALLOWED", "G20_PHYSICS_MIN_2SS_2US",
                "G26_G14_PRODUCTION_DISABLED", "P6D_FROZEN_50X50_9LAYERS",
                "DRIVER_FROZEN_UP_FILE", "DRIVER_FROZEN_CGAMMA_SITE_IJ",
                "ORCHESTRATOR_FORBIDS_NEW_SITE"}
    names = {row["id"] for row in findings}
    if names & required != required:
        raise ValueError("P6A stage blocker inventory incomplete")
    if len(names) != len(findings):
        raise ValueError("P6A repeated finding IDs")
    return {
        "schema": "cteas.s4.p6a.original_source_hardcoding_audit.v1",
        "status": "P6A_SOURCE_HARDCODE_INVENTORY_PASS_NO_P6_PHYSICS_ACCEPTANCE",
        "scoped_upstream_s3": "REAL_HUOSHAN_1SS_1US_100X100_2022_6H_G19_PASS",
        "findings": findings, "source_files": manifests, "remediation_order": SEQUENCE,
        "P6_FIRST_HOUR_NEW_SITE_NATIVE_FIELD": "NOT_RUN",
        "P6_45_FIELD_ORIGINAL_COMPARISON": "NOT_RUN",
        "S4_P6_SCIENCE": "NOT_ACCEPTED",
        "wet_deposition": "DEFERRED",
        "docker": "DEFERRED",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=REPO)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = audit(args.repo)
        out = args.out.absolute()
        if out.exists() or out.is_symlink():
            raise ValueError("P6A evidence output must be new/never overwritten")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    except (OSError, ValueError, UnicodeError) as exc:
        print(json.dumps({"status": "P6A_SOURCE_AUDIT_BLOCKED", "error": str(exc)}),
              file=sys.stderr)
        return 2
    print(json.dumps({"status": result["status"], "findings": len(result["findings"]),
                      "source_files": len(result["source_files"]),
                      "next_gate": "P6B0_P6B1", "P6_sci": result["S4_P6_SCIENCE"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
