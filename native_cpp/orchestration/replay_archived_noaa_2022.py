#!/usr/bin/env python3
"""Offline, immutable archived NOAA 2022 -> FSL/GENERIC selected-case replay.

Runs REAL P4 IGRA and P5 full-ISD/ISD-Lite wind preprocessing, not synthetic
test vectors. Never downloads files, updates project/current, writes to the
golden case or invokes original READ62/SMERGE/CALMET binaries.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
from pathlib import Path

CASE_ID = "hefei5km_2022_reference_case_20261011"
P4_RAW = "met/upperair/2022/CHM00058424-data.txt"
P4_SELECTION = "met/upperair/2022/upperair_station_used_list.txt"
P4_PSTOP = "met/upperair/2022/pstop_hpa.txt"
P4_REFERENCE = "met/upperair/2022/igra2fsl/58424.txt"
P5_FULL = "met/surface/isd_raw/58321099999-2022.csv"
P5_LITE = "met/surface/isd_raw/isd_lite/583210-99999-2022.gz"
P5_SELECTION = "met/surface/isd_raw/station_selection_2022.json"
P5_REFERENCE = "met/surface/isd2smerge_ready/583210-99999.csv"
TIME = "grid/research_time"
SOURCES = [P4_RAW,P4_SELECTION,P4_PSTOP,P4_REFERENCE,P5_FULL,P5_LITE,
           P5_SELECTION,P5_REFERENCE,TIME]


def sha(path: Path) -> str:
    d=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):
            d.update(block)
    return d.hexdigest()


def checked(case: Path, relative: str) -> Path:
    p=case
    for name in Path(relative).parts:
        p=p/name
        if p.is_symlink():
            raise ValueError("symlink source not allowed: "+relative)
    if not p.is_file():
        raise ValueError("required source missing: "+relative)
    return p


def copy_source(case: Path, work: Path, relative: str) -> Path:
    src=checked(case,relative)
    dst=work/relative
    dst.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(src,dst)
    if sha(src)!=sha(dst):
        raise ValueError("source copy changed: "+relative)
    return dst


def byte_gate(generated: Path, expected: Path, label: str) -> dict:
    if not generated.is_file():
        raise ValueError(label+" output missing")
    produced={"bytes":generated.stat().st_size,"sha256":sha(generated)}
    frozen={"bytes":expected.stat().st_size,"sha256":sha(expected)}
    if produced!=frozen:
        left=generated.read_bytes()
        right=expected.read_bytes()
        first=next((i for i,(a,b) in enumerate(zip(left,right)) if a!=b),min(len(left),len(right)))
        # Bounded diagnostics only, no original raw archived data copies.
        mismatch={"status":"MISMATCH_NOT_ACCEPTED","fresh":produced,
                  "frozen":frozen,"first_mismatch_byte_zero_based":first,
                  "fresh_prefix_at_difference_hex":left[max(0,first-20):first+60].hex(),
                  "frozen_prefix_at_difference_hex":right[max(0,first-20):first+60].hex(),
                  "fresh_lines":left.count(b"\n"),
                  "frozen_lines":right.count(b"\n")}
        print("S3D_"+label+"_ARCHIVED_RAW_TO_PREPARED=DIFFERENCE_REQUIRES_REVIEW",
              "first_byte=",first,"fresh_bytes=",len(left),
              "frozen_bytes=",len(right),flush=True)
        return mismatch
    print("S3D_"+label+"_ARCHIVED_RAW_TO_PREPARED_BYTE_IDENTITY=PASS",flush=True)
    return {"status":"EXACT_BYTE_PARITY","fresh":produced,"frozen":frozen}


def replay(case: Path, work: Path, source_sha: str) -> dict:
    if not re.fullmatch(r"[a-f0-9]{40}",source_sha):
        raise ValueError("source SHA not pinned")
    if case.name!=CASE_ID or case.is_symlink() or not case.is_dir():
        raise ValueError("wrong archived-case root")
    if work.exists() or work.is_symlink():
        raise ValueError("scratch must not exist before this run")
    if not work.parent.is_dir() or case.resolve().is_relative_to(work.resolve()) or (
        work.resolve().is_relative_to(case.resolve())
    ):
        raise ValueError("unsafe scratch location")
    # An on-disk hash alone is a self-reference: pin EVERY original NOAA,
    # historical prepared output and source manifest to the checked-out Git
    # tree object. A tampered worktree must fail before any replay happens.
    repo_root=Path(__file__).resolve().parents[2]
    if case.resolve()!=repo_root.joinpath("project/cases",CASE_ID).resolve():
        raise ValueError("archived original input must be the pinned repository case")
    original={}
    for name in SOURCES:
        selected=checked(case,name)
        rel=selected.relative_to(repo_root).as_posix()
        expected_blob=subprocess.check_output(
            ["git","-C",str(repo_root),"rev-parse",source_sha+":"+rel],
            text=True).strip()
        present_blob=subprocess.check_output(
            ["git","-C",str(repo_root),"hash-object",str(selected)],
            text=True).strip()
        if expected_blob!=present_blob:
            raise ValueError("archived raw/manifest differs from pinned Git tree: "+name)
        original[name]={"sha256":sha(selected),
                        "bytes":selected.stat().st_size,
                        "git_blob":expected_blob}
    if checked(case,TIME).read_text().strip()!="BEGIN:20220101-000000\nEND:20220106-230000":
        raise ValueError("research calendar changed")
    selection=json.loads(checked(case,P5_SELECTION).read_text())
    if (selection.get("primary_sid")!="58321099999" or
        selection.get("year")!=2022 or len(selection.get("stations",[]))!=1 or
        selection["stations"][0].get("wind_data_source")!="NOAA_ISD_LITE" or
        selection["stations"][0].get("wind_treatment")!="COMPLETE_FILL_AND_CALM_REPLACE"):
        raise ValueError("NOAA primary and wind policy changed")
    import subprocess
    actual_head=subprocess.check_output(["git","rev-parse","HEAD"],
                                         text=True).strip()
    if source_sha!=actual_head:
        raise ValueError("checked-out source does not match pinned HEAD")
    with checked(case,P4_SELECTION).open(newline="") as f:
        rows=list(csv.DictReader(f))
    if len(rows)!=1 or rows[0]["id"]!="CHM00058424" or rows[0]["year"]!="2022":
        raise ValueError("P4 archived station selection changed")
    if checked(case,P4_PSTOP).read_text().strip()!="500.0":
        raise ValueError("P4 PSTOP changed")
    work.mkdir()
    for name in SOURCES:
        # Reference files copied only for audit convenience, NEVER as outputs.
        if name in (P4_REFERENCE,P5_REFERENCE): continue
        copy_source(case,work,name)

    # P4: actual 75 MB NOAA IGRA text -> 2022 cleaned 00/12 profiles
    # -> 2022 gap policy -> FSL (existing production functions).
    from native_cpp.modules.p4_read62.data_prep import parse_igra_to_csv as igra
    from native_cpp.modules.p4_read62.data_prep import read as read62
    row=rows[0]
    csvdir=work/"met/upperair/2022/CHM00058424_igra_every_moment"
    raw=work/P4_RAW
    stats=igra.convert_igra_to_csv(raw,csvdir,"58424",2022,
                                    float(row["elev_m"]),500.0)
    # Eligibility is based on ORIGINAL cleaned 00/12 profiles before any
    # same-/previous-day clone, never on the 730 filled profiles.
    original_slots={p.stem.split("_",1)[1] for p in csvdir.glob("58424_*.csv")
                    if re.fullmatch(r"58424_2022[0-9]{4}[01][02]\\.csv",p.name)}
    original_slots={x for x in original_slots if x.endswith(("00","12"))}
    # Match is deliberately explicit and independent of the FSL output size.
    observed=len(original_slots)
    if observed*5<=730*4:
        raise ValueError("P4 original IGRA observation coverage not strict >80%")
    filled=igra.ensure_year_completeness(
        csvdir,"58424",2022,stats.get("dropped_slots"))
    if filled["unresolved_slots"]>0:
        raise ValueError("P4 still has missing 00/12 after original filling")
    fsl=work/P4_REFERENCE
    fsl.parent.mkdir(parents=True)
    lat,lon=float(row["lat"]),float(row["lon"])
    kwargs=dict(
        csv_dir=csvdir,station_id="58424",
        latitude=f"{abs(lat):.2f}{'N' if lat>=0 else 'S'}",
        longitude=f"{abs(lon):.2f}{'E' if lon>=0 else 'W'}",
        elevation=str(int(round(float(row["elev_m"])))),
        target_year="2022",min_pressure_hpa=500.0)
    # The original frozen FSL predates the OPTIONAL trailing P4EXACT
    # header extension. Replay the historical format for byte identity,
    # then independently demonstrate that the current 6-decimal-station
    # metadata extension changes NO old READ62-readable input bytes.
    read_stats=read62.convert_csv_profiles_to_fsl(
        output_path=fsl,**kwargs)
    p4_byte=byte_gate(fsl,checked(case,P4_REFERENCE),"P4_FSL")
    modern_fsl=work/"met/upperair/2022/igra2fsl/58424-with-P4EXACT.txt"
    read62.convert_csv_profiles_to_fsl(
        output_path=modern_fsl,exact_lat=lat,exact_lon=lon,
        coord_digits=6,**kwargs)
    import re as _re
    encoded=modern_fsl.read_bytes()
    # Only the optional FSL header extension is permitted to differ;
    # explicitly check the number of affected header records.
    extra=(f" P4EXACT_LAT={lat:.6f} P4EXACT_LON={lon:.6f}").encode("ascii")
    if encoded.count(extra)!=730:
        raise ValueError("P4 exact-coordinate extension count not 730")
    normalized=encoded.replace(extra,b"")
    if normalized!=fsl.read_bytes():
        raise ValueError("P4EXACT extension unexpectedly changes fixed-column FSL values")
    print("S3D_P4_OPTIONAL_6DP_STATION_METADATA_PRESERVES_LEGACY_FSL=PASS",flush=True)
    print("S3D_P4_IGRA_ORIGINAL_CLEANED_COUNT=",stats["soundings_written"],flush=True)

    # P5: archived 2022 full-ISD plus full-year ISD-Lite winds ->
    # actual original wind V2 hourly fill/interpolation + GENERIC.
    # Never hand original case paths to the P5 script globals.
    from native_cpp.modules.p5_smerge.data_prep import isd_to_smerge_and_fill as p5base
    from native_cpp.modules.p5_smerge.data_prep import clean_merge_filled_by_research_time as p5clip
    from native_cpp.modules.p5_smerge.data_prep import convert_cleaned_to_smerge_ready as p5ready
    surface=work/"met/surface"
    p5base.BASE_DIR=surface
    p5base.INPUT_DIR=surface/"isd_raw"
    p5base.OUTPUT_DIR=surface/"isd2smerge_and_fill"
    # Guard source stage before any processing.
    from native_cpp.modules.p5_smerge.data_prep.isd_lite_wind import parse_lite_winds
    lite=parse_lite_winds(work/P5_LITE,2022,"58321099999")
    if len(lite)!=8692 or sha(work/P5_LITE)!=selection["stations"][0]["wind_isd_lite"]["sha256"]:
        raise ValueError("P5 archived ISD-Lite source selection incompatible")
    if p5base.main()!=0:
        raise ValueError("P5 raw ISD+Lite conversion failed")
    native_source=surface/"isd2smerge_and_fill/583210-99999-2022_isd_lite_source.json"
    if not native_source.is_file():
        raise ValueError("P5 native source-audit not emitted from actual NOAA")
    wind_source=json.loads(native_source.read_text())
    expected=selection["stations"][0]
    if (wind_source.get("original_full_isd_hour_count")!=expected["full_isd_raw_hours"] or
        wind_source.get("original_lite_hour_count")!=expected["isd_lite_raw_hours"] or
        expected["full_isd_raw_hours"]*10<=8760*9 or
        expected["isd_lite_raw_hours"]*10<=8760*9):
        raise ValueError("P5 raw full+Lite year 2022 eligibility not strictly >90%")
    p5clip.CASE_ROOT=work
    p5clip.INPUT_DIR=p5base.OUTPUT_DIR
    p5clip.OUTPUT_DIR=surface/"isd2smerge_cleaned"
    p5clip.RESEARCH_TIME_FILE=work/TIME
    if p5clip.main()!=0:
        raise ValueError("P5 research-time filtered primary failed")
    p5ready.CASE_ROOT=work
    p5ready.INPUT_DIR=p5clip.OUTPUT_DIR
    p5ready.OUTPUT_DIR=surface/"isd2smerge_ready"
    if p5ready.main()!=0:
        raise ValueError("P5 cleaned-to-GENERIC failed")
    generic=work/P5_REFERENCE
    p5_byte=byte_gate(generic,checked(case,P5_REFERENCE),"P5_GENERIC")
    # Do not trust one manifest to independently certify the raw selections.
    with checked(case,P5_FULL).open(newline="",encoding="utf-8") as f:
        raw_rows=sum(1 for _ in f)-1
    if raw_rows<8692:
        raise ValueError("full ISD unexpectedly below selected raw coverage")
    for name,meta in original.items():
        if sha(checked(case,name))!=meta["sha256"]:
            raise ValueError("immutable original case mutated: "+name)
    report={
        "schema":"CTEAS_S3D_ARCHIVED_NOAA_OFFLINE_REPLAY_V1",
        "case":CASE_ID,"source_sha":source_sha,
        "status":("PASS_SCOPED_RAW_TO_FSL_GENERIC"
                  if p4_byte["status"]=="EXACT_BYTE_PARITY" and
                     p5_byte["status"]=="EXACT_BYTE_PARITY"
                  else "FAIL_RAW_TO_PREPARED_MISMATCH"),
        "no_network_download":True,"no_golden_case_mutation":True,
        "raw_sources":original,
        "p4":{"stats":stats,"original_valid_slots":observed,
              "year_expected_slots":730,
              "raw_coverage_strict_above_80_percent":True,
              "filled":filled,"fsl_stats":read_stats,
              "produced_fsl":p4_byte,
              "new_optional_p4exact_extension_profiles":730,
              "new_optional_p4exact_extension_sha256":sha(modern_fsl),
              "exact_coord_is_station_metadata_not_utm_grid_origin":True},
        "p5":{"original_lite_hours":len(lite),
              "raw_full_and_lite_coverage_strict_above_90_percent":True,
              "verified_native_full_isd_hours":wind_source["original_full_isd_hour_count"],
              "full_isd_source_rows":raw_rows,
              "wind_source":"NOAA_ISD_LITE",
              "produced_generic":p5_byte},
        "research_period":"2022-01-01T00:00_to_2022-01-06T23:00",
        "utm_xrefkm":"510.885","utm_yrefkm":"3531.269",
        "recomputed_p4_to_p7_in_this_job":False,
        "general_site_validated":False
    }
    audit=work/"audit"
    audit.mkdir()
    (audit/"s3d-archived-noaa-replay.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2,default=str)+"\n")
    if report["status"]!="PASS_SCOPED_RAW_TO_FSL_GENERIC":
        print("S3D_RAW_REPLAY_STATUS=BLOCKED_UPSTREAM_BYTE_MISMATCH",flush=True)
        raise ValueError("at least one true NOAA raw-to-prepared output mismatches frozen; audit emitted")
    print("S3D_P4_P5_ARCHIVED_RAW_PREPARED_BOTH_BYTE_IDENTITY=PASS")
    return report


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--case",type=Path,required=True)
    p.add_argument("--work",type=Path,required=True)
    p.add_argument("--source-head",required=True)
    a=p.parse_args()
    replay(a.case.resolve(),a.work.absolute(),a.source_head)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
