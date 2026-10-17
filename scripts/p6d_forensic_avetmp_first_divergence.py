#!/usr/bin/env python3
"""Write-only AVETMP first-divergence trace (Fortran vs native C++), NOT a physics fix.

Instrument only temporary build copies, preserve accepted source and ensure the
instrumented original still generates the frozen 143h MET.DAT byte-for-byte.
The probe is at the 2022-01-01_19 TEMP2D worst cell: 1-based (12,19).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "native_cpp/modules/p6_calmet/reference"))
import original_internal_state_dump as dgm

FOREIGN_ANCHOR = "      ztave(i,j)  = ztbar  / sumwt\n"
FOREIGN_PROBE = """      if (i.eq.12.and.j.eq.19) then
         open(93,file='dgm_avetmp_probe.txt',status='unknown',
     1        position='append')
         write(93,'(7(ES24.15E3,1X))') u(i,j),v(i,j),
     1        ztemp(i,j),sumwt,ztbar,ztave(i,j),eta
         close(93)
      endif
"""
CPP_ANCHOR = "            out[local]=ztbar/sumwt;\n"
CPP_PROBE = """            if(i==11 && j==18) {
                std::fprintf(stderr,
                    "CTEAS_AVETMP_PROBE %.9g %.9g %.9g %.9g %.9g %.9g %.9g\\n",
                    a.u_ms[local],a.v_ms[local],a.temperature_k[local],
                    sumwt,ztbar,out[local],eta);
            }
"""

QH_PRE_ANCHOR = "         if (itprog.lt.2) call airden(pres,temp2d,rho)\n"
QH_POST_ANCHOR = "     2               nx,ny,mcloud,ccgrid,ipsifcn,qh,ustar,el)\n"
QH_PRE_PROBE = """          open(92,file='dgm_qh_pre_probe.txt',status='unknown',
     1         position='append')
          write(92,'(7(ES24.15E3,1X))') ug(23,29,1),vg(23,29,1),
     1          temp2d(23,29),rho(23,29),qh(23,29),
     2          z0(23,29),sinalpc(23,29)
          close(92)
"""
QH_POST_PROBE = """          open(91,file='dgm_qh_post_probe.txt',status='unknown',
     1         position='append')
          write(91,'(3(ES24.15E3,1X))') qh(23,29),
     1         ustar(23,29),el(23,29)
          close(91)
"""
CPP_QH_PRE_ANCHOR = "        const auto stable_state=cteas::p6e::stable_elustr(stable);\n"
CPP_QH_PRE_PROBE = """        if(h==131U) {
            const auto qk=static_cast<std::size_t>(28*nx+22);
            std::fprintf(stderr,
                "CTEAS_QH_PRE %.9g %.9g %.9g %.9g %.9g %.9g %.9g\\n",
                corrected_u[qk],corrected_v[qk],surface_state.temp_k[qk],
                diag_rho[qk],heat_flux[qk],geo.z0_m[qk],sinalpc[qk]);
        }
"""
CPP_QH_POST_ANCHOR = "        // SLOPE now consumes the source-ordered *post-ELUSTR* QH field.\n"
CPP_QH_POST_PROBE = """        if(h==131U) {
            const auto qk=static_cast<std::size_t>(28*nx+22);
            std::fprintf(stderr,"CTEAS_QH_POST %.9g %.9g %.9g\\n",
                heat_flux[qk],stable_state.ustar_ms[qk],
                stable_state.monin_obukhov_m[qk]);
        }
