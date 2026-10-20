#!/usr/bin/env python3
"""S4-A: fail-closed inventory of *actual* C1/C2 P6 execution routes.

This does not compile physics, change a solver, or assert cross-route parity.
It pins auditable source-level facts for a future unified production runner.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

C1_WORKFLOW = ".github/workflows/science-c1-143h.yml"
C2_WORKFLOW = ".github/workflows/science-c2-143h.yml"
C1_DRIVER = "native_cpp/modules/p6_calmet/src/native_hourly_driver_main.cpp"
C1_WIND = "native_cpp/modules/p6_calmet/src/realcase_wind_field_main.cpp"
C2_RUNNER = "native_cpp/modules/p6_calmet/src/p6g_g34b_six_hour_selected_gate_main.cpp"
C2_SELECTED = "native_cpp/modules/p6_calmet/include/cteas/p6/p6g_s4b2_selected_hour.hpp"
C2_DIAGNO = "native_cpp/modules/p6_calmet/include/cteas/p6/p6g_g26_file_backed_g14_diagno_bridge.hpp"
C2_COMP = "native_cpp/modules/p6_calmet/include/cteas/p6/p6g_g26b_file_backed_comp_bridge.hpp"
TERRAIN = "native_cpp/modules/p6_calmet/include/cteas/p6/p6g_terrain_hour.hpp"
STATION = "native_cpp/modules/p6_calmet/include/cteas/p6/p6g_g17c3_station_diagi.hpp"
SCIENCE = "docs/science_acceptance/C1_C2_143H_RERUN_20261017.md"

# One occurrence of each precisely scoped source anchor is necessary.
# The values are *facts to review*, not implicit permission to retain limits.
ANCHORS = (
    ("c1_hourly_binary", C1_WORKFLOW, r'"\$RUNNER_TEMP/c1/p6d/cteas_p6_native_hourly_driver"'),
    ("c1_frozen_143h", C1_WORKFLOW, r'--hours 143 --emit-source-stage-trace'),
    ("c1_original_is_frozen", C1_WORKFLOW, r'C1_CURRENT_NATIVE_P6_143H_AND_STRICT_FIELD_GATE=PASS'),
    ("c1_driver_bound_143h", C1_DRIVER, r'o\.hours<1\|\|o\.hours>143'),
    ("c1_driver_fixed_up_name", C1_DRIVER, r'up_58424\.dat'),
    ("c1_p6d_fixed_grid", C1_WIND, r'if\(nx!=50\|\|ny!=50\|\|nz!=9\)'),
    ("c1_p6d_one_one", C1_WIND, r'deck_int\(controls,"NSSTA",-1\)!=1\|\|deck_int\(controls,"NUSTA",-1\)!=1'),
    ("c2_selected_g14_binary", C2_WORKFLOW, r'"\$RUNNER_TEMP/p7-c2/g35-build/cteas_p6g_g34b_six_hour_selected_gate"'),
    ("c2_original_fresh_runner", C2_WORKFLOW, r'g31_run_literal_original_calmet_multisite\.py'),
    ("c2_fortran_native_45field", C2_WORKFLOW, r'--out "\$RUNNER_TEMP/p7-c2/original-vs-native-45field\.json"'),
    ("c2_fixed_two_two", C2_RUNNER, r'source\.stations\.surface\.size\(\)!=2\|\|source\.stations\.upper\.size\(\)!=2'),
    ("c2_fixed_grid", C2_RUNNER, r'source\.grid\.nx!=12\|\|source\.grid\.ny!=12'),
    ("c2_g14_17stages", C2_SELECTED, r'if\(cursor_<12\) diagno_\.run_selected'),
    ("c2_g14_comp", C2_SELECTED, r'else if\(cursor_<16\) comp_\.run_selected'),
    ("c2_p6f", C2_SELECTED, r'const auto records=p6g::g18c5_selected_p6f_fields'),
    ("c2_g26_diag", C2_SELECTED, r'p6g::G26SourceFileBackedG14DiagnoBridge diagno_'),
    ("c2_g26b_comp", C2_SELECTED, r'p6g::G26BSourceFileBackedCompBridge comp_'),
    ("c2_diag_production_disabled", C2_DIAGNO, r'return \{p6::NativeHourSource::Unknown,false\};'),
    ("c2_selected_wind1", C2_DIAGNO, r'g20_file_backed_source_wind1_profiles\(frame,true\)'),
    ("c2_selected_fradj", C2_DIAGNO, r'g21_selected_original_file_fradj\('),
    ("c2_selected_slope", C2_DIAGNO, r'g22_selected_source_thermal_slope\('),
    ("c2_selected_inter2", C2_DIAGNO, r'g23_source_stheor_diagi_inter2\('),
    ("c2_selected_wind_tail", C2_DIAGNO, r'g24_selected_original_wind_tail\('),
    ("c2_comp_reuses_selected", C2_COMP, r'G18D4SelectedCompStageAdapter'),
    ("shared_c1_froude", C1_WIND, r'#include "cteas/p6/froude_adjust\.hpp"'),
    ("shared_c2_froude", TERRAIN, r'#include "cteas/p6/froude_adjust\.hpp"'),
    ("shared_c1_slope", C1_WIND, r'#include "cteas/p6/slope_flow\.hpp"'),
    ("shared_c2_slope", TERRAIN, r'#include "cteas/p6/slope_flow\.hpp"'),
    ("shared_c1_elustr2", C1_WIND, r'#include "cteas/p6/station_elustr2\.hpp"'),
    ("shared_c2_elustr2", STATION, r'#include "cteas/p6/station_elustr2\.hpp"'),
    ("shared_c1_mixhtst", C1_WIND, r'#include "cteas/p6/station_mixhtst\.hpp"'),
    ("shared_c2_mixhtst", STATION, r'#include "cteas/p6/station_mixhtst\.hpp"'),
    ("shared_c1_similt", C1_WIND, r'#include "cteas/p6/similt_profile\.hpp"'),
    ("shared_c2_similt", STATION, r'#include "cteas/p6/similt_profile\.hpp"'),
    ("accepted_both_scoped", SCIENCE, r'C1_143H_SCIENCE=PASS_SCOPED.*C2_143H_SCIENCE=PASS_SCOPED'),
    ("c1_original_frozen_disclosure", SCIENCE, r'original_calmet_2022_fresh_rerun=NOT_RUN_FROZEN_REFERENCE_INPUT'),
    ("c2_synthetic_disclosure", SCIENCE, r'受控合成多站案例'),
)

def audit(repo: Path, *, injected: dict[str, str] | None = None) -> dict:
    repo = repo.resolve(strict=True)
    files: dict[str, str] = {}
    facts = []
    for code, relative, expression in ANCHORS:
        path = repo / relative
        if relative not in files:
            if not path.is_file() or path.is_symlink():
                raise ValueError(f"{code}: missing or symlinked source {relative}")
            files[relative] = path.read_text(encoding="utf-8")
        data = (injected or {}).get(relative, files[relative])
        matches = list(re.finditer(expression, data, re.MULTILINE))
        if len(matches) != 1:
            raise ValueError(f"{code}: {relative}: expected exactly one, found {len(matches)}")
        m = matches[0]
        line = data.count("\n", 0, m.start()) + 1
        facts.append({"key":code, "source_file":relative, "line":line,
                      "anchor_sha256":hashlib.sha256(m.group(0).encode()).hexdigest()})
    return {
        "status": "S4A_C1_C2_SOURCE_EXECUTION_ROUTE_AUDIT_PASS_SCOPED",
        "source_level_only": True,
        "physics_formulas_modified": False,
        "original_calmet_fresh_C1": False,
        "original_calmet_fresh_C2": True,
        "c1_c2_one_shared_production_binary": False,
        "c1_c2_cross_runner_numerical_identity_proven": False,
        "next_gate": "S4_B_UNIFIED_C1_C2_RUNNER_ORIGINAL_SCIENCE",
        "source_files": [{
            "path": key, "sha256": hashlib.sha256(value.encode()).hexdigest(),
            "byte_count": len(value.encode())} for key, value in sorted(files.items())],
        "fact_count": len(facts),
        "facts": facts,
    }

def negative_self_test(repo: Path):
    good = audit(repo)
    path = C2_RUNNER
    source = (repo / path).read_text(encoding="utf-8")
    old = "source.stations.surface.size()!=2||source.stations.upper.size()!=2"
    if source.count(old) != 1:
        raise ValueError("cannot prove drift-negative: original C2 anchor absent")
    try:
        audit(repo, injected={path: source.replace(old, "source.stations.surface.size()!=1||source.stations.upper.size()!=1")})
    except ValueError as exc:
        if "c2_fixed_two_two" not in str(exc):
            raise ValueError("drift-negative rejected a different assertion") from exc
    else:
        raise ValueError("S4A source inventory silently accepted changed C2 gate")
    if good["fact_count"] < 35:
        raise ValueError("S4A source inventory unexpectedly truncated")
    print("S4A_C1_C2_CHANGED_CASE_GATE_NEGATIVE=PASS")

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", type=Path, default=Path("."))
    p.add_argument("--out", type=Path)
    p.add_argument("--negative-self-test", action="store_true")
    args = p.parse_args()
    try:
        if args.negative_self_test:
            negative_self_test(args.repo)
            return 0
        report = audit(args.repo)
        if args.out is not None:
            if args.out.exists() or args.out.is_symlink():
                raise ValueError("audit JSON must be fresh")
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print(json.dumps({"status": report["status"], "facts": report["fact_count"],
                          "files": len(report["source_files"]),
                          "full_original_v_native_parity": "NOT_RUN",
                          "full_newsite_MET45": "NOT_ACCEPTED"}))
        return 0
    except (ValueError, OSError, UnicodeError) as exc:
        print(json.dumps({"status": "S4A_SOURCE_AUDIT_FAILED_CLOSED",
                          "reason": str(exc)}), file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
