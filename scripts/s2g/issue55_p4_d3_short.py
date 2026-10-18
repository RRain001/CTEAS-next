#!/usr/bin/env python3
"""#55 D3 bounded real NOAA independent original Fortran vs native READ62.

One real non-Hefei B-0 staged case, same immutable NOAA POR -> FSL -> native
and independently compiled unchanged Fortran READ62, strict byte/field parity.
Only 6 model hours; never asserts full-year/generic science or P6/P7 parity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
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
from native_cpp.modules.p5_smerge.data_prep import download_isd_by_grid as p5
from scripts.s2g.real_noaa_native_p4_up import ORIGINAL_NOAA, ORIGINAL_STATION
from scripts.s3f.verify_real_noaa_2022_2023_station_selection import (
    P5_STATIONS, generate_grid,
)

ROOT = Path(__file__).resolve().parents[2]
WMO = "58424"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as file:
        for part in iter(lambda: file.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def exec_checked(cmd: list[str], *, cwd: Path | None = None, seconds: int = 120) -> str:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                          check=False, timeout=seconds)
    if proc.returncode:
        raise RuntimeError(f"command failed {cmd[0]!r} rc={proc.returncode}:\n"
                           f"stdout={proc.stdout[-1500:]}\nstderr={proc.stderr[-1500:]}")
    return proc.stdout


def replace_bang(template: str, updates: dict[str, str]) -> str:
    out = template
    for key, value in updates.items():
        out, count = re.subn(
            r"(!\s*" + re.escape(key) + r"\s*=\s*)[^!]*!",
            lambda m: m.group(1) + value + " !", out, count=1)
        if count != 1:
            raise RuntimeError(f"original READ62 INP missing authoritative control {key}")
    return out


def stage_case(base: Path, year: int) -> tuple[Path, Path, Path]:
    case = base / f"huoshan_xinqiao_p4_real_{year}"
    catalog = p5.parse_history_txt(ROOT / "engine/resources/isd/isd-history.txt")
    positions = [(r.lat, r.lon) for r in catalog if r.sid in P5_STATIONS]
    if len(positions) != len(P5_STATIONS):
        raise RuntimeError("authentic Huoshan/Xinqiao source catalog missing")
    grid_file, center_file, time_file = generate_grid(case / "grid", positions)
    grid = load_strict_utm_grid(grid_file)
    center_txt = center_file.read_text()
    lat = float(re.search(r"latitude:\s*([-\d.]+)", center_txt).group(1))
    lon = float(re.search(r"longitude:\s*([-\d.]+)", center_txt).group(1))
    # Six hourly ends, supported original 00/12 UTC June 1 soundings.
    begin = datetime(year, 6, 1, 1)
    end = begin + timedelta(hours=6)
    time_file.write_text(f"BEGIN: {begin:%Y%m%d-%H%M%S}\n"
                         f"END: {end:%Y%m%d-%H%M%S}\n", encoding="utf-8")
    cfg = {
        "schema_version": 1,
        "case_name": case.name,
        "settings": {"timezone": "UTC+0000"},
        "preprocess": {
            "grid": {"utm_zone": grid.iutmzn, "hemisphere": grid.lsohem,
                     "center": {"latitude": lat, "longitude": lon},
                     "domain": {"length_km": grid.nx * grid.dgridkm,
                                "width_km": grid.ny * grid.dgridkm},
                     "resolution_km": grid.dgridkm, "nz": grid.nz},
            "research_time": {"begin": begin.strftime("%Y%m%d-%H%M%S"),
                              "end": end.strftime("%Y%m%d-%H%M%S")},
            "upperair": {"station_id": "auto", "pstop_hpa": 500.0},
        },
        "puff": {"point_sources": [{"latitude": lat, "longitude": lon}]},
    }
    case.mkdir(parents=True, exist_ok=True)
    (case / "met").mkdir()
    (case / "case.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    return case, begin, end


def run(year: int, native: Path, original: Path, inp_template: Path,
        preflight: Path) -> dict:
    if year not in (2022, 2023):
        raise ValueError("only genuine archived Anqing 2022/2023 test years admitted")
    for path in (native, original, inp_template, preflight, ORIGINAL_NOAA):
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"required authentic source/compiler artifact missing: {path}")
    if ORIGINAL_NOAA.stat().st_size < 20_000_000:
        raise RuntimeError("the retained genuine NOAA Anqing POR was not restored")
    original_sha = sha(ORIGINAL_NOAA)
    with tempfile.TemporaryDirectory(prefix="cteas-p4-55-d3-") as dirname:
        work = Path(dirname)
        case, begin, end = stage_case(work, year)
        archive = work / "read_only_noaa"
        archive.mkdir()
        raw = archive / (ORIGINAL_STATION + "-data.txt")
        shutil.copyfile(ORIGINAL_NOAA, raw)
        if sha(raw) != original_sha:
            raise RuntimeError("genuine NOAA source copy changed")
        upper = case / "met/upperair"
        cmd = [
            sys.executable, "-m", "native_cpp.modules.p4_read62.data_prep.run_cpp_pipeline",
            "--cpp-bin", str(native.resolve()),
            "--case-root", str(case), "--upperair-root", str(upper),
            "--offline-archive-root", str(archive),
            "--candidate-final", "--execute",
        ]
        exec_checked(cmd, cwd=ROOT, seconds=900)
        manifest = json.loads((upper / "p4_d1a_annual_manifest.json").read_text())
        assert manifest["status"] == "PRODUCED_UNVERIFIED"
        assert manifest["candidate_final"]["status"] == "PRODUCED_UNVERIFIED"
        jobs = manifest["stations"]
        if len(jobs) != 1 or jobs[0]["source_station_id"] != ORIGINAL_STATION:
            raise RuntimeError(f"non-Hefei case did not select authentic nearest Anqing: {jobs}")
        job = jobs[0]
        assert job["station_id"] == WMO and job["site_type"] == "VIRTUAL_RELOCATED"
        year_data = manifest["source_lineage"]["source_and_cleaning_evidence"][str(year)][WMO]
        if job["raw_igra_sha256"] != original_sha or year_data["source_sha256"] != original_sha:
            raise RuntimeError("offline original source lineage lost during annual selection")
        raw_cpp = Path(job["output_updat"])
        fsl = Path(job["input_fsl"])
        reference_dir = work / "original"
        reference_dir.mkdir()
        shutil.copyfile(fsl, reference_dir / "58424.fsl")
        original_output = reference_dir / "original_up.dat"
        options = {
            "INDAT": "58424.fsl", "UPDAT": "original_up.dat",
            "RUNLST": "original.lst",
            "IBYR": str(year), "IBMO": "6", "IBDY": "1", "IBHR": "0", "IBSEC": "0",
            "IEYR": str(year), "IEMO": "6", "IEDY": "1", "IEHR": "12", "IESEC": "0",
            "PSTOP": "500.0", "JDAT": "2", "IFMT": "1",
            "ISUB": "0", "LHT": "F", "LTEMP": "F",
            "LWD": "F", "LWS": "F", "LXTOP": "F", "LXSFC": "F",
        }
        control = replace_bang(inp_template.read_text(encoding="utf-8"), options)
        inp = reference_dir / "read62.inp"
        inp.write_text(control, encoding="utf-8")
        exec_checked([str(original.resolve()), "read62.inp"],
                     cwd=reference_dir, seconds=180)
        if not original_output.is_file():
            raise RuntimeError("original Fortran produced no UP.DAT")
        parity = compare(original_output, raw_cpp)
        if not parity["pass"] or original_output.read_bytes() != raw_cpp.read_bytes():
            raise RuntimeError("original READ62/C++ D3 parity failure: "
                               + json.dumps(parity["differences"][:5]))
        # Final UP is validated by the independently compiled P6 source-only
        # original-format reader, NOT by a CALMET/P6 physics model.
        final = upper / "final" / f"up_{WMO}.dat"
        first_hour = int((begin + timedelta(hours=1))
                         .replace(tzinfo=timezone.utc).timestamp())
        last_hour = int(end.replace(tzinfo=timezone.utc).timestamp())
        proof = exec_checked([str(preflight.resolve()), str(final), WMO,
                              str(first_hour), str(last_hour)], seconds=90)
        if (f"WMO={WMO}" not in proof or "HOURS=6" not in proof
                or "PASS_P6G_REAL_NOAA_UP_SOURCE_TIME_BRACKETS" not in proof):
            raise RuntimeError("P6 original-format G19 source-only bracket proof invalid")
        # Fail-closed negative probes: wrong station and missing future bracket.
        for sid, final_hour in ((str(int(WMO) + 1), last_hour),
                                (WMO, last_hour + 36 * 3600)):
            negative = subprocess.run(
                [str(preflight.resolve()), str(final), sid, str(first_hour),
                 str(final_hour)], capture_output=True, text=True, timeout=90)
            if negative.returncode == 0 or "BLOCKED_P6G_NOAA_UP_SOURCE_PREFLIGHT" not in negative.stderr:
                raise RuntimeError("P6 source-only negative bracket/WMO check unexpectedly accepted")
        if sha(ORIGINAL_NOAA) != original_sha or sha(raw) != original_sha:
            raise RuntimeError("immutable NOAA source changed during independent parity")
        return {
            "status": "PASS_SCOPED_REAL_NON_HEFEI_SHORT_P4_D3_RAW_PARITY_AND_UP_PREFLIGHT",
            "year": year, "site": "independent Huoshan/Xinqiao-centred WGS84 UTM50N",
            "noaa_source": ORIGINAL_STATION, "source_wmo": WMO,
            "source_sha256": original_sha, "source_station_count": 1,
            "site_type": job["site_type"],
            "original_source_sha256": sha(inp_template),
            "original_read62_binary_sha256": sha(original),
            "native_read62_binary_sha256": sha(native),
            "same_fsl_sha256": sha(fsl),
            "fortran_raw_up_sha256": sha(original_output),
            "native_raw_up_sha256": sha(raw_cpp),
            "raw_up_byte_identical": True,
            "matched_profiles": parity["matched_profiles"],
            "matched_levels": parity["matched_levels"],
            "matched_fields": parity["matched_fields"],
            "final_candidate_sha256": sha(final),
            "original_format_g19_source_only": "PASS_SCOPED_6_HOURS",
            "negative_wrong_wmo": "BLOCKED_AS_EXPECTED",
            "negative_missing_future_bracket": "BLOCKED_AS_EXPECTED",
            "P4_FULL_YEAR_ORIGINAL_PARITY": "NOT_RUN_THIS_D3",
            "P3_GEO": "NOT_PRODUCED", "P5_SURF": "NOT_PRODUCED",
            "G19_COMPLETE": "NOT_RUN",
            "P6_PHYSICS": "NOT_RUN", "P7": "NOT_RUN",
        }


def main() -> int:
    p = argparse.ArgumentParser(description="Bounded original Fortran/native P4 D3 real-source parity")
    p.add_argument("--year", type=int, required=True, choices=(2022, 2023))
    p.add_argument("--native-bin", type=Path, required=True)
    p.add_argument("--original-bin", type=Path, required=True)
    p.add_argument("--original-inp", type=Path, required=True)
    p.add_argument("--g19-source-preflight", type=Path, required=True)
    p.add_argument("--evidence-out", type=Path, required=True)
    a = p.parse_args()
    report = run(a.year, a.native_bin, a.original_bin,
                 a.original_inp, a.g19_source_preflight)
    if a.evidence_out.is_symlink():
        raise ValueError("evidence destination symlink forbidden")
    a.evidence_out.parent.mkdir(parents=True, exist_ok=True)
    a.evidence_out.write_text(json.dumps(report, indent=2, ensure_ascii=False)
                              + "\n", encoding="utf-8")
    print("P4_D3=" + report["status"])
    print("G19_COMPLETE=NOT_RUN P4_FULL_YEAR_ORIGINAL_PARITY=NOT_RUN")


if __name__ == "__main__":
    raise SystemExit(main())
