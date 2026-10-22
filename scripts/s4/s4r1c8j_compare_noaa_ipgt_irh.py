#!/usr/bin/env python3
"""Independent exact integer equality for original CALMET IPGT+IRH.

Native G58 takes only original forcing, not original P6F output;
the independent untouched-original six-hour MET.DAT is read only here.
"""
from __future__ import annotations
import argparse,json,struct,hashlib
from pathlib import Path
from scripts.s4.s4r1c8i_compare_noaa_43_real_p6f import (
    NX,NY,NC,INT,original_hour,sha
)
def compare(original:Path,native:Path,log:Path,receipt:Path,report:Path)->bool:
    proof=json.loads(receipt.read_text())
    txt=log.read_text()
    if(proof.get("status")!="PASS_SOURCE_SCOPED_REAL_NOAA_NATIVE_P6F_43_REAL_FIELDS"
       or proof.get("above_tolerance")!=0
       or proof.get("float_compared")!=43*NC
       or proof.get("original_full_six_hour_met_sha256")!=sha(original)
       or "S4R1C8J_REAL_NOAA_NATIVE_INTEGER_FIELDS=PRODUCED_UNVERIFIED" not in txt
       or "ORIGINAL_INTERMEDIATE_INPUT=FALSE" not in txt):
        raise ValueError("G58 43 source REAL4 fields and original provenance not proven")
    if native.stat().st_size!=2*INT.size:
        raise ValueError("G58 source P6F IPGT/IRH binary extent invalid")
    fields,hours=original_hour(original)
    if hours!=6:raise ValueError("G58 sixhour original clock changed")
    raw=native.read_bytes()
    calculated={
        "IPGT    ":INT.unpack_from(raw,0),
        "IRH     ":INT.unpack_from(raw,INT.size),
    }
    mismatch=[]
    checks={}
    total=0
    for label in ("IPGT    ","IRH     "):
        ref=INT.unpack(fields[label])
        predicted=calculated[label]
        bad=0;worst=None
        for i,(a,b) in enumerate(zip(ref,predicted,strict=True)):
            if label=="IPGT    " and not(1<=a<=6 and 1<=b<=6):
                raise ValueError("G58 PGT physically invalid")
            if label=="IRH     " and not(0<=a<=100 and 0<=b<=100):
                raise ValueError("G58 original relative humidity physically invalid")
            if a!=b:
                bad+=1
                if worst is None:
                    worst={"i":i%NX+1,"j":i//NX+1,"original":a,"native":b}
                if len(mismatch)<20:
                    mismatch.append({"label":label,"i":i%NX+1,
                                     "j":i//NX+1,"original":a,"native":b})
        checks[label.strip()]={"integer_comparisons":NC,"not_equal":bad,
                               "first_failure":worst}
        total+=bad
    result={
        "status":("PASS_SOURCE_SCOPED_REAL_NOAA_TWO_P6F_INTEGERS" if total==0
                  else "FAIL_REAL_NOAA_P6F_IPGT_IRH_NUMERIC"),
        "source_scoped":"FIRSTHOUR_REAL_NOAA_2SS1US_6907LAND_63WATER",
        "source_unmodified_original_6h_met_sha256":sha(original),
        "native_2integer_sha256":sha(native),
        "independent_43real_receipt_sha256":sha(receipt),
        "original_intermediate_used_as_native_input":False,
        "integer_field_count":2,"integer_comparisons":2*NC,
        "not_equal":total,"fields":checks,"first_differences":mismatch,
        "firsthour_all_45_numeric_science":"CONDITIONAL_ONLY_43_REAL_PLUS_2_INTEGER",
        "native_complete_p6f_45_record_file":"NOT_ACCEPTED",
        "g14_sixhour_causal":"NOT_ACCEPTED","p7":"NOT_ACCEPTED"
    }
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("S4R1C8J_REAL_NOAA_IPGT_IRH="+result["status"])
    print("S4R1C8J_INTEGER_NOT_EQUAL="+str(total))
    print("S4R1C8J_FULL_P6F_G26_P7=NOT_ACCEPTED")
    return total==0
def main():
    p=argparse.ArgumentParser()
    for k in ("original","native","log","receipt","report"):
        p.add_argument("--"+k,type=Path,required=True)
    a=p.parse_args()
    if not compare(a.original,a.native,a.log,a.receipt,a.report):
        raise SystemExit(3)
if __name__=="__main__":main()
