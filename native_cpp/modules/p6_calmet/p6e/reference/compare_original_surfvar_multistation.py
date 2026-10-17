#!/usr/bin/env python3
"""Unchanged full original CALMET SURFVAR multistation TEMP/RH interpolation.

Selected observed, all-land NOOBS=0 ITPROG=0 IRHPROG=0 NPSTA=0,
IALL=1 IAVET=0, 4 surface sites, zero overwater sites.
"""
import argparse,hashlib,json,math,subprocess,tempfile
from pathlib import Path
BLOB="437f43bb7f0e51a1919e56664663e1a046986ed0"
CASES,NX,NY,NS=48,5,4,4
ABS_TEMP_K=0.0003
PARAMS="""      integer mxnx,mxny,mxnz,mxss,mxows,mxtmp,mxwb
      parameter(mxnx=5,mxny=4,mxnz=9,mxss=4,mxows=2,
     1          mxtmp=6,mxwb=1)
      integer nx,ny,nz,nlu,nssta,nowsta,itprog,irhprog
      integer noobs,npsta,iavet,irad,numts,io6
      integer ilucat(38),ilandu(mxnx,mxny)
      integer jwat1(mxwb),jwat2(mxwb)
      integer nears(mxnx,mxny),irh(mxss),ipcode(mxss)
      real dgrid,trad,mnmdav,hafang
      real otempk(mxss),xssta(mxss),yssta(mxss)
      real tairow(mxows),rhow(mxows),xowsta(mxows),yowsta(mxows)
      common /p6e_state/ nx,ny,nz,nlu,nssta,nowsta,itprog,
     1       irhprog,noobs,npsta,iavet,irad,numts,io6,
     2       ilucat,ilandu,jwat1,jwat2,nears,irh,ipcode,
     3       dgrid,trad,mnmdav,hafang,otempk,xssta,yssta,
     4       tairow,rhow,xowsta,yowsta
"""
DRIVER="""      program multistation_surfvar_driver
      include 'params.met'
      real u(mxnx,mxny),v(mxnx,mxny)
      real tprog(mxnx,mxny,mxnz),t2d(mxnx,mxny)
      integer rh2d(mxnx,mxny),pc2d(mxnx,mxny)
      integer irhpg(mxnx,mxny),ipcodepg(mxnx,mxny)
      common /surfprog/ irhpg,ipcodepg
      integer cases,nx_in,ny_in,ns_in,c,i,j,s,iall
      read(*,*)cases,nx_in,ny_in,ns_in
      if(nx_in.ne.5.or.ny_in.ne.4.or.ns_in.ne.4)stop 92
      nx=nx_in
      ny=ny_in
      nz=9
      nssta=ns_in
      nowsta=0
      noobs=0
      npsta=0
      itprog=0
      irhprog=0
      iavet=0
      nlu=1
      ilucat(1)=12
      jwat1(1)=50
      jwat2(1)=60
      dgrid=100.
      mnmdav=0.
      hafang=0.
      io6=6
      do i=1,nx
        do j=1,ny
          ilandu(i,j)=12
          nears(i,j)=1
          u(i,j)=2.
          v(i,j)=-1.
          irhpg(i,j)=60
          ipcodepg(i,j)=0
        enddo
      enddo
      do c=1,cases
        read(*,*)irad,numts,trad
        do s=1,nssta
          read(*,*)xssta(s),yssta(s),otempk(s),irh(s)
          ipcode(s)=9999
        enddo
        iall=1
        call surfvar(u,v,tprog,t2d,rh2d,pc2d,iall)
        do i=1,nx
          do j=1,ny
            write(*,'(3(I4,1X),ES20.11E3,1X,2(I5,1X))')
     1        c,i,j,t2d(i,j),rh2d(i,j),pc2d(i,j)
          enddo
        enddo
      enddo
      end
      subroutine avetmp(nx,ny,mnmdav,hafang,dgrid,u,v,t)
      stop 77
      end
"""
def run(args,data=None):
    return subprocess.run([str(x) for x in args],capture_output=True,
                          input=data,text=True,check=True).stdout
def original(raw):
    lines=raw.decode("utf-8").splitlines(keepends=True)
    first=[i for i,v in enumerate(lines) if v.lower().startswith("      subroutine surfvar(")]
    last=[i for i,v in enumerate(lines) if v.lower().startswith("      subroutine outhr(")]
    if len(first)!=1 or len(last)!=1 or not 490<last[0]-first[0]<570:
        raise RuntimeError("Original SURFVAR body changed")
    return "".join(lines[first[0]:last[0]]),[first[0]+1,last[0]]
