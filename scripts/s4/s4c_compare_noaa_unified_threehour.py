#!/usr/bin/env python3
"""Independent fixed Fortran original vs S4B2 WATER G14 scoped prefix.

The same frozen reader and field tolerances work for 3..6 hours without
copying per-hour audit scripts. The 3-hour public API remains compatible.
Original result is read only after native execution, never as model forcing.
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


def native_prefix_hours(path: Path, expected_hours: int) -> tuple[dict[str, bytes], ...]:
    if expected_hours not in (3,4,5,6):
        raise ValueError('native NOAA scoped audit supports only 3..6h')
    records=fortran_records(path.read_bytes())
    if len(records)<4 or len(records[0])!=96 or (
       records[0][:16].decode('ascii').strip()!='CALMET.DAT'):
        raise ValueError('native CALMET.DAT 2.1 signature absent')
    if len(records[1])!=4:
        raise ValueError('native CALMET comments invalid')
    (ncom,)=struct.unpack('<i',records[1])
    if not 0<=ncom<10000 or ncom+3>len(records):
        raise ValueError('native comment record count invalid')
    header=records[ncom+2]
    if len(header)!=176:
        raise ValueError('native CALMET output header invalid')
    dims=struct.unpack_from('<5i',header,48)
    stations=struct.unpack_from('<4i',header,80)
    if dims!=(expected_hours,1,NX,NY,NZ) or stations!=(1,2,1,0):
        raise ValueError(f'native prefix grid/time/stations mismatch: {dims}/{stations}')
    hourly=[]
    for record in records[ncom+3:]:
        if len(record)<24:
            raise ValueError('truncated native MET field')
        clock=struct.unpack_from('<4i',record,8)
        if clock[0]==0 and clock[2]==0:
            continue
        if len(record)!=24+4*NC:
            raise ValueError('native field is not 6970 REAL4/INTEGER4 cells')
        hourly.append((record[:8].decode('ascii'),clock,record[24:]))
    if len(hourly)!=45*expected_hours:
        raise ValueError(f'native prefix needs {45*expected_hours} fields: {len(hourly)}')
    results=[]
    for index in range(expected_hours):
        group=hourly[45*index:45*(index+1)]
        if [label for label,_,_ in group]!=LABELS:
            raise ValueError(f'native 45 field labels/order invalid at {index+1}')
        expected=202215201+index
        if {clock for _,clock,_ in group}!={(expected,0,expected,3600)}:
            raise ValueError(f'native hour {index+1} UTC differs from original')
        results.append({label:payload for label,_,payload in group})
    return tuple(results)


def native_three_hours(path: Path) -> tuple[dict[str, bytes], ...]:
    """Backward compatible fixed-three-hour parser and negative tests."""
    return native_prefix_hours(path,3)


def audit(original:Path,native:Path,original_sha:str,native_sha:str,
          report:Path,native_hours:int=3)->dict:
    if original.resolve()==native.resolve() or report.exists():
        raise ValueError('independent original/native and unoccupied report required')
    if digest(original)!=original_sha or digest(native)!=native_sha:
        raise ValueError('frozen original/native SHA256 mismatch')
    if native_hours not in (3,4,5,6):
        raise ValueError('native NOAA scoped audit requires 3..6 committed hours')
    source=tuple(read_hour(original,6,h) for h in range(native_hours))
    calculated=native_prefix_hours(native,native_hours)
    first_differences=[];hours=[];total_bad=0;total_equal=0
    for hour in range(native_hours):
        compare=source[hour];got=calculated[hour]
        fields={};bad=0;equal=0
        for label in LABELS:
            a=compare[label];b=got[label]
            n_equal=sum(a[i:i+4]==b[i:i+4] for i in range(0,4*NC,4))
            equal+=n_equal
            is_integer=label in ('IPGT    ','IRH     ')
            unpack=INT if is_integer else F32
            excess=0;biggest=0.0
            for cell,(x,y) in enumerate(zip(unpack.unpack(a),unpack.unpack(b),strict=True)):
                if not is_integer and (not math.isfinite(x) or not math.isfinite(y)):
                    raise ValueError('nonfinite original/native P6F REAL4 field')
                delta=abs(x-y);biggest=max(biggest,delta)
                if x!=y if is_integer else delta>tol(label,x,y):
                    excess+=1
                    if len(first_differences)<24:
                        first_differences.append({'hour':hour+1,'label':label.strip(),
                                                  'i':cell%NX+1,'j':cell//NX+1,
                                                  'abs_diff':delta})
            fields[label.strip()]={'count':NC,'bitwise_equal':n_equal,
                                   'frozen_exceedances':excess,'max_abs':biggest}
            bad+=excess
        hours.append({'hour_ordinal':hour+1,
                      'source_end_utc':f'2022-06-01 {hour+2:02d}:00 UTC',
                      'compared_values':45*NC,'bitwise_equal':equal,
                      'frozen_exceedances':bad,'fields':fields})
        total_equal+=equal;total_bad+=bad
    human={3:'THREE',4:'FOUR',5:'FIVE',6:'SIX'}[native_hours]
    label=f'S4C_SHARED_{human}HOUR_FORTRAN_{45*native_hours}'
    result={'status':('PASS_SCOPED_'+label if not total_bad else 'FAIL_'+label),
            'original_met_sha256':original_sha,'native_met_sha256':native_sha,
            'original_hours':6,'native_hours':native_hours,'grid':[NX,NY,NZ],
            'stations':[2,1],'water_cells':63,
            'compared_fields':45*native_hours,
            'compared_values':45*native_hours*NC,'bitwise_equal':total_equal,
            'frozen_exceedances':total_bad,'first_differences':first_differences,
            'hours':hours,'state_carry':'G14_NATIVE_COMMITTED_ZI_ZICONV_DPTT_AND_NATIVE_P6F_WATER',
            'production_P6':'NOT_ACCEPTED','P7':'NOT_RUN',
            'independent_science_review':'NOT_RUN'}
    report.write_text(json.dumps(result,indent=2)+'\n')
    return result


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument('--original',type=Path,required=True)
    p.add_argument('--native',type=Path,required=True)
    p.add_argument('--original-sha256',required=True)
    p.add_argument('--native-sha256',required=True)
    p.add_argument('--report',type=Path,required=True)
    p.add_argument('--native-hours',type=int,choices=(3,4,5,6),default=3)
    a=p.parse_args();r=audit(a.original,a.native,a.original_sha256,
                             a.native_sha256,a.report,a.native_hours)
    print(r['status'],'values',r['compared_values'],
          'bitwise',r['bitwise_equal'],'exceedances',r['frozen_exceedances'])
    if r['frozen_exceedances']:
        raise SystemExit(3)

if __name__=='__main__':main()
