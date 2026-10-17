#!/usr/bin/env python3
"""Decode the selected original CALMET.DAT 2.1 hourly field/time structure.

Directly grounded in unchanged CALMET 6.5.0 OUTHD L12448-L12540,
OUTHR L13148-L13234, WRTR2D L36829-L36881, WRTI2D L36734-L36788.

Unlike a file-size smoke check, this verifies every expected 2-D field
name, dimensions and explicit start/end time interval for all 143 expected
*intervals* from 144 configured endpoint labels. It does not assert model
wind numerical correctness or full external CALPUFF compatibility.
"""
from __future__ import annotations
import argparse,collections,datetime,hashlib,json,math,struct
from pathlib import Path

NX=50; NY=50; NZ=9
LABELS=tuple(k for n in range(1,NZ+1)
               for k in (f"U-LEV{n:>3}",f"V-LEV{n:>3}",f"WFACE{n:>3}")) +\
       tuple(f"T-LEV{n:>3}" for n in range(1,NZ+1)) +\
       ("IPGT","USTAR","ZI","EL","WSTAR","TEMPK","RHO","QSW","IRH")
EXPECTED_RECORD_BYTES=8+4*4+NX*NY*4
EXPECTED_STEPS=143

def describe_hour(clock:int,seconds:int):
    year=clock//100000
    rest=clock%100000
    jul=rest//100
    hour=rest%100
    if not (2000<=year<=2100 and 1<=jul<=366 and 0<=hour<=23 and 0<=seconds<=3600):
        raise ValueError(f"invalid original explicit timestamp ({clock},{seconds})")
    start=datetime.datetime(year,1,1,tzinfo=datetime.timezone.utc)
    when=start+datetime.timedelta(days=jul-1,hours=hour,seconds=seconds)
    if when.year!=year and jul!=366:
        raise ValueError("out-of-year original CALMET timestamp")
    return when

def records(path:Path):
    with path.open("rb") as inp:
        idx=0
        while True:
            prefix=inp.read(4)
            if not prefix:break
            if len(prefix)!=4:raise ValueError("truncated original Fortran record prefix")
            (n,)=struct.unpack("<i",prefix)
            if n<0 or n>100000000:raise ValueError("unexpected big-endian or damaged record")
            payload=inp.read(n)
            tail=inp.read(4)
            if len(payload)!=n or len(tail)!=4 or struct.unpack("<i",tail)[0]!=n:
                raise ValueError("Fortran record marker mismatch")
            yield idx,payload
            idx+=1

