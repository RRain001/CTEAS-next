#!/usr/bin/env python3
"""Pinned unchanged MIXHT+MIXDT+MIXHMC+MIXHBG full selected path.

Both original convective-growth closures are compiled from the pinned
original unchanged Fortran source (IMIXH=1 Maul-Carson via MIXHMC and
IMIXH=2 Batchvarova-Gryning via MIXHBG+FBG). MIXDT2 and OUT fail-stop
stubs deliberately rule out unsupported pathways. Not COMP/2022 parity.
"""
import argparse
import hashlib
import json
import math
import subprocess
import tempfile
from pathlib import Path
BLOB="437f43bb7f0e51a1919e56664663e1a046986ed0"
CASES,NX,NY,NS,NLEV=60,5,4,2,10
CASES_MC=28
CASES_BG=20
CASES_RC=12
ABS=(0.07,0.07,0.004)
REL=0.00008
PARAMS="""      integer mxnx,mxny,mxus,mxlev,io6
      parameter(mxnx=5,mxny=4,mxus=2,mxlev=10,io6=6)
"""
DRIVER="""      program original_mixht_mc_observed
      include 'params.met'
      include 'ziparm.met'
      include 'upmet.met'
      include 'gen.met'
      real qh(mxnx,mxny),ustar(mxnx,mxny),el(mxnx,mxny)
      real rho(mxnx,mxny),zi(mxnx,mxny),ziconv(mxnx,mxny)
      real dptt(mxnx,mxny)
      common /tjump/dptt
      integer ilandu(mxnx,mxny),nearu(mxnx,mxny)
      integer cases,nx,ny,ns,nlev,iupt,imixh
      integer c,i,j,st,k,b,watlow,wathigh
      logical ldbhr
      read(*,*)cases,nx,ny,ns,nlev
      if(nx.ne.5.or.ny.ne.4.or.ns.ne.2.or.nlev.ne.10)stop 66
      watlow=50
      wathigh=60
      ldbhr=.false.
      do c=1,cases
        read(*,*)iupt,constn,zimin,zimax,threshl,dptmin,dzzi,
     1           onedte,twodte,izicrlx,tzicrlx,nsecdt,imixh
        do st=1,ns
          read(*,*)justa(st)
          nlaa(st)=nlev
          nlbb(st)=nlev
        enddo
        do b=1,2
          do st=1,ns
            do k=1,nlev
              if(b.eq.1)then
                read(*,*)zlaa(st,k),tzaa(st,k)
              else
                read(*,*)zlbb(st,k),tzbb(st,k)
              endif
            enddo
          enddo
        enddo
        do i=1,nx
          do j=1,ny
            read(*,*)qh(i,j),ustar(i,j),el(i,j),rho(i,j),
     1        cmech(i,j),fcori(i,j),ilandu(i,j),nearu(i,j),
     2        zi(i,j),ziconv(i,j),dptt(i,j)
          enddo
        enddo
        call mixht(el,ustar,qh,nx,ny,rho,12,nearu,
     1        iupt,ilandu,watlow,wathigh,ldbhr,imixh,zi,ziconv)
        do i=1,nx
          do j=1,ny
            write(*,'(3(I6,1X),3(ES24.14E3,1X))')
     1        c,i,j,zi(i,j),ziconv(i,j),dptt(i,j)
          enddo
        enddo
      enddo
      end
      subroutine mixdt2
      stop 92
      end
      subroutine out
      stop 93
      end
"""
def run(command,inp=None):
    return subprocess.run([str(x) for x in command],input=inp,
                          text=True,capture_output=True,check=True).stdout
