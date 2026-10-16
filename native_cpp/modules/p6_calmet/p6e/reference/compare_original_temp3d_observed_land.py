#!/usr/bin/env python3
"""Compare original full unchanged TEMP3D all-land observed 00/12 UTC path.

Fortran original code is extracted verbatim. Auxiliary time DEDAT and
DELTSEC stubs exactly implement the *same-date UTC hours only* test
scope; all mixed-date and overwater paths remain deliberately outside
this acceptance gate.
"""
import argparse,hashlib,json,math,subprocess,tempfile
from pathlib import Path
BLOB="437f43bb7f0e51a1919e56664663e1a046986ed0"
CASES,NX,NY,NZ,NS=24,5,4,6,2
ABS_TOL_K=0.0005
REL_TOL=0.00001
PARAMS="""      integer mxnx,mxny,mxnz,mxnzp1,mxus,mxlev,mxtmp
      integer mxss,mxows,mxwb,io6
      parameter(mxnx=5,mxny=4,mxnz=6,mxnzp1=7,mxus=2,
     1 mxlev=10,mxtmp=6,mxss=4,mxows=2,mxwb=1,io6=6)
      integer nx,ny,nz,nzp1,nusta,itprog,irad,nowsta
      integer nssta,nlu,numts,ilandu(mxnx,mxny),ilucat(38)
      integer jwat1(mxwb),jwat2(mxwb)
      integer justa(mxus),jusdt(mxus),ntzaa(mxus),ntzbb(mxus)
      integer jaasec(mxus),jbbsec(mxus)
      real dgrid,zface(mxnzp1),zmid(mxnz)
      real xusta(mxus),yusta(mxus),xowsta(mxows),yowsta(mxows)
      real tgradb(mxows),tgrada(mxows),tgdefb,tgdefa,trad
      common /p6e_temp_state/ nx,ny,nz,nzp1,nusta,itprog,irad,
     1 nowsta,nssta,nlu,numts,ilandu,ilucat,jwat1,jwat2,
     2 justa,jusdt,ntzaa,ntzbb,jaasec,jbbsec,dgrid,zface,
     3 zmid,xusta,yusta,xowsta,yowsta,tgradb,tgrada,
     4 tgdefb,tgdefa,trad
"""
DRIVER="""      program original_temp3d_selected_driver
      include 'params.met'
      real temp2d(mxnx,mxny),ziconv(mxnx,mxny)
      real zi(mxnx,mxny),tzgraa(mxnzp1,mxus)
      real tzgrbb(mxnzp1,mxus),ztemp(mxnx,mxny,mxnz)
      real tprog(mxnx,mxny,mxnz)
      integer cases,nxi,nyi,nzi,nsta,c,i,j,k,st,hr
      read(*,*)cases,nxi,nyi,nzi,nsta
      if(nxi.ne.mxnx.or.nyi.ne.mxny.or.nzi.ne.mxnz)stop 77
      if(nsta.ne.mxus)stop 78
      nx=nxi
      ny=nyi
      nz=nzi
      nzp1=nz+1
      nusta=nsta
      itprog=0
      nowsta=0
      nssta=0
      nlu=1
      ilucat(1)=12
      jwat1(1)=50
      jwat2(1)=60
      numts=2
      trad=100.
      do i=1,nx
        do j=1,ny
          ilandu(i,j)=12
        enddo
      enddo
      do c=1,cases
        read(*,*)irad,hr,dgrid
        do k=1,nzp1
          read(*,*)zface(k)
        enddo
        do st=1,nusta
          read(*,*)justa(st),xusta(st),yusta(st)
          jusdt(st)=43200
          if(justa(st).gt.0)then
            ntzaa(st)=202200100
            ntzbb(st)=202200112
          else
            ntzaa(st)=202200112
            ntzbb(st)=202200100
          endif
          jaasec(st)=0
          jbbsec(st)=0
        enddo
        do st=1,nusta
          do k=1,nzp1
            read(*,*)tzgraa(k,st),tzgrbb(k,st)
          enddo
        enddo
        do i=1,nx
          do j=1,ny
            read(*,*)temp2d(i,j),ziconv(i,j)
            zi(i,j)=ziconv(i,j)
          enddo
        enddo
        call temp3d(2022,1,hr,0,temp2d,ziconv,tzgraa,
     1              tzgrbb,ztemp,zi,tprog)
        do i=1,nx
          do j=1,ny
            do k=1,nz
              write(*,'(4(I6,1X),ES24.14E3)')
     1              c,i,j,k,ztemp(i,j,k)
            enddo
          enddo
        enddo
      enddo
      end
      subroutine dedat(t,yr,jday,hr)
      integer t,yr,jday,hr
      yr=t/100000
      jday=mod(t,100000)/100
      hr=mod(t,100)
      return
      end
      subroutine deltsec(t1,s1,t2,s2,dt)
      integer t1,s1,t2,s2,dt
      if(t1/100.ne.t2/100)stop 92
      dt=(mod(t2,100)-mod(t1,100))*3600+s2-s1
      return
      end
      subroutine grday
      stop 93
      end
"""
def cmd(args,inp=None):
    return subprocess.run([str(x) for x in args],input=inp,
                          text=True,capture_output=True,check=True).stdout
