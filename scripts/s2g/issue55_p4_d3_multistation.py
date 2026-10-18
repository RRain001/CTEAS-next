#!/usr/bin/env python3
"""#55 D3 real in-domain 1/N upper-air stations, original READ62 vs C++.

This is a bounded 6-hour source-only multi-station case. Both observations
are complete, unmodified NOAA IGRA POR files retained in existing snapshots.
No original annual data are fabricated or downloaded. No CALMET/P6 model.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from engine.run_met.station_grid import load_strict_utm_grid
from native_cpp.modules.p4_read62.verify_updat_parity import compare
from native_cpp.modules.p4_read62.data_prep.p4_case_year_gate import writer_window
from native_cpp.modules.p4_read62.data_prep.download_igra import load_station_list
from scripts.s2g.issue55_p4_d3_short import exec_checked, replace_bang, sha
from scripts.s3f.verify_real_noaa_2022_2023_station_selection import (
    HEFEI, SMOKE, P4_STATIONS, generate_grid,
)

ROOT = Path(__file__).resolve().parents[2]
RAW = {
    "CHM00058203": SMOKE / "met/upperair/2023/CHM00058203-data.txt",
    "CHM00058424": HEFEI / "met/upperair/2022/CHM00058424-data.txt",
}
WMO = ("58203", "58424")


def stage(base: Path, year: int) -> tuple[Path, datetime, datetime]:
    station_list = load_station_list(ROOT / "engine/resources/igra/igra2-station-list.txt")
    stations = {row["id"]: row for row in station_list if row["id"] in P4_STATIONS}
    if set(stations) != set(P4_STATIONS):
        raise RuntimeError("authentic IGRA source catalog lacks expected two station IDs")
    positions = [(stations[sid]["lat"], stations[sid]["lon"]) for sid in P4_STATIONS]
    case = base / f"p4_two_real_in_domain_utm50_{year}"
    grid_file, center_file, clock_file = generate_grid(case / "grid", positions)
    grid = load_strict_utm_grid(grid_file)
    center = center_file.read_text(encoding="utf-8")
    lat = float(re.search(r"latitude:\s*([-\d.]+)", center).group(1))
    lon = float(re.search(r"longitude:\s*([-\d.]+)", center).group(1))
    # Pre-registered short window; two independent authentic sources must both
    # contain 00 and 12 UTC or the test blocks rather than using filled slots.
    begin = datetime(year, 6, 1, 1)
    end = begin + timedelta(hours=6)
    clock_file.write_text(
        f"BEGIN: {begin:%Y%m%d-%H%M%S}\nEND: {end:%Y%m%d-%H%M%S}\n",
        encoding="utf-8")
    config = {
        "schema_version": 1,
        "case_name": case.name,
        "settings": {"timezone": "UTC+0000"},
        "preprocess": {
            "grid": {
                "utm_zone": grid.iutmzn, "hemisphere": grid.lsohem,
                "center": {"latitude": lat, "longitude": lon},
                "domain": {"length_km": grid.nx * grid.dgridkm,
                           "width_km": grid.ny * grid.dgridkm},
                "resolution_km": grid.dgridkm, "nz": grid.nz,
            },
            "research_time": {
                "begin": begin.strftime("%Y%m%d-%H%M%S"),
                "end": end.strftime("%Y%m%d-%H%M%S"),
            },
            "upperair": {"station_id": "auto", "pstop_hpa": 500.0},
        },
        "puff": {"point_sources": [{"latitude": lat, "longitude": lon}]},
    }
    case.mkdir(parents=True, exist_ok=True)
    (case / "met").mkdir()
    (case / "case.yaml").write_text(yaml.safe_dump(config, sort_keys=False),
                                    encoding="utf-8")
    return case, begin, end


def run(year: int, native: Path, original: Path, template: Path,
        g19: Path) -> dict:
    if year not in (2022, 2023):
        raise ValueError("only 2022/2023 original NOAA source years supported")
    all_files = [native, original, template, g19, *RAW.values()]
    for item in all_files:
        if not item.is_file() or item.is_symlink():
            raise RuntimeError(f"original input/binary missing or symlink: {item}")
    source_shas = {sid: sha(file) for sid, file in RAW.items()}
    if any(RAW[sid].stat().st_size < 1_000_000 for sid in RAW):
        raise RuntimeError("NOAA IGRA POR files unexpectedly small")
    with tempfile.TemporaryDirectory(prefix="p4-55-two-noaa-") as td:
        sandbox = Path(td)
        case, begin, end = stage(sandbox, year)
        archive = sandbox / "original_noaa_read_only"
        archive.mkdir()
        for sid, src in RAW.items():
            item = archive / (sid + "-data.txt")
            shutil.copyfile(src, item)
            if sha(item) != source_shas[sid]:
                raise RuntimeError("retained NOAA POR byte identity was not preserved")
        upper = case / "met/upperair"
        cmd = [
            sys.executable, "-m", "native_cpp.modules.p4_read62.data_prep.run_cpp_pipeline",
            "--cpp-bin", str(native.resolve()), "--case-root", str(case),
            "--upperair-root", str(upper), "--offline-archive-root", str(archive),
            "--candidate-final", "--execute",
        ]
        exec_checked(cmd, cwd=ROOT, seconds=900)
        manifest = json.loads((upper / "p4_d1a_annual_manifest.json").read_text())
        jobs = manifest["stations"]
        if len(jobs) != 2 or {j["source_station_id"] for j in jobs} != set(RAW):
            raise RuntimeError("real 1/N in-domain stations not retained independently")
        if any(j["site_type"] != "OBSERVED" for j in jobs):
            raise RuntimeError("NOAA in-domain stations must not be virtual relocated")
        if sorted(j["station_id"] for j in jobs) != list(WMO):
            raise RuntimeError("two original WMO identities not preserved")
        if (manifest["source_lineage"]["station_wmo"] != list(WMO)
                or manifest["candidate_final"]["station_count"] != 2):
            raise RuntimeError("cross-year P4 final metadata station count incorrect")
        stations_csv = list(csv.DictReader((upper / "final/stations.csv").open()))
        if [s["station_id"] for s in stations_csv] != list(WMO):
            raise RuntimeError("CALMET P4 final static WMO station ordering invalid")
        begin_raw, end_raw = writer_window(begin, end)
        first = int((begin + timedelta(hours=1)).replace(tzinfo=timezone.utc).timestamp())
        last = int(end.replace(tzinfo=timezone.utc).timestamp())
        output = []
        for job in sorted(jobs, key=lambda j: j["station_id"]):
            wmo = job["station_id"]
            source = job["source_station_id"]
            if sha(Path(job["raw_igra"])) != source_shas[source]:
                raise RuntimeError("genuine original NOAA source lineage not retained")
            original_dir = sandbox / ("fortran_" + wmo)
            original_dir.mkdir()
            fsl = Path(job["input_fsl"])
            shutil.copyfile(fsl, original_dir / (wmo + ".fsl"))
            options = {
                "INDAT": wmo + ".fsl", "UPDAT": "original_up.dat",
                "RUNLST": "original.lst",
                "IBYR": str(begin_raw.year), "IBMO": str(begin_raw.month),
                "IBDY": str(begin_raw.day), "IBHR": str(begin_raw.hour),
                "IBSEC": "0", "IEYR": str(end_raw.year),
                "IEMO": str(end_raw.month), "IEDY": str(end_raw.day),
                "IEHR": str(end_raw.hour), "IESEC": "0",
                "PSTOP": "500.0", "JDAT": "2", "IFMT": "1", "ISUB": "0",
                "LHT": "F", "LTEMP": "F", "LWD": "F",
                "LWS": "F", "LXTOP": "F", "LXSFC": "F",
            }
            (original_dir / "read62.inp").write_text(
                replace_bang(template.read_text(encoding="utf-8"), options),
                encoding="utf-8")
            exec_checked([str(original.resolve()), "read62.inp"],
                         cwd=original_dir, seconds=180)
            fortran_up = original_dir / "original_up.dat"
            cpp_up = Path(job["output_updat"])
            parity = compare(fortran_up, cpp_up)
            if not parity["pass"] or fortran_up.read_bytes() != cpp_up.read_bytes():
                raise RuntimeError(f"{wmo} genuine NOAA original/native parity difference: "
                                   + json.dumps(parity["differences"][:5]))
            final = upper / "final" / ("up_" + wmo + ".dat")
            proof = exec_checked([str(g19.resolve()), str(final), wmo,
                                  str(first), str(last)], seconds=90)
            if (f"WMO={wmo}" not in proof or "HOURS=6" not in proof
                    or "PASS_P6G_REAL_NOAA_UP_SOURCE_TIME_BRACKETS" not in proof):
                raise RuntimeError(f"{wmo} did not pass source-only G19 reader")
            negative = subprocess.run(
                [str(g19.resolve()), str(final), "59999", str(first), str(last)],
                capture_output=True, text=True, timeout=90)
            if negative.returncode == 0:
                raise RuntimeError("G19 source-only preflight accepted wrong station")
            output.append({
                "source_station": source, "wmo": wmo,
                "source_site_type": job["site_type"], "noaa_sha256": source_shas[source],
                "native_fsl_sha256": sha(fsl),
                "original_up_sha256": sha(fortran_up),
                "native_up_sha256": sha(cpp_up), "byte_identical": True,
                "matched_profiles": parity["matched_profiles"],
                "matched_levels": parity["matched_levels"],
                "matched_fields": parity["matched_fields"],
                "final_up_sha256": sha(final),
                "g19_source_only_hours": 6,
            })
        if {sha(path) for path in RAW.values()} != set(source_shas.values()):
            raise RuntimeError("retained original raw NOAA unexpectedly mutated")
        return {
            "status": "PASS_SCOPED_TWO_REAL_IN_DOMAIN_STATIONS_ORIGINAL_READ62_PARITY",
            "year": year, "site": "independent NOAA two-in-domain-station UTM50N",
            "station_count": 2, "stations": output,
            "source_catalog": "authentic unmodified NOAA IGRA station-list",
            "station_csv_sha256": sha(upper / "final/stations.csv"),
            "original_read62_binary_sha256": sha(original),
            "native_read62_binary_sha256": sha(native),
            "g19_reader_sha256": sha(g19),
            "real_full_year_original_parity": "NOT_RUN",
            "joint_geo_surf_up": "NOT_RUN", "p6_physics": "NOT_RUN",
            "p7": "NOT_RUN",
        }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, choices=(2022, 2023), required=True)
    ap.add_argument("--native-bin", type=Path, required=True)
    ap.add_argument("--original-bin", type=Path, required=True)
    ap.add_argument("--original-inp", type=Path, required=True)
    ap.add_argument("--g19-source-preflight", type=Path, required=True)
    ap.add_argument("--evidence-out", type=Path, required=True)
    args = ap.parse_args()
    out = run(args.year, args.native_bin, args.original_bin,
              args.original_inp, args.g19_source_preflight)
    if args.evidence_out.is_symlink():
        raise RuntimeError("evidence target must not be a symlink")
    args.evidence_out.parent.mkdir(parents=True, exist_ok=True)
    args.evidence_out.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n",
                                 encoding="utf-8")
    print("P4_55_D3_MULTISTATION=" + out["status"])
    print("ORIGINAL_MULTI_STATION_COUNT=2 FULL_YEAR=NOT_RUN P6_P7=NOT_RUN")


if __name__ == "__main__":
    main()
