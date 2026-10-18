#!/usr/bin/env python3
"""G1B-B2 genuine original NOAA 2022/23 -> native P5 SURF.DAT, input-only.

Uses unchanged S3-F official NOAA source-selection and original ISD/ISD-Lite
bytes, but ALL P5 stage globals and C++ working files are isolated in one
temporary new-site WGS84 UTM case per year. No mutation of project/current or
frozen Hefei case. The actual stage-2 primary-wind and sparse-secondary science
modules run unchanged, not substituted or mocked. No P6 numerical model/P7.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from native_cpp.modules.p5_smerge.data_prep import isd_to_smerge_and_fill as process
from native_cpp.modules.p5_smerge.data_prep import clean_merge_filled_by_research_time as clean
from native_cpp.modules.p5_smerge.data_prep import convert_cleaned_to_smerge_ready as ready
from native_cpp.modules.p5_smerge.data_prep import generate_smerge_input_sections as control
from native_cpp.modules.p5_smerge.data_prep import download_isd_by_grid as p5
from native_cpp.modules.p5_smerge.data_prep.isd_lite_wind import filename as lite_filename
from scripts.s3f.verify_real_noaa_2022_2023_station_selection import (
    ROOT, YEARS, P5_STATIONS, digest, p5_check,
)

MODEL_START = (6, 1, 0)
MODEL_END = (6, 1, 7)
EXPECTED_HOURS = 7


def _bin(path: Path) -> Path:
    if path.is_symlink() or not path.is_file():
        raise ValueError("required explicit native C++ executable missing or symlink")
    return path.absolute()


def _call(func, label: str) -> None:
    result = func()
    if result not in (0, None):
        raise RuntimeError(f"P5 original-source stage {label} failed: {result}")


def _stage_year(raw_source: Path, case: Path, year: int) -> dict:
    grid_dir = case / "grid"
    grid_dir.mkdir(parents=True)
    for file in ("grid.cmn", "center_location"):
        shutil.copyfile(raw_source.parent / "grid" / file, grid_dir / file)
    research = grid_dir / "research_time"
    research.write_text(
        f"BEGIN: {year}0601-000000\nEND: {year}0601-070000\n",
        encoding="utf-8")
    raw = case / "met/surface/isd_raw"
    raw.mkdir(parents=True)
    for sid in P5_STATIONS:
        for src, rel in (
            (raw_source / f"{sid}-{year}.csv", f"{sid}-{year}.csv"),
            (raw_source / "isd_lite" / lite_filename(sid, year),
             "isd_lite/" + lite_filename(sid, year)),
        ):
            if not src.is_file() or src.stat().st_size == 0:
                raise FileNotFoundError("genuine NOAA original source unavailable: " + str(src))
            dst = raw / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
            if digest(src) != digest(dst):
                raise RuntimeError("actual NOAA source staging changed bytes")
    src_manifest = raw_source / f"station_selection_{year}.json"
    shutil.copyfile(src_manifest, raw / src_manifest.name)
    manifest = json.loads(src_manifest.read_text(encoding="utf-8"))
    if (manifest.get("mode") != "OBSERVED" or
            manifest.get("station_selection_case") != "IN_DOMAIN_MULTIPLE" or
            len(manifest["stations"]) != 2 or
            {s["sid"] for s in manifest["stations"]} != set(P5_STATIONS)):
        raise RuntimeError("not genuine NOAA 2-station in-domain annual selection")
    sorted_station = sorted(manifest["stations"], key=lambda st: (
        -st["isd_lite_raw_hours"], -st["full_isd_raw_hours"], st["sid"]))
    if manifest["primary_sid"] != sorted_station[0]["sid"]:
        raise RuntimeError("primary station does not match authentic raw rankings")
    if sum(s["wind_treatment"] == "COMPLETE_FILL_AND_CALM_REPLACE"
           for s in manifest["stations"]) != 1:
        raise RuntimeError("source selector lost primary/sparse role distinction")

    run_dir = case / "run/smerge"
    run_dir.mkdir(parents=True)
    sm_template = ROOT / "engine/templates/smerge.inp"
    if not sm_template.is_file():
        raise FileNotFoundError("original selected SMERGE control template missing")
    shutil.copyfile(sm_template, run_dir / "smerge.inp")
    return {"manifest": manifest, "raw": raw, "run_dir": run_dir}


def _process_to_control(case: Path) -> dict:
    base = case / "met/surface"
    out_fill = base / "isd2smerge_and_fill"
    out_clean = base / "isd2smerge_cleaned"
    out_ready = base / "isd2smerge_ready"
    run = case / "run/smerge"
    # Each global path belongs to a production stage; the bound original
    # Python algorithm and its subprocess interpolate operate in scratch.
    mutations = [
        (process, "BASE_DIR", base),
        (process, "INPUT_DIR", base / "isd_raw"),
        (process, "OUTPUT_DIR", out_fill),
        (clean, "CASE_ROOT", case),
        (clean, "INPUT_DIR", out_fill),
        (clean, "OUTPUT_DIR", out_clean),
        (clean, "RESEARCH_TIME_FILE", case / "grid/research_time"),
        (ready, "CASE_ROOT", case),
        (ready, "INPUT_DIR", out_clean),
        (ready, "OUTPUT_DIR", out_ready),
        (control, "CASE_ROOT", case),
        (control, "INPUT_DIR", out_ready),
        (control, "OUTPUT_DIR", run),
        (control, "SMERGE_INP", run / "smerge.inp"),
        (control, "OUTPUT_TXT", run / "smerge_manual_sections.txt"),
    ]
    with contextlib.ExitStack() as stack:
        for module, name, value in mutations:
            stack.enter_context(patch.object(module, name, value))
        _call(process.main, "original NOAA full+Lite -> role-aware GENERIC")
        _call(clean.main, "complete primary wind and retain sparse secondary")
        _call(ready.main, "original compatible SMERGE-ready GENERIC")
        _call(control.main, "write original compatible isolated smerge.inp")
    # Validate original scientific wind treatments were separately published.
    stage_rows = {}
    for path in sorted(out_fill.glob("*_filled.stage.json")):
        if re.search(r"\d{6}-\d{5}-\d{4}_filled.stage.json$", path.name):
            meta = json.loads(path.read_text(encoding="utf-8"))
            sid = path.name[:6] + path.name[7:12]
            stage_rows[sid] = meta["stage"]
    if set(stage_rows) != set(P5_STATIONS):
        raise RuntimeError("P5 yearly output stage provenance missing/extra stations")
    if sorted(stage_rows.values()) != ["final", "secondary_raw_sparse"]:
        raise RuntimeError("P5 primary filled/sparse secondary wind policy not preserved")
    return {"wind_stages": stage_rows, "run_dir": run,
            "source_stage_files_sha256": {
                str(p.relative_to(case)): digest(p)
                for p in sorted(out_ready.glob("*.csv"))
            }}


def _from_control_order(inp: Path) -> list[int]:
    from native_cpp.modules.p5_smerge.data_prep.run_smerge_and_monitor import (
        parse_station_records,
    )
    rows = parse_station_records(inp.read_text(encoding="utf-8"))
    ids = [int(st["ifstn"]) for st in rows]
    if len(ids) != len(set(ids)) or not ids:
        raise RuntimeError("P5 source control contains duplicate/no station aliases")
    return ids


def _run_cpp(native_p5: Path, cpp_reader: Path, case: Path,
             manifest: dict, year: int, run_dir: Path) -> dict:
    ctl = run_dir / "smerge.inp"
    text = ctl.read_text(encoding="utf-8")
    ids = _from_control_order(ctl)
    expected = {int(s["ifstn"]) for s in manifest["stations"]}
    if set(ids) != expected or len(ids) != 2:
        raise RuntimeError("P5 SMERGE deck identifiers not equal raw NOAA annual selection")
    for key, val in (("NFF", "2"), ("JDAT", "8"), ("IOFORM", "2"), ("IOPACK", "0")):
        match = re.search(r"!\s*" + key + r"\s*=\s*([^!]+)!", text, re.I)
        if not match or match.group(1).strip().strip("'") != val:
            raise RuntimeError(f"unsupported original P5 control {key}")
    produced = subprocess.run([str(native_p5), str(ctl)], cwd=run_dir,
                              capture_output=True, text=True, check=False, timeout=150)
    if produced.returncode or "P5_CPP_SURFDAT_OK" not in produced.stderr:
        raise RuntimeError("actual native C++ SMERGE writer rejected NOAA-derived GENERIC: "
                           + produced.stderr[-1800:])
    surf = run_dir / "surf.dat"
    if not surf.is_file() or surf.stat().st_size < 200:
        raise RuntimeError("native P5 original SURF.DAT not produced")
    positive = subprocess.run([str(cpp_reader), str(surf), str(EXPECTED_HOURS),
                               *[str(i) for i in ids]],
                              check=False, text=True, capture_output=True, timeout=90)
    if positive.returncode or "PASS_P6G_REAL_NOAA_NATIVE_SURF_SOURCE_HOURLY" not in positive.stdout:
        raise RuntimeError("independent P6 native SURF source reader failed: "
                           + positive.stderr[-1500:])
    wrong = subprocess.run([str(cpp_reader), str(surf), str(EXPECTED_HOURS),
                            *[str(i) for i in reversed(ids)]],
                           capture_output=True, text=True, check=False, timeout=90)
    if wrong.returncode == 0 or "BLOCKED_P6G_REAL_NOAA_SURF_SOURCE" not in wrong.stderr:
        raise RuntimeError("independent native SURF reader did not reject wrong station ordering")
    corrupt = case / "corrupted_source_surf.dat"
    content = surf.read_bytes().splitlines(keepends=True)
    if len(content) < 9:
        raise RuntimeError("SURF original format unexpectedly short")
    corrupt.write_bytes(b"".join(content[:-1]))
    missing = subprocess.run([str(cpp_reader), str(corrupt), str(EXPECTED_HOURS),
                              *[str(i) for i in ids]],
                             capture_output=True, text=True, check=False, timeout=90)
    if missing.returncode == 0 or "BLOCKED_P6G_REAL_NOAA_SURF_SOURCE" not in missing.stderr:
        raise RuntimeError("independent original SURF reader accepted truncated station-hour")
    return {
        "surf_sha256": digest(surf), "surf_bytes": surf.stat().st_size,
        "control_sha256": digest(ctl),
        "native_p5_executable_sha256": digest(native_p5),
        "independent_cpp_source_reader_sha256": digest(cpp_reader),
        "native_p5_writer": produced.stderr[-1200:],
        "independent_cpp_surf_reader": positive.stdout[-1200:],
        "ordered_station_ifstn_ids": ids,
        "source_station_ids": [s["sid"] for s in manifest["stations"]],
        "negative_reversed_station_order": "BLOCKED_AS_EXPECTED",
        "negative_truncated_original_hour": "BLOCKED_AS_EXPECTED",
    }


def run(native_p5: Path, cpp_reader: Path) -> dict:
    native_p5 = _bin(native_p5)
    cpp_reader = _bin(cpp_reader)
    with tempfile.TemporaryDirectory(prefix="s2g1bb2-authentic-noaa-surf-") as td:
        top = Path(td)
        provenance = p5_check(top / "authentic_p5")
        original = top / "authentic_p5/surface"
        evidence = []
        for year in YEARS:
            case = top / f"independent_huoshan_xinqiao_surface_{year}"
            case.mkdir()
            setup = _stage_year(original, case, year)
            prepared = _process_to_control(case)
            compiled = _run_cpp(native_p5, cpp_reader, case,
                                setup["manifest"], year, prepared["run_dir"])
            # Retained original NOAA full and Lite bytes remain unchanged.
            source_hashes = {}
            for sid in P5_STATIONS:
                for rel in (f"{sid}-{year}.csv",
                            "isd_lite/" + lite_filename(sid, year)):
                    item = setup["raw"] / rel
                    key = f"{year}/{rel}"
                    source_hashes[key] = digest(item)
                    if source_hashes[key] != provenance["raw_sha256"][rel]:
                        raise RuntimeError("NOAA source changed after processing")
            evidence.append({
                "year": year,
                "selection_manifest_sha256":
                    digest(setup["raw"] / f"station_selection_{year}.json"),
                "primary_sid": setup["manifest"]["primary_sid"],
                "station_roles": {
                    s["sid"]: s["wind_treatment"]
                    for s in setup["manifest"]["stations"]
                },
                "original_noaa_sha256": source_hashes,
                **prepared, **compiled,
            })
        return {
            "status": "G1BB2_REAL_NOAA_P5_NATIVE_SURF_INPUT_PASS_SCOPED",
            "site": "new Huoshan/Xinqiao shared WGS84 UTM50N original NOAA 2022/2023",
            "annual_original_primary_switch": provenance["real_primary_switch"],
            "years": evidence,
            "P3_GEO": "NOT_PRODUCED",
            "G19_FULL_SOURCE": "BLOCKED_NO_INDEPENDENT_GEO",
            "P6D_P6E_P6F": "NOT_RUN",
            "P7": "NOT_RUN",
            "G5": "NOT_RUN",
            "science_45_field_accepted": False,
        }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Genuine NOAA 2 year P5 source-only native SURF")
    ap.add_argument("--native-p5-bin", required=True, type=Path)
    ap.add_argument("--native-surf-preflight-bin", required=True, type=Path)
    ap.add_argument("--evidence-out", required=True, type=Path)
    args = ap.parse_args(argv)
    try:
        result = run(args.native_p5_bin, args.native_surf_preflight_bin)
        if args.evidence_out.is_symlink():
            raise ValueError("output JSON symlink not allowed")
        args.evidence_out.parent.mkdir(parents=True, exist_ok=True)
        args.evidence_out.write_text(
            json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        print("S2G_G1BB2="+result["status"])
        print("P3_GEO=NOT_PRODUCED G19_FULL_SOURCE=BLOCKED")
        print("P6D_E_F=NOT_RUN P7=NOT_RUN")
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(json.dumps({
            "status":"BLOCKED_GENUINE_NOAA_NATIVE_P5_SURF",
            "error":str(exc), "P6":"NOT_RUN", "P7":"NOT_RUN",
        }, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
