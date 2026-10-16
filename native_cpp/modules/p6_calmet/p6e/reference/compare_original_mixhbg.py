#!/usr/bin/env python3
"""Unmodified CALMET v6.5.0 MIXHBG (Batchvarova-Gryning) convective height.

The comparator compiles the verbatim MIXHBG subroutine plus its FBG helper
extracted from the pinned vendor calmet.for, together with the original
ZIPARM/GEN COMMON includes, and compares both exported fields (ZICBG and the
floored lapse rate GAMMA) against the independent C++20 kernel.

Only the ILAPSE=2 entry point is exercised (lapse passed in). MIXDT2, used by
the ILAPSE=1 MM5 path, is a fail-stop stub: reaching it aborts the driver.

Frozen limits: 0.07 m / 8e-5 relative for the convective height, 2e-7 K/m
/ 8e-5 relative for the lapse rate.
"""
import argparse,hashlib,json,math,subprocess,tempfile
from pathlib import Path
BLOB="437f43bb7f0e51a1919e56664663e1a046986ed0"
CASES=240
ABS=(0.07,2e-7)
REL=0.00008
MIN_CLASS={"collapse":20,"keep_previous":5,"relax":10,"growth":20,
           "deep_limit":20}
# (WT, GAMMA, THRESH, EL, ZICBGOLD, USTAR, TK, IZICRLX, TZICRLX, NSECDT)
EDGE=((0.0,0.002,0.0,-100.0,300.0,0.2,290.0,0,800.0,3600),
      (0.0,0.002,0.0,-100.0,0.0,0.2,290.0,0,800.0,1800),
      (0.0,0.002,0.01,-80.0,500.0,0.3,292.0,1,1200.0,3600),
      (0.0005,0.002,0.05,-60.0,900.0,0.4,300.0,1,900.0,1800),
      (0.05,0.01,0.0,-250.0,100.0,0.5,300.0,0,800.0,600),
      (0.001,0.0005,0.0,-20.0,200.0,0.1,295.0,0,800.0,1800),
      (0.02,0.002,0.2,-400.0,1500.0,0.8,305.0,0,800.0,3600),
      (0.005,0.001,0.0,30.0,400.0,0.2,290.0,1,800.0,3600))
