#!/usr/bin/env python3
"""G25C source 2SS+2US daytime original MIXHTST + MIXDT + MIXHMC parity.

Uses original hourly first G14 file-backed SURF station ELUSTR2 QH/U*/EL,
previous immutable COMP ZI/ZICONV/DPTT and ORIGINAL older UP sounding
selected per station (not synthesized profiles). Literal unchanged vendor
MIXHTST/MIXDT/MIXHMC are executed; MIXHBG (IMIXH=2), MIXDT2 prognostic
branch and OUT debug are hard-stop stubs.  No native multistation 17-stage
hour committed. No source-vendor full 45-field hour acceptance.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,subprocess,tempfile
from pathlib import Path
from compare_original_similt_profile import VENDOR_BLOB

ROOT=Path(__file__).resolve().parents[4]
VENDOR=ROOT/"engine/vendor/src/CALMET_v6.5.0_L150223"
TOL_ZI_M=0.01
TOL_ZICONV_M=0.01
TOL_DPTT_K=0.0001

DRIVER="""      program g25_daytime_mixhtst
      include 'params.met'
      include 'grid.met'
      include 'ziparm.met'
      include 'upmet.met'
      include 'gen.met'
      include 'outpt.met'
      common /tjump/ dptt(mxnx,mxny)
      real qh,ustar,el,rho,oldjump,f,c,zi,ziconv
      integer land,iw1,iw2,imethod,nlev,k
      character*256 input,output
      call get_command_argument(1,input)
      call get_command_argument(2,output)
      open(10,file=trim(input),status='old')
      read(10,*)qh,ustar,el,rho,zi,ziconv,oldjump,
     1 f,c,zimin,zimax,constn,land,iw1,iw2,imethod,
     2 dptmin,dzzi,threshl,onedte,twodte,tzicrlx,izicrlx
      read(10,*)nlev
      if(nlev.lt.2.or.nlev.gt.mxlev)stop 92
      do k=1,nlev
        read(10,*)zlaa(1,k),tzaa(1,k)
      enddo
      close(10)
      if(qh.le.0..or.ustar.le.0..or.el.ge.0.)stop 95
      if(f.le.0..or.c.le.0..or.zimin.le.0.)stop 96
      if(land.ge.iw1.and.land.le.iw2)stop 97
      if(imethod.ne.1)stop 98
      nx=12
      ny=12
      nz=9
      fcori(1,1)=f
      cmech(1,1)=c
      dptt(1,1)=oldjump
      ldbhr=.false.
      nsecdt=3600
      justa(1)=1
      nlaa(1)=nlev
      nlbb(1)=0
      call mixhtst(el,ustar,qh,rho,2,1,1,1,-1,
     1 land,iw1,iw2,imethod,zi,ziconv)
      open(11,file=trim(output),status='replace')
      write(11,'(3ES22.13E3)')zi,ziconv,dptt(1,1)
      close(11)
      end
c --- Only source IMIXH=1 / IUPT=-1 and observed MIXDT is validated.
      subroutine mixhbg
      stop 98
      end
      subroutine mixdt2
      stop 98
      end
      subroutine out
      stop 98
      end
