#!/usr/bin/env python3
"""Reproducibly run untouched original MAKEGEO 3.2 on original TERREL/CTGPROC outputs.

All original files are read-only. Controls, compilers and outputs remain isolated.
"""
from __future__ import annotations
import argparse,hashlib,json,re,shutil,subprocess,sys
from pathlib import Path

def sha(f):
    return hashlib.sha256(f.read_bytes()).hexdigest()

def run(cmd,cwd,log,timeout=150):
    p=subprocess.run(cmd,cwd=cwd,timeout=timeout,capture_output=True,text=True)
    log.with_suffix(".stdout.txt").write_text(p.stdout)
    log.with_suffix(".stderr.txt").write_text(p.stderr)
    if p.returncode:
        raise RuntimeError(f"command failed rc={p.returncode}: {cmd} (see {log})")
    return p

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",required=True,type=Path)
    args=ap.parse_args()
    root=Path(__file__).resolve().parents[2]
    output=args.output.resolve()
    # This script requires the original P1/P2 capture in output; separate
    # from the C++ reconstruction under validation.
    p1,p2=output/"p1",output/"p2"
    if not (p1/"terrel.dat").is_file() or not (p2/"lu.dat").is_file():
        raise RuntimeError("capture_p1_p2 must complete first")
    original=root/"engine/vendor/src/MAKEGEO_V3.2_L110401"
    work=output/"p3"
    work.mkdir(exist_ok=False)
    shutil.copy2(original/"makegeo.inp",work/"makegeo.inp")
    sys.path.insert(0,str(root))
    from engine.preprocess.makegeo.auto_config_makegeo import GridDef,update_makegeo
    manifest=json.loads((output/"manifest.json").read_text())
    g=manifest["grid"]
    grid=GridDef(imap="UTM",iutmzn=50,lsohem="N",datum="WGS-84",
        xrefkm=g["x0_km"],yrefkm=g["y0_km"],nx=50,ny=50,dgridkm=0.1)
    update_makegeo(work/"makegeo.inp",grid,p2/"lu.dat",p1/"terrel.dat",False)
    ctrl=(work/"makegeo.inp").read_text()
    expected={"LTERR":"T","LLU2":"F","LSNOW":"F","NSPLIT":"0",
              "NOUTCAT":"14","NINCAT":"38","NUMWAT":"5"}
    for key,val in expected.items():
        m=re.search(r"!\s*"+key+r"\s*=\s*([^!]+)!",ctrl)
        if not m or m.group(1).strip()!=val:
            raise RuntimeError(f"unsupported original MAKEGEO control {key}: {m.group(1).strip() if m else None}")
    binroot=output/"bin"
    binroot.mkdir(exist_ok=True)
    alias=output/"include_alias_makegeo"
    alias.mkdir(exist_ok=False)
    for original_file in sorted(original.iterdir()):
        if original_file.is_file():
            lower=original_file.name.lower()
            if not (alias/lower).exists():
                (alias/lower).symlink_to(original_file)
    binary=binroot/"makegeo.x"
    compile_cmd=["gfortran","-std=legacy","-fno-automatic","-fno-align-commons",
                 "-fallow-argument-mismatch","-ffixed-line-length-none","-O0",
                 "-I"+str(alias),"-I"+str(original),
                 str(original/"makegeo.for"),"-o",str(binary)]
    run(compile_cmd,root,output/"makegeo_compile")
    run([str(binary),"makegeo.inp"],work,output/"makegeo_run")
    geo=work/"geo.dat"
    if not geo.is_file() or geo.stat().st_size<30000:
        raise RuntimeError("GEO.DAT missing, not complete")
    lines=geo.read_text().splitlines()
    if not lines or "GEO.DAT" not in lines[0] or len(lines)<100:
        raise RuntimeError("GEO.DAT missing expected header")
    details={"status":"ORIGINAL_MAKEGEO_REFERENCE_CAPTURED_NOT_YET_COMPARED",
             "grid":g,"original_source_sha256":sha(original/"makegeo.for"),
             "original_control_sha256":sha(original/"makegeo.inp"),
             "actual_control_sha256":sha(work/"makegeo.inp"),
             "lu_dat_sha256":sha(p2/"lu.dat"),
             "terrain_dat_sha256":sha(p1/"terrel.dat"),
             "geo_dat_sha256":sha(geo),"geo_dat_bytes":geo.stat().st_size,
             "geo_dat_lines":len(lines),"control_modes":expected}
    (output/"p3_manifest.json").write_text(json.dumps(details,indent=2)+"\n")
    print(json.dumps(details,indent=2))
if __name__=="__main__":
    main()
