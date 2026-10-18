#!/usr/bin/env python3
"""Scoped P4 case runner: original IGRA Python -> C++20 UP.DAT -> copied merger.

The original Fortran READ62 is never executed by this wrapper. To preserve
the source authority, the legacy merge_final_upperair.py is copied unchanged.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from engine.core.paths import current_project_path
from native_cpp.modules.p4_read62.data_prep.p4_case_d1 import admit_staged_case, sha256_file

REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE = "native_cpp.modules.p4_read62.data_prep"


def research_times(case_root: Path | None = None) -> tuple[datetime, datetime]:
    from native_cpp.modules.p4_read62.data_prep.merge_final_upperair import parse_research_time
    return parse_research_time(case_root / "grid" / "research_time" if case_root else
                               current_project_path("grid", "research_time"))


def station_jobs(year: int, pstop_hpa: float, cpp_binary: Path,
                 begin: datetime, end: datetime,
                 upperair_root: Path | None = None) -> list[dict]:
    year_dir=(upperair_root / str(year) if upperair_root else
              current_project_path("met", "upperair", str(year)))
    station_file=year_dir/"upperair_station_used_list.txt"
    if not station_file.is_file():
        raise ValueError(f"station metadata missing: {station_file}")
    rows=list(csv.DictReader(station_file.open(encoding="utf-8", newline="")))
    if not rows: raise ValueError(f"no eligible annual stations in {year}")
    lo=max(begin,datetime(year,1,1,0,0))
    hi=min(end,datetime(year,12,31,23,0))
    if hi<lo: raise ValueError(f"year outside research interval: {year}")
    if (lo.minute,lo.second,hi.minute,hi.second)!=(0,0,0,0):
        raise ValueError("P4 C++ timestamp interface currently requires hourly UTC boundaries")
    jobs=[]
    seen=set()
    for row in rows:
        numeric=row["id"][-5:]
        if not re.fullmatch(r"\d{5}",numeric):
            raise ValueError("5-digit WMO station ID required")
        if numeric in seen: raise ValueError(f"5-digit station ID collision: {numeric}")
        seen.add(numeric)
        if float(row["raw_coverage"])<=0.80:
            raise ValueError(f"P4 coverage gate violated in retained station {row['id']}")
        fsl=year_dir/"igra2fsl"/f"{numeric}.txt"
        if not fsl.is_file() or fsl.stat().st_size==0:
            raise FileNotFoundError(f"FSL missing: {fsl}")
        output=year_dir/"fsl_data"/f"up_{numeric}_{year}.dat"
        command=[
            str(cpp_binary.resolve()),str(fsl.resolve()),str(output.resolve()),
            lo.strftime("%Y-%m-%dT%H:00Z"),hi.strftime("%Y-%m-%dT%H:00Z"),
            str(pstop_hpa),numeric,
        ]
        jobs.append({"station_id":numeric,"source_station_id":row["id"],
                     "effective_lat":row["lat"],"effective_lon":row["lon"],
                     "source_lat":row.get("source_lat"),"source_lon":row.get("source_lon"),
                     "site_type":row["site_type"],"coverage":row["raw_coverage"],
                     "raw_igra":row["raw_txt"],
                      "input_fsl":str(fsl),"output_updat":str(output),"command":command})
    return jobs


def main() -> int:
    ap=argparse.ArgumentParser(description="P4 end-to-end C++ UP.DAT case execution")
    ap.add_argument("--cpp-bin",type=Path,required=True)
    ap.add_argument("--year",type=int,help="Single year; default entire research interval")
    ap.add_argument("--pstop",type=float,default=500.)
    ap.add_argument("--skip-inputs",action="store_true",help="Use already prepared IGRA/FSL")
    ap.add_argument("--merge-final",action="store_true",help="Execute scoped copied original UP.DAT merger")
    ap.add_argument("--execute",action="store_true",help="Default dry run (no downloads/writes)")
    ap.add_argument("--case-root",type=Path,help="Already-staged independent case from #42 B-0")
    ap.add_argument("--upperair-root",type=Path,help="case_root/met/upperair, initially nonexistent")
    ap.add_argument("--offline-archive-root",type=Path,help="Read-only original IGRA archive")
    args=ap.parse_args()
    if not 0<args.pstop<=1500:ap.error("invalid PSTOP")
    isolated = any((args.case_root,args.upperair_root,args.offline_archive_root))
    if isolated and not all((args.case_root,args.upperair_root,args.offline_archive_root)):
        ap.error("isolated P4 requires --case-root, --upperair-root and --offline-archive-root")
    if isolated and (args.pstop != 500.0 or args.skip_inputs or args.merge_final):
        ap.error("P4 D1-A supports only PSTOP=500, fresh QA, annual raw UP; D2 final publication is blocked")
    admission = None
    if isolated:
        try:
            admission = admit_staged_case(args.case_root,args.upperair_root,
                                          args.offline_archive_root,REPO_ROOT)
        except (ValueError,OSError,TypeError,KeyError) as exc:
            ap.error(f"P4_B0_ADMISSION_BLOCKED: {exc}")
    begin,end=research_times(args.case_root if isolated else None)
    years=[args.year] if args.year is not None else list(range(begin.year,end.year+1))
    if args.merge_final and set(years)!=set(range(begin.year,end.year+1)):
        ap.error("partial year range cannot be published as final")
    if args.execute and not args.cpp_bin.is_file():
        ap.error(f"C++ binary missing: {args.cpp_bin}")
    records=[]
    for year in years:
        if not args.skip_inputs:
            cmd=[sys.executable,"-m",MODULE+".prepare_inputs",
                 "--year",str(year),"--pstop",str(args.pstop)]
            if isolated:
                cmd += ["--case-root",str(args.case_root),
                        "--upperair-root",str(args.upperair_root),
                        "--offline-archive-root",str(args.offline_archive_root)]
            if args.execute:cmd.append("--execute")
            print("P4_INPUTS",cmd,flush=True)
            if args.execute:subprocess.run(cmd,cwd=REPO_ROOT,check=True)
        if args.execute or args.skip_inputs:
            jobs=station_jobs(year,args.pstop,args.cpp_bin,begin,end,
                              args.upperair_root if isolated else None)
            for job in jobs:
                records.append(job)
                print("P4_CPP_STATION",job["station_id"],job["site_type"],flush=True)
                if args.execute:
                    Path(job["output_updat"]).parent.mkdir(parents=True,exist_ok=True)
                    subprocess.run(job["command"],cwd=REPO_ROOT,check=True)
    if args.execute and isolated:
        # D1-A stops at annual raw UP: no unsafe cross-year union or cloned AA/BB.
        archive=args.offline_archive_root.resolve(strict=True)
        for job in records:
            source=Path(job["raw_igra"]).resolve(strict=True)
            if not (source == archive or archive in source.parents):
                raise ValueError("selected NOAA source escaped explicit offline archive")
            job["raw_igra_sha256"]=sha256_file(source)
            job["fsl_sha256"]=sha256_file(Path(job["input_fsl"]))
            job["annual_raw_up_sha256"]=sha256_file(Path(job["output_updat"]))
        for relative, expected in admission.items():
            if relative in ("case_root","upperair_root"):
                continue
            if sha256_file(args.case_root / relative) != expected:
                raise ValueError(f"immutable B-0 case input changed during P4 execution: {relative}")
        out=args.upperair_root/"p4_d1a_annual_manifest.json"
        manifest={"status":"PRODUCED_UNVERIFIED", "producer_issue":55,
                  "gate":"P4_D1A_ANNUAL_RAW_ONLY",
                  "scientific_acceptance":"NOT_EVALUATED",
                  "final_up_g19":"BLOCKED_D2_D3",
                  "source_path":"NOAA_IGRA_EXTRACTED_OFFLINE",
                  "pstop_hpa":500.0,"jdat":2,"ifmt":1,
                  "admission":admission,"years":years,
                  "cpp_executable":str(args.cpp_bin.resolve()),
                  "cpp_sha256":sha256_file(args.cpp_bin), "stations":records}
        out.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print("P4_D1A_ANNUAL_RAW_PRODUCED_UNVERIFIED",out,flush=True)
    if args.execute and args.merge_final:
        # This is the exact, separately copied legacy final merge algorithm.
        subprocess.run([sys.executable,"-m",MODULE+".merge_final_upperair"],
                       cwd=REPO_ROOT,check=True)
        final=current_project_path("met","upperair","final")
        for job in records:
            if not (final/f"up_{job['station_id']}.dat").is_file():
                raise FileNotFoundError("missing merged final UP.DAT "+job["station_id"])
        manifest=final/"p4_cpp_execution_manifest.json"
        manifest.write_text(json.dumps({"years":years,"stations":records,
                                        "cpp_executable":str(args.cpp_bin),"merged":True},
                                       ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print("P4_CALMET_UPDAT_FINAL_PASS",manifest,flush=True)
    if not args.execute:
        print("P4_DRY_RUN no writes or external execution",flush=True)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
