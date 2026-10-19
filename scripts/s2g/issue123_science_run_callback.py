#!/usr/bin/env python3
"""#123: main-only GitHub Actions D6/D8/D9 bounded audit-status issue callback.

Published statuses are *reported*, not independently accepted scientific
verdicts. Never publishes vendor binaries, BLN, GLCC, sample points, or logs.
Only configured main workflow calls the POST action; PR CI is offline only.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import sys
from urllib.request import Request, urlopen

ISSUE=123
REPO="RRain001/CTEAS-next"
D6="D6B_GNU_SPLIT_IO_EOF_ADAPTED_ORIGINAL_COASTEXT_GENERATED_BLN_SCOPED"
D8="D8_REAL_ORIGINAL_BLN_IPTYPE_ZERO_MISMATCH_PASS_SCOPED"
D9="D9_REAL_ORIGINAL_GLAZAS_HITS_38_ZERO_DIFF_PASS_SCOPED"


def bounded(root: Path,relative:str) -> dict:
    path=root/relative
    if path.is_symlink() or not path.is_file():
        return {}
    if path.stat().st_size>256_000:
        return {}
    try:
        data=json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data,dict) else {}
    except (ValueError,OSError):
        return {}


def safe_status(data:dict, expected:str) -> str:
    s=data.get("status")
    if not isinstance(s,str) or not re.fullmatch(r"[A-Z0-9_]{1,100}",s):
        return "REPORT_NOT_PRESENT_OR_INVALID"
    if s==expected:return s + " (report exists; verify artifact)"
    return s + " (not accepted)"


def report_body(root:Path,run_id:int,head_sha:str) -> str:
    if run_id<=0 or not re.fullmatch(r"[0-9a-f]{40}",head_sha):
        raise ValueError("D8D9_INVALID_RUN_OR_COMMIT")
    d6=bounded(root,"issue123-d6b-original-run/original_coastext_report.json")
    d8=bounded(root,"issue123-d8-oracle/d8_iptype_report.json")
    d9=bounded(root,"issue123-d9-hits-report.json")
    run=f"https://github.com/{REPO}/actions/runs/{run_id}"
    bln=d6.get("original_bln_sha256","")
    if not isinstance(bln,str) or not re.fullmatch(r"[0-9a-f]{64}",bln):
        bln="NOT_ACCEPTED"
    source=d6.get("original_source_sha256","")
    if not isinstance(source,str) or not re.fullmatch(r"[0-9a-f]{64}",source):
        source="NOT_ACCEPTED"
    return (
       "### #123 D6/D8/D9 main science run report (automatic)\n\n"
       f"- Run: {run}\n"
       f"- Commit: {head_sha}\n"
       f"- D6 genuine original BLN: {safe_status(d6,D6)}\n"
       f"- D8 genuine BLN original Fortran/C++ IPTYPE: {safe_status(d8,D8)}\n"
       f"- D9 200x200x38 original HITS parity: {safe_status(d9,D9)}\n"
       f"- Original vendor source SHA256: {source}\n"
       f"- Original BLN SHA256: {bln}\n"
       f"- Artifact listing: {run}#artifacts\n\n"
       "Reported JSON presence is not an independently accepted scientific result. "
       "Inspect the completed job logs, source inputs, exact commit and uploaded "
       "D6/D8/D9 audit JSON before declaring any scoped PASS. "
       "Do not infer D10 LU.DAT fraction parity or close #123.\n"
    )


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root",type=Path,required=True)
    p.add_argument("--run-id",type=int,required=True)
    p.add_argument("--head-sha",required=True)
    p.add_argument("--repo",required=True)
    p.add_argument("--ref",required=True)
    p.add_argument("--event",required=True)
    p.add_argument("--publish",action="store_true")
    args=p.parse_args()
    try:
        if (args.repo!=REPO or args.ref!="refs/heads/main" or
            args.event=="pull_request"):
            raise ValueError("D8D9_CALLBACK_UNTRUSTED_EVENT_OR_REF")
        body=report_body(args.root,args.run_id,args.head_sha)
        if args.publish:
            token=os.environ.get("GH_TOKEN")
            if not token:
                raise ValueError("D8D9_CALLBACK_MISSING_TOKEN")
            url=f"https://api.github.com/repos/{REPO}/issues/{ISSUE}/comments"
            req=Request(url,data=json.dumps({"body":body}).encode("utf-8"),
              headers={"Authorization":f"Bearer {token}",
                       "Accept":"application/vnd.github+json",
                       "X-GitHub-Api-Version":"2022-11-28",
                       "Content-Type":"application/json"},method="POST")
            with urlopen(req,timeout=20) as resp:
                if resp.status!=201:
                    raise ValueError("D8D9_CALLBACK_COMMENT_NOT_CREATED")
            print("ISSUE123_MAIN_SCIENCE_RUN_CALLBACK_POSTED")
        else:
            print(body)
        return 0
    except (OSError,ValueError) as exc:
        print(f"ISSUE123_CALLBACK_FAIL_CLOSED:{type(exc).__name__}:{str(exc)[:180]}",
              file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
