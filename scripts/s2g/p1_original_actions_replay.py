"""#54: independent read-only TERREL 7.0.0 Level 141010 original replay.

Run ONLY after a genuine #54 original/native source producer ran in a
manual GitHub Actions job. Original sources belong to separately checked-out,
exact-SHA RRain001/CTEAS: NEVER commit vendor files into CTEAS-next or
upload original binaries, raw GeoTIFF, control deck, logs or source.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from native_cpp.reference.compare_p1_general import compare, ComparisonError, sha

ORIGINAL_REV="dfad99a78ed84d655e21411c9d25eb0d2583bf13"
VENDOR_REL=Path("engine/vendor/src/TERREL_v7.0.0_L141010")
MAX_OUTPUT=25_000_000

class OriginalReplayError(ValueError):
    pass


def hash_file(path:Path)->str:
    if not path.is_file() or path.is_symlink() or path.stat().st_size<=0:
        raise OriginalReplayError("original provenance asset missing or symlinked")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _invoke(cmd:list[str],*,cwd:Path,seconds:int,logprefix:Path)->dict:
    result=subprocess.run(cmd,cwd=cwd,text=True,capture_output=True,timeout=seconds,check=False)
    if len(result.stdout)>MAX_OUTPUT or len(result.stderr)>MAX_OUTPUT:
        raise OriginalReplayError("vendor output exceeds audited limit")
    out=logprefix.with_suffix(".stdout.txt")
    err=logprefix.with_suffix(".stderr.txt")
    out.write_text(result.stdout)
    err.write_text(result.stderr)
    return {"returncode":result.returncode,
            "stdout_sha256":hash_file(out) if out.stat().st_size else None,
            "stderr_sha256":hash_file(err) if err.stat().st_size else None}


def validate_original_checkout(root:Path)->Path:
    if root.is_symlink() or not root.is_dir():
        raise OriginalReplayError("CTEAS original checkout absent/symlinked")
    vendor=root/VENDOR_REL
    required=("terrel.for","terrel.inp","CONTROL.TRL","CALUTILS.FOR",
              "COORDLIB.FOR","TIFFINFO.FOR")
    # CTEAS stores tiffinfo.for (lowercase), unlike upper-case includes.
    required=tuple("tiffinfo.for" if x=="TIFFINFO.FOR" else x for x in required)
    for name in required:
        p=vendor/name
        if p.is_symlink() or not p.is_file() or p.stat().st_size<256:
            raise OriginalReplayError("unavailable original TERREL source dependency: "+name)
    version=(vendor/"terrel.for").read_text(encoding="latin-1")[:1100]
    if "TERREL" not in version or "7.0.0" not in version or "141010" not in version:
        raise OriginalReplayError("unexpected original TERREL version")
    return vendor


def compile_original(vendor:Path,workspace:Path)->tuple[Path,dict]:
    build=workspace/"original_build"
    build.mkdir(exist_ok=False)
    aliases=build/"aliases"
    aliases.mkdir()
    # Uppercase/lowercase INCLUDE compatibility on a case-sensitive runner.
    # These are symlinks in scratch only; original CTEAS repo is read-only.
    for p in vendor.iterdir():
        if p.is_file():
            alias=aliases/p.name.lower()
            if not alias.exists():
                alias.symlink_to(p)
    binary=build/"terrel-original.x"
    args=["gfortran","-std=legacy","-fno-automatic","-fno-align-commons",
          "-fallow-argument-mismatch","-O0","-ffixed-line-length-none",
          "-I"+str(aliases),"-I"+str(vendor),str(vendor/"terrel.for"),
          "-o",str(binary)]
    result=_invoke(args,cwd=build,seconds=180,logprefix=build/"compile")
    if result["returncode"]!=0 or not binary.is_file():
        raise OriginalReplayError("original untouched TERREL Fortran compilation failed")
    result["original_executable_sha256"]=sha(binary)
    result["original_terrel_source_sha256"]=sha(vendor/"terrel.for")
    return binary,result


def prepare_control(vendor:Path, checkout:Path, workspace:Path,
                    selected:Path, grid:dict)->Path:
    original=workspace/"original"
    original.mkdir(exist_ok=False)
    control=original/"terrel.inp"
    shutil.copyfile(vendor/"terrel.inp",control)
    # Invoke THE ORIGINAL CTEAS source/grid control updater from its pinned,
    # separate repository. No control generator fork or physics options added.
    script=StringCode.UPDATE_CONTROL
    payload={
      "control":str(control),
      "selected":str(selected),
      "grid":grid,
    }
    args=[sys.executable,"-c",script,json.dumps(payload)]
    proc=subprocess.run(args,cwd=checkout,text=True,capture_output=True,
                        env={**os.environ,"PYTHONPATH":str(checkout)},
                        timeout=25,check=False)
    if proc.returncode:
        raise OriginalReplayError("CTEAS original TERREL input-control generator rejected grid/source")
    if not control.is_file():
        raise OriginalReplayError("original TERREL control was not generated")
    return control


class StringCode:
    UPDATE_CONTROL = """
