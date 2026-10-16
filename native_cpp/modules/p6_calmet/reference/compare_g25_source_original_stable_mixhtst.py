#!/usr/bin/env python3
"""G25B literal untouched CALMET MIXHTST L10684-10935 STABLE QH<0 branch.

Real G23 source-file 2SS+2US station ELUSTR2 QH/U*/L and original previous
COMP ZI/ZICONV/DPTT state; original Fortran computes stable MIXHTST ZI,
ZICONV/DPTT. Daytime MIXDT/MIXHMC/MIXHBG are deliberately hard-fail stubs,
not passed: daytime MIXHTST independent parity remains not accepted.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,subprocess,tempfile
from pathlib import Path
from compare_original_similt_profile import VENDOR_BLOB

ROOT=Path(__file__).resolve().parents[4]
VENDOR=ROOT/"engine/vendor/src/CALMET_v6.5.0_L150223"
# Selected physical mix-height/memory tolerance, not multistation 45 fields.
TOL_ZI_M=0.01
TOL_ZICONV_M=0.01
TOL_DPTT_K=0.0001

DRIVER="""      program g25_stable_mixhtst
      include 'params.met'
      include 'grid.met'
      include 'ziparm.met'
      include 'outpt.met'
      common /tjump/ dptt(mxnx,mxny)
      real qh,ustar,el,rho,prevjump,f,c,zi,ziconv
      integer land,iw1,iw2,imethod
      character*256 input,output
      call get_command_argument(1,input)
      call get_command_argument(2,output)
      open(10,file=trim(input),status='old')
      read(10,*)qh,ustar,el,rho,zi,ziconv,prevjump,
     1 f,c,zimin,zimax,constn,land,iw1,iw2,imethod
      close(10)
      if(qh.ge.0..or.ustar.le.0..or.el.le.0.)stop 95
      if(f.le.0..or.c.le.0..or.zimin.le.0.)stop 96
      if(land.ge.iw1.and.land.le.iw2)stop 97
      nx=12
      ny=12
      nz=9
      fcori(1,1)=f
      cmech(1,1)=c
      dptt(1,1)=prevjump
      ldbhr=.false.
      call mixhtst(el,ustar,qh,rho,2,1,1,1,-1,
     1 land,iw1,iw2,imethod,zi,ziconv)
      open(11,file=trim(output),status='replace')
      write(11,'(3ES22.13E3)')zi,ziconv,dptt(1,1)
      close(11)
      end
c --- The following original MIXHTST day functions MUST NOT run here.
      subroutine mixdt
      stop 96
      end
      subroutine mixhmc
      stop 96
      end
      subroutine mixhbg
      stop 96
      end
      subroutine out
      stop 96
      end
