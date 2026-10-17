#!/usr/bin/env python3
"""G36B adversarial durability gates on a genuine computed native 143h image.

Each negative test injects a crash at a distinct filesystem publication
boundary and verifies the incomplete output is never declared READY.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import json
import tempfile

from g36b_atomic_calmet_publish import (
    MET,READY,publish,check_published,verify_image,digest
)


def rejects(action,what:str)->None:
    try:
        action()
    except (ValueError,RuntimeError,OSError,AssertionError):
        # The independent Fortran framing oracle intentionally raises
        # AssertionError on truncated record bodies/trailers. It is a
        # rejection, not an accepted damaged byte stream.
        return
    raise AssertionError("G36B accepted unsafe operation "+what)


def test(native:Path)->dict:
    original=verify_image(native)
    outcomes=[]
    with tempfile.TemporaryDirectory(prefix="g36b-crash-checks-") as tmp:
        root=Path(tmp)
        target=root/"valid"
        record=publish(native,target,"none")
        if record["sha256"]!=original["sha256"] or (
            digest(target/MET)!=original["sha256"]):
            raise AssertionError("G36B committed a nonidentical weather image")
        if check_published(target)["records"]!=6435:
            raise AssertionError("G36B committed partial 143h weather")
        if not publish(native,target,"none").get("idempotent"):
            raise AssertionError("G36B idempotent same-input retry rejected")
        outcomes.append("valid_sha256_143h_commit_and_idempotent_retry")

        for fault in ("before_stage_fsync","after_stage_fsync",
                      "after_met_rename","before_ready_rename"):
            dest=root/fault
            rejects(lambda fault=fault,dest=dest:publish(native,dest,fault),
                    "injected crash "+fault)
            if (dest/READY).exists():
                raise AssertionError("G36B published READY after injected crash "+fault)
            rejects(lambda dest=dest:check_published(dest),
                    "uncommitted after injected "+fault)
            if fault in ("after_met_rename","before_ready_rename"):
                if not (dest/MET).exists():
                    raise AssertionError("G36B crash at rename missed orphan case")
                rejects(lambda dest=dest:publish(native,dest,"none"),
                        "uncommitted orphan overwrite")
            else:
                if (dest/MET).exists():
                    raise AssertionError("G36B prematurely published met.dat "+fault)
            outcomes.append("crash_rejected_"+fault)

        fragment=root/"truncated-native.met.dat"
        fragment.write_bytes(native.read_bytes()[:-12])
        rejects(lambda:publish(fragment,root/"truncated","none"),
                "truncated full native source")
        if (root/"truncated"/READY).exists():
            raise AssertionError("G36B published truncated native source")
        outcomes.append("truncated_original_fortran_record_rejected")

        # Integrity must still be enforced AFTER published hash/READY.
        changed=bytearray((target/MET).read_bytes())
        changed[-8]^=0x01
        (target/MET).write_bytes(changed)
        rejects(lambda:check_published(target),"tampered committed image")
        outcomes.append("published_byte_corruption_rejected")

        if (target/READY).exists():
            (target/MET).write_bytes(native.read_bytes())
            ready=json.loads((target/READY).read_text())
            ready["sha256"]="0"*64
            (target/READY).write_text(json.dumps(ready)+"\n")
            rejects(lambda:check_published(target),"tampered READY SHA256")
            outcomes.append("tampered_sha_manifest_rejected")
    return {"status":"PASS_G36B_ATOMIC_PUBLICATION_FAULT_MATRIX",
            "native_source_sha256":original["sha256"],
            "hour_count":original["hours"],"field_count":original["records"],
            "checks":outcomes,"check_count":len(outcomes)}


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--native-met",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    opt=ap.parse_args()
    opt.out.parent.mkdir(parents=True,exist_ok=True)
    try:
        verdict=test(opt.native_met)
    except Exception as error:
        opt.out.write_text(json.dumps({"status":"BLOCKED_G36B","error":str(error)},
                                      indent=2)+"\n")
        raise
    opt.out.write_text(json.dumps(verdict,indent=2)+"\n")
    print(json.dumps(verdict,indent=2))