def fixture():
    coords=((50.,50.),(450.,50.),(50.,350.),(450.,350.))
    temps=(270.0,279.5,285.0,290.25,295.75,302.0,310.0)
    rh=(10,15,45,65,70,85,99,100)
    trad=(0.15,0.75,1.5,3.5,12.)
    rows=[f"{CASES} {NX} {NY} {NS}"]
    counts={"radius_outside":0,"irad1":0,"irad2":0,"rh_all_missing_cases":0}
    for c in range(CASES):
        mode=1+c%2
        nts=1+c%NS
        t=trad[c%len(trad)]
        rows.append(f"{mode} {nts} {t}")
        counts["irad"+str(mode)]+=1
        counts["radius_outside"]+=t<1.
        missing_all=c%13==0
        counts["rh_all_missing_cases"]+=missing_all
        for st in range(NS):
            x,y=coords[st]
            # Expose different nearest-station ties and radius paths.
            x+=float((c//5)%3)*10.0
            y+=float((c//7)%3)*5.0
            temp=9999. if (c+st)%9==0 else temps[(c+2*st)%len(temps)]
            humidity=9999 if missing_all or (c+2*st)%7==0 else rh[(c+3*st)%len(rh)]
            rows.append(f"{x} {y} {temp} {humidity}")
    return "\n".join(rows)+"\n",counts
def parse(txt):
    values=[]
    for line in txt.splitlines():
        s=line.split()
        if len(s)!=6:raise RuntimeError("SURFVAR multistation output schema")
        idx=tuple(map(int,s[:3]))
        vals=(float(s[3]),int(s[4]),int(s[5]))
        if not math.isfinite(vals[0]):raise RuntimeError("nonfinite SURFVAR TEMP")
        values.append((idx,vals))
    if len(values)!=CASES*NX*NY:raise RuntimeError("SURFVAR grid count")
    return values
def main():
    p=argparse.ArgumentParser()
    for n in ("vendor","cpp","out"):p.add_argument("--"+n,required=True,type=Path)
    a=p.parse_args()
    raw=a.vendor.read_bytes()
    sha=run(["git","hash-object",a.vendor]).strip()
    if sha!=BLOB:raise RuntimeError("Vendor source hash drift")
    full,loc=original(raw)
    test,cases=fixture()
    with tempfile.TemporaryDirectory(prefix="cteas-multistation-surfvar-") as tempdir:
        d=Path(tempdir)
        files={"params.met":PARAMS,"surfvar_original.for":full,"driver.for":DRIVER}
        for empty in ("grid.met","met1.met","met2.met","tmp.met","geo.met",
                      "ovrwat.met","ziparm.met"):
            files[empty]="c mocked COMMON state in params.met\n"
        for name,content in files.items():(d/name).write_text(content)
        run(["gfortran","-O0","-std=legacy","-fno-automatic",
             "-ffixed-line-length-none","-I"+str(d),
             d/"surfvar_original.for",d/"driver.for","-o",d/"original"])
        reference=parse(run([d/"original"],test))
    candidate=parse(run([a.cpp],test))
    diffs=[];count=0;max_temp=0.
    for (k,ref),(kk,cpp) in zip(reference,candidate):
        if k!=kk:raise RuntimeError("SURFVAR multistation cell ordering mismatch")
        dt=abs(ref[0]-cpp[0]);max_temp=max(max_temp,dt)
        if dt>ABS_TEMP_K or ref[1:]!=cpp[1:]:
            count+=1
            if len(diffs)<25:diffs.append({"cell":k,"original":ref,"candidate":cpp})
    result={"status":"PASS" if count==0 else "FAIL",
            "cases":CASES,"grid_cells":len(reference),
            "scalar_comparisons":3*len(reference),
            "frozen_temperature_abs_tol_K":ABS_TEMP_K,
            "max_temperature_abs_diff_K":max_temp,
            "humidity_and_ipcode_exact":count==0,
            "mismatches":count,"first_mismatches":diffs,
            "test_distribution":cases,
            "original_vendor_blob":sha,"original_sha256":hashlib.sha256(raw).hexdigest(),
            "original_full_surfvar_source_lines":loc,
            "scope":"Observed 4-station, all-land, IRAD1/2, NUMTS radius, missing RH/temp; NPSTA=0 unverified precipitation; no smoothing, water, or prognostic fields"}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
    if count:raise SystemExit(1)
if __name__=="__main__":main()