def source(raw):
    rows=raw.decode("utf-8").splitlines(keepends=True)
    specs=(("      subroutine mixht(","      subroutine mixhtst(",230,320),
           ("      subroutine mixdt(","      subroutine mixdt2(",185,220),
           ("      subroutine mixhmc(","      subroutine openot",150,240),
           ("      subroutine mixhbg (","      subroutine mixhmc(",200,320))
    portions=[];loc=[]
    for first,last,low,high in specs:
        aa=[i for i,v in enumerate(rows) if v.lower().startswith(first)]
        bb=[i for i,v in enumerate(rows) if v.lower().startswith(last)]
        if len(aa)!=1 or len(bb)!=1 or not low<bb[0]-aa[0]<high:
            raise RuntimeError("CALMET original subroutine anchor drift "+first)
        portions.append("".join(rows[aa[0]:bb[0]]))
        loc.append([aa[0]+1,bb[0]])
    return "\n".join(portions),loc
def fixture():
    heights=(0.,50.,100.,180.,300.,450.,650.,900.,1250.,1800.)
    qh=(-0.1,0.,5.,35.,90.,160.,400.)
    ht=(80.,120.,240.,400.)
    # (QH, EL, USTAR, RHO, ZICONVOLD, DPTT) scenarios for the IMIXH=2 set:
    # unstable EL on daytime cells, stable EL on nocturnal cells, plus the
    # exact zero-net-buoyancy retention and the EL <= -500 m deep limit.
    scen=((200.,-120.,0.4,1.2,200.,0.5),
          (60.,-40.,0.3,1.2,100.,0.2),
          (5.,-800.,0.5,1.2,300.,0.0),
          (0.,-100.,0.3,1.2,250.,0.4),
          (30.,-60.,0.25,1.1,150.,0.1),
          (400.,-300.,0.8,1.3,400.,1.0),
          (-0.1,25.,0.2,1.2,0.,0.),
          (-0.1,60.,0.4,1.14,0.,0.),
          (12.,-500.,0.2,1.2,100.,0.3),
          (10.,-20.,0.15,1.05,50.,0.))
    rows=[f"{CASES} {NX} {NY} {NS} {NLEV}"]
    counts=dict(water=0,stable=0,day=0,aa=0,bb=0,iupt_override=0,
                bg_water=0,bg_stable=0,bg_day=0,bg_aa=0,bg_bb=0,
                bg_collapse=0,bg_retain=0,bg_relax=0,bg_growth=0,bg_deep=0)
    for c in range(CASES_MC):
        iupt=2 if c%3==0 else -1
        counts["iupt_override"]+=iupt>0
        zimin=20.+5.*(c%2);zimax=1500.+100.*(c%5)
        thresh=(0.,0.02,0.10)[c%3]
        relax=c%2
        rows.append(f"{iupt} 2400.0 {zimin} {zimax} {thresh} "
                    f"0.001 200. 4140. 1080. {relax} 800. 3600 1")
        justa=[1 if (st+c)%2==0 else -1 for st in range(NS)]
        for x in justa:rows.append(str(x))
        for buf in range(2):
            for st in range(NS):
                for k,h in enumerate(heights):
                    z=h
                    temp=303.-0.0075*z+0.9*st+buf*1.8+c*0.01+0.1*(k%3)
                    rows.append(f"{z:.4f} {temp:.6f}")
        for i in range(NX):
            for j in range(NY):
                k=i+2*j+c
                # Deliberately avoid coupling water-mask periodicity to
                # the QH stable (-0.1) period of 7; that masked every
                # QH<0 cell in the initial nominal joint test.
                use=55 if (i+2*j+c)%9==0 else 12
                heat=qh[k%len(qh)]
                if use==55:counts["water"]+=1
                elif heat<0:counts["stable"]+=1
                else:counts["day"]+=1
                near=1+((i+j+c)%NS)
                station=(iupt-1) if iupt>0 else near-1
                oldbuffer=0 if justa[station]>0 else 1
                counts["aa" if oldbuffer==0 else "bb"]+=use!=55 and heat>=0
                us=(0.12,0.22,0.4,0.8)[(i+j+c)%4]
                el=(15.,40.,100.,200.)[(i+2*j+c)%4]
                rho=(1.05,1.14,1.2,1.3)[(i+j+c)%4]
                zic=ht[(i+3*j+c)%4] if use!=55 else -7777.
                jump=(0.,0.2,0.5,1.)[(i+2*j+c)%4] if use!=55 else -7777.
                rows.append(f"{heat} {us} {el} {rho} "
                            f"{90.+10.*(i%3)} 0.00007 {use} {near} "
                            f"-7777.0 {zic} {jump}")
    for c in range(CASES_BG):
        iupt=2 if c%4==0 else -1
        counts["iupt_override"]+=iupt>0
        zimin=20.+5.*(c%2);zimax=1500.+100.*(c%5)
        thresh=(0.,0.02,0.10)[c%3]
        relax=c%2
        # The exact zero-net-buoyancy retention branch needs THRESH=0; the
        # relaxation branch needs THRESH>0, so never combine IZICRLX=1 with
        # a zero threshold (the original equilibrium height is 0/0 there).
        if relax==1 and thresh==0.:thresh=0.005
        step=(600,1800,3600)[c%3]
        rows.append(f"{iupt} 2400.0 {zimin} {zimax} {thresh} "
                    f"0.001 200. {step*1.15:.4f} {step*0.3:.4f} "
                    f"{relax} 800. {step} 2")
        justa=[1 if (st+c)%2==0 else -1 for st in range(NS)]
        for x in justa:rows.append(str(x))
        for buf in range(2):
            for st in range(NS):
                for k,h in enumerate(heights):
                    z=h
                    temp=303.-0.0075*z+0.9*st+buf*1.8+c*0.01+0.1*(k%3)
                    rows.append(f"{z:.4f} {temp:.6f}")
        for i in range(NX):
            for j in range(NY):
                heat,el,us,rho,zic,jump=scen[(i+NX*j+c)%len(scen)]
                use=55 if (i+2*j+c)%11==0 else 12
                if use==55:
                    heat,el,us,rho,zic,jump=-7777.,-7777.,-7777.,-7777.,-7777.,-7777.
                    counts["bg_water"]+=1
                elif heat<0:
                    counts["bg_stable"]+=1
                else:
                    counts["bg_day"]+=1
                    h0=max(zic,zimin)
                    wto=thresh*h0/(1.2*1005.)
                    wptp=heat/(rho*996.)-wto
                    if relax==1:
                        label="bg_relax" if wptp<=0. else "bg_growth"
                    else:
                        if wptp<0.:label="bg_collapse"
                        elif wptp==0.:label="bg_retain"
                        else:label="bg_growth"
                    counts[label]+=1
                    if label=="bg_growth" and el<=-500.:counts["bg_deep"]+=1
                near=1+((i+j+c)%NS)
                station=(iupt-1) if iupt>0 else near-1
                oldbuffer=0 if justa[station]>0 else 1
                counts["aa" if oldbuffer==0 else "bb"]+=use!=55 and heat>=0
                counts["bg_aa" if oldbuffer==0 else "bg_bb"]+=use!=55 and heat>=0
                rows.append(f"{heat} {us} {el} {rho} "
                            f"{90.+10.*(i%3)} 0.00007 {use} {near} "
                            f"-7777.0 {zic} {jump}")
    if min(counts["stable"],counts["day"],counts["water"],
           counts["aa"],counts["bb"],counts["iupt_override"]) < 10:
        raise RuntimeError("MIXHT MC branch coverage insufficient")
    if min(counts["bg_stable"],counts["bg_day"],counts["bg_water"],
           counts["bg_collapse"],counts["bg_retain"],counts["bg_relax"],
           counts["bg_growth"],counts["bg_deep"],counts["bg_aa"],
           counts["bg_bb"]) < 5:
        raise RuntimeError("MIXHT BG branch coverage insufficient")
    rc_counts=dict(rc_day=0,rc_stable=0,rc_water=0,rc_aa=0,rc_bb=0,
                   rc_relaxation=0,rc_relax_reachable=0)
    rc_rows,_=realcase_rows(1,rc_counts)
    rows.extend(rc_rows)
    counts.update(rc_counts)
    if min(counts["rc_day"],counts["rc_stable"],counts["rc_water"],
           counts["rc_aa"],counts["rc_bb"]) < 10:
        raise RuntimeError("MIXHT real-case option tuple coverage insufficient")
    if counts["rc_relax_reachable"] != 0:
        raise RuntimeError("THRESHL=0 must make the IZICRLX relaxation unreachable")
    return "\n".join(rows)+"\n",counts