import json,sys
from pathlib import Path
from engine.preprocess.terrel.auto_select_srtm_to_terrel import GridDef,update_terrel
data=json.loads(sys.argv[1])
g=data['grid']
v=GridDef(imap='UTM',iutmzn=g['zone'],lsohem=g['hemisphere'],
          datum='WGS-84',xrefkm=float(g['xrefkm']),
          yrefkm=float(g['yrefkm']),nx=g['nx'],ny=g['ny'],
          dgridkm=g['dgridkm'])
update_terrel(Path(data['control']),v,[Path(data['selected'])],False)
"""


def audit(*,case_root:Path,checkout:Path,route:str,report:Path)->dict:
    if case_root.name!="issue54_p1_seam_2022":
        raise OriginalReplayError("independent staged case name mismatch")
    if report.exists() or report.is_symlink():
        raise OriginalReplayError("original parity report cannot be overwritten")
    original_vendor=validate_original_checkout(checkout)
    native_root=case_root/"geo/terrel/p1_native"
    native_m=native_root/"p1_native_manifest.json"
    native_csv=native_root/"terrain.csv"
    source_m=case_root/"geo/terrel/p1_source/p1_source_manifest.json"
    for p in (native_m,native_csv,source_m):
        hash_file(p)
    native=json.loads(native_m.read_text())
    source=json.loads(source_m.read_text())
    if (native["route"]!=route or native["case_name"]!=case_root.name or
            native["grid"]["zone"]!=50 or native["grid"]["hemisphere"]!="N" or
            native["grid"]["nx"]!=50 or native["grid"]["ny"]!=50):
        raise OriginalReplayError("original replay only supports reviewed real #54 seam case")
    selected=Path(source["selected_tif"])
    if sha(selected)!=source["selected_tif_sha256"] or sha(selected)!=native["selected_tif_sha256"]:
        raise OriginalReplayError("selected original/native actual TIFF bytes inconsistent")
    grid=case_root/"grid/grid.cmn"
    if sha(grid)!=native["grid_sha256"]:
        raise OriginalReplayError("shared original/native authoritative grid changed")
    workspace=case_root/"geo/terrel/original_independent"
    workspace.mkdir(exist_ok=False)
    binary,build=compile_original(original_vendor,workspace)
    ctrl=prepare_control(original_vendor,checkout,workspace,selected,native["grid"])
    original_dir=ctrl.parent
    run=_invoke([str(binary),ctrl.name],cwd=original_dir,
                seconds=300,logprefix=workspace/"run")
    dat=original_dir/"terrel.dat"
    sav=original_dir/"terrel.sav"
    if run["returncode"]!=0 or not dat.is_file() or not sav.is_file():
        return {
          "status":"BLOCKED_ORIGINAL_TERREL_EXECUTION",
          "route":route,
          "original_fortran_build":"PASS",
          "original_returncode":run["returncode"],
          "vendor_git_sha":ORIGINAL_REV,
          "original_source_sha256":sha(original_vendor/"terrel.for"),
          "original_control_sha256":sha(ctrl),
          "selected_tif_sha256":sha(selected),
          "original_binary_sha256":sha(binary),
          "original_run_stdout_sha256":run["stdout_sha256"],
          "original_run_stderr_sha256":run["stderr_sha256"],
          "native_source_produced":True,
          "science_acceptance":"NOT_ACCEPTED"
        }
    attest={
      "route":route,"grid_sha256":native["grid_sha256"],
      "selected_tif_sha256":sha(selected),
      "original_terrel_dat_sha256":sha(dat),
      "original_terrel_sav_sha256":sha(sav),
      "original_control_sha256":sha(ctrl),
      "original_executable_sha256":sha(binary)
    }
    attpath=workspace/"original_attestation.json"
    attpath.write_text(json.dumps(attest,indent=2)+"\n")
    output=workspace/"original_native_comparison.json"
    try:
        compared=compare(native_manifest=native_m,original_attestation=attpath,
                         native_terrain=native_csv,original_dat_path=dat,
                         original_sav_path=sav,original_control=ctrl,
                         original_executable=binary,selected_tif=selected,report=output)
    except (ComparisonError,ValueError,OSError) as exc:
        return {
          "status":"BLOCKED_ORIGINAL_NATIVE_COMPARATOR_SCHEMA",
          "route":route,"reason_type":type(exc).__name__,
          "vendor_git_sha":ORIGINAL_REV,
          "original_source_sha256":sha(original_vendor/"terrel.for"),
          "original_control_sha256":sha(ctrl),
          "selected_tif_sha256":sha(selected),
          "original_terrel_dat_sha256":sha(dat),
          "original_terrel_sav_sha256":sha(sav),
          "original_binary_sha256":sha(binary),
          "original_run_stdout_sha256":run["stdout_sha256"],
          "original_run_stderr_sha256":run["stderr_sha256"],
          "science_acceptance":"NOT_ACCEPTED"
        }
    # THIS is a numeric comparison; independent review of original
    # execution and physical input source remains a distinct D4 audit.
    return {
      "status":compared["numeric_parity"],
      "route":route,
      "vendor_git_sha":ORIGINAL_REV,
      "original_source_sha256":sha(original_vendor/"terrel.for"),
      "original_control_sha256":sha(ctrl),
      "selected_tif_sha256":sha(selected),
      "original_terrel_dat_sha256":sha(dat),
      "original_terrel_sav_sha256":sha(sav),
      "original_binary_sha256":sha(binary),
      "original_run_stdout_sha256":run["stdout_sha256"],
      "original_run_stderr_sha256":run["stderr_sha256"],
      "matched_grid_rows":compared["cells"],
      "original_hits_total":compared["original_hits_total"],
      "native_hits_total":compared["native_hits_total"],
      "hit_count_mismatches":compared["hit_count_mismatches"],
      "dat_bad_cells":compared["dat_bad_cells"],
      "raw_mean_bad_cells":compared["raw_mean_bad_cells"],
      "max_dat_error_m":compared["max_dat_error_m"],
      "max_raw_mean_error_m":compared["max_raw_mean_error_m"],
      "parity_comparison_report_sha256":sha(output),
      "science_acceptance":"NOT_ACCEPTED_INDEPENDENT_ORIGINAL_RUN_AUDIT_REQUIRED"
    }


def main(argv=None)->int:
    p=argparse.ArgumentParser()
    p.add_argument("--case-root",required=True,type=Path)
    p.add_argument("--cteas-checkout",required=True,type=Path)
    p.add_argument("--route",required=True,choices=("P1_A_90M_LOCAL","P1_B_30M_DOWNLOAD"))
    p.add_argument("--report",required=True,type=Path)
    args=p.parse_args(argv)
    try:
        data=audit(case_root=args.case_root,checkout=args.cteas_checkout,
                   route=args.route,report=args.report)
    except (OriginalReplayError,OSError,ValueError,TimeoutError,subprocess.SubprocessError) as exc:
        # All diagnostics are immutable fixed enums from this repository.
        # No raw Fortran logs, provider response, credentials, full local
        # absolute paths or exception tracebacks are written to artifacts.
        allowed_errors={
            "missing/empty/symlinked evidence file":"FILE_EVIDENCE_MISSING_EMPTY_OR_SYMLINKED",
            "original attestation does not match actual bytes":"PROVENANCE_HASH_MISMATCH",
            "invalid evidence JSON":"EVIDENCE_JSON_REJECTED",
            "unsupported SAV record schema/shape":"UNSUPPORTED_ORIGINAL_SAV_SCHEMA",
            "TERREL.DAT version/header mismatch":"UNSUPPORTED_ORIGINAL_DAT_SCHEMA",
            "original TERREL control absent/duplicated":"CONTROL_REJECTED",
        }
        message=str(exc) if type(exc).__name__=="ComparisonError" else ""
        reason_code=allowed_errors.get(message,"OTHER_ORIGINAL_REPLAY_BLOCKER")
        # Bounded Python function/line provenance narrows technical failure,
        # while never exporting file contents, body text or execution inputs.
        tb=exc.__traceback__
        last=""
        while tb is not None:
            last=tb.tb_frame.f_code.co_name
            tb=tb.tb_next
        data={"status":"BLOCKED_ORIGINAL_TERREL_INPUT_OR_COMPILATION",
              "reason_type":type(exc).__name__,
              "reason_code":reason_code,
              "failed_function":last if last in {
                  "audit","sha","compile_original","prepare_control",
                  "validate_original_checkout","compare","fortran_dat",
                  "fortran_sav","validate_original_terrel_control",
                  "native_csv","hash_file","_invoke","main"} else "OTHER",
              "route":args.route,"vendor_git_sha":ORIGINAL_REV,
              "science_acceptance":"NOT_ACCEPTED"}
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"status":data["status"],"route":args.route,
                      "science_acceptance":data["science_acceptance"]}))
    return 0 if data["status"]=="NUMERIC_PASS_PROVISIONAL" else 2

if __name__=="__main__":
    raise SystemExit(main())
