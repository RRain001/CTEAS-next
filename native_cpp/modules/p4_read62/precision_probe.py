"""Verify original READ62 + C++ P4 both accept exact 3,4,5,6 decimal suffixes.

Legacy column positions are never shifted. This tests a separate optional
P4EXACT tag, not an impossible F6.2 longitude expansion inside fixed fields.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from native_cpp.modules.p4_read62.verify_updat_parity import compare

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def variants(fsl_content: str, lat: float, lon: float, digits: int):
    result=[]
    count=0
    for row in fsl_content.splitlines():
        if row.startswith("      1  99999"):
            row=row.split(" P4EXACT_LAT=", 1)[0]
            row += f" P4EXACT_LAT={lat:.{digits}f} P4EXACT_LON={lon:.{digits}f}"
            count+=1
        result.append(row)
    if count==0:
        raise RuntimeError("no FSL header2 records")
    return "\n".join(result)+"\n",count

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--fsl",type=Path,required=True)
    p.add_argument("--fortran",type=Path,required=True)
    p.add_argument("--template-inp",type=Path,required=True)
    p.add_argument("--baseline-updat",type=Path,required=True)
    p.add_argument("--cpp",type=Path,required=True)
    p.add_argument("--outdir",type=Path,required=True)
    p.add_argument("--lat",type=float,required=True)
    p.add_argument("--lon",type=float,required=True)
    args=p.parse_args()
    args.outdir.mkdir(parents=True,exist_ok=True)
    template=args.template_inp.read_text(encoding="utf-8")
    text=args.fsl.read_text(encoding="utf-8")
    results=[]
    for digits in (3,4,5,6):
        work=args.outdir/f"decimal_{digits}"
        work.mkdir(exist_ok=True)
        input_fsl,n=variants(text,args.lat,args.lon,digits)
        (work/"precision.fsl").write_text(input_fsl,encoding="utf-8")
        ini=template
        for k,v in {"INDAT":"precision.fsl",
                    "UPDAT":"fortran_precision_up.dat",
                    "RUNLST":"fortran_precision.lst"}.items():
            ini,changed=re.subn(r"(!\s*"+k+r"\s*=\s*)[^!]*!",
                                lambda m:m.group(1)+v+" !",ini,count=1)
            if changed!=1:
                raise RuntimeError("cannot patch INP "+k)
        (work/"read62.inp").write_text(ini,encoding="utf-8")
        fortran=subprocess.run([str(args.fortran.resolve()),"read62.inp"],
                               cwd=work,capture_output=True,text=True,check=False)
        (work/"fortran.log").write_text(fortran.stdout+"\n"+fortran.stderr)
        cpp=subprocess.run([str(args.cpp.resolve()),str((work/"precision.fsl").resolve()),
                          str((work/"cpp_precision_up.dat").resolve()),
                          "2022-01-01T00:00Z","2022-01-06T23:00Z","500","58424"],
                          cwd=work,capture_output=True,text=True,check=False)
        (work/"cpp.log").write_text(cpp.stdout+"\n"+cpp.stderr)
        m=re.search(r"P4_CPP_EFFECTIVE_COORD\s+([-\d.]+)\s+([-\d.]+)",cpp.stdout)
        parsed=tuple(map(float,m.groups())) if m else None
        target=(round(args.lat,digits),round(args.lon,digits))
        fortran_out=work/"fortran_precision_up.dat"
        cpp_out=work/"cpp_precision_up.dat"
        identical=fortran_out.is_file() and digest(args.baseline_updat)==digest(fortran_out)
        parity=compare(fortran_out,cpp_out) if fortran_out.is_file() and cpp_out.is_file() else {}
        result={"digits":digits,"fsl_headers":n,"fortran_exit":fortran.returncode,
                "cpp_exit":cpp.returncode,"parsed_cpp_coords":parsed,
                "expected_coords":target,"fortran_output_identical_to_baseline":identical,
                "cpp_numeric_parity":parity.get("pass",False)}
        result["pass"]=(fortran.returncode==0 and cpp.returncode==0 and identical
                        and parity.get("pass",False) and parsed is not None
                        and all(abs(p-q)<0.0000011 for p,q in zip(parsed,target)))
        results.append(result)
        print("P4_COORD_PRECISION",json.dumps(result))
    summary={"all_pass":all(x["pass"] for x in results),"runs":results,
             "interpretation":"P4EXACT trailing tag stores exact 3-6 decimals; READ62 fixed F7.2/F6.2 still uses 2 dp"}
    (args.outdir/"precision-verification.json").write_text(json.dumps(summary,indent=2)+"\n")
    if not summary["all_pass"]:
        raise SystemExit("P4 coordinate precision probe failed")

if __name__=="__main__":
    main()
