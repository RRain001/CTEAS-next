#!/usr/bin/env python3
"""Pinned unmodified original CALMET 6h COMP TEMP3D write-only oracle.

Source physical statements unchanged; only append 6h × 82×85×9
original ZTEMP after selected source TEMP3D. All 45 MET fields must
remain byte-identical with an independently executed pristine original.
"""
from __future__ import annotations
import argparse,hashlib,json,math,struct,subprocess,tempfile
from datetime import datetime,timedelta,timezone
from pathlib import Path
BLOB="437f43bb7f0e51a1919e56664663e1a046986ed0"
NX,NY,NZ,NH=82,85,9,6
NC=NX*NY*NZ
FIRST=datetime(2022,6,1,1,tzinfo=timezone.utc)
NAME="s4r1c8h-original-comp-temp3d.bin"
HEAD=struct.Struct("<6i")
FIELD=struct.Struct("<"+str(NC)+"f")
ROW=HEAD.size+FIELD.size
PINS={
    4760:"       if( LCALGRD .or. itprog.ge.1 )then",
    4766:"             call temp3d(nyrze,njulze,nhrze,nsecze,temp2d,ziconv,",
    4767:"     &                tzgraa,tzgrbb,ztemp,zi,tprog)",
    4772:"          endif",
    4773:"c",
}
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def pinned(path:Path):
    blob=subprocess.run(["git","hash-object",str(path)],
                        check=True,capture_output=True,text=True).stdout.strip()
    if blob!=BLOB:raise ValueError("S4R1c8h original CALMET immutable blob drift")
    a=path.read_text().splitlines(keepends=True)
    for ln,value in PINS.items():
        if a[ln-1].rstrip("\n")!=value:
            raise ValueError(f"S4R1c8h original TEMP3D source anchor L{ln} moved")
    return a
HOOK="""      open(unit=94,file='s4r1c8h-original-comp-temp3d.bin',
     1 form='unformatted',access='stream',status='unknown',
     2 position='append')
      write(94) 60,ndathrb,nsecb,nx,ny,nz
      write(94) (((ztemp(i,j,k),i=1,nx),j=1,ny),k=1,nz)
      close(unit=94)
"""
def prepare(vendor:Path,destination:Path,receipt:Path):
    a=pinned(vendor)
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text("".join(a[:4772])+HOOK+"".join(a[4772:]))
    receipt.parent.mkdir(parents=True,exist_ok=True)
    receipt.write_text(json.dumps({
        "status":"PREPARED_S4R1C8H_SHA_PINNED_ORIGINAL_TEMP3D_WRITE_ONLY",
        "original_vendor_git_blob":BLOB,
        "original_vendor_sha256":sha(vendor),
        "scratch_source_sha256":sha(destination),
        "hook_after_original_fortran_line":4772,
        "original_physics_modified":False,
        "native_temp3d_accepted":False,
    },indent=2,sort_keys=True)+"\n")
    print("S4R1C8H_ORIGINAL_TEMP3D_SHA_PIN=PASS")
def decode(path:Path):
    raw=path.read_bytes()
    if len(raw)!=NH*ROW:
        raise ValueError("S4R1c8h original sixhour TEMP3D binary extent wrong")
    fields=[]
    for hr in range(NH):
        off=hr*ROW
        time=FIRST+timedelta(hours=hr)
        packed=time.year*100000+time.timetuple().tm_yday*100+time.hour
        header=HEAD.unpack_from(raw,off)
        if header!=(60,packed,0,NX,NY,NZ):
            raise ValueError(f"S4R1c8h original TEMP3D header/source hour drift {header}")
        a=FIELD.unpack_from(raw,off+HEAD.size)
        if not all(math.isfinite(x) and 180<=x<=350 for x in a):
            raise ValueError("S4R1c8h original TEMP3D thermal field invalid")
        fields.append(a)
    return fields
def verify(vendor:Path,pristine:Path,scratch:Path,trace:Path,report:Path):
    pinned(vendor)
    if sha(pristine)!=sha(scratch):
        raise ValueError("S4R1c8h original TEMP3D trace altered sixhour MET.DAT 45-fields")
    data=decode(trace)
    first=data[0]
    if not any(v!=first[0] for v in first):
        raise ValueError("S4R1c8h original TEMP3D is trivially uniform")
    result={
        "status":"PASS_SOURCE_ONLY_ORIGINAL_NOAA_6H_TEMP3D",
        "source_scope":"2022_2SS1US_82x85x9_6h",
        "source_vendor_blob":BLOB,
        "pristine_45field_met_sha256":sha(pristine),
        "instrumented_45field_met_sha256":sha(scratch),
        "sixhour_original_met_byte_identical":True,
        "trace_sha256":sha(trace),
        "sixhour_float_counts":[len(x) for x in data],
        "firsthour_temperature_min_k":min(first),
        "firsthour_temperature_max_k":max(first),
        "source_native_temp3d":"NOT_RUN",
        "causal_sixhour_g26_p7":"NOT_ACCEPTED",
    }
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("S4R1C8H_ORIGINAL_6H_TEMP3D=PASS_REFERENCE_ONLY")
    print("S4R1C8H_ORIGINAL_6H45_MET=BYTE_IDENTICAL")
    print("S4R1C8H_G26_P7=NOT_ACCEPTED")
def selftest():
    with tempfile.TemporaryDirectory() as d:
        p=Path(d)/NAME
        with p.open("wb") as f:
            for hr in range(NH):
                t=FIRST+timedelta(hours=hr)
                packed=t.year*100000+t.timetuple().tm_yday*100+t.hour
                f.write(HEAD.pack(60,packed,0,NX,NY,NZ))
                f.write(FIELD.pack(*([270.]*NC)))
        assert len(decode(p))==6
        q=bytearray(p.read_bytes());q[0]=1;p.write_bytes(q)
        try:decode(p)
        except ValueError:pass
        else:raise AssertionError("S4R1c8h forged source header accepted")
    print("S4R1C8H_TEMP3D_ORIGINAL_HEADER_NEGATIVE=PASS")
def main():
    p=argparse.ArgumentParser()
    cmd=p.add_subparsers(dest="cmd",required=True)
    for name,args in (("prepare",("vendor","destination","receipt")),
                      ("verify",("vendor","pristine","scratch","trace","report"))):
        sub=cmd.add_parser(name)
        for x in args:sub.add_argument("--"+x,required=True,type=Path)
    cmd.add_parser("selftest")
    a=p.parse_args()
    if a.cmd=="prepare":prepare(a.vendor,a.destination,a.receipt)
    elif a.cmd=="verify":verify(a.vendor,a.pristine,a.scratch,a.trace,a.report)
    else:selftest()
if __name__=="__main__":main()