def inspect(file:Path):
    iterator=records(file)
    first,p1=next(iterator)
    if first!=0 or not p1.startswith(b"CALMET.DAT") or b"2.1" not in p1[:40]:
        raise ValueError("Original CALMET.DAT 2.1 identity invalid")
    second,p2=next(iterator)
    if second!=1 or len(p2)!=4:raise ValueError("Original CALMET comment count missing")
    (ncom,)=struct.unpack("<i",p2)
    if not 0<=ncom<=10000:raise ValueError("Unreasonable original header comment count")
    for n in range(ncom):
        idx,p=next(iterator)
        if idx!=n+2 or len(p)!=132:raise ValueError("CALMET control comment record size")
    controls_idx,controls=next(iterator)
    if controls_idx!=ncom+2 or len(controls)<100:
        raise ValueError("Original CALMET run control header unexpectedly short")
    # Exact original OUTHD writer packs in this order:
    # 10 ints beginning/ending, timezone char8, 5 ints,
    # 3 real32 (spacing/grid origin), 8 ints ... .
    ten_ints=struct.unpack_from("<10i",controls,0)
    configured=(ten_ints[:5],ten_ints[5:])
    tz=controls[40:48].decode("ascii").strip()
    irlg,irtype,nx,ny,nz=struct.unpack_from("<5i",controls,48)
    grid_scale,orig_x,orig_y=struct.unpack_from("<3f",controls,68)
    wind_code,nssta,nusta,npsta=struct.unpack_from("<4i",controls,80)
    if (nx,ny,nz)!=(NX,NY,NZ) or irtype!=1 or wind_code!=1 or npsta!=0:
        raise ValueError(f"Unsupported original output settings {(nx,ny,nz,irtype,wind_code,npsta)}")
    if tz!="UTC+0000" or abs(grid_scale-100)>1e-4:
        raise ValueError(f"unexpected original time/grid parameters {tz} {grid_scale}")
    if nssta<1 or nusta<1:raise ValueError("no surface/upper station metadata")
    steps=collections.OrderedDict()
    headers=collections.Counter()
    samples={}
    recorded=0
    first_payload=None
    for idx,p in iterator:
        recorded+=1
        if len(p)<24:
            headers["short_metadata"]+=1
            continue
        label=p[:8].decode("ascii",errors="strict").strip()
        begin,sec_begin,end,sec_end=struct.unpack_from("<4i",p,8)
        if begin==0 and end==0:
            headers[label]+=1
            continue
        if len(p)!=EXPECTED_RECORD_BYTES:
            raise ValueError(f"hourly field payload bad size #{idx}: {label}: {len(p)}")
        beg_t=describe_hour(begin,sec_begin)
        end_t=describe_hour(end,sec_end)
        if (end_t-beg_t)!=datetime.timedelta(seconds=3600):
            raise ValueError(f"nonhourly original field {label}: {beg_t} to {end_t}")
        key=(beg_t,end_t)
        data=steps.setdefault(key,[])
        if len(data)==0 and label!=LABELS[0]:
            raise ValueError(f"hour starts with {label}, expected {LABELS[0]}")
        expected=LABELS[len(data)] if len(data)<len(LABELS) else "<none>"
        if label!=expected:
            raise ValueError(f"hour field order mismatch: {beg_t}: {label} != {expected}")
        data.append(label)
        if len(data)>len(LABELS):raise ValueError("too many fields for hour")
        if len(steps)==1:
            # Store only representative values, never an untrusted full numeric
            # field derived from historical weather; this is the new 2022 run.
            val=struct.unpack_from("<f",p,24)[0]
            if not math.isfinite(val):raise ValueError("nonfinite first-grid value")
            samples[label]={"cell_1_1_value":val,
                             "field_payload_sha256":hashlib.sha256(p).hexdigest()}
    if len(steps)!=EXPECTED_STEPS:
        raise ValueError(f"unexpected original full 5d+ hourly interval count {len(steps)} !=143")
    for key,fields in steps.items():
        if len(fields)!=len(LABELS):
            raise ValueError(f"hourly output missing fields: {key}: {len(fields)} != {len(LABELS)}")
    times=list(steps.keys())
    if times[0][0]!=datetime.datetime(2022,1,1,tzinfo=datetime.timezone.utc):
        raise ValueError(f"original CALMET starts at wrong time {times[0]}")
    if times[-1][1]!=datetime.datetime(2022,1,6,23,tzinfo=datetime.timezone.utc):
        raise ValueError(f"original CALMET ends at wrong time {times[-1]}")
    for i in range(1,len(times)):
        if times[i-1][1]!=times[i][0]:
            raise ValueError(f"original CALMET timeline gap/overlap {times[i-1]} -> {times[i]}")
    return {
        "status":"PASS_ORIGINAL_CALMET_EXPLICIT_TIME_AND_FIELD_LAYOUT",
        "scope":"Fortran binary field structure, NOT C++ wind model parity",
        "dataset":"CALMET.DAT 2.1","grid":[nx,ny,nz],
        "grid_spacing_m":grid_scale,
        "xorig_m":orig_x,"yorig_m":orig_y,
        "time_zone":tz,"irtype":irtype,"iwfcod":wind_code,
        "nssta":nssta,"nusta":nusta,"npsta":npsta,
        "legacy_reference_n_time_labels":144,"actual_n_hour_intervals":len(steps),
        "hour_interval_first":times[0][0].isoformat(),
        "hour_interval_end":times[-1][1].isoformat(),
        "fields_per_interval":len(LABELS),
        "total_hourly_fields":sum(map(len,steps.values())),
        "hourly_labels":LABELS,
        "number_original_control_comments":ncom,
        "header_labels_counts":dict(headers),
        "first_interval_representative_first_cell":samples,
        "original_calmet_sha256":hashlib.sha256(file.read_bytes()).hexdigest(),
        "source_anchors":["OUTH D original L12448-L12540","OUTHR L13148-L13234",
                          "WRTI2D L36734-L36788","WRTR2D L36829-L36881"],
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("met_dat",type=Path)
    ap.add_argument("--report",required=True,type=Path)
    a=ap.parse_args()
    result=inspect(a.met_dat)
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.report.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({key:val for key,val in result.items() if key not in
          ("first_interval_representative_first_cell","hourly_labels","header_labels_counts")},indent=2))
if __name__=="__main__":
    main()
