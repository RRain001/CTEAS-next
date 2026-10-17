#!/usr/bin/env python3
"""G25A literal original CALMET ELUSTR2 (QH, USTAR, EL) with actual G23
source-file station flux inputs; one selected 2SS+2US synthetic-weather hour.

Actual unchanged vendor ELUSTR2 and PSIUD calculate fluxes.  MIXHTST and
SIMILT hooks are isolated with NO-OP capture stubs and are deliberately NOT
claimed to have passed original Fortran validation.  No 17-stage CALMET,
COMP/P6F or full 45-field multistation original parity.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import subprocess
import tempfile
from pathlib import Path

from compare_original_similt_profile import original_sources, VENDOR_BLOB

ROOT = Path(__file__).resolve().parents[4]
VENDOR = ROOT / "engine/vendor/src/CALMET_v6.5.0_L150223"
# Explicit conservative G25A stage-only gates. These are NOT a frozen
# original multi-site 45-field acceptance threshold.
TOL_USTAR_MPS = 2e-4
TOL_QH_WM2 = 0.01
TOL_EL_M = 0.05

DRIVER = """      program g25_vendor_elustr2
      include 'params.met'
      include 'hflux.met'
      include 'ziparm.met'
      include 'grid.met'
      include 'geo.met'
      real us(mxnz,mxwnd),vs(mxnz,mxwnd)
      real zi(mxnx,mxny),ziconv(mxnx,mxny)
      real ccgrid(mxnx,mxny)
      integer icc(mxss)
      real u0,v0,zm,zzanem,rough,sun,temp,rho
      real alb,bow,hg,qflux
      real qhprobe,ustarprobe,elprobe
      common /g25capture/ qhprobe,ustarprobe,elprobe
      common /salp/ ihr2gmt,sinalp2(mxnx,mxny)
      character*256 input,output
      call get_command_argument(1,input)
      call get_command_argument(2,output)
      open(10,file=trim(input),status='old')
      read(10,*) u0,v0,zm,zzanem,rough,sun,temp,rho,
     1 icc0,ha1,ha2,hb1,hb2,hc1,hc2,hc3p1,
     2 alb,bow,hg,qflux
      close(10)
      if(zzanem.le.rough.or.zm.le.rough)stop 92
      nx=12
      ny=12
      nz=9
      nzp1=10
      nssta=2
      zmid(1)=zm
      z0(1,1)=rough
      albedo(1,1)=alb
      bowen(1,1)=bow
      hcg(1,1)=hg
      qf(1,1)=qflux
      sinalp2(1,1)=sun
      icc(1)=icc0
      zi(1,1)=100.
      ziconv(1,1)=0.
      nearu(1,1)=1
      imixh=1
      ihr2gmt=2
      us(1,1)=u0
      vs(1,1)=v0
      qhprobe=1.234567e25
      ustarprobe=1.234567e25
      elprobe=1.234567e25
      call elustr2(ziconv,us,vs,1,zzanem,1,1,icc,-1,
     1 0,0,ccgrid,zi,temp,rho,0)
      open(11,file=trim(output),status='replace')
      write(11,'(3ES22.13E3)')qhprobe,ustarprobe,elprobe
      close(11)
      end
c --- Isolated future vendor MIXHTST: capture actual upstream ELUSTR2
c --- inputs WITHOUT asserting source MIXHTST has been validated.
      subroutine mixhtst(el,ustar,qh,rho,ihrgmt,ist,jst,nearus,
     1 iupt,ilandu,iwat1,iwat2,imixh,zi,ziconv)
      real el,ustar,qh,rho,zi,ziconv
      real qhprobe,ustarprobe,elprobe
      common /g25capture/ qhprobe,ustarprobe,elprobe
      qhprobe=qh
      ustarprobe=ustar
      elprobe=el
      end
c --- Original ITPROG=0 chooses MIXHTST, never the prognostic
c --- ITPROG=2 MIXHT2ST branch. Provide a hard-stop linker stub.
      subroutine mixht2st(el,ustar,qh,rho,ihrgmt,ist,jst,
     1 ilandu,iwat1,iwat2,imixh,zi,ziconv)
      real el,ustar,qh,rho,zi,ziconv
      stop 98
      end
c --- Terminal SIMILT is a separate independently verified G23 kernel.
      subroutine similt(zzanem,el,z0,zi,ns,ipsifcn,us,vs,zimin)
      real zzanem,el,z0,zi,zimin,us(*),vs(*)
      end
c --- Only IPSIFCN=0 from original ICOARE>0 READCF is scoped.
      real function psiuc(z,l,m)
      real z,l
      stop 99
      end
