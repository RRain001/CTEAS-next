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

REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE = "native_cpp.modules.p4_read62.data_prep"


def research_times() -> tuple[datetime, datetime]:
    from native_cpp.modules.p4_read62.data_prep.merge_final_upperair import parse_research_time
    return parse_research_time(current_project_path("grid", "research_time"))


def station_jobs(year: int, pstop_hpa: float, cpp_binary: Path,
                 begin: datetime, end: datetime) -> list[dict]:
    year_dir=current_project_path("met", "upperair", str(year))
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
    args=ap.parse_args()
    if not 0<args.pstop<=1500:ap.error("invalid PSTOP")
    begin,end=research_times()
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
            if args.execute:cmd.append("--execute")
            print("P4_INPUTS",cmd,flush=True)
            if args.execute:subprocess.run(cmd,cwd=REPO_ROOT,check=True)
        if args.execute or args.skip_inputs:
            jobs=station_jobs(year,args.pstop,args.cpp_bin,begin,end)
            for job in jobs:
                records.append(job)
                print("P4_CPP_STATION",job["station_id"],job["site_type"],flush=True)
                if args.execute:
                    Path(job["output_updat"]).parent.mkdir(parents=True,exist_ok=True)
                    subprocess.run(job["command"],cwd=REPO_ROOT,check=True)
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
