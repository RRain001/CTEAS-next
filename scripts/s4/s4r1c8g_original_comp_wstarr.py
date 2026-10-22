#!/usr/bin/env python3
"""SHA-pinned original CALMET COMP WSTARR 6h oracle, write-only scratch.

The original Fortran physical formula is left untouched. The 6-hour
45-field MET.DAT must remain byte identical after tracing. Native G55
never receives any original WSTAR or other original intermediate fields.
"""
from __future__ import annotations
import argparse,hashlib,json,math,struct,subprocess,tempfile
from datetime import datetime,timedelta,timezone
from pathlib import Path
BLOB="437f43bb7f0e51a1919e56664663e1a046986ed0"
NX,NY,NH=82,85,6
NC=NX*NY
FIRST=datetime(2022,6,1,1,tzinfo=timezone.utc)
NAME="s4r1c8g-original-comp-wstarr.bin"
HEAD=struct.Struct("<5i")
GRID=struct.Struct("<"+str(NC)+"f")
RECORD=HEAD.size+GRID.size
PINS={
  4740:"c --- compute convective velocity scale *** LAND CELLS ***",
  4744:"          call wstarr(ziconv,qh,temp2d,rho,ilandu,iwat1,iwat2,nx,ny,",
  4745:"     1   wstar)",
  4750:"      endif",
}
HELPER=r"""
c S4-R1c8g original selected COMP WSTARR, write-only after call
      subroutine s4c8g_wstar(raw)
      include 'params.met'
      include 'gen.met'
      include 'grid.met'
      real raw(mxnx,mxny)
      integer i,j
      logical opened
      save opened
      data opened/.false./
      if(.not.opened)then
         open(91,file='s4r1c8g-original-comp-wstarr.bin',
     1        form='unformatted',access='stream',status='replace')
         opened=.true.
      endif
      write(91) 59,ndathrb,nsecb,nx,ny
      write(91) ((raw(i,j),i=1,nx),j=1,ny)
      return
      end
"""
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def checked_vendor(path:Path)->list[str]:
    blob=subprocess.run(["git","hash-object",str(path)],
                        capture_output=True,text=True,check=True).stdout.strip()
    if blob!=BLOB:raise ValueError("original CALMET WSTARR source blob changed")
    rows=path.read_text().splitlines(keepends=True)
    for ln,value in PINS.items():
        if rows[ln-1].rstrip("\n")!=value:
            raise ValueError(f"original Fortran WSTARR source L{ln} shifted")
    return rows
def prepare(vendor:Path,destination:Path,receipt:Path)->None:
    a=checked_vendor(vendor)
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text("".join(a[:4750])+
                           "      call s4c8g_wstar(wstar)\n"+
                           "".join(a[4750:])+HELPER)
    receipt.parent.mkdir(parents=True,exist_ok=True)
    receipt.write_text(json.dumps({
        "status":"PINNED_ORIGINAL_WSTARR_WRITE_ONLY",
        "original_vendor_git_blob":BLOB,
        "original_vendor_sha256":sha(vendor),
        "scratch_writer_sha256":sha(destination),
        "hook_after_original_fortran_line":4750,
        "physics_changed":False,
        "native_g55_accepted":False,
    },indent=2,sort_keys=True)+"\n")
    print("S4R1C8G_PIN_ORIGINAL_WSTARR=PASS")
def records(trace:Path):
    b=trace.read_bytes()
    if len(b)!=NH*RECORD:
        raise ValueError("G55 original CALMET WSTARR record count/size wrong")
    out=[]
    for h in range(NH):
        off=h*RECORD
        when=FIRST+timedelta(hours=h)
        packed=when.year*100000+when.timetuple().tm_yday*100+when.hour
        if HEAD.unpack_from(b,off)!=(59,packed,0,NX,NY):
            raise ValueError("G55 original WSTARR clock or grid mismatch")
        row=GRID.unpack_from(b,off+HEAD.size)
        if not all(math.isfinite(x) and x>=0 for x in row):
            raise ValueError("G55 original WSTARR nonfinite/negative")
        out.append(row)
    return out
def verify(vendor:Path,pristine:Path,scratch:Path,trace:Path,report:Path)->None:
    checked_vendor(vendor)
    if sha(pristine)!=sha(scratch):
        raise ValueError("original WSTARR-only tracing changed pristine MET.DAT")
    data=records(trace)
    first=data[0]
    if not any(x>0 for x in first):
        raise ValueError("original firsthour WSTARR is all zero, numeric scope not tested")
    result={
        "status":"PASS_ORIGINAL_GENUINE_NOAA_SIXHOUR_WSTARR_REFERENCE_ONLY",
        "original_vendor_blob":BLOB,
        "original_pristine_met_sha256":sha(pristine),
        "original_instrumented_met_sha256":sha(scratch),
        "original_sixhour_45field_met_byte_identical":True,
        "original_wstarr_trace_sha256":sha(trace),
        "grid":[NX,NY],
        "sixhour_real4_counts":[len(x) for x in data],
        "firsthour_nonzero_cell_count":sum(x>0 for x in first),
        "firsthour_wstar_min_mps":min(first),
        "firsthour_wstar_max_mps":max(first),
        "native_firsthour_wstarr":"NOT_RUN",
        "native_temp3d_g26_p7":"NOT_ACCEPTED",
    }
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("S4R1C8G_ORIGINAL_6H_WSTARR=PASS_REFERENCE_ONLY")
    print("S4R1C8G_ORIGINAL_6H45_MET=BYTE_IDENTICAL")
    print("S4R1C8G_NATIVE_G26_P7=NOT_ACCEPTED")
def selftest():
    with tempfile.TemporaryDirectory() as d:
        p=Path(d)/NAME
        with p.open("wb") as f:
            for h in range(NH):
                w=FIRST+timedelta(hours=h)
                packed=w.year*100000+w.timetuple().tm_yday*100+w.hour
                f.write(HEAD.pack(59,packed,0,NX,NY))
                f.write(GRID.pack(*([.5]*NC)))
        assert len(records(p))==NH
        b=bytearray(p.read_bytes());b[0]=42;p.write_bytes(b)
        try:records(p)
        except ValueError:pass
        else:raise AssertionError("G55 accepted forged original clock header")
    print("S4R1C8G_ORIGINAL_WSTARR_NEGATIVE_SCHEMA=PASS")
def main():
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest="cmd",required=True)
    for cmd,fields in (
        ("prepare",("vendor","destination","receipt")),
        ("verify",("vendor","pristine","scratch","trace","report"))):
        s=sub.add_parser(cmd)
        for k in fields:s.add_argument("--"+k,required=True,type=Path)
    sub.add_parser("selftest")
    q=p.parse_args()
    if q.cmd=="prepare":prepare(q.vendor,q.destination,q.receipt)
    elif q.cmd=="verify":verify(q.vendor,q.pristine,q.scratch,q.trace,q.report)
    else:selftest()
if __name__=="__main__":main()
