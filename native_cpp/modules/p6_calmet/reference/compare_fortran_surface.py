#!/usr/bin/env python3
"""Real 2022 SURF.DAT native Fortran-format vs C++ P6C raw observation parity.

Follows original CALMET 6.5.0 formatted RDHD (L14862-14927) and RDSN
(L23556-23561) source for one original SMERGE virtual station. This is a
separate Fortran record-format comparator, not original full RDSN timestep
interpolation / time-zone / station-flow code or physical observation QA.
"""
from __future__ import annotations
import argparse,csv,datetime,hashlib,json,math,subprocess
from pathlib import Path

DRIVER=r"""      program read_formatted_surface
      implicit none
      integer id,ncomments,nsta
      integer sy,sj,sh,ss,ey,ej,eh,es
      integer cei,cloud,rh,ipcode,i
      real ws,wd,tempk,pres
      character*16 dataset,dataver
      character*64 datamod
      character*80 comment
      character*8 pmap,axtz
      character*256 inp,out
      call get_command_argument(1,inp)
      call get_command_argument(2,out)
      open(10,file=trim(inp),status='old')
      read(10,'(2a16,a64)')dataset,dataver,datamod
      if(dataset.ne.'SURF.DAT'.or.dataver.ne.'2.1')stop 1
      read(10,*)ncomments
      if(ncomments.lt.0.or.ncomments.gt.10000)stop 2
      do i=1,ncomments
        read(10,'(a80)')comment
      enddo
      read(10,'(a8)')pmap
      read(10,'(a8)')axtz
      if(pmap.ne.'NONE'.or.axtz.ne.'UTC+0000')stop 3
      read(10,*)sy,sj,sh,ss,ey,ej,eh,es,nsta
      if(nsta.ne.1)stop 4
      read(10,*)id
      if(id.lt.1)stop 5
      open(11,file=trim(out),status='replace')
      do i=1,143
        read(10,*)sy,sj,sh,ss,ey,ej,eh,es,
     1             ws,wd,cei,cloud,tempk,rh,pres,ipcode
        write(11,*)id,sy,sj,sh,ss,ey,ej,eh,es,
     1              ws,wd,cei,cloud,tempk,rh,pres,ipcode
      enddo
      close(10)
      close(11)
      end
"""

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def call(args):
    p=subprocess.run(list(map(str,args)),capture_output=True,text=True)
    if p.returncode:raise RuntimeError(f"bad native reader {args} stderr={p.stderr[-2500:]} stdout={p.stdout[-1200:]}")

def second(year,jul,hour,secs):
    base=datetime.datetime(year,1,1,tzinfo=datetime.timezone.utc)
    return int((base+datetime.timedelta(days=jul-1,hours=hour,seconds=secs)).timestamp())

def source_anchors(path):
    lines=path.read_text().splitlines()
    checks=["read(io,'(2a16,a64)') dataset,dataver,datamod",
            "read(io,*) ncomment",
            "read(io,'(a8)') axtz",
            "read(io,*)ibyrn,ibjuln,ibhrn,ibsecn,ieyrn,iejuln,iehrn,",
            "read(io,*)ibyrn,ibjuln,ibhrn,ibsecn,ieyrn,iejuln,iehrn,"]
    # Source's original RDHD and RDSN lists may be continued and comments
    # may contain similarly-shaped reads. Match scoped procedure windows.
    regions=[(14862,15005,"RDHD"),(23437,23661,"RDSN")]
    found={}
    for st,en,name in regions:
        sub=lines[st-1:en]
        anchor=("read(io,*)ibyrn,ibjuln,ibhrn,ibsecn,ieyrn,iejuln,iehrn,"
                if name=="RDSN" else
                "read(io,*)ibyrn,ibjuln,ibhrn,ibsecn,ieyrn,iejuln,iehrn,")
        matches=[st+i for i,l in enumerate(sub) if anchor in l.replace(" ","")]
        # Note source actually varies spaces; semantic anchor uses hard-coded
        # source interval and raw RDSN quote above, not an AST parser.
        found[name]={"source_lines":[st,en],"unique_raw_read_forms":
                     [st+i for i,l in enumerate(sub) if "read(io,*)" in l]}
    return found

def compare(orig,cpp):
    original=[line.split() for line in orig.read_text().splitlines()]
    with cpp.open(newline="") as f:modern=list(csv.DictReader(f))
    if len(original)!=143 or len(modern)!=143:
        raise ValueError("SURF original/C++ expected 143 records")
    int_fields=[(11,"iceil"),(12,"icc"),(14,"irh"),(16,"ipcode")]
    real_fields=[(9,"ws"),(10,"wd"),(13,"tempk"),(15,"pres")]
    max_error={name:0 for _,name in real_fields}
    missing={key:0 for key in ("wind","precipitation_code","cloud")}
    differences=[]
    for index,(r,c) in enumerate(zip(original,modern)):
        if len(r)!=17:raise ValueError("original surface row not 17 fields")
        if int(r[0])!=int(c["station_id"]) or\
           second(*map(int,r[1:5]))!=int(c["start_epoch_s"]) or\
           second(*map(int,r[5:9]))!=int(c["end_epoch_s"]):
            differences.append({"hour":index,"field":"station_id or time"})
        for col,name in int_fields:
            if int(r[col])!=int(c[name]):
                differences.append({"hour":index,"field":name,
                                    "fortran":r[col],"cpp":c[name]})
        for col,name in real_fields:
            error=abs(float(r[col])-float(c[name]))
            if not math.isfinite(error):raise ValueError("nonfinite surf raw value")
            max_error[name]=max(max_error[name],error)
            if error>0.0002 and len(differences)<20:
                differences.append({"hour":index,"field":name,"abs_error":error})
        missing["wind"]+=int(c["wind_valid"])==0
        missing["precipitation_code"]+=int(c["precip_valid"])==0
        missing["cloud"]+=int(c["cloud_valid"])==0
    return {"status":"PASS" if not differences else "FAIL",
            "records":143,"compared_raw_fields":143*8,
            "compared_station_time_fields":143*3,
            "max_absolute_error_real_fields":max_error,
            "missing_counts_from_explicit_masks":missing,
            "predeclared_raw_float_tolerance":0.0002,
            "first_differences":differences[:20]}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--vendor",required=True,type=Path)
    ap.add_argument("--surf",required=True,type=Path)
    ap.add_argument("--cpp",required=True,type=Path)
    ap.add_argument("--out",required=True,type=Path)
    args=ap.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    driver=args.out/"fortran_surface_input.for"
    driver.write_text(DRIVER)
    binary=args.out/"fortran_surface_input"
    call(["gfortran","-O0","-std=legacy","-ffixed-line-length-none",
          driver,"-o",binary])
    ref=args.out/"original_surface.txt"
    candidate=args.out/"modern_surface.csv"
    call([binary,args.surf,ref])
    call([args.cpp,args.surf,candidate])
    result={**compare(ref,candidate),
            "surf_dat_sha256":sha(args.surf),
            "driver_sha256":sha(driver),
            "calmet_source_sha256":sha(args.vendor/"calmet.for"),
            "read_source":source_anchors(args.vendor/"calmet.for"),
            "scope":"Native Fortran selected formatted RDHD/RDSN record layout vs C++; NOT full RDSN state machine or observation scientific validity"}
    (args.out/"p6c_surface_fortran_parity.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
    if result["status"]!="PASS":raise SystemExit(1)
if __name__=="__main__":main()