"""

def inject_once(content: str, anchor: str, extra: str) -> str:
    if content.count(anchor) != 1:
        raise RuntimeError("expected exactly one source-locked AVETMP anchor")
    return content.replace(anchor, anchor + extra, 1)

def original(args):
    audit = json.loads((args.audit_dir / "dgm-audit.json").read_text())
    if audit["status"] != "ORIGINAL_MET_DAT_IDENTICAL":
        raise RuntimeError("unverified original CALMET source")
    source = args.audit_dir / "calmet_instrumented.for"
    if dgm.sha256_file(source) != audit["instrumentation"]["instrumented_sha256"]["calmet_instrumented.for"]:
        raise RuntimeError("instrumented source changed")
    root = args.work / "original_avetmp_probe"
    root.mkdir(parents=True,exist_ok=True)
    source_copy = root / "calmet_avetmp_probe.for"
    original_text=inject_once(source.read_text(), FOREIGN_ANCHOR, FOREIGN_PROBE)
    original_text=inject_once(original_text,QH_PRE_ANCHOR,QH_PRE_PROBE)
    # Both ISFCMET=0 and =1 ELUSTR branches end in this literal line.
    # The frozen case uses ISFCMET=0; instrument only the first branch.
    if original_text.count(QH_POST_ANCHOR)!=2:
        raise RuntimeError("original DIAGNO ELUSTR branch source drift")
    original_text=original_text.replace(QH_POST_ANCHOR,
                                        QH_POST_ANCHOR+QH_POST_PROBE,1)
    source_copy.write_text(original_text)
    binary = root / "bin" / "calmet-avetmp-probe.x"
    dgm._build(args.compiler,source_copy,args.audit_dir / "include-alias",binary)
    case_dir = root / "case"
    dgm._stage_case(args.case.resolve(), case_dir)
    metdir = case_dir / "run" / "met"
    result = dgm._run(binary, metdir)
    if result["met_dat_sha256"] != dgm.TARGET_MET_DAT_SHA256:
        raise RuntimeError("AVETMP tracing perturbed original MET.DAT -- DO NOT TRUST")
    trace = metdir / "dgm_avetmp_probe.txt"
    if not trace.exists():raise RuntimeError("original AVETMP probe not created")
    (args.work/"original_avetmp_probe.txt").write_bytes(trace.read_bytes())
    for name in ("dgm_qh_pre_probe.txt","dgm_qh_post_probe.txt"):
        qh_trace=metdir/name
        if not qh_trace.is_file() or len(qh_trace.read_text().splitlines())!=143:
            raise RuntimeError(f"original hourly QH trace incomplete: {name}")
        (args.work/name).write_bytes(qh_trace.read_bytes())
    print("ORIGINAL_AVETMP_WRITE_ONLY_FROZEN_MET_SHA_PASS",len(trace.read_text().splitlines()))

def cpp(args):
    header = args.header
    text = header.read_text()
    text = inject_once(text, CPP_ANCHOR, CPP_PROBE)
    text = text.replace("#include <cmath>", "#include <cmath>\n#include <cstdio>", 1)
    header.write_text(text)
    main=args.main_file
    source=main.read_text()
    source=inject_once(source,CPP_QH_PRE_ANCHOR,CPP_QH_PRE_PROBE)
    source=inject_once(source,CPP_QH_POST_ANCHOR,CPP_QH_POST_PROBE)
    source=source.replace("#include <iomanip>","#include <iomanip>\n#include <cstdio>",1)
    main.write_text(source)
    print("CXX_AVETMP_AND_QH_FORENSIC_BUILD_ONLY_PROBES_INSTALLED")

def report(args):
    originals=[]
    for line in (args.work/"original_avetmp_probe.txt").read_text().splitlines():
        values=[float(x.replace("D","E")) for x in line.split()]
        if len(values)!=7:raise ValueError("unexpected original AVETMP trace")
        originals.append(values)
    candidates=[]
    for line in (args.work/"cpp_avetmp_probe.log").read_text().splitlines():
        m=re.search(r"CTEAS_AVETMP_PROBE\s+(.+)$",line)
        if m:
            values=[float(x) for x in m.group(1).split()]
            if len(values)!=7:raise ValueError("unexpected native AVETMP trace")
            candidates.append(values)
    nh=143
    if len(originals)!=3*nh or len(candidates) not in (nh,2*nh):
        raise RuntimeError(
            f"unexpected original/native hourly AVETMP calls: {len(originals)}/{len(candidates)}")
    native_per_hour=len(candidates)//nh
    # The original always evaluates three AVETMP calls per model hour:
    # DIAGNO's first SURFVAR, DIAGNO's post-FRADJ SURFVAR, then COMP.
    # Native P6D formerly had only one DIAGNO call; the source-order repair
    # introduces the second, and this test must follow both explicitly.
    # Never pair against a globally nearest hour with coincident observations.
    results=[]
    for hour in range(nh):
        for phase in range(native_per_hour):
            cand=candidates[hour*native_per_hour+phase]
            ref=originals[hour*3+phase]
            results.append({
                "hour_index":hour,
                "phase":"DIAGNO_initial" if phase==0 else "DIAGNO_post_FRADJ",
                "candidate":cand,"original_stage_matched":ref,
                "original_probe_index":hour*3+phase,
                "input_max_abs_difference":max(abs(cand[k]-ref[k]) for k in range(3)),
                "out_delta_K":cand[5]-ref[5],
                "sumwt_delta":cand[3]-ref[3],
                "ztbar_delta":cand[4]-ref[4]})
    by_phase={}
    for phase in ("DIAGNO_initial","DIAGNO_post_FRADJ"):
        subset=[r for r in results if r["phase"]==phase]
        if subset:by_phase[phase]={
            "calls":len(subset),
            "max_input_abs_error":max(x["input_max_abs_difference"] for x in subset),
            "max_temperature_abs_error_K":max(abs(x["out_delta_K"]) for x in subset),
            "max_weight_sum_abs_error":max(abs(x["sumwt_delta"]) for x in subset),
            "strict_1e-4K_exceedances":sum(abs(x["out_delta_K"])>1e-4 for x in subset)}
    report={"status":"FORENSIC_NOT_SCIENCE_PASS","grid_point":[12,19],
            "original_calls":len(originals),"native_calls":len(candidates),
            "native_DIAGNO_calls_per_hour":native_per_hour,
            "by_stage":by_phase,"sequence":results}
    qh_original_pre=[[float(v.replace("D","E")) for v in line.split()]
                     for line in (args.work/"dgm_qh_pre_probe.txt").read_text().splitlines()]
    qh_original_post=[[float(v.replace("D","E")) for v in line.split()]
                      for line in (args.work/"dgm_qh_post_probe.txt").read_text().splitlines()]
    qh_native_pre=[]
    qh_native_post=[]
    for line in (args.work/"cpp_avetmp_probe.log").read_text().splitlines():
        for prefix,dest,expected in (("CTEAS_QH_PRE",qh_native_pre,7),
                                     ("CTEAS_QH_POST",qh_native_post,3)):
            m=re.search(prefix+r"\s+(.+)$",line)
            if m:
                vals=[float(v) for v in m.group(1).split()]
                if len(vals)!=expected:raise ValueError("malformed QH probe")
                dest.append(vals)
    if (len(qh_original_pre)!=nh or len(qh_original_post)!=nh
        or len(qh_native_pre)!=1 or len(qh_native_post)!=1):
        raise RuntimeError("QH real-case 143h probe counts incomplete")
    qh_index=131  # 2022-01-06 12:00 end, 1-based grid (23,29)
    report["QH_ELUSTR_first_divergence"]={
        "hour_end":"2022-01-06_12","grid_point":[23,29],
        "original_before_ELUSTR":qh_original_pre[qh_index],
        "native_before_ELUSTR":qh_native_pre[0],
        "original_after_ELUSTR":qh_original_post[qh_index],
        "native_after_ELUSTR":qh_native_post[0],
        "before_max_abs_by_field":
            [abs(a-b) for a,b in zip(qh_original_pre[qh_index],qh_native_pre[0])],
        "after_abs_by_field":
            [abs(a-b) for a,b in zip(qh_original_post[qh_index],qh_native_post[0])]}
    outfile=args.work/"avetmp_first_divergence.json"
    outfile.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({
        "status":report["status"],"original_calls":len(originals),
        "native_calls":len(candidates),"by_stage":by_phase,
        "Jan1_19_stage_values": [r for r in results if r["hour_index"]==18],
        "QH_ELUSTR_first_divergence":report["QH_ELUSTR_first_divergence"],
        "largest_output_delta":
            sorted(results,key=lambda x:abs(x["out_delta_K"]),reverse=True)[:5]},indent=2))

def main():
    p=argparse.ArgumentParser()
    p.add_argument("mode",choices=("original","cpp","report"))
    p.add_argument("--audit-dir",type=Path)
    p.add_argument("--case",type=Path)
    p.add_argument("--work",type=Path,required=True)
    p.add_argument("--header",type=Path)
    p.add_argument("--main-file",type=Path)
    p.add_argument("--compiler",default="gfortran-11")
    a=p.parse_args()
    a.work.mkdir(parents=True,exist_ok=True)
    if a.mode=="original":original(a)
    elif a.mode=="cpp":cpp(a)
    else:report(a)

if __name__=="__main__":main()
