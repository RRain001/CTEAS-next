#!/usr/bin/env python3
"""CALMET PREPDI source-exact U/V time interpolation, 143 hours, 9 layers.

Fortran uses literal PREPDI original source lines (xfact + jorder arrays).
Upper profile wind source is output of literal original VERTAV on same P4
2022 UP.DAT, while independent C++ parses the raw original UP.DAT.
Chronological bracket labels computed from literal UP.DAT 6201 record
times, independent of the C++ hourly scheduler. This verifies numerical
PREPDI interpolation but NOT full original COMP loop/station states.
"""
from __future__ import annotations
import argparse,bisect,csv,datetime,hashlib,json,math,re,subprocess
from pathlib import Path

HEAD=r"""      program prepdi_source_time
      implicit none
      integer nz,j,n,idx,nhours,jorder,jdelta,jtogo,i
      real xfact
      real uaveaa(9,1),uavebb(9,1),vaveaa(9,1),vavebb(9,1)
      real uave(9,1),vave(9,1)
      character*256 inp,out
      nz=9
      j=1
      jorder=1
      call get_command_argument(1,inp)
      call get_command_argument(2,out)
      open(10,file=trim(inp),status='old')
      open(11,file=trim(out),status='replace')
      read(10,*)nhours
      do idx=1,nhours
        read(10,*)jdelta,jtogo,jorder
        if(jorder.ne.-1.and.jorder.ne.1)stop 15
        if(jdelta.lt.3600.or.jdelta.gt.50400)stop 13
        if(jtogo.lt.0.or.jtogo.gt.jdelta)stop 14
        do n=1,nz
          read(10,*)uaveaa(n,1),vaveaa(n,1),
     1               uavebb(n,1),vavebb(n,1)
        enddo
"""
TAIL=r"""        do n=1,nz
          write(11,'(2(I4,1X),2(ES22.13E3,1X))')
     1       idx,n,uave(n,1),vave(n,1)
        enddo
      enddo
      close(10)
      close(11)
      end
"""
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def run(args):
    r=subprocess.run(list(map(str,args)),capture_output=True,text=True)
    if r.returncode:raise RuntimeError(f"PREPDI reference error {args}: rc={r.returncode}, stderr={r.stderr[-1600:]}, stdout={r.stdout[-1600:]}")
def extract(path,destination):
    ls=path.read_text().splitlines(keepends=True)
    begin=[i for i,l in enumerate(ls) if l.lower().startswith("      subroutine prepdi(")]
    end=[i for i,l in enumerate(ls) if l.lower().startswith("      subroutine progrd(")]
    if len(begin)!=1 or len(end)!=1 or end[0]<=begin[0]:
        raise RuntimeError("original CALMET PREPDI procedure boundaries drifted")
    st=[i for i in range(begin[0],end[0])
        if ls[i].strip()=="xfact = float(jtogo) / float(jdelta)"]
    if len(st)!=2:
        raise RuntimeError(f"unexpected PREPDI in-routine time factors: {st}")
    # Second original occurrence is PREPDI's per-layer UAVE time loop.
    i=st[1]
    en=next((j for j in range(i+1,i+15) if ls[j].strip()=="15    continue"),None)
    if en is None:raise RuntimeError("PREPDI ending original DO15 not found")
    snippet="".join(ls[i:en+1])
    for required in ("uave(i,j)=uaveaa(i,j)","uave(i,j)=uavebb(i,j)","vave(i,j)=vavebb(i,j)"):
        if required not in snippet:raise RuntimeError("PREPDI changed source logic")
    destination.write_text(HEAD+snippet+TAIL)
    return {"original_source_sha256":sha(path),
            "PREPDI_source_line_first":i+1,"PREPDI_source_line_last":en+1,
            "Fortran_driver_sha256":sha(destination)}
def parse_profiles(path):
    dates=[]
    for line in path.read_text().splitlines():
        if not line.startswith("   6201"):continue
        x=line.split()
        if len(x)!=14 or x[0]!="6201":raise ValueError("unexpected current original UP.DAT 6201 metadata")
        y,month,day,h,sec=map(int,x[7:12])
        t=datetime.datetime(y,month,day,h,0,sec,tzinfo=datetime.timezone.utc)
        if y!=2022 or t.hour not in (0,12):raise ValueError("upper sounding outside original 12h case")
        dates.append(int(t.timestamp()))
    if len(dates)!=13 or len(set(dates))!=13 or dates!=sorted(dates):
        raise ValueError(f"expected 13 unique 2022 UP.DAT soundings, got {len(dates)}")
    return dates
def parse_vertav(file):
    profiles={}
    for line in file.read_text().splitlines():
        n,nlev,k,u,v=line.split()
        n=int(n);k=int(k)
        profiles.setdefault(n,{})[k]=(float(u),float(v))
    if len(profiles)!=13 or any(set(layers)!=set(range(1,10)) for layers in profiles.values()):
        raise ValueError("original VERTAV fields not complete")
    return profiles
