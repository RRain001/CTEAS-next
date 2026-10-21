#!/usr/bin/env python3
"""Actual original CALMET WATER numerical state probe, not C++ physical parity.

Instrument an isolated copy of SHA-pinned vendor Fortran; never mutate the
vendor checkout or ship instrumented source. Run both independently on byte-
identical genuine NOAA GEO/SURF/UP/met.inp and require unchanged MET.DAT.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
from collections import defaultdict
from pathlib import Path

ORIGINAL_BLOB = "437f43bb7f0e51a1919e56664663e1a046986ed0"
ACTUAL_NX, ACTUAL_NY = 82, 85
INSTRUMENT_FILENAME = "s4n-original-water-states.txt"
RECORDS_PER_HOUR = 63
HOURS = 6
FIELDS = ("qh", "ustar", "el", "zi", "wstar", "z0", "wt", "ws10")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pinned_original(path: Path) -> list[str]:
    blob = subprocess.run(["git", "hash-object", str(path)], text=True,
                          capture_output=True, check=True).stdout.strip()
    if blob != ORIGINAL_BLOB:
        raise ValueError(f"Original CALMET vendor blob mismatch: {blob}")
    lines = path.read_text(encoding="utf-8").splitlines()
    checks = {
        32708: "do 500 i=1,nx",
        32709: "do 500 j=1,ny",
        32713: "if(ilandu(i,j).lt.iwat1.or.ilandu(i,j).gt.iwat2)go to 500",
        32815: "wt=0.",
        33065: "qh(i,j)=wt*rhocp",
        33080: "500   continue",
        33083: "return",
    }
    for line, text in checks.items():
        if lines[line - 1].strip().lower() != text:
            raise ValueError(f"Refuse modification: original WATER line {line} changed")
    # Original CALL WATER is in COMP, and its unique water source output must
    # follow HEATFX before ELUSTR. Assert original stable references.
    if "call water(u,v,imixh" not in lines[4618].lower():
        raise ValueError("Original COMP calls no longer select WATER")
    return lines


def prepare(vendor: Path, out: Path, evidence: Path) -> None:
    lines = pinned_original(vendor)
    inserts = {
        # Only native Fortran source COPY is instrumented, never vendor input.
        32708: [
            f"      open(unit=98,file='{INSTRUMENT_FILENAME}',",
            "     1     status='unknown',position='append',action='write')",
        ],
        # original QH and IPGT must already be computed before this record;
        # capture exactly selected original variables at the WATER exit.
        33080: [
            "      write(98,9858) i,j,nhrz,ilandu(i,j),ipgt(i,j),",
            "     1   qh(i,j),ustar(i,j),el(i,j),zi(i,j),wstar(i,j),",
            "     2   z0(i,j),wt,ws10",
            " 9858 format(5(i5,1x),8(es23.15,1x))",
        ],
        33081: ["      close(unit=98)"],
    }
    modified = []
    for i, line in enumerate(lines, start=1):
        modified.extend(inserts.get(i, ()))
        modified.append(line)
    if sum(len(x) for x in inserts.values()) != 7:
        raise AssertionError("Unexpected instrument footprint")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(modified) + "\n", encoding="utf-8")
    evidence.parent.mkdir(parents=True, exist_ok=True)
    receipt = {
        "status": "S4N_REFERENCE_ONLY_EXACT_PINNED_ORIGINAL_WATER_TRACE_PREPARED",
        "vendor_original_blob": ORIGINAL_BLOB,
        "vendor_original_sha256": sha(vendor),
        "instrumented_copy_sha256": sha(out),
        "insertion_before_original_lines": list(inserts),
        "added_source_lines": 7,
        "original_vendor_source_mutated": False,
        "numerical_comparisons": "NOT_RUN",
        "physical_native_adapter": "NOT_IMPLEMENTED",
    }
    evidence.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
    print("S4N_INSTRUMENTED_VENDOR_COPY_ONLY_SHA_PINNED=PREPARED")


def verify(
    vendor: Path, geo: Path, deck: Path, baseline: Path, instrumented: Path,
    trace: Path, prepared: Path, out: Path,
) -> None:
    pinned_original(vendor)
    from native_cpp.reference.compare_p3_makegeo_dynamic import parse_geo
    from scripts.s4.s4m_real_water_original_route_audit import audit as route_audit

    route = route_audit(vendor, deck, geo)
    if route["status"] != "S4M_REAL_2SS1US_ORIGINAL_NO_WATER_STATION_WATER_ROUTE_AUDIT_PASS_SCOPED":
        raise ValueError("Not the original actual NOWSTA=0 WATER branch")
    if route["original_READCF_controls"] != {"NOWSTA": 0, "ITWPROG": 0,
                                             "ICOARE": 10, "IMIXH": 1}:
        raise ValueError("Current actual observed case no longer selects scoped water physics")
    geo_data = parse_geo(geo, nx=ACTUAL_NX, ny=ACTUAL_NY,
                         zone=50, hem="N", x0=426.590, y0=3464.125, dx=1.)
    water_set = {(index % ACTUAL_NX + 1, index // ACTUAL_NX + 1)
                 for index, v in enumerate(geo_data["category"]) if 50 <= int(v) <= 55}
    if len(water_set) != RECORDS_PER_HOUR:
        raise ValueError(f"Genuine water cells changed: {len(water_set)}")
    before = prepared.read_text()
    source_receipt = json.loads(before)
    if (source_receipt["status"] !=
            "S4N_REFERENCE_ONLY_EXACT_PINNED_ORIGINAL_WATER_TRACE_PREPARED" or
            source_receipt["vendor_original_sha256"] != sha(vendor)):
        raise ValueError("Instrument copy no longer originates from exact vendor")
    if not baseline.is_file() or not instrumented.is_file():
        raise ValueError("Both independently executed CALMET.DAT are mandatory")
    # Source instrumentation must not affect any final scientific output.
    if sha(baseline) != sha(instrumented):
        raise ValueError("Instrumented CALMET changed the original MET.DAT bytes")
    by_hour: dict[int, dict[tuple[int, int], dict]] = defaultdict(dict)
    for line in trace.read_text().splitlines():
        values = line.strip().split()
        if len(values) != 5 + len(FIELDS):
            raise ValueError(f"Original water state row has wrong arity: {len(values)}")
        i, j, hour, category, pgt = (int(x) for x in values[:5])
        fields = dict(zip(FIELDS, (float(x.replace("D", "E")) for x in values[5:])))
        if (i, j) not in water_set or (i, j) in by_hour[hour] or not 50 <= category <= 55:
            raise ValueError("Original WATER trace identity/duplicate/non-water row")
        if pgt != 4:
            raise ValueError(f"Neutral-original PGT is not class D at ({i},{j}) hour {hour}")
        if not all(math.isfinite(x) for x in fields.values()):
            raise ValueError(f"Nonfinite original surface physics at ({i},{j}) hour {hour}")
        if fields["qh"] != 0 or fields["wt"] != 0 or fields["wstar"] != 0:
            raise ValueError("Original NOWSTA0 water buoyancy/wstar not zero as expected")
        if abs(fields["el"] - 9.9e9) > 2048:
            raise ValueError("Original neutral water Monin-Obukhov sentinel drift")
        if not 50 - 0.001 <= fields["zi"] <= 3000 + 0.001:
            raise ValueError("Original water ZI outside actual original ZIMINW/ZIMAXW")
        if fields["ustar"] <= 0 or fields["z0"] <= 0 or fields["ws10"] < 0:
            raise ValueError("Original water neutral friction/roughness invalid")
        z0 = max(2.0e-6 * fields["ws10"] ** 2.5, 2.0e-6)
        if not math.isclose(fields["z0"], z0, rel_tol=4e-6, abs_tol=1e-10):
            raise ValueError("Original water Hosker roughness does not match neutral source")
        ustar = max(0.4 * fields["ws10"] / math.log(10.0 / fields["z0"]), 1e-9)
        if not math.isclose(fields["ustar"], ustar, rel_tol=3e-5, abs_tol=2e-8):
            raise ValueError("Original neutral-water USTAR does not match source formula")
        by_hour[hour][(i, j)] = {"category": category, "pgt": pgt, **fields}
    if len(by_hour) != HOURS:
        raise ValueError(f"Expected original six independent hourly water states, got {len(by_hour)}")
    for hour, cells in by_hour.items():
        if set(cells) != water_set:
            raise ValueError(f"Original WATER source missing or extraneous cell hour {hour}")

    import statistics
    result = {
        "status": "S4N_ACTUAL_VENDOR_63_WATER_CELLS_SIX_HOURS_NEUTRAL_WATER_VALUES_PASS_SCOPED_ORIGINAL_ONLY",
        "real_2022_authentic_noaa_2ss_1us": True,
        "water_grid_cells": len(water_set),
        "modeled_hours": HOURS,
        "original_water_cell_hour_records": HOURS * RECORDS_PER_HOUR,
        "source_original_git_blob": ORIGINAL_BLOB,
        "source_original_sha256": sha(vendor),
        "source_real_geo_sha256": sha(geo),
        "source_real_metinp_sha256": sha(deck),
        "original_uninstrumented_calmet_sha256": sha(baseline),
        "original_instrumented_calmet_sha256": sha(instrumented),
        "original_45_field_native_dataset_byte_identical_to_instrumented": True,
        "water_hour_ending_values": sorted(by_hour),
        "original_controls": route["original_READCF_controls"],
        "water_flux_qh_wm2_all_exact_zero": True,
        "water_neutral_wt_all_exact_zero": True,
        "water_ustar_source_formula_test": "PASS",
        "water_z0_original_hosker_source_formula_test": "PASS",
        "water_pgt_all_class_d": True,
        "values": {},
        "native_Cpp_water_physics": "NOT_RUN",
        "original_vs_native_CALMET_6x45": "NOT_RUN",
        "g26_default_production": "NOT_ACCEPTED",
        "P7": "NOT_RUN",
    }
    for key in FIELDS:
        numbers = [cell[key] for cells in by_hour.values() for cell in cells.values()]
        result["values"][key] = {"min": min(numbers), "max": max(numbers),
                                  "mean": statistics.fmean(numbers)}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print("S4N_TRUE_NOAA_ORIGINAL_63_WATER_CELLS_X_6H=378_VALUES_PASS_SCOPED")
    print("S4N_INSTRUMENTED_CALMET_45_FIELDS_BYTE_IDENTICAL_UNMODIFIED=PASS")
    print("S4N_CPP_WATER_PHYSICS_AND_G26_45_FIELDS=NOT_RUN")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--vendor", required=True, type=Path)
    prep.add_argument("--out", required=True, type=Path)
    prep.add_argument("--receipt", required=True, type=Path)
    validate = sub.add_parser("verify")
    for name in ("vendor", "geo", "met", "baseline", "instrumented",
                 "trace", "receipt", "out"):
        validate.add_argument("--" + name, required=True, type=Path)
    a = parser.parse_args()
    if a.mode == "prepare":
        prepare(a.vendor, a.out, a.receipt)
    else:
        verify(a.vendor, a.geo, a.met, a.baseline,
               a.instrumented, a.trace, a.receipt, a.out)


if __name__ == "__main__":
    main()