"""

def literal_sources(root: Path):
    vendor = VENDOR / "calmet.for"
    data=vendor.read_bytes()
    fingerprint=hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()
    if fingerprint!=VENDOR_BLOB:
        raise RuntimeError("G25A source original CALMET blob changed")
    lines=data.decode().splitlines(keepends=True)
    starts=lambda n:[i for i,v in enumerate(lines)
                       if v.lower().startswith(f"      subroutine {n}(")]
    a=starts("elustr2")
    b=starts("esat")  # ESAT is FUNCTION, not SUBROUTINE.
    if len(a)!=1:
        raise RuntimeError("G25A literal ELUSTR2 source not unique")
    next_name=[i for i,v in enumerate(lines)
               if v.lower().startswith("      function esat(")]
    if len(next_name)!=1 or a[0]+1!=6580 or next_name[0]+1!=6898:
        raise RuntimeError("G25A ELUSTR2 source function boundary drift")
    el=root/"vendor_elustr2.for"
    el.write_text("".join(lines[a[0]:next_name[0]]))
    _,psiud=original_sources(VENDOR,root)
    return [el,psiud["file"]],{
        "original_vendor_blob":fingerprint,
        "elustr2_lines":[a[0]+1,next_name[0]],
        "elustr2_sha256":hashlib.sha256(el.read_bytes()).hexdigest(),
        "psiud_sha256":psiud["sha256"],
    }


def one_input(path: Path)->dict:
    vals=path.read_text().split()
    if len(vals)!=20:
        raise ValueError(f"G25A station original source input 20 scalars required: {path}")
    cloud=int(vals[8])
    values=[float(v) for v in vals]
    if any(not math.isfinite(v) for v in values) or cloud<0 or cloud>10:
        raise ValueError("G25A original station input nonfinite/NWS cloud missing")
    if values[0]**2+values[1]**2<1e-6 or values[2]<=values[4] or (
        values[3]<=values[4] or values[6]<=0 or values[7]<=0 or
        values[15]<=0
    ):
        raise ValueError("G25A actual station physical source not validated")
    return {"u0":values[0],"v0":values[1],"sun":values[5],
            "temperature_k":values[6],"cloud_tenths":cloud}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source-prefix",type=Path,required=True)
    parser.add_argument("--mode",choices=("Debug","Release"),required=True)
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--require-branch",choices=("night","day"),required=True)
    args=parser.parse_args()
    original_inputs=[
        one_input(Path(str(args.source_prefix)+f".s{i}.input")) for i in (1,2)]
    with Path(str(args.source_prefix)+".native.csv").open(newline="") as file:
        cpp=list(csv.DictReader(file))
    if len(cpp)!=2 or any(int(cpp[k]["surface_ordinal"])!=k+1 for k in (0,1)):
        raise ValueError("G25A selected station identity/order differs from G23")
    with tempfile.TemporaryDirectory(prefix="g25a-original-elustr2-") as tmp:
        root=Path(tmp)
        chunks,provenance=literal_sources(root)
        driver=root/"g25_vendor_driver.for"
        driver.write_text(DRIVER)
        exe=root/"original_g25_elustr2"
        opt="-O0" if args.mode=="Debug" else "-O2"
        p=subprocess.run(
            ["gfortran",opt,"-std=legacy","-fno-automatic",
             "-ffixed-line-length-none","-fallow-argument-mismatch",
             "-I"+str(VENDOR),*[str(x) for x in chunks],str(driver),
             "-o",str(exe)],
            capture_output=True,text=True,
        )
        if p.returncode:
            raise RuntimeError(
                "G25A original ELUSTR2 compile error: "+p.stderr[-4500:])
        errors=[];max_abs={k:0. for k in ("sensible_wm2",
                                           "friction_velocity_mps",
                                           "monin_obukhov_m")}
        branches=[]
        for i in (1,2):
            inp=Path(str(args.source_prefix)+f".s{i}.input")
            target=root/f"station{i}.ref"
            run=subprocess.run([str(exe),str(inp),str(target)],
                               capture_output=True,text=True)
            if run.returncode:
                raise RuntimeError(
                    f"G25A literal vendor ELUSTR2 station{i} failed: "+
                    run.stderr[-1200:]+run.stdout[-1200:])
            result=[float(x) for x in target.read_text().split()]
            if len(result)!=3 or not all(map(math.isfinite,result)):
                raise RuntimeError("G25A original vendor QH/USTAR/EL not captured")
            branches.append("night" if result[0]<0 else "day")
            for key,reference,tolerance in zip(
                    ("sensible_wm2","friction_velocity_mps",
                     "monin_obukhov_m"),result,
                    (TOL_QH_WM2,TOL_USTAR_MPS,TOL_EL_M)):
                actual=float(cpp[i-1][key])
                diff=abs(reference-actual)
                max_abs[key]=max(max_abs[key],diff)
                if diff>tolerance:
                    errors.append([i,key,reference,actual,diff,tolerance])
    if any(v!=args.require_branch for v in branches):
        raise AssertionError("G25A source branch differs from required original "+
                             args.require_branch+": "+str(branches))
    evidence={
        "scope":"literal source ELUSTR2 station QH USTAR EL only",
        "input":"G19 2SS+2US file-driven G23 observed synthetic first-hour station",
        "upstream_readcf_and_source_stage":original_inputs,
        "mode":args.mode,"stations":2,"comparisons":6,
        "predeclared_required_heat_branch":args.require_branch,
        "source_provenance":provenance,"heat_flux_sign":branches,
        "max_abs":max_abs,
        "tolerance":{"sensible_wm2":TOL_QH_WM2,
                     "friction_velocity_mps":TOL_USTAR_MPS,
                     "monin_obukhov_m":TOL_EL_M},
        "errors":errors,
        "original_vendor_mixhtst":False,
        "original_vendor_full_stheor":False,
        "full_multistation_45_field":False,
    }
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(evidence,indent=2)+"\n")
    if errors:
        raise AssertionError(
            "G25A literal vendor original station flux parity failed "+str(errors))
    print(
        "PASS_P6G_G25A_LITERAL_ORIGINAL_ELUSTR2 "
        f"mode={args.mode} stations=2 values=6 branches={branches} "
        f"max_abs={max_abs} ORIGINAL_VENDOR_MIXHTST=NOT_VALIDATED"
    )

if __name__=="__main__":
    main()