def original_full_temp3d(raw):
    lines=raw.decode("utf-8").splitlines(keepends=True)
    a=[i for i,v in enumerate(lines) if v.lower().startswith("      subroutine temp3d(")]
    b=[i for i,v in enumerate(lines) if v.lower().startswith("      subroutine setcoast(")]
    if len(a)!=1 or len(b)!=1 or not 500<b[0]-a[0]<610:
        raise RuntimeError("Original TEMP3D source bounds drift")
    return "".join(lines[a[0]:b[0]]),[a[0]+1,b[0]]
def fixture():
    faces=(0.,100.,220.,400.,680.,1000.,1550.)
    zi=(0.,80.,100.,220.,300.,500.,750.,1200.,1600.)
    hours=(1,3,6,9,11)
    rows=[f"{CASES} {NX} {NY} {NZ} {NS}"]
    counts={"irad1":0,"irad2":0,"midlayer":0,"aa_older":0,"bb_older":0}
    for c in range(CASES):
        irad=1+c%2
        hour=hours[c%len(hours)]
        rows.append(f"{irad} {hour} 100.0")
        counts["irad"+str(irad)]+=1
        for z in faces:rows.append(str(z))
        for st in range(NS):
            older=1 if (st+c)%2==0 else -1
            counts["aa_older" if older>0 else "bb_older"]+=1
            sx=(50.,450.)[st];sy=(50.,350.)[st]
            rows.append(f"{older} {sx} {sy}")
        for st in range(NS):
            for k,h in enumerate(faces):
                aa=303.-0.007*h+c*0.03+st*1.2+(k%3)*0.11
                bb=aa+(1.8 if st==0 else -0.7)
                rows.append(f"{aa:.6f} {bb:.6f}")
        for i in range(NX):
            for j in range(NY):
                zic=zi[(i+2*j+c)%len(zi)]
                counts["midlayer"]+=int(zic in (80.,300.,500.,750.,1200.))
                ts=295.+0.5*i+0.3*j+c*0.02
                rows.append(f"{ts:.6f} {zic:.6f}")
    return "\n".join(rows)+"\n",counts
def parse(text):
    rows=[]
    for line in text.splitlines():
        t=line.split()
        if len(t)!=5:raise RuntimeError("TEMP3D schema: "+line)
        key=tuple(map(int,t[:4]));v=float(t[4])
        if not math.isfinite(v):raise RuntimeError("nonfinite TEMP3D original result")
        rows.append((key,v))
    if len(rows)!=CASES*NX*NY*NZ:
        raise RuntimeError("TEMP3D insufficient original records")
    return rows
def main():
    p=argparse.ArgumentParser()
    for n in ("vendor","cpp","out"):p.add_argument("--"+n,type=Path,required=True)
    x=p.parse_args()
    raw=x.vendor.read_bytes()
    sha=cmd(["git","hash-object",x.vendor]).strip()
    if sha!=BLOB:raise RuntimeError("Original CALMET vendor SHA drift")
    original,loc=original_full_temp3d(raw)
    inp,counts=fixture()
    with tempfile.TemporaryDirectory(prefix="cteas-temp3d-selected-") as tmp:
        d=Path(tmp)
        for name,body in (("params.met",PARAMS),
                          ("original_temp3d.for",original),
                          ("driver.for",DRIVER)):
            (d/name).write_text(body)
        for name in ("grid.met","met1.met","upmet.met","tmp.met",
                     "geo.met","ovrwat.met"):
            (d/name).write_text("c selected all-land COMMON in params.met\n")
        cmd(["gfortran","-O0","-std=legacy","-fno-automatic",
             "-ffixed-line-length-none","-I"+str(d),
             d/"original_temp3d.for",d/"driver.for","-o",d/"original"])
        reference=parse(cmd([d/"original"],inp))
    candidate=parse(cmd([x.cpp],inp))
    bad=0;maxerr=0.;first=[]
    for (key,ref),(kk,val) in zip(reference,candidate):
        if key!=kk:raise ValueError("TEMP3D Fortran/C++ index ordering mismatch")
        err=abs(ref-val);maxerr=max(maxerr,err)
        if err>ABS_TOL_K+REL_TOL*abs(ref):
            bad+=1
            if len(first)<20:first.append({"cell":key,"fortran":ref,"cpp":val,"diff":err})
    out=dict(status="PASS" if bad==0 else "FAIL",
        cases=CASES,grid_cells=CASES*NX*NY,vertical_levels=NZ,
        scalar_comparisons=CASES*NX*NY*NZ,
        branch_distribution=counts,
        max_abs_temp_error_k=maxerr,
        frozen_abs_tolerance_k=ABS_TOL_K,frozen_rel_tolerance=REL_TOL,
        mismatches=bad,first_mismatches=first,
        original_git_blob=sha,original_sha256=hashlib.sha256(raw).hexdigest(),
        unchanged_original_temp3d_lines=loc,
        scope="CALMET TEMP3D observed same-day AA/BB 00-12Z land-only;"
              " no water, prognostic, actual 2022 COMP, midnight/crossyear")
    x.out.parent.mkdir(parents=True,exist_ok=True)
    x.out.write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps(out,indent=2))
    if bad:raise SystemExit(1)
if __name__=="__main__":main()
