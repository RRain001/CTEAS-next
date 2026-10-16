#!/usr/bin/env python3
"""Compare selected actual CALMET 6.5.0 RDUPN Fortran read+conversion to P6 C++20.

For this study UP.DAT v2.1, original CALMET uses RDHDU + **RDUPN**,
not legacy RDUP: calmet.for L15222-15280, L24119-24287.
Fortran driver uses the same original RDUPN input format statements
3 FORMAT(9x,i8,2(4x,i4,i4,i3,i3,i5),8x,i5),
4 FORMAT(4(3x,f6.1,1x,f5.0,1x,f5.1,1x,f3.0,1x,f3.0))
and exactly the selected UTM projection/ICONVRT=1 formulas; this
is independent native Fortran format and numeric parity, NOT the complete
original RDUPN subroutine's AA/BB array scheduling or Fortran utilities.
"""
from __future__ import annotations
import argparse,csv,datetime,hashlib,json,math,subprocess
from pathlib import Path

FORTRAN=r"""      program original_rdupn_selected
      implicit none
      integer ios,year1,mon1,day1,hour1,sec1
      integer year2,mon2,day2,hour2,sec2
      integer station,n,mraw,expected,l,ncomment,jdat,ifmt
      integer sb,db,hb,seb,se,db2,he,see
      real pressure(99),height(99),tempk(99),dir(99),speed(99)
      real u,v,zl,deg,top
      character*256 inp,out,record
      character*16 dataset,version
      character*64 modifier
      character*8 projection,timezone
      character*80 comment
      logical lht,ltemp,lwd,lws
      call get_command_argument(1,inp)
      call get_command_argument(2,out)
      call get_command_argument(3,record)
      read(record,*)expected
      open(10,file=trim(inp),status='old')
      read(10,'(2a16,a64)')dataset,version,modifier
      if(dataset.ne.'UP.DAT'.or.version.ne.'2.1')stop 1
      read(10,*)ncomment
      do l=1,ncomment
         read(10,'(a80)')comment
      enddo
      read(10,'(a8)')projection
      read(10,'(a8)')timezone
      if(projection.ne.'NONE'.or.timezone.ne.'UTC+0000')stop 2
      read(10,*)sb,db,hb,seb,se,db2,he,see,top,jdat,ifmt
      if(jdat.ne.2.or.ifmt.ne.1.or.abs(top-500.).gt.0.01)
     1 stop 3
      read(10,*)lht,ltemp,lwd,lws
      if(lht.or.ltemp.or.lwd.or.lws)stop 4
      open(11,file=trim(out),status='replace')
      n=0
  100 continue
      read(10,3,iostat=ios)station,year1,mon1,day1,
     1 hour1,sec1,year2,mon2,day2,hour2,sec2,mraw
  3   format(9x,i8,2(4x,i4,i4,i3,i3,i5),8x,i5)
      if(ios.lt.0)go to 900
      if(ios.ne.0)stop 5
      if(station.ne.expected.or.mraw.lt.1.or.mraw.gt.99)stop 6
      read(10,4,iostat=ios)(pressure(l),height(l),tempk(l),
     1 dir(l),speed(l),l=1,mraw)
  4   format(4(3x,f6.1,1x,f5.0,1x,f5.1,1x,f3.0,1x,f3.0))
      if(ios.ne.0)stop 7
      n=n+1
      do l=1,mraw
        if(height(l).ge.9998.)stop 8
        zl=height(l)-height(1)
        if(dir(l).lt.998.99.and.speed(l).lt.998.99)then
          deg=0.0174533*dir(l)
          u=-speed(l)*sin(deg)
          v=-speed(l)*cos(deg)
        else
          u=999.
          v=999.
        endif
        write(11,*)station,year1,mon1,day1,hour1,sec1,
     1   year2,mon2,day2,hour2,sec2,l,mraw,
     2   pressure(l),height(l),tempk(l),dir(l),speed(l),
     3   zl,u,v
      enddo
      go to 100
  900 continue
      if(n.lt.1)stop 9
      close(10)
      close(11)
      end
"""
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
def run(argv):
    p=subprocess.run(list(map(str,argv)),capture_output=True,text=True)
    if p.returncode:raise RuntimeError(f"failed {argv} rc={p.returncode}\n{p.stderr[-2500:]}\n{p.stdout[-1000:]}")
def second(y,m,d,h,secs):
    if y<2022 or y>2023:raise ValueError("UPDAT time outside model study")
    base=datetime.datetime(y,m,d,tzinfo=datetime.timezone.utc)
    return int((base+datetime.timedelta(hours=h,seconds=secs)).timestamp())
