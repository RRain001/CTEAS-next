#!/usr/bin/env python3
"""Read-only CALPUFF 7.2.1 RLSMET/WSNEW source audit, no vendor edits.

The original input source on the GitHub-hosted runner is a trustworthy oracle.
Find every RLSMET call and declaration, the POINTS1 WSNEW/XTMP1 cadence
dependency, and stage original source slices for code-by-code reconstruction.
This script does NOT assert that an independent native RLSMET exists.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import pathlib
import re

CALPUFF_SHA = "da40372cab1c181158d0ee5faac16f678e876fc14415073c38c8e3bdabfbc568"
HEADER = re.compile(r"^\s{6}(?:(?:real|integer|logical|double\s+precision)\s+)?(?:subroutine|function)\s+(\w+)\s*(?:\(|$)",re.I)
TERMINATOR = re.compile(r"^      end\s*(?:!.*)?$",re.I)
WORD = re.compile(r"\brlsmet\b",re.I)
CONTEXT = re.compile(r"\b(?:wsnew|xtmp1|npnew|newpt1|rlsmet|wsvar)\b",re.I)

def audit(vendor: pathlib.Path) -> tuple[dict,list[str]]:
    target=vendor/"calpuff.for"
    raw=target.read_bytes()
    actual=hashlib.sha256(raw).hexdigest()
    if actual != CALPUFF_SHA:
        raise ValueError(f"Original calpuff.for SHA differs: {actual}")
    files=sorted(vendor.glob("*.for"))
    if not files: raise ValueError("No vendor Fortran source files")
    matches=[]
    subroutines=[]
    extracted=[]
    for path in files:
        data=path.read_bytes()
        lines=data.decode("latin-1").splitlines()
        for i,line in enumerate(lines):
            if WORD.search(line):
                matches.append({"file":path.name,"line":i+1,"text":line.rstrip()})
        for i,line in enumerate(lines):
            h=HEADER.match(line)
            if h and h.group(1).lower() in ("rlsmet","windset","zfind"):
                end=next((j for j in range(i+1,len(lines)) if TERMINATOR.match(lines[j])),None)
                if end is None: raise ValueError(f"RLSMET missing END at {path.name}:{i+1}")
                src="\n".join(lines[i:end+1])+"\n"
                record={"file":path.name,"first_line":i+1,"last_line":end+1,
                        "source_sha256":hashlib.sha256(src.encode("latin-1")).hexdigest(),
                        "lines":end+1-i}
                name=h.group(1).lower()
                if name=="rlsmet": subroutines.append(record)
                extracted += [f"{name.upper()} original {record}:"]+[f"{j+1:6d} {lines[j]}" for j in range(i,end+1)]
        if path.name=="calpuff.for":
            start=next((i for i,line in enumerate(lines) if re.search(r"^      subroutine points1\b",line,re.I)),None)
            if start is None: raise ValueError("Original POINTS1 subroutine missing")
            stop=next((j for j in range(start+1,len(lines)) if TERMINATOR.match(lines[j])),None)
            if stop is None: raise ValueError("Original POINTS1 termination missing")
            for j in range(start,stop+1):
                if CONTEXT.search(lines[j]):
                    lo=max(start,j-4)
                    hi=min(stop+1,j+5)
                    extracted.append(f"POINTS1 context {lo+1}-{hi} around L{j+1}")
                    extracted.extend(f"{k+1:6d} {lines[k]}" for k in range(lo,hi))
    if not matches:
        raise ValueError("No original RLSMET reference in vendor *.for")
    if not subroutines:
        extracted.append("RLSMET definition absent from vendor .for: inspect module/includes manually")
    report={
        "gate":"P7_RLSMET_SOURCE_DISCOVERY_ONLY",
        "vendor_calpuff_sha256":actual,
        "fortran_files_scanned":len(files),
        "rlsmet_references":matches,
        "rlsmet_definitions":subroutines,
        "native_rlsmet_implemented":False,
        "full_original_143h_equivalence":"NOT_PASS",
        "vendor_modified":False,
    }
    return report,extracted

def main()->int:
    a=argparse.ArgumentParser()
    a.add_argument("--vendor",type=pathlib.Path,required=True)
    a.add_argument("--report",type=pathlib.Path,required=True)
    a.add_argument("--source-extract",type=pathlib.Path,required=True)
    args=a.parse_args()
    report,source=audit(args.vendor)
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.source_extract.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    args.source_extract.write_text("\n".join(source)+"\n")
    print("P7_RLSMET_VENDOR_SHA=PASS")
    print("P7_RLSMET_ORIGINAL_REFERENCES="+str(len(report["rlsmet_references"])))
    print("P7_RLSMET_ORIGINAL_DEFINITIONS="+str(len(report["rlsmet_definitions"])))
    print("P7_RLSMET_NATIVE_EQUIVALENCE=NOT_PASS")
    for row in report["rlsmet_references"][:35]:
        print(f"RLSMET_REF {row['file']}:{row['line']} {row['text']}")
    for row in report["rlsmet_definitions"]:
        print(f"RLSMET_SOURCE {row['file']}:{row['first_line']}-{row['last_line']}")
    # This is the ORIGINAL order that computes stack-level wind, PRFIN
    # final height, the second RLSMET release-height wind and WSNEW.
    lines=(args.vendor/"calpuff.for").read_bytes().decode("latin-1").splitlines()
    for first,last in ((15428,15464),(15694,15730),(15935,16010)):
        print(f"P7_ORIGINAL_POINTS1_SOURCE_CONTEXT L{first}-L{last}")
        for index in range(first-1,last):
            print(f"POINTS1_SOURCE {index+1:6d} {lines[index]}")
    return 0

if __name__=="__main__":raise SystemExit(main())
