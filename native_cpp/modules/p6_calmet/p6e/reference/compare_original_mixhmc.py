#!/usr/bin/env python3
"""Unmodified CALMET v6.5.0 MIXHMC original convective height, ILAPSE=2.
160 cases cover collapse, growth, relaxation, top clipping and timestep.
"""
import argparse,hashlib,json,math,subprocess,tempfile
from pathlib import Path
BLOB="437f43bb7f0e51a1919e56664663e1a046986ed0"
CASES=160
ABS=(0.07,0.003,2e-7,0.002,0.002)
REL=0.00008
PARAMS="""      integer mxnx,mxny,io6
      parameter(mxnx=5,mxny=4,io6=6)
"""
DRIVER="""      program mixhmc_original_driver
      include 'params.met'
      include 'ziparm.met'
      include 'gen.met'
      integer cases,c,mode
      real wt,gamma,threshold,zimx,htold,dptt,tht,thtp,zic
      read(*,*)cases
      do c=1,cases
        read(*,*)wt,gamma,threshold,zimx,htold,dptt,
     1       tht,thtp,izicrlx,tzicrlx,dptmin,twodte,
     2       onedte,nsecdt
        zic=-7777.
        call mixhmc(12,1,1,wt,gamma,2,threshold,zimx,
     1              htold,zic,dptt,tht,thtp)
        write(*,'(I6,1X,5(ES23.13E3,1X))')
     1       c,zic,dptt,gamma,tht,thtp
      enddo
      end
      subroutine mixdt2
      stop 77
      end
"""
def run(args,inp=None):
    return subprocess.run([str(x) for x in args],capture_output=True,
                          input=inp,text=True,check=True).stdout
def extract(raw):
    lines=raw.decode("utf-8").splitlines(keepends=True)
    first=[i for i,v in enumerate(lines) if v.lower().startswith("      subroutine mixhmc(")]
    last=[i for i,v in enumerate(lines) if v.lower().startswith("      subroutine openot")]
    if len(first)!=1 or len(last)!=1 or not 150<last[0]-first[0]<240:
        raise RuntimeError("Unmodified MIXHMC bounds changed")
    return "".join(lines[first[0]:last[0]]),[first[0]+1,last[0]]
def fixture():
    wt=(-0.01,0.,0.0003,0.003,0.01,0.05,0.2,0.5)
    gamma=(0.0002,0.0008,0.002,0.01)
    ht=(0.,20.,100.,500.,1000.)
    thresh=(0.,0.01,0.05,0.2)
    dptt=(0.,0.1,0.8,2.)
    rows=[str(CASES)];count={"relax":0,"collapse":0,"growth":0,"no_heat":0}
    for c in range(CASES):
        w=wt[(3*c+c//13)%len(wt)]
        g=gamma[(c//2)%len(gamma)]
        h=ht[(c//3)%len(ht)]
        t=thresh[(c//5)%len(thresh)]
        mode=c%2
        step=(600,1800,3600)[c%3]
        two=2.*step*0.15
        one=step*(1.+0.15)
        zi=850. if c%6==0 else 2500.
        dpt=dptt[(c//7)%len(dptt)]
        wto=t*h/(1.2*996.)
        if w<=0:count["no_heat"]+=1
        elif w-wto<=0:
            count["relax" if mode==1 else "collapse"]+=1
        else:count["growth"]+=1
        rows.append(f"{w} {g} {t} {zi} {h} {dpt} 288.0 289.0 "
                    f"{mode} 800.0 0.001 {two:.6f} {one:.6f} {step}")
    return "\n".join(rows)+"\n",count
def parse(raw):
    result=[]
    for line in raw.splitlines():
        s=line.split()
        if len(s)!=6:raise RuntimeError("MIXHMC original reference schema")
        key=int(s[0]);v=tuple(float(x) for x in s[1:])
        if not all(math.isfinite(x) for x in v):
            raise RuntimeError("Nonfinite MIXHMC source")
        result.append((key,v))
    if len(result)!=CASES:raise RuntimeError("MIXHMC missing comparison data")
    return result
def main():
    p=argparse.ArgumentParser()
    for name in ("vendor","cpp","out"):p.add_argument("--"+name,required=True,type=Path)
    a=p.parse_args()
    raw=a.vendor.read_bytes()
    sha=run(["git","hash-object",a.vendor]).strip()
    if sha!=BLOB:raise RuntimeError("CALMET original source drift")
    original,loc=extract(raw)
    inp,classes=fixture()
    with tempfile.TemporaryDirectory(prefix="cteas-p6e-mixhmc-") as work:
        d=Path(work)
        for name,txt in (("params.met",PARAMS),
                         ("ziparm.met",(a.vendor.parent/"ziparm.met").read_text()),
                         ("gen.met",(a.vendor.parent/"gen.met").read_text()),
                         ("mixhmc_original.for",original),("driver.for",DRIVER)):
            (d/name).write_text(txt)
        run(["gfortran","-O0","-std=legacy","-fno-automatic",
             "-ffixed-line-length-none","-I"+str(d),
             d/"mixhmc_original.for",d/"driver.for","-o",d/"original"])
        original_rows=parse(run([d/"original"],inp))
    cpp_rows=parse(run([a.cpp],inp))
    largest=[0.,0.,0.,0.,0.];first=[];bad=0
    for (case,f),(c,v) in zip(original_rows,cpp_rows):
        if case!=c:raise RuntimeError("MIXHMC shuffled cases")
        for field,(orig,candidate) in enumerate(zip(f,v)):
            delta=abs(orig-candidate)
            largest[field]=max(largest[field],delta)
            if delta>ABS[field]+REL*abs(orig):
                bad+=1
                if len(first)<20:first.append({"case":case,"field":field,
                            "original":orig,"cpp":candidate,"error":delta})
    report={"status":"PASS" if bad==0 else "FAIL","cases":CASES,
            "scalar_comparisons":CASES*5,
            "condition_distribution":classes,
            "max_abs_differences_ZIC_DPTT_GAMMA_THT_THTP":largest,
            "frozen_abs_limits":ABS,"frozen_relative_limit":REL,
            "exceedances":bad,"first_mismatches":first,
            "original_blob":sha,"vendor_sha256":hashlib.sha256(raw).hexdigest(),
            "unmodified_source_lines":loc,
            "scope":"MIXHMC ILAPSE=2 using provided lapse, not full MIXHT/MIXDT or 2022 COMP"}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    if bad:raise SystemExit(1)
if __name__=="__main__":main()