def realcase_rows(izicrlx,counts):
    """Exact real-deck option tuple: IMIXH=1, THRESHL=0.0, IZICRLX, IUPT=-1."""
    heights=(0.,50.,100.,180.,300.,450.,650.,900.,1250.,1800.)
    qh=(-0.1,0.,30.,80.,150.)
    rows=[]
    for c in range(CASES_RC):
        zimax=1200.+100.*(c%3)
        rows.append(f"-1 2400.0 20.0 {zimax} 0.0 0.001 200. "
                    f"4140. 1080. {izicrlx} 800. 3600 1")
        justa=[1 if (st+c)%2==0 else -1 for st in range(NS)]
        for x in justa:rows.append(str(x))
        for buf in range(2):
            for st in range(NS):
                for k,h in enumerate(heights):
                    temp=303.-0.0075*h+0.9*st+buf*1.8+c*0.01+0.1*(k%3)
                    rows.append(f"{h:.4f} {temp:.6f}")
        for i in range(NX):
            for j in range(NY):
                near=1+((i+j+c)%NS)
                use=55 if (i+2*j+c)%7==0 else 12
                heat=qh[(i+3*j+c)%len(qh)]
                if use==55:
                    heat,el,us,rho,zic,jump=(-7777.,)*6
                    counts["rc_water"]+=1
                else:
                    el=(20.+5.*((i+j)%4)) if heat<0. else -(40.+20.*((i+j)%5))
                    us=0.15+0.02*((i+j)%4)
                    rho=1.15
                    zic=60.+10.*((i+j)%5)
                    jump=0.3
                    if heat<0:counts["rc_stable"]+=1
                    else:counts["rc_day"]+=1
                station=near-1
                oldbuffer=0 if justa[station]>0 else 1
                counts["rc_aa" if oldbuffer==0 else "rc_bb"]+=use!=55 and heat>=0
                if use!=55 and heat>=0:
                    # THRESHL=0 => WTO=0, so the IZICRLX relaxation needs
                    # 0 < WT <= WTO = 0, which can never happen.
                    cp=996.
                    wt=heat/(rho*cp)
                    wto=0.0*max(zic,20.0)/(rho*cp)
                    if wt>0. and (wt-wto)<=0.:
                        counts["rc_relax_reachable"]+=1
                        if izicrlx!=0:counts["rc_relaxation"]+=1
                rows.append(f"{heat} {us} {el} {rho} "
                            f"{90.+10.*(i%3)} 0.00007 {use} {near} "
                            f"-7777.0 {zic} {jump}")
    return rows,counts

