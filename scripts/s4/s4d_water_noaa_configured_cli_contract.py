#!/usr/bin/env python3
"""Single prefix-parameterized G65 research entry must fail closed.

Original NOAA inputs are intentionally never needed in this negative
contract: any claimed source acceptance with non-existent files fails.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import tempfile


LEGACY=(
    '--water-firsthour-g14-trial-only',
    '--water-secondhour-g14-trial-only',
    '--water-thirdhour-g14-trial-only',
    '--water-fourthhour-g14-trial-only',
    '--water-fifthhour-g14-trial-only',
    '--water-sixthhour-g14-trial-only',
)


def check(binary:Path)->None:
    with tempfile.TemporaryDirectory(prefix='s4d-noaa-configured-') as t:
        root=Path(t);fake=str(root/'absent');out=str(root/'model.met')
        args=['--selected-experimental','--water-noaa-g14-trial-only',
              '--met',fake,'--geo',fake,'--surf',fake,'--up',fake,
              '--hours','6','--probe-prefix-hours','6','--out',out]
        def fails(items:list[str], contains:str, keep_existing:bool=False)->None:
            p=subprocess.run([str(binary),*items],capture_output=True,
                             text=True,timeout=20)
            assert p.returncode==2,(p.returncode,p.stdout,p.stderr)
            assert contains in p.stderr,(contains,p.stderr)
            assert 'PRODUCED_UNVERIFIED' not in p.stdout
            if not keep_existing:
                assert not Path(out).exists()
        # Source preflight is separate and always retains raw original
        # provenance; passing options cannot manufacture original inputs.
        fails(args,'S4B2_FAIL_CLOSED')
        for mode in (*LEGACY,'--g26-normal-entry-trial',
                     '--water-source-preflight-only',
                     '--water-noaa-g14-trial-only'):
            fails([*args,mode], 'S4B2_FAIL_CLOSED')
        fails([*args,'--native-comp-trace',str(root/'trace.csv')],
              'S4D unified NOAA WATER requires')
        assert not (root/'trace.csv').exists()
        for n in (0,7,143):
            other=args.copy();other[other.index('--probe-prefix-hours')+1]=str(n)
            fails(other,'S4B3 invalid probe hours' if n==0
                  else 'S4D unified NOAA WATER requires')
        for n in (1,2,3,4,5):
            other=args.copy();other[other.index('--hours')+1]=str(n)
            fails(other,'S4D unified NOAA WATER requires')
        missing=args.copy();missing.remove('--selected-experimental')
        fails(missing,'S4B2 experimental ONLY')
        empty_prefix=args.copy()
        i=empty_prefix.index('--probe-prefix-hours')
        del empty_prefix[i:i+2]
        fails(empty_prefix,'S4D unified NOAA WATER requires')
        occupied=Path(out);occupied.write_bytes(b'must-not-touch')
        fails(args,'S4B2 refuses to overwrite existing output',True)
        assert occupied.read_bytes()==b'must-not-touch'
    print('S4D_SINGLE_NOAA_CONFIGURED_G14_FAIL_CLOSED=PASS')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--binary',type=Path,required=True)
    a=p.parse_args()
    assert a.binary.is_file(),a.binary
    check(a.binary)
