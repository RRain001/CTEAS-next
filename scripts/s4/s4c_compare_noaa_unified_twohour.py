#!/usr/bin/env python3
"""Independent fixed original Fortran 6h vs shared native G14 first TWO hours.

The native physics actor never reads original result; original sequential
MET.DAT is opened exclusively here after the native execution completed.
"""
from __future__ import annotations
import argparse
import json
import math
import struct
from pathlib import Path
from scripts.s4.s4r1c8i_compare_noaa_43_real_p6f import (
    LABELS, NC, NX, NY, NZ, F32, INT, fortran_records, tol,
)
from scripts.s4.s4c_compare_noaa_unified_firsthour import digest
from scripts.s4.s4r1c9ah_compare_hour6_p6f45 import read_hour


def native_two_hours(path: Path) -> tuple[dict[str, bytes], dict[str, bytes]]:
    records=fortran_records(path.read_bytes())
    if len(records)<4 or len(records[0])!=96 or (
       records[0][:16].decode('ascii').strip()!='CALMET.DAT'):
        raise ValueError('native CALMET.DAT 2.1 signature absent')
    if len(records[1])!=4:
        raise ValueError('native CALMET comments header invalid')
    (ncom,)=struct.unpack('<i',records[1])
    if not 0<=ncom<10000 or ncom+3>len(records):
        raise ValueError('native comment record count invalid')
    header=records[ncom+2]
    if len(header)!=176:
        raise ValueError('native CALMET output header invalid')
    dims=struct.unpack_from('<5i',header,48)
    stations=struct.unpack_from('<4i',header,80)
    if dims!=(2,1,NX,NY,NZ) or stations!=(1,2,1,0):
        raise ValueError(f'native grid/time/station dimensions drifted: {dims}/{stations}')
    hourly=[]
    for record in records[ncom+3:]:
        if len(record)<24:
            raise ValueError('truncated native MET field')
        clock=struct.unpack_from('<4i',record,8)
        if clock[0]==0 and clock[2]==0:
            continue
        if len(record)!=24+4*NC:
            raise ValueError('wrong real/integer grid size')
        hourly.append((record[:8].decode('ascii'),clock,record[24:]))
    if len(hourly)!=90:
        raise ValueError(f'native MET not two full 45-field hours: {len(hourly)}')
    out=[]
    for index in range(2):
        block=hourly[45*index:45*(index+1)]
        if [label for label,_,_ in block]!=LABELS:
            raise ValueError(f'native field names/order drift at hour {index+1}')
        h=202215201+index
        if {clock for _,clock,_ in block}!={(h,0,h,3600)}:
            raise ValueError(f'native hour {index+1} UTC clock drift')
        out.append({label:payload for label,_,payload in block})
    return out[0],out[1]


def audit(original:Path,native:Path,original_sha:str,native_sha:str,report:Path)->dict:
    if original.resolve()==native.resolve() or report.exists():
        raise ValueError('independent originals and unoccupied report required')
    if digest(original)!=original_sha or digest(native)!=native_sha:
        raise ValueError('frozen original/native SHA256 mismatch')
    ref=(read_hour(original,6,0),read_hour(original,6,1))
    got=native_two_hours(native)
    entries=[];first_diffs=[];total_bad=0;total_bitwise=0
    for index in range(2):
        fields={};bad=0;bits=0
        for label in LABELS:
            a=ref[index][label];b=got[index][label]
            exact=sum(a[k:k+4]==b[k:k+4] for k in range(0,4*NC,4))
            bits+=exact
            integer=label in ('IPGT    ','IRH     ')
            unpack=INT if integer else F32
            bad_field=0;max_abs=0.0
            for cell,(x,y) in enumerate(zip(unpack.unpack(a),unpack.unpack(b),strict=True)):
                if not integer and (not math.isfinite(x) or not math.isfinite(y)):
                    raise ValueError('nonfinite original/native physical field')
                diff=abs(x-y);max_abs=max(max_abs,diff)
                if (x!=y if integer else diff>tol(label,x,y)):
                    bad_field+=1
                    if len(first_diffs)<24:
                        first_diffs.append({'hour':index+1,'field':label.strip(),
                                            'i':cell%NX+1,'j':cell//NX+1,
                                            'abs_diff':diff})
            fields[label.strip()]={'count':NC,'bitwise_equal':exact,
                                   'frozen_exceedances':bad_field,'max_abs':max_abs}
            bad+=bad_field
        entries.append({'hour_ordinal':index+1,
                        'source_end_utc':f'2022-06-01 {index+2:02d}:00 UTC',
                        'compared_values':45*NC,'bitwise_equal':bits,
                        'frozen_exceedances':bad,'fields':fields})
        total_bad+=bad;total_bitwise+=bits
    result={'status':('PASS_SCOPED_S4C_SHARED_TWOHOUR_FORTRAN_90' if not total_bad
                      else 'FAIL_S4C_SHARED_TWOHOUR_FORTRAN_90'),
            'original_met_sha256':original_sha,'native_met_sha256':native_sha,
            'native_hours':2,'original_hours':6,'grid':[NX,NY,NZ],
            'stations':[2,1],'water_cells':63,'compared_fields':90,
            'compared_values':90*NC,'bitwise_equal':total_bitwise,
            'frozen_exceedances':total_bad,'first_differences':first_diffs,
            'hours':entries,'state_carry':'NATIVE_G14_COMMITTED_PREPOST_BITS_VERIFIED',
            'production_P6':'NOT_ACCEPTED','P7':'NOT_RUN',
            'independent_science_review':'NOT_RUN'}
    report.write_text(json.dumps(result,indent=2)+'\n')
    return result


def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument('--original',required=True,type=Path)
    p.add_argument('--native',required=True,type=Path)
    p.add_argument('--original-sha256',required=True)
    p.add_argument('--native-sha256',required=True)
    p.add_argument('--report',required=True,type=Path)
    a=p.parse_args()
    result=audit(a.original,a.native,a.original_sha256,a.native_sha256,a.report)
    print(result['status'], 'values', result['compared_values'],
          'bitwise',result['bitwise_equal'],
          'exceedances',result['frozen_exceedances'])
    if result['frozen_exceedances']:
        raise SystemExit(3)

if __name__=='__main__':
    main()