"""

def vendor_source(out:Path)->tuple[Path,dict]:
    source=VENDOR/"calmet.for"
    data=source.read_bytes()
    sha=hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()
    if sha!=VENDOR_BLOB:
        raise RuntimeError("G25B original CALMET vendor source drift")
    lines=data.decode().splitlines(keepends=True)
    ix=[i for i,v in enumerate(lines)
        if v.lower().startswith("      subroutine mixhtst(")]
    end=[i for i,v in enumerate(lines)
         if v.lower().startswith("      subroutine mixht2(")]
    if len(ix)!=1 or len(end)!=1 or ix[0]+1!=10684 or end[0]+1!=10937:
        raise RuntimeError("G25B original MIXHTST source boundary drift")
    extracted=out/"original_mixhtst.for"
    extracted.write_text("".join(lines[ix[0]:end[0]]))
    return extracted,{
        "vendor_blob":sha,"source_lines":[ix[0]+1,end[0]],
        "routine_sha256":hashlib.sha256(extracted.read_bytes()).hexdigest(),
    }

def source_input(p:Path)->dict:
    values=p.read_text().split()
    if len(values)!=16:
        raise ValueError("G25B original source MIXHTST requires 16 controls")
    pars=[float(x) for x in values]
    if not all(map(math.isfinite,pars)):
        raise ValueError("G25B MIXHTST input nonfinite")
    if not(pars[0]<0 and pars[1]>0 and pars[2]>0 and pars[3]>0 and
           pars[7]>0 and pars[8]>0 and pars[9]>0 and
           pars[12]<pars[13] and not pars[13]<=pars[12]<=pars[14] and
           int(pars[15])==1):
        raise ValueError("G25B original stable mixing source scope not proven")
    return {"qh_wm2":pars[0],"ustar_mps":pars[1],
            "monin_obukhov_m":pars[2],"previous_comp_zi":pars[4],
            "previous_comp_ziconv":pars[5],"previous_comp_dptt":pars[6]}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--mode",choices=("Debug","Release"),required=True)
    parser.add_argument("--source-prefix",required=True,type=Path)
    parser.add_argument("--out",required=True,type=Path)
    a=parser.parse_args()
    cases=[source_input(Path(str(a.source_prefix)+f".mixht.s{i}.input"))
           for i in (1,2)]
    with Path(str(a.source_prefix)+".mixht.native.csv").open(newline="") as f:
        modern=list(csv.DictReader(f))
    if len(modern)!=2 or any(
        int(modern[i]["surface_ordinal"])!=i+1 for i in range(2)):
        raise ValueError("G25B source station identities reordered")
    with tempfile.TemporaryDirectory(prefix="g25-stable-mixhtst-") as folder:
        out=Path(folder)
        routine,meta=vendor_source(out)
        driver=out/"g25_stable_driver.for"
        driver.write_text(DRIVER)
        exe=out/"g25_original_mixhtst"
        opt="-O0" if a.mode=="Debug" else "-O2"
        p=subprocess.run([
            "gfortran",opt,"-std=legacy","-fno-automatic",
            "-ffixed-line-length-none","-fallow-argument-mismatch",
            "-I"+str(VENDOR),str(routine),str(driver),"-o",str(exe)
        ],capture_output=True,text=True)
        if p.returncode:
            raise RuntimeError("G25B original MIXHTST compile: "+p.stderr[-3500:])
        errors=[];maxima={"zi_m":0.,"ziconv_m":0.,"dptt_k":0.}
        for i in (1,2):
            target=out/f"s{i}.vendor"
            p=subprocess.run([
                str(exe),str(a.source_prefix)+f".mixht.s{i}.input",str(target)
            ],capture_output=True,text=True)
            if p.returncode:
                raise RuntimeError(
                    f"G25B original stable MIXHTST s{i} invalid "
                    +p.stderr[-1200:]+p.stdout[-1200:])
            vals=[float(v) for v in target.read_text().split()]
            if len(vals)!=3 or not all(map(math.isfinite,vals)):
                raise ValueError("G25B original MIXHTST output incomplete")
            for k,original,tol in zip(
                ("zi_m","ziconv_m","dptt_k"),vals,
                (TOL_ZI_M,TOL_ZICONV_M,TOL_DPTT_K)):
                actual=float(modern[i-1][k])
                delta=abs(original-actual)
                maxima[k]=max(maxima[k],delta)
                if delta>tol:
                    errors.append([i,k,original,actual,delta,tol])
    report={
        "scope":"literal original MIXHTST stable branch on source G23 previous COMP grid state",
        "input":"synthetic observations in original-format 2SS+2US",
        "mode":a.mode,"sites":2,"numeric_fields":6,
        "source_routine":meta,"inputs":cases,"max_abs":maxima,
        "tolerance":{"zi_m":TOL_ZI_M,"ziconv_m":TOL_ZICONV_M,
                     "dptt_k":TOL_DPTT_K},
        "errors":errors,
        "daytime_original_mixhtst_pass":False,
        "multi_hour_comp_state_accepted":False,
        "full_multistation_45_field":False,
    }
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2)+"\n")
    if errors:
        raise AssertionError("G25B original stable MIXHTST numeric mismatch "+str(errors))
    print(f"PASS_P6G_G25B_LITERAL_ORIGINAL_STABLE_MIXHTST "
          f"mode={a.mode} sites=2 values=6 max_abs={maxima} "
          "DAYTIME_MIXHTST=NOT_ACCEPTED "
          "G14_MULTI_HOUR_STATE=NOT_ACCEPTED")

if __name__=="__main__":
    main()
