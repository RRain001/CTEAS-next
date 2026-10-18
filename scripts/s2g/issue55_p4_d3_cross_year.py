#!/usr/bin/env python3
"""P4 #55 D2/D3: authentic NOAA original/C++ READ62 across New Year.

All observations come from the same unmodified public archived IGRA POR.
The existing isolated producer must select each year independently, preserve
one static WMO source and use genuine 2022-12-31 / 2023-01-01 00/12
brackets. Original READ62 is run independently on exactly the same FSL
per year. This is bounded P4 source-only validation, not a P6 physics run.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from native_cpp.modules.p4_read62.data_prep.p4_case_year_gate import writer_window
from native_cpp.modules.p4_read62.verify_updat_parity import compare
from scripts.s2g.issue55_p4_d3_short import (
    ORIGINAL_NOAA, ORIGINAL_STATION, ROOT, WMO,
    exec_checked, replace_bang, sha, stage_case,
)

BEGIN = datetime(2022, 12, 31, 22)
END = datetime(2023, 1, 1, 6)
EXPECTED_SOURCE_SLOTS = ["2022123112", "2023010100", "2023010112"]


def run(native: Path, original: Path, template: Path, g19: Path) -> dict:
    for f in (native, original, template, g19, ORIGINAL_NOAA):
        if f.is_symlink() or not f.is_file():
            raise RuntimeError(f"required genuine original or compiler asset missing: {f}")
    if ORIGINAL_NOAA.stat().st_size < 20_000_000:
        raise RuntimeError("authentic retained NOAA POR unexpectedly small")
    source_sha = sha(ORIGINAL_NOAA)
    with tempfile.TemporaryDirectory(prefix="cteas-p4-55-crossyear-") as temp:
        scratch = Path(temp)
        case, _, _ = stage_case(scratch, 2022)
        cfgpath = case / "case.yaml"
        cfg = yaml.safe_load(cfgpath.read_text())
        cfg["preprocess"]["research_time"]["begin"] = BEGIN.strftime("%Y%m%d-%H%M%S")
        cfg["preprocess"]["research_time"]["end"] = END.strftime("%Y%m%d-%H%M%S")
        cfgpath.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
        (case / "grid/research_time").write_text(
            f"BEGIN: {BEGIN:%Y%m%d-%H%M%S}\nEND: {END:%Y%m%d-%H%M%S}\n",
            encoding="utf-8")

        archive = scratch / "authentic_read_only_igra_por"
        archive.mkdir()
        raw = archive / (ORIGINAL_STATION + "-data.txt")
        shutil.copyfile(ORIGINAL_NOAA, raw)
        if sha(raw) != source_sha:
            raise RuntimeError("source transport violated original NOAA SHA")
        upper = case / "met/upperair"
        command = [
            sys.executable, "-m",
            "native_cpp.modules.p4_read62.data_prep.run_cpp_pipeline",
            "--cpp-bin", str(native.resolve()),
            "--case-root", str(case),
            "--upperair-root", str(upper),
            "--offline-archive-root", str(archive),
            "--candidate-final", "--execute",
        ]
        exec_checked(command, cwd=ROOT, seconds=900)
        manifest = json.loads((upper / "p4_d1a_annual_manifest.json").read_text())
        jobs = manifest["stations"]
        if len(jobs) != 2 or {j["station_id"] for j in jobs} != {WMO}:
            raise RuntimeError("P4 did not independently prepare both true calendar years")
        if any(j["source_station_id"] != ORIGINAL_STATION
               or j["site_type"] != "VIRTUAL_RELOCATED" for j in jobs):
            raise RuntimeError("P4 changed real/effective station identity across the year")
        lineage = manifest["source_lineage"]
        if (lineage["years_with_boundary_inputs"] != [2022, 2023]
                or lineage["station_wmo"] != [WMO]
                or not lineage["real_aa_bb_each_hour"]):
            raise RuntimeError("P4 authentic AA/BB cross-year source lineage blocked")
        observed = set()
        for y in (2022, 2023):
            annual = lineage["source_and_cleaning_evidence"][str(y)][WMO]
            if annual["source_sha256"] != source_sha:
                raise RuntimeError("P4 reused inconsistent original NOAA POR SHA")
            observed.update(annual["original_valid_utc_slots"])
        if not set(EXPECTED_SOURCE_SLOTS).issubset(observed):
            raise RuntimeError("real 2022/2023 year-boundary 00/12 source missing")

        lo, hi = writer_window(BEGIN, END)
        parity_reports = []
        for job in sorted(jobs, key=lambda x: int(Path(x["output_updat"]).parent.parent.name)):
            year = int(Path(job["output_updat"]).parent.parent.name)
            if year == 2022:
                first, last = lo, datetime(2022, 12, 31, 23)
            elif year == 2023:
                first, last = datetime(2023, 1, 1, 0), hi
            else:
                raise RuntimeError("unexpected calendar year in P4 FSL/native UP")
            original_dir = scratch / f"original_read62_{year}"
            original_dir.mkdir()
            fsl = Path(job["input_fsl"])
            shutil.copyfile(fsl, original_dir / "58424.fsl")
            opts = {
                "INDAT": "58424.fsl", "UPDAT": "original_up.dat",
                "RUNLST": "original.lst",
                "IBYR": str(first.year), "IBMO": str(first.month),
                "IBDY": str(first.day), "IBHR": str(first.hour), "IBSEC": "0",
                "IEYR": str(last.year), "IEMO": str(last.month),
                "IEDY": str(last.day), "IEHR": str(last.hour), "IESEC": "0",
                "PSTOP": "500.0", "JDAT": "2", "IFMT": "1", "ISUB": "0",
                "LHT": "F", "LTEMP": "F", "LWD": "F", "LWS": "F",
                "LXTOP": "F", "LXSFC": "F",
            }
            (original_dir / "read62.inp").write_text(
                replace_bang(template.read_text(encoding="utf-8"), opts), encoding="utf-8")
            exec_checked([str(original.resolve()), "read62.inp"],
                         cwd=original_dir, seconds=180)
            original_up = original_dir / "original_up.dat"
            native_up = Path(job["output_updat"])
            evidence = compare(original_up, native_up)
            if not evidence["pass"] or original_up.read_bytes() != native_up.read_bytes():
                raise RuntimeError(f"2022/2023 real New Year original/native mismatch {year}: "
                                   + json.dumps(evidence["differences"][:5]))
            parity_reports.append({
                "year": year, "genuine_original_profiles": evidence["matched_profiles"],
                "matched_levels": evidence["matched_levels"],
                "matched_fields": evidence["matched_fields"],
                "original_native_bytes_identical": True,
                "source_sha256": source_sha,
                "same_fsl_sha256": sha(fsl),
                "original_up_sha256": sha(original_up),
                "cpp_up_sha256": sha(native_up),
            })
        if [p["year"] for p in parity_reports] != [2022, 2023]:
            raise RuntimeError("yearly original comparisons were not independently run")
        if [p["genuine_original_profiles"] for p in parity_reports] != [1, 2]:
            raise RuntimeError("P4 cross-year original source did not produce 1+2 genuine soundings")

        candidate = upper / "final/up_58424.dat"
        first_hour = int((BEGIN + timedelta(hours=1)).replace(tzinfo=timezone.utc).timestamp())
        last_hour = int(END.replace(tzinfo=timezone.utc).timestamp())
        verify = exec_checked([str(g19.resolve()), str(candidate), WMO,
                               str(first_hour), str(last_hour)], seconds=90)
        if "PASS_P6G_REAL_NOAA_UP_SOURCE_TIME_BRACKETS" not in verify or "HOURS=8" not in verify:
            raise RuntimeError("cross-year original 00/12 source G19 checker did not admit 8 hours")
        for wrong_station, bad_end in (("59999", last_hour), (WMO, last_hour + 36 * 3600)):
            failure = subprocess.run(
                [str(g19.resolve()), str(candidate), wrong_station,
                 str(first_hour), str(bad_end)],
                text=True, capture_output=True, timeout=90)
            if failure.returncode == 0 or "BLOCKED_P6G_NOAA_UP_SOURCE_PREFLIGHT" not in failure.stderr:
                raise RuntimeError("cross-year G19 accepted incorrect WMO or fictitious future source")
        final_meta = json.loads((upper / "final/p4_candidate_manifest.json").read_text())
        if (final_meta["files"][0]["soundings"] != 3
                or final_meta["station_count"] != 1):
            raise RuntimeError("cross-year final candidate lost authentic source soundings")
        if sha(ORIGINAL_NOAA) != source_sha or sha(raw) != source_sha:
            raise RuntimeError("NOAA original mutated")
        return {
            "status": "PASS_SCOPED_REAL_NOAA_2022_2023_AUTHENTIC_CROSS_YEAR",
            "year_boundary_utc": [BEGIN.isoformat(), END.isoformat()],
            "observed_genuine_00_12": EXPECTED_SOURCE_SLOTS,
            "original_noaa_igra": ORIGINAL_STATION,
            "original_noaa_por_sha256": source_sha,
            "wmo": WMO,
            "annual_independent_original_parity": parity_reports,
            "candidate_final_sha256": sha(candidate),
            "final_soundings": 3,
            "g19_hour_end_checked": 8,
            "wrong_wmo": "BLOCKED_AS_EXPECTED",
            "future_source_cloning": "BLOCKED_AS_EXPECTED",
            "p4_g19_source_only": "PASS_SCOPED",
            "p3_geo": "NOT_PRODUCED", "p5_surf": "NOT_PRODUCED",
            "g19_complete": "NOT_RUN", "p6_p7_physics": "NOT_RUN",
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--native-bin", type=Path, required=True)
    parser.add_argument("--original-bin", type=Path, required=True)
    parser.add_argument("--original-inp", type=Path, required=True)
    parser.add_argument("--g19-source-preflight", type=Path, required=True)
    parser.add_argument("--evidence-out", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.native_bin, args.original_bin, args.original_inp,
                 args.g19_source_preflight)
    if args.evidence_out.is_symlink():
        raise RuntimeError("cross-year evidence destination must not be symlink")
    args.evidence_out.parent.mkdir(parents=True, exist_ok=True)
    args.evidence_out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                                 encoding="utf-8")
    print("P4_D2_D3_REAL_CROSS_YEAR=" + result["status"])
    print("G19_COMPLETE=NOT_RUN P6_P7=NOT_RUN")


if __name__ == "__main__":
    main()