def check(original:Path,cpp:Path):
    rows=[line.split() for line in original.read_text().splitlines()]
    with cpp.open(newline="") as f:modern=list(csv.DictReader(f))
    if len(rows)!=len(modern) or not rows:
        raise RuntimeError(f"UPDAT Fortran/C++ level totals mismatch: {len(rows)} {len(modern)}")
    float_fields={13:"pressure_hpa",14:"height_msl_m",15:"temperature_k",
                  16:"wd_deg",17:"ws_mps",18:"height_lgl_m",
                  19:"u_mps",20:"v_mps"}
    errors={name:0. for name in float_fields.values()}
    failure=[]
    unique=set()
    missing_wind=0
    wind_nz=0
    for i,(r,c) in enumerate(zip(rows,modern)):
        if len(r)!=21:raise ValueError(f"original Fortran result not 21 values at {i}")
        t1=second(*map(int,r[1:6]))
        t2=second(*map(int,r[6:11]))
        if int(r[0])!=int(c["station_id"]) or\
           t1!=int(c["epoch_begin"]) or t2!=int(c["epoch_end"]) or\
           int(r[11])!=int(c["level"]) or int(r[12])!=int(c["nlevels"]):
            failure.append({"record":i,"problem":"station/time/index mismatch"})
        unique.add(t2)
        missing_wind+=int(c["wind_valid"])==0
        wind_nz+=float(c["ws_mps"])<998.99 and float(c["ws_mps"])>0
        for k,key in float_fields.items():
            a,b=float(r[k]),float(c[key])
            if not math.isfinite(a) or not math.isfinite(b):
                raise ValueError("nonfinite original/C++ upper met value")
            err=abs(a-b)
            errors[key]=max(errors[key],err)
            tol=0.0002 if key not in ("u_mps","v_mps") else 0.0001
            if err>tol and len(failure)<30:
                failure.append({"record":i,"field":key,"fortran":a,"cpp":b,
                                "abs_error":err,"tolerance":tol})
    if wind_nz==0:raise RuntimeError("all upper air winds zero/missing; test is vacuous")
    return {"status":"PASS" if not failure else "FAIL",
            "station_count":1,"soundings":len(unique),"levels":len(rows),
            "compared_numeric_fields":len(rows)*8,
            "missing_wind_levels":missing_wind,
            "nonzero_wind_levels":wind_nz,
            "maximum_errors":errors,
            "first_mismatches":failure[:30]}
def main():
    p=argparse.ArgumentParser()
    for key in ("vendor","up","cpp","out"):p.add_argument("--"+key,required=True,type=Path)
    p.add_argument("--station",required=True,type=int)
    a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    src=a.vendor/"calmet.for"
    original=src.read_text()
    for anchor in [
      "subroutine rdhdu(","subroutine rdupn(",
      "format(9x,i8,2(4x,i4,i4,i3,i3,i5),8x,i5)",
      "format(4(3x,f6.1,1x,f5.0,1x,f5.1,1x,f3.0,1x,f3.0))",
      "dir=0.0174533*uaa(iup,i)",
      "uaa(iup,i)=-spd*sin(dir)",
      "vaa(iup,i)=-spd*cos(dir)",
    ]:
        if anchor not in original.lower():
            raise RuntimeError(f"Original RDUPN source anchor missing: {anchor}")
    driver=a.out/"rdupn_format_driver.for";driver.write_text(FORTRAN)
    binary=a.out/"original_rdupn_format"
    run(["gfortran","-O0","-std=legacy","-ffixed-line-length-none",driver,"-o",binary])
    fortran=a.out/"fortran_upper_levels.txt"
    modern=a.out/"cpp_upper_levels.csv"
    run([binary,a.up,fortran,a.station])
    run([a.cpp,a.up,modern,a.station])
    result=check(fortran,modern)
    result.update({"up_dat_sha256":sha(a.up),"fortran_driver_sha256":sha(driver),
                   "calmet_source_sha256":sha(src),
                   "original_call_path":"RDHDU → RDUPN (UP.DAT version 2.1, IFMTU=1, UTM no rotation)",
                   "scope_limit":"Native Fortran original selected RDUPN fixed-format + relative-height and wind conversion; not full original RDUPN AA/BB time flow or whole P6C completion"})
    (a.out/"p6c-upper-rdupn-format-parity.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
    if result["status"]!="PASS":raise SystemExit(1)
if __name__=="__main__":main()
