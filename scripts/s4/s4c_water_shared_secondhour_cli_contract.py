#!/usr/bin/env python3
"""The NOAA 2h native G14 route cannot silently become production P6."""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import tempfile


def test_cli(binary:Path)->None:
    with tempfile.TemporaryDirectory(prefix='s4c-water-hour2-') as temp:
        root=Path(temp);fake=root/'missing';out=root/'no.met.dat';trace=root/'no.trace'
        base=['--selected-experimental','--water-secondhour-g14-trial-only',
              '--met',str(fake),'--geo',str(fake),'--surf',str(fake),
              '--up',str(fake),'--hours','6','--probe-prefix-hours','2',
              '--out',str(out)]
        forbidden=(
            (['--water-firsthour-g14-trial-only'],'cannot mix first/second'),
            (['--water-source-preflight-only'],'cannot mix source/physics'),
            (['--g26-normal-entry-trial'],'normal G26 not admitted'),
            (['--native-comp-trace',str(trace)],'source-only trace isolated'),
            (['--water-secondhour-g14-trial-only'],'duplicate research option'),
        )
        for flags,label in forbidden:
            p=subprocess.run([str(binary),*base,*flags],capture_output=True,
                             text=True,timeout=20)
            assert p.returncode==2,(label,p.returncode,p.stderr)
            assert 'S4B2_FAIL_CLOSED' in p.stderr,(label,p.stderr)
            assert not out.exists() and not trace.exists(),label
        for key,value in (('--probe-prefix-hours','1'),
                          ('--probe-prefix-hours','6'),('--hours','5')):
            args=base.copy();args[args.index(key)+1]=value
            p=subprocess.run([str(binary),*args],capture_output=True,
                             text=True,timeout=20)
            assert p.returncode==2 and 'S4C NOAA WATER secondhour requires' in p.stderr,(key,p.stderr)
            assert not out.exists(),key
        implicit=base.copy();implicit.remove('--selected-experimental')
        p=subprocess.run([str(binary),*implicit],capture_output=True,
                         text=True,timeout=20)
        assert p.returncode==2 and 'experimental ONLY' in p.stderr,p.stderr
        p=subprocess.run([str(binary),*base],capture_output=True,
                         text=True,timeout=20)
        assert p.returncode==2 and 'S4B2_FAIL_CLOSED' in p.stderr,p.stderr
        assert 'PRODUCED_UNVERIFIED' not in p.stdout and not out.exists()
    print('S4C_TWOHOUR_SHARED_G14_FAIL_CLOSED=PASS')

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--binary',required=True,type=Path)
    args=parser.parse_args()
    if not args.binary.is_file():parser.error('shared native S4B2 binary absent')
    test_cli(args.binary)