"""


def vendor_sources(out:Path):
    data=(VENDOR/"calmet.for").read_bytes()
    sha=hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()
    if sha!=VENDOR_BLOB:
        raise RuntimeError("G25C original CALMET source blob drift")
    lines=data.decode().splitlines(keepends=True)
    blocks=[
        ("mixhtst","      subroutine mixhtst(","      subroutine mixht2(",10684,10937),
        ("mixdt","      subroutine mixdt(","      subroutine mixdt2(",10005,10203),
        ("mixhmc","      subroutine mixhmc(","      subroutine openot",11558,11746),
    ]
    files=[];proof={}
    for name,start,end,expected_start,expected_end in blocks:
        ix=[i for i,v in enumerate(lines) if v.lower().startswith(start)]
        ex=[i for i,v in enumerate(lines) if v.lower().startswith(end)]
        if len(ix)!=1 or len(ex)!=1 or (
            ix[0]+1!=expected_start or ex[0]+1!=expected_end or ex[0]<=ix[0]
        ):
            raise RuntimeError(f"G25C literal Fortran {name} anchor drift")
        file=out/f"original_{name}.for"
        file.write_text("".join(lines[ix[0]:ex[0]]))
        proof[name]={"lines":[ix[0]+1,ex[0]],
                     "sha256":hashlib.sha256(file.read_bytes()).hexdigest()}
        files.append(file)
    return files,{"original_vendor_blob":sha,"extracted":proof}


def source_input(p:Path)->dict:
    lines=p.read_text().splitlines()
    if len(lines)<4:
        raise ValueError("G25C original UP sounding missing")
    scalars=lines[0].split()
    if len(scalars)!=23:
        raise ValueError("G25C source MIXHTST day controls not 23 fields")
    xs=[float(v) for v in scalars]
    nlev=int(lines[1].strip())
    if len(lines)!=nlev+2 or nlev<2 or nlev>80 or not all(map(math.isfinite,xs)):
        raise ValueError("G25C missing selected source older UP sounding")
    if not(xs[0]>0 and xs[1]>0 and xs[2]<0 and xs[3]>0 and
           xs[7]>0 and xs[8]>0 and xs[9]>0 and xs[12]<xs[13] and
           int(xs[15])==1 and int(xs[22])==1):
        raise ValueError("G25C source daytime MC overland not supported")
    records=[]
    for line in lines[2:]:
        values=[float(v) for v in line.split()]
        if len(values)!=2 or not all(map(math.isfinite,values)):
            raise ValueError("G25C original UP height-temperature record invalid")
        records.append(values)
    if any(b[0]<=a[0] for a,b in zip(records,records[1:])):
        raise ValueError("G25C physical UP sounding vertical ordering invalid")
    return {"qh_wm2":xs[0],"previous_zi_m":xs[4],
            "previous_ziconv_m":xs[5],"previous_dptt_k":xs[6],
            "upper_sounding_levels":nlev}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--mode",choices=("Debug","Release"),required=True)
    parser.add_argument("--source-prefix",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    cases=[source_input(Path(str(args.source_prefix)+f".mixht.day.s{i}.input"))
           for i in (1,2)]
    with Path(str(args.source_prefix)+".mixht.native.csv").open(newline="") as handle:
        cpp=list(csv.DictReader(handle))
    if len(cpp)!=2 or any(int(cpp[i]["surface_ordinal"])!=i+1 for i in (0,1)):
        raise ValueError("G25C source surface station identity changed")
    with tempfile.TemporaryDirectory(prefix="g25-original-day-mixht-") as temp:
        root=Path(temp)
        sources,evidence=vendor_sources(root)
        driver=root/"daytime_mixht_driver.for"
        driver.write_text(DRIVER)
        exe=root/"g25_daytime_vendor"
        opt="-O0" if args.mode=="Debug" else "-O2"
        compile=subprocess.run([
            "gfortran",opt,"-std=legacy","-fno-automatic",
            "-ffixed-line-length-none","-fallow-argument-mismatch",
            "-I"+str(VENDOR),*[str(s) for s in sources],str(driver),"-o",str(exe)
        ],capture_output=True,text=True)
        if compile.returncode:
            raise RuntimeError("G25C original MIXHTST/MIXDT/MIXHMC compile: "+
                               compile.stderr[-4200:])
        failures=[];maxima={"zi_m":0.,"ziconv_m":0.,"dptt_k":0.}
        for n in (1,2):
            out=root/f"station{n}.vendor"
            proc=subprocess.run([str(exe),str(args.source_prefix)+
                                 f".mixht.day.s{n}.input",str(out)],
                                capture_output=True,text=True)
            if proc.returncode or not out.exists():
                raise RuntimeError(
                    f"G25C original Fortran day MIXHTST station{n} failed "
                    f"rc={proc.returncode}: "+proc.stderr[-1300:]+proc.stdout[-1300:])
            results=[float(v) for v in out.read_text().split()]
            if len(results)!=3 or not all(map(math.isfinite,results)):
                raise ValueError("G25C original MIXHTST day results incomplete")
            for k,ref,tol in zip(("zi_m","ziconv_m","dptt_k"),results,
                                 (TOL_ZI_M,TOL_ZICONV_M,TOL_DPTT_K)):
                val=float(cpp[n-1][k])
                delta=abs(val-ref)
                maxima[k]=max(maxima[k],delta)
                if delta>tol:
                    failures.append([n,k,ref,val,delta,tol])
    record={
        "scope":"Literal original MIXHTST MIXDT MIXHMC from source older UP and prev COMP",
        "input_type":"synthetic observation data in original-format 2SS+2US source",
        "mode":args.mode,"stations":2,"comparisons":6,
        "provenance":evidence,"station_inputs":cases,
        "max_abs":maxima,
        "tolerance":{"zi_m":TOL_ZI_M,"ziconv_m":TOL_ZICONV_M,
                     "dptt_k":TOL_DPTT_K},
        "mismatches":failures,
        "full_stheor_original_hour_accepted":False,
        "original_multistation_45fields":False,
    }
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(record,indent=2)+"\n")
    if failures:
        raise AssertionError("G25C full original daytime MIXHTST mismatch "+str(failures))
    print(
        f"PASS_P6G_G25C_LITERAL_ORIGINAL_DAY_MIXHTST mode={args.mode} "
        f"stations=2 values=6 max_abs={maxima} "
        "FULL_MULTISTATION_45_FIELD=NOT_ACCEPTED"
    )


if __name__=="__main__":
    main()
