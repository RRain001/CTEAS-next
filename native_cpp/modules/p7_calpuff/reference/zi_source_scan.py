#!/usr/bin/env python3
"""Print pinned CALPUFF 7.2.1 historical ZIOLD/ZIMAX write sites.

READ-ONLY source inventory, never infer a native update rule from DGM alone.
"""
from pathlib import Path
import hashlib
import json
import re
import sys

EXPECTED="da40372cab1c181158d0ee5faac16f678e876fc14415073c38c8e3bdabfbc568"

def main():
    if len(sys.argv)!=2:
        raise ValueError("usage: zi_source_scan.py PINNED_CALPUFF.FOR")
    path=Path(sys.argv[1])
    raw=path.read_bytes()
    sha=hashlib.sha256(raw).hexdigest()
    if sha!=EXPECTED:
        raise ValueError(f"original CALPUFF source hash drift: {sha}")
    lines=raw.decode("latin-1").splitlines()
    subroutine="OUTSIDE_UNIT"
    methods=[]
    all_refs=0
    pattern=re.compile(r"\b(ziold|zimax)\s*\([^)]*\)\s*=",re.IGNORECASE)
    unit=re.compile(r"\b(?:subroutine|function)\s+([a-z0-9_]+)",re.IGNORECASE)
    for i,line in enumerate(lines):
        if line and line[0] in "cC*!":continue
        if re.search(r"^\s*end\s*$",line,re.I):
            subroutine="OUTSIDE_UNIT"
        matched_unit=unit.search(line)
        if matched_unit:subroutine=matched_unit.group(1).upper()
        if re.search(r"\b(ziold|zimax)\b",line,re.I):all_refs+=1
        match=pattern.search(line)
        if match:
            start=max(0,i-7);end=min(len(lines),i+8)
            methods.append({
                "line":i+1,"subroutine":subroutine,
                "assignment":match.group(0).strip(),
                "context":[f"{j+1}: {lines[j]}" for j in range(start,end)],
            })
    result={"status":"PINNED_CALPUFF_ZI_WRITES_AUDITED",
            "sha256":sha,"source_lines":len(lines),"references":all_refs,
            "assignment_count":len(methods),
            "assignments":methods}
    print(json.dumps(result,ensure_ascii=False,indent=2))
    print("P7_ORIGINAL_ZI_ASSIGNMENTS=PASS COUNT="+str(len(methods)))
    if not methods:
        raise RuntimeError("no original ZIOLD/ZIMAX assignments found")

if __name__=="__main__":main()