def make_hour_data(out,profile_times,vertav):
    start=int(datetime.datetime(2022,1,1,tzinfo=datetime.timezone.utc).timestamp())
    inputs=[]
    with out.open("w") as h:
        h.write("143\n")
        for index in range(1,144):
            t=start+index*3600
            next_index=bisect.bisect_right(profile_times,t)
            if next_index<=0 or next_index>=len(profile_times):
                raise ValueError(f"unbracketed original sounding {index}")
            lower=next_index-1
            delta=profile_times[next_index]-profile_times[lower]
            togo=profile_times[next_index]-t
            if delta!=43200 or not 0<=togo<=delta:
                raise ValueError(f"bad original profile window {index}")
            jorder=1 if lower%2==0 else -1
            inputs.append({"hour":index,"lower":lower+1,"higher":next_index+1,
                           "gap":delta,"togo":togo,"jorder":jorder})
            h.write(f"{delta} {togo} {jorder}\n")
            for layer in range(1,10):
                prior_u,prior_v=vertav[lower+1][layer]
                newest_u,newest_v=vertav[next_index+1][layer]
                if jorder>0:
                    aa_u,aa_v,bb_u,bb_v=prior_u,prior_v,newest_u,newest_v
                else:
                    aa_u,aa_v,bb_u,bb_v=newest_u,newest_v,prior_u,prior_v
                h.write(f"{aa_u:.13e} {aa_v:.13e} {bb_u:.13e} {bb_v:.13e}\n")
    return inputs
def compare(ref,modern,expected):
    a=[line.split() for line in ref.read_text().splitlines()]
    with modern.open(newline="") as h:b=list(csv.DictReader(h))
    if len(a)!=1287 or len(b)!=1287:raise ValueError("143 hourly x9 wind layers missing")
    errors={"u_mps":0.,"v_mps":0.}
    failures=[]
    for n,(r,c) in enumerate(zip(a,b)):
        hour=n//9+1;layer=n%9+1;match=expected[hour-1]
        if len(r)!=4 or int(r[0])!=hour or int(r[1])!=layer or\
           int(c["hour_index"])!=hour or int(c["layer"])!=layer or\
           int(c["aa_sounding"])!=match["lower"] or int(c["bb_sounding"])!=match["higher"] or\
           int(c["gap_s"])!=match["gap"] or int(c["to_go_s"])!=match["togo"]:
            raise ValueError(f"original/C++ profile timeline index or bracket mismatch at {n}")
        for i,key in ((2,"u_mps"),(3,"v_mps")):
            x,y=float(r[i]),float(c[key])
            if not (math.isfinite(x) and math.isfinite(y)):
                raise ValueError("PREPDI nonfinite wind values")
            d=abs(x-y)
            errors[key]=max(errors[key],d)
            if d>0.0003 and len(failures)<25:
                failures.append({"hour":hour,"layer":layer,"field":key,"fortran":x,"modern":y,"error":d})
    return {"status":"PASS" if not failures else "FAIL",
            "compared_hourly_layer_wind_components":2574,
            "jorder_positive_hours":sum(x["jorder"]==1 for x in expected),
            "jorder_negative_hours":sum(x["jorder"]==-1 for x in expected),
            "jorder_switches":sum(expected[i]["jorder"]!=expected[i-1]["jorder"] for i in range(1,len(expected))),
            "one_hour_intervals":143,"layers_per_hour":9,
            "max_abs_error_mps":errors,"frozen_tolerance_mps":0.0003,
            "first_mismatches":failures}
def main():
    a=argparse.ArgumentParser()
    for name in ("vendor","up","original-vertav","modern-hourly","out"):
        a.add_argument("--"+name,required=True,type=Path)
    p=a.parse_args()
    p.out.mkdir(parents=True,exist_ok=True)
    drv=p.out/"source_prepdi_time.for"
    source=extract(p.vendor/"calmet.for",drv)
    binary=p.out/"source_prepdi_time"
    run(["gfortran","-O0","-std=legacy","-ffixed-line-length-none",
         drv,"-o",binary])
    input_file=p.out/"original_vertav_to_prepdi.txt"
    profile_stamps=parse_profiles(p.up)
    timeline=make_hour_data(input_file,profile_stamps,parse_vertav(p.original_vertav))
    reference=p.out/"original_prepdi_143h.txt"
    run([binary,input_file,reference])
    result=compare(reference,p.modern_hourly,timeline)
    result.update({"reference":source,"input_up_sha256":sha(p.up),
                   "original_vertav_sha256":sha(p.original_vertav),
                   "limits":"Selected PREPDI with both original JORDER branches on all 143h; independent live COMP instrumented source audit is a separate gate. No CGAMMA or diagnostic wind parity."})
    (p.out/"p6c-prepdi-time-parity.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
    if result["status"]!="PASS":raise SystemExit(1)
if __name__=="__main__":main()
