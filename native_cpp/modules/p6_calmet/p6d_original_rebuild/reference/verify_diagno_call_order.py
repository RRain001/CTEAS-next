#!/usr/bin/env python3
"""Prevent noncommutative FRADJ/SLOPE order regression in the real P6D producer.

This is a *source-order guard*, NOT a physical parity proof. The latter is
established by original-Fortran-vs-C++ field comparisons separately.
"""
from __future__ import annotations
import argparse
import hashlib
import re
from pathlib import Path

ORIGINAL="437f43bb7f0e51a1919e56664663e1a046986ed0"


def read_original(f: Path):
    raw=f.read_bytes()
    digest=hashlib.sha1(f"blob {len(raw)}\0".encode()+raw).hexdigest()
    if digest!=ORIGINAL:raise RuntimeError(f"CALMET original blob changed: {digest}")
    return raw.decode(errors="replace").splitlines()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--vendor",type=Path,required=True)
    parser.add_argument("--producer",type=Path,required=True)
    a=parser.parse_args()
    lines=read_original(a.vendor)
    fr="IF (IFRADJ .EQ. 1) CALL FRADJ"
    sl="if (ISLOPE.EQ.1)CALL SLOPE"
    if fr not in lines[5642] or sl not in lines[5721]:
        raise RuntimeError("original DIAGNO FRADJ/SLOPE line anchors changed")
    producer=a.producer.read_text()
    # Match actual calls, not the text of comment explanations.
    match_f=re.findall(r"\bfroude_adjust\s*\(",producer)
    match_s=re.findall(r"\bcompute_original_slope_scoped\s*\(",producer)
    if len(match_f)!=1 or len(match_s)!=1:
        raise RuntimeError("P6D diagnostics expect exactly one FRADJ and SLOPE call")
    surface=producer.index("surfvar_one_station(")
    f=producer.index("froude_adjust(")
    heat=producer.index("cteas::p6e::heatfx(")
    s=producer.index("compute_original_slope_scoped(")
    blend=producer.index("original_inter2_selected(",s)
    if not (0<surface<f<heat<s<blend):
        raise RuntimeError(
            "original SURFVAR -> FRADJ -> HEATFX -> SLOPE -> INTER2 "
            "stage sequence violated")
    # Source-authentic double snapshot for the selected GEO HTFAC=1 case.
    # The L6100 snapshot overwrites L5748 after INTER2 before SMOOTH.
    if ("CALL WINDBC(UG,VG,UB,VB,K)" not in lines[5747] or
            "CALL INTER2(US," not in lines[6054] or
            "CALL INTER2(VS," not in lines[6058] or
            "IF(HTFAC.LE.0.) GO TO 285" not in lines[6091] or
            "CALL WINDBC(U,V,UB,VB,K)" not in lines[6099] or
            "CALL SMOOTH(U,V,UB,VB,NSMTH)" not in lines[6118]):
        raise RuntimeError("original CALMET double WINDBC order or HTFAC gating changed")
    start=producer.index("SmoothInput tail;",blend)
    end=producer.index("original_smooth_divcel_w(",start)
    tail=producer[start:end]
    if ("tail.u_mps=blended_u;tail.v_mps=blended_v;" not in tail):
        raise RuntimeError("post-INTER2 U/V must remain the working tail wind")
    lhs_u=re.findall(r"tail\.ub_west_east_mps\[[^;]+?\]\s*=\s*blended_u\[",tail)
    lhs_v=re.findall(r"tail\.vb_south_north_mps\[[^;]+?\]\s*=\s*blended_v\[",tail)
    if len(lhs_u)!=2 or len(lhs_v)!=2:
        raise RuntimeError("HTFAC=1 requires second WINDBC snapshot from INTER2 U/V")
    if re.search(r"tail\.(?:ub_west_east_mps|vb_south_north_mps)"
                 r"\[[^;]+?\]\s*=\s*corrected_[uv]\[",tail):
        raise RuntimeError("stale pre-INTER2 boundary incorrectly passed to SMOOTH")
    print("PASS_P6D_SOURCE_ORDER_DOUBLE_WINDBC_AND_INTER2")
    print("CALMET: WINDBC(UG,VG) L5748, INTER2 L6055/L6059, "
          "HTFAC>0 WINDBC(U,V) L6100, SMOOTH L6119")
    print("PASS_P6D_HTFAC1_POST_INTER2_BOUNDARY_FOR_SMOOTH_DIVCEL_W")


if __name__=="__main__":
    main()