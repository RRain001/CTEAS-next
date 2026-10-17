#!/usr/bin/env python3
"""Drive REAL C++ P6D(hour n) -> P6E(hour n) in ONE causal 2022 hour loop.

This is the first no-original-wind / no-full-period-COMP-feedback integrated
numerical producer, not yet scientific parity. The original frozen met.dat is
used ONLY for the selected-case controls/grid/station header; the 45 hourly
METEOROLOGICAL field values come from native P6D and native P6E kernels.
The P6D PREPDI FRADJ path may still omit CGAMMA, and original U/V/W may fail.
The source-first G3/G4 scientific gates remain NOT_PASS until checked.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys

SHA="b1823cda92280888d70b00961ab39486036a3086e18637fff21efb4f4b237d30"
STATE=("zi","ziconv","dptt")
CELLS=2500
BYTES=CELLS*4

def digest(p:pathlib.Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for blob in iter(lambda:f.read(1048576),b""):h.update(blob)
    return h.hexdigest()

def run(command:list[object],log:pathlib.Path)->None:
    result=subprocess.run([str(x) for x in command],capture_output=True,text=True)
    log.write_text(f"exit={result.returncode}\n"+result.stdout+"\n"+result.stderr)
    if result.returncode!=0:
        raise RuntimeError(f"failed {command[0]}: {log}; {result.stderr[-1200:]}")

def main():
    cli=argparse.ArgumentParser()
    cli.add_argument("--case",required=True,type=pathlib.Path)
    cli.add_argument("--p6d",required=True,type=pathlib.Path)
    cli.add_argument("--p6e",required=True,type=pathlib.Path)
    cli.add_argument("--bridge",required=True,type=pathlib.Path)
    cli.add_argument("--cgamma",required=True,type=pathlib.Path)
    cli.add_argument("--work",required=True,type=pathlib.Path)
    cli.add_argument("--hours",type=int,default=6)
    cli.add_argument("--emit-source-stage-trace",action="store_true",
        help="flatten per-hour native FRADJ, SLOPE, INTER2 traces for pinned original forensic comparison")
    a=cli.parse_args()
    if not 1<=a.hours<=143:raise ValueError("1..143 consecutive Hefei hours required")
    case=a.case.resolve();work=a.work.resolve();work.mkdir(parents=True,exist_ok=True)
    met=case/"run/met/met.dat"
    surf=case/"met/surface/final/surf.dat"
    upper=case/"met/upperair/final/up_58424.dat"
    geo=case/"geo/makegeo/geo.dat"
    for p in (met,surf,upper,geo):
        if not p.is_file():raise RuntimeError(f"missing frozen case input {p}")
    if digest(met)!=SHA:raise RuntimeError("original CALMET grid/control reference changed")
    hourly=work/"observations.csv"
    run([a.bridge,surf,upper,58424,hourly],work/"bridge.log")
    history=work/"history"/"comp"
    history.parent.mkdir(exist_ok=True)
    manifest=work/"native_hourly_files.txt"
    files=[]
    station_flux_lines=[]
    stage_root=work/"native_source_stage_143h"
    stage_rows=[]
    if a.emit_source_stage_trace:
        if a.hours!=143:raise ValueError("original source stage trace requires full 143-hour frozen interval")
        stage_root.mkdir(exist_ok=True)
    for hour in range(a.hours):
        folder=work/f"hour_{hour:03d}"
        folder.mkdir(exist_ok=True)
        d=folder/"diagno"
        d.mkdir(exist_ok=True)
        gamma=folder/"gamma"
        gamma.mkdir(exist_ok=True)
        # PREPDI CGAMMA reads only n-1 committed P6E state, not future P6E
        # or the original CALMET source-state trace.
        run([a.cgamma,"--up",upper,"--p6e-state-prefix",history,
             "--out",gamma,"--station-id",58424,"--zupt",200,
             "--upper-i",25,"--upper-j",26,
             "--causal-hours",hour+1],folder/"cgamma.log")
        if len(list(gamma.glob("gamma_*.f32")))!=1:
            raise RuntimeError("native causal CGAMMA did not emit exactly one current-hour plane")
        command=[a.p6d,"--case",case,"--first-hour",hour,
                 "--hours",1,"--out",d,"--gamma",gamma]
        if hour:
            command.extend(["--comp-state-prefix",history])
        else:
            # Original CALMET SETUP initializes COMMON thermal state to zero;
            # DIAGNO still executes real STHEOR/MIXHTST/SIMILT at hour 1.
            command.append("--native-setup-hour0")
        run(command,folder/"p6d.log")
        flux_lines=(d/"station_elustr2.csv").read_text().splitlines()
        if len(flux_lines)!=2:
            raise RuntimeError(f"hour={hour}: single-hour native P6D station flux malformed")
        if not station_flux_lines:station_flux_lines.append(flux_lines[0])
        elif station_flux_lines[0]!=flux_lines[0]:
            raise RuntimeError("native station flux column contract changed")
        station_flux_lines.append(flux_lines[1])
        native=folder/"comp"
        opts=[
            a.p6e,"emit-realcase",
            "--reference",met,"--observations",hourly,
            "--geo-file",geo,
            "--native-hour-comp",1,
            "--native-p6d-dir",d,
            "--station-flux-csv",d/"station_elustr2.csv",
            "--first-hour",hour,"--hours",1,
            "--state-prefix",native,
            "--out",folder/"met_native_1h.dat",
            "--report",folder/"comp_report.json",
        ]
        if hour:
            opts.extend(["--previous-comp-prefix",
                         work/f"hour_{hour-1:03d}"/"comp"])
        run(opts,folder/"p6e.log")
        meta=json.loads(pathlib.Path(str(native)+".state.json").read_text())
        if meta.get("first_hour_zero_based")!=hour or meta.get("shape")!=[1,50,50]:
            raise RuntimeError(f"hour {hour}: native COMP provenance does not match time")
        for name in STATE:
            field=pathlib.Path(f"{native}.{name}.f32")
            if not field.is_file() or field.stat().st_size!=BYTES:
                raise RuntimeError(f"hour {hour}: missing native thermal state {name}")
            with field.open("rb") as src, pathlib.Path(f"{history}.{name}.f32").open("ab") as dst:
                shutil.copyfileobj(src,dst)
            if pathlib.Path(f"{history}.{name}.f32").stat().st_size!=(hour+1)*BYTES:
                raise RuntimeError("COMP state append ordering failed")
        shutil.copyfile(str(native)+".state.json",str(history)+".state.json")
        f=folder/"met_native_1h.dat"
        if not f.is_file():raise RuntimeError("missing native P6D/P6E hour")
        if a.emit_source_stage_trace:
            label=(d/"produced_hours.txt").read_text().strip()
            for prefix in ("fradj_corrected_u","fradj_corrected_v",
                           "wind1_u","wind1_v",
                           "slope_corrected_u","slope_corrected_v",
                           "inter2_u","inter2_v"):
                original_plane=d/f"{prefix}_{label}.f32"
                if not original_plane.is_file() or original_plane.stat().st_size!=9*CELLS*4:
                    raise RuntimeError(f"missing original stage input in native C++ output: {original_plane}")
                # Keep the source stage physically unchanged (read-only forensic copy).
                shutil.copyfile(original_plane,stage_root/original_plane.name)
            neutral_profile=d/f"wind1_neutral_profile_{label}.f32"
            if not neutral_profile.is_file() or neutral_profile.stat().st_size!=18*4:
                raise RuntimeError(f"missing WIND1 neutral REAL4 forensic profile: {neutral_profile}")
            shutil.copyfile(neutral_profile,stage_root/neutral_profile.name)
            stage_lines=(d/"station_inter2_layer1.csv").read_text().splitlines()
            if len(stage_lines)!=2:raise RuntimeError("single-hour INTER2 station trace malformed")
            if not stage_rows:stage_rows.append(stage_lines[0])
            elif stage_rows[0]!=stage_lines[0]:raise RuntimeError("station stage header drift")
            stage_rows.append(stage_lines[1])
        files.append(f)
        # One hour at a time, NEVER run full-period P6E before P6D.
    manifest.write_text("\n".join(map(str,files))+"\n")
    joined_station=work/"native_station_flux.csv"
    joined_station.write_text("\n".join(station_flux_lines)+"\n")
    if a.emit_source_stage_trace:
        (stage_root/"station_inter2_layer1.csv").write_text("\n".join(stage_rows)+"\n")
    merged=work/"native_causal_calmet.dat"
    run([a.p6e,"merge-native-hours","--manifest",manifest,"--out",merged],
        work/"writer.log")
    if not merged.is_file() or merged.stat().st_size<1000000:
        raise RuntimeError("native 45-field CALMET.DAT format candidate absent")
    report={
        "status":"PASS_NATIVE_CAUSAL_DIAGNO_COMP_EXECUTION",
        "hours_completed":a.hours,
        "native_p6d_wind":True,
        "native_prepdi_cgamma_previous_comp_state":True,
        "first_hour_stheor_mixhtst_original_setup_zero":True,
        "native_p6e_comp":True,
        "hourly_execution":"P6D[n] -> P6E[n] -> commit ZI/ZICONV/DPTT -> P6D[n+1]",
        "frozen_original_wind_used":False,
        "frozen_original_met_dat_role":"CASE_CONTROL_HEADER_ONLY",
        "unmodified_original_wind_27_field_parity":"NOT_PASS_UNCHECKED",
        "full_45_field_reference_parity":"NOT_PASS_UNCHECKED",
        "complete_45_field_writer":"PASS_FORMAT_ONLY_NOT_REFERENCE_PARITY",
        "native_calmet_dat":str(merged),
        "native_calmet_dat_sha256":digest(merged),
        "native_station_flux_csv":str(joined_station),
        "native_source_stage_trace":str(stage_root) if a.emit_source_stage_trace else None,
        "first_hour":str(files[0]),
        "last_hour":str(files[-1]),
        "hour_files_manifest":str(manifest),
    }
    (work/"native_hourly_manifest.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    return 0

if __name__=="__main__":
    try:sys.exit(main())
    except Exception as error:
        print(f"FAIL_NATIVE_CAUSAL_P6D_P6E: {error}",file=sys.stderr)
        sys.exit(3)