def fixture_realcase(izicrlx):
    counts=dict(rc_day=0,rc_stable=0,rc_water=0,rc_aa=0,rc_bb=0,
                rc_relaxation=0,rc_relax_reachable=0)
    rows,_=realcase_rows(izicrlx,counts)
    return f"{CASES_RC} {NX} {NY} {NS} {NLEV}\n"+"\n".join(rows)+"\n"
def parse(txt):
    out=[]
    for line in txt.splitlines():
        a=line.split()
        if len(a)!=6:raise RuntimeError("MIXHT MC invalid comparator schema "+line)
        key=tuple(int(x) for x in a[:3]);val=tuple(float(x) for x in a[3:])
        if not all(math.isfinite(x) for x in val):
            raise RuntimeError("MIXHT MC original nonfinite value")
        out.append((key,val))
    if len(out)!=CASES*NX*NY:
        raise RuntimeError(f"MIXHT MC original output size {len(out)}")
    return out
def main():
    p=argparse.ArgumentParser()
    for flag in ("vendor","cpp","out"):p.add_argument("--"+flag,type=Path,required=True)
    x=p.parse_args()
    raw=x.vendor.read_bytes()
    sha=run(["git","hash-object",x.vendor]).strip()
    if sha!=BLOB:raise RuntimeError("Original CALMET vendor blob changed")
    fortran,loc=source(raw)
    test,counts=fixture()
    with tempfile.TemporaryDirectory(prefix="p6e-mixht-mc-") as tmp:
        d=Path(tmp)
        for name,data in (("params.met",PARAMS),
                          ("ziparm.met",(x.vendor.parent/"ziparm.met").read_text()),
                          ("upmet.met",(x.vendor.parent/"upmet.met").read_text()),
                          ("gen.met",(x.vendor.parent/"gen.met").read_text()),
                          ("original.for",fortran),("driver.for",DRIVER)):
            (d/name).write_text(data)
        run(["gfortran","-O0","-std=legacy","-fno-automatic",
             "-ffixed-line-length-none","-I"+str(d),
             d/"original.for",d/"driver.for","-o",d/"original"])
        expected=parse(run([d/"original"],test))
        # Source-level proof that THRESHL=0 makes IZICRLX=1 inert: the same
        # real-case option tuple with IZICRLX=0 and IZICRLX=1 must produce
        # byte-identical output from the unmodified original subroutines.
        probe0=fixture_realcase(0)
        probe1=fixture_realcase(1)
        inert=(run([d/"original"],probe0)==run([d/"original"],probe1))
    if not inert:
        raise RuntimeError("original MIXHT IZICRLX relaxation not inert at THRESHL=0")
    actual=parse(run([x.cpp],test))
    errs=[0.,0.,0.];errs_mc=[0.,0.,0.];errs_bg=[0.,0.,0.]
    errs_rc=[0.,0.,0.]
    first=[];bad=0
    for (a,f),(b,v) in zip(expected,actual):
        if a!=b:raise RuntimeError("MIXHT MC output order mismatch")
        water=f[0]==-7777.
        bucket=(errs_mc if a[0]<=CASES_MC else
                errs_bg if a[0]<=CASES_MC+CASES_BG else errs_rc)
        for k in range(3):
            err=abs(f[k]-v[k]);errs[k]=max(errs[k],err)
            bucket[k]=max(bucket[k],err)
            fail=(f[k]!=v[k]) if water else err>ABS[k]+REL*abs(f[k])
            if fail:
                bad+=1
                if len(first)<25:first.append(
                    dict(grid=a,field=k,original=f[k],cpp=v[k],absdiff=err))
    result=dict(status="PASS" if bad==0 else "FAIL",
        cases=CASES,grids=CASES*NX*NY,scalar_comparisons=3*CASES*NX*NY,
        distribution=counts,max_abs_error_ZI_ZICONV_DPTT=errs,
        max_abs_error_IMIXH1_MC=errs_mc,max_abs_error_IMIXH2_BG=errs_bg,
        realcase_option_profile=dict(
            irtype=1,imixh=1,threshl_wm2perm=0.0,izicrlx=1,iupt=-1,
            isurft=-1,itprog=0,noobs=0,nowsta=0,nm3d=0,
            cases=CASES_RC,cells=CASES_RC*NX*NY,
            max_abs_error_ZI_ZICONV_DPTT=errs_rc,
            relaxation_branch_cells=counts["rc_relaxation"],
            relaxation_unreachable_at_zero_threshold=True,
            original_source_izicrlx_0_vs_1_identical=inert),
        frozen_abs_tolerance=ABS,frozen_rel_tolerance=REL,
        mismatches=bad,first_mismatches=first,
        original_git_blob=sha,original_sha256=hashlib.sha256(raw).hexdigest(),
        unmodified_original_subroutines_lines=loc,
        scope="Selected CALMET full MIXHT grid path with original IMIXH=1 "
              "(MIXHMC) and IMIXH=2 (MIXHBG) closures, AA/BB JUSTA, IUPT, "
              "plus the real-case option tuple IMIXH=1/THRESHL=0/IZICRLX=1/"
              "IUPT=-1; synthetic only, no water/OCD scheme, no 2022 COMP "
              "or wet forcing")
    x.out.parent.mkdir(parents=True,exist_ok=True)
    x.out.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
    if bad:raise SystemExit(1)
if __name__=="__main__":main()