PARAMS="""      integer mxnx,mxny,io6
      parameter(mxnx=5,mxny=4,io6=6)
"""
DRIVER="""      program mixhbg_original_driver
      include 'params.met'
      include 'ziparm.met'
      include 'gen.met'
      integer cases,c,imode,istep
      real wt,gamma,threshold,zimx,zimn,ustar,el,zicbgold,zicbg
      real tk,tzrlx,dpmin,tht,thtp
      read(*,*)cases
      do c=1,cases
        read(*,*)wt,gamma,threshold,zimx,zimn,ustar,el,zicbgold,
     1       tk,imode,tzrlx,dpmin,istep
        izicrlx=imode
        tzicrlx=tzrlx
        dptmin=dpmin
        zimin=zimn
        nsecdt=istep
        zicbg=-7777.
        tht=0.
        thtp=0.
        call mixhbg(12.,1,1,wt,gamma,tk,2,threshold,zimx,zimn,
     1              ustar,el,zicbgold,zicbg,tht,thtp)
        write(*,'(I6,1X,2(ES23.13E3,1X))') c,zicbg,gamma
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
    first=[i for i,v in enumerate(lines)
           if v.lower().startswith("      subroutine mixhbg (")]
    last=[i for i,v in enumerate(lines)
          if v.lower().startswith("      subroutine mixhmc(")]
    if len(first)!=1 or len(last)!=1 or not 200<last[0]-first[0]<320:
        raise RuntimeError("Unmodified MIXHBG bounds changed")
    return "".join(lines[first[0]:last[0]]),[first[0]+1,last[0]]
def classify(w,gamma,threshold,zimx,zimn,ustar,el,old,tk,mode,tz,step):
    h0=max(old,zimn)
    wto=threshold*h0/(1.2*1005.)
    wptp=w-wto
    if mode==0:
        if el>0 or wptp<0:label="collapse"
        elif wptp==0:label="keep_previous"
        else:label="growth"
    else:
        if el>0 or w<0:label="collapse"
        elif wptp<=0:label="relax"
        else:label="growth"
    return label,(label=="growth" and el<=-500.)
def fixture():
    wt=(-0.01,0.0,0.0005,0.002,0.005,0.02,0.05,0.08)
    gamma=(0.0005,0.001,0.002,0.005,0.01)
    thresh=(0.0,0.005,0.02,0.1)
    elv=(-300.0,-120.0,-40.0,-5.0,25.0)
    old=(0.0,60.0,250.0,900.0)
    zmin=(0.0,50.0)
    usta=(0.05,0.25,0.6)
    tks=(288.0,302.0)
    tzr=(600.0,1500.0)
    step=(600,1800,3600)
    rows=[];classes={k:0 for k in MIN_CLASS};deep=0
    deep_n=48
    general=CASES-deep_n-len(EDGE)
    for c in range(general):
        w=wt[(3*c+c//11)%len(wt)]
        g=gamma[(c//2)%len(gamma)]
        t=thresh[(c//3)%len(thresh)]
        e=elv[(c//4)%len(elv)]
        o=old[(c//5)%len(old)]
        zm=zmin[(c//6)%len(zmin)]
        u=usta[(c//7)%len(usta)]
        tk=tks[(c//8)%len(tks)]
        mode=c%2
        tz=tzr[(c//9)%len(tzr)]
        st=step[c%3]
        if mode==1 and w<=0.0 and t==0.0:t=0.005
        label,isdeep=classify(w,g,t,2500.0,zm,u,e,o,tk,mode,tz,st)
        if isdeep:raise RuntimeError("general set reached the deep limit")
        classes[label]+=1
        rows.append(f"{w} {g} {t} 2500.0 {zm} {u} {e} {o} {tk} "
                    f"{mode} {tz} 0.001 {st}")
    for w,g,t,e,o,u,tk,mode,tz,st in EDGE:
        zm=50.0 if o>0.0 else 0.0
        label,isdeep=classify(w,g,t,2500.0,zm,u,e,o,tk,mode,tz,st)
        if isdeep:raise RuntimeError("edge set reached the deep limit")
        classes[label]+=1
        rows.append(f"{w} {g} {t} 2500.0 {zm} {u} {e} {o} {tk} "
                    f"{mode} {tz} 0.001 {st}")
    deepv=((0.001,0.005,-520.0,700.0,600),
           (0.004,0.01,-700.0,1200.0,1800),
           (0.02,0.005,-1000.0,1800.0,1800),
           (0.001,0.01,-500.0,900.0,3600),
           (0.008,0.005,-900.0,1500.0,600),
           (0.003,0.005,-600.0,1000.0,1800))
    for i in range(deep_n):
        w,g,e,o,st=deepv[i%len(deepv)]
        mode=i%2
        zmin_=50.0*(i%2)
        a=(w-0.0)/g
        if o**3-6.0*a*e*st<=0.0:
            raise RuntimeError("deep limit fixture would be nonfinite")
        label,isdeep=classify(w,g,0.0,2500.0,zmin_,0.2,e,o,300.0,mode,800.0,st)
        if label!="growth" or not isdeep:
            raise RuntimeError("deep limit fixture not in growth branch")
        classes[label]+=1;deep+=1
        rows.append(f"{w} {g} 0.0 2500.0 {zmin_} 0.2 {e} {o} 300.0 "
                    f"{mode} 800.0 0.001 {st}")
    classes["deep_limit"]=deep
    for name,minimum in MIN_CLASS.items():
        got=classes[name]
        if got<minimum:
            raise RuntimeError(f"coverage too small for {name}: {got}")
    return str(CASES)+"\n"+"\n".join(rows)+"\n",classes,deep
def parse(raw):
    result=[]
    for line in raw.splitlines():
        s=line.split()
        if len(s)!=3:raise RuntimeError("MIXHBG original reference schema")
        key=int(s[0]);v=tuple(float(x) for x in s[1:])
        if not all(math.isfinite(x) for x in v):
            raise RuntimeError("Nonfinite MIXHBG source value")
        result.append((key,v))
    if len(result)!=CASES:raise RuntimeError("MIXHBG missing comparison data")
    return result
def main():
    p=argparse.ArgumentParser()
    for name in ("vendor","cpp","out"):p.add_argument("--"+name,required=True,type=Path)
    a=p.parse_args()
    raw=a.vendor.read_bytes()
    sha=run(["git","hash-object",a.vendor]).strip()
    if sha!=BLOB:raise RuntimeError("CALMET original source drift")
    original,loc=extract(raw)
    inp,classes,deep=fixture()
    with tempfile.TemporaryDirectory(prefix="cteas-p6e-mixhbg-") as work:
        d=Path(work)
        for name,txt in (("params.met",PARAMS),
                         ("ziparm.met",(a.vendor.parent/"ziparm.met").read_text()),
                         ("gen.met",(a.vendor.parent/"gen.met").read_text()),
                         ("mixhbg_original.for",original),("driver.for",DRIVER)):
            (d/name).write_text(txt)
        run(["gfortran","-O0","-std=legacy","-fno-automatic",
             "-ffixed-line-length-none","-I"+str(d),
             d/"mixhbg_original.for",d/"driver.for","-o",d/"original"])
        original_rows=parse(run([d/"original"],inp))
    cpp_rows=parse(run([a.cpp],inp))
    largest=[0.,0.];first=[];bad=0
    for (case,f),(c,v) in zip(original_rows,cpp_rows):
        if case!=c:raise RuntimeError("MIXHBG shuffled cases")
        for field,(orig,candidate) in enumerate(zip(f,v)):
            delta=abs(orig-candidate)
            largest[field]=max(largest[field],delta)
            if delta>ABS[field]+REL*abs(orig):
                bad+=1
                if len(first)<20:first.append({"case":case,"field":field,
                            "original":orig,"cpp":candidate,"error":delta})
    report={"status":"PASS" if bad==0 else "FAIL","cases":CASES,
            "fields_compared":CASES*2,
            "condition_distribution":classes,"deep_limit_cases":deep,
            "max_abs_differences_ZICBG_GAMMA":largest,
            "frozen_abs_limits":ABS,"frozen_relative_limit":REL,
            "exceedances":bad,"first_mismatches":first,
            "original_blob":sha,"vendor_sha256":hashlib.sha256(raw).hexdigest(),
            "unmodified_source_lines":loc,
            "scope":"MIXHBG Batchvarova-Gryning ILAPSE=2 only; no MM5 MIXDT2, "
                    "no IMIXH=2 full-MIXHT wiring, no 2022 COMP coupling"}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    if bad:raise SystemExit(1)
if __name__=="__main__":main()
