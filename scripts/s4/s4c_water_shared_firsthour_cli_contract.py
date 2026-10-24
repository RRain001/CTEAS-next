#!/usr/bin/env python3
"""S4-C first-hour G65 shared actor must never become implicit production.

Uses only nonexistent paths: tests CLI safety, not original science parity.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import tempfile


def test_cli(binary: Path) -> None:
    with tempfile.TemporaryDirectory(prefix='s4c-unified-hour1-') as directory:
        root=Path(directory)
        missing=root/'nonexistent-original'
        out=root/'native-hour1.met.dat'
        trace=root/'state.csv'
        base=['--selected-experimental','--water-firsthour-g14-trial-only',
              '--met',str(missing),'--geo',str(missing),
              '--surf',str(missing),'--up',str(missing),
              '--hours','6','--probe-prefix-hours','1','--out',str(out)]
        cases=(
            (['--g26-normal-entry-trial'], 'normal G26 cannot mix'),
            (['--native-comp-trace',str(trace)],'forbid state evidence injection'),
            (['--water-source-preflight-only'],'source-only preflight disjoint'),
            (['--water-firsthour-g14-trial-only'],'duplicate first-hour flag'),
            (['--probe-prefix-hours','2'],'duplicate/forbidden prefix'),
        )
        for tail,label in cases:
            res=subprocess.run([str(binary),*base,*tail],
                               capture_output=True,text=True,timeout=25)
            assert res.returncode==2,(label,res.returncode,res.stderr)
            assert 'S4B2_FAIL_CLOSED' in res.stderr,(label,res.stderr)
            assert not out.exists() and not trace.exists(),label
        # Separate malformed source windows are rejected before G19 reads.
        for target,old,new in (
            ('wrong source hours','6','5'),
            ('wrong execution prefix','1','2'),
        ):
            flag='--hours' if target=='wrong source hours' else '--probe-prefix-hours'
            cmd=base.copy();cmd[cmd.index(flag)+1]=new
            res=subprocess.run([str(binary),*cmd],
                               capture_output=True,text=True,timeout=25)
            assert res.returncode==2 and 'S4C NOAA WATER G14 requires' in res.stderr,(target,res.stderr)
            assert not out.exists(),target
        no_opt=base.copy();no_opt.remove('--selected-experimental')
        res=subprocess.run([str(binary),*no_opt],capture_output=True,text=True,timeout=25)
        assert res.returncode==2 and 'S4B2 experimental ONLY' in res.stderr,res.stderr
        # The fully formed CLI cannot signal research success with no inputs.
        res=subprocess.run([str(binary),*base],capture_output=True,text=True,timeout=25)
        assert res.returncode==2 and 'S4B2_FAIL_CLOSED' in res.stderr,res.stderr
        assert 'PRODUCED_UNVERIFIED' not in res.stdout
        assert not out.exists() and not trace.exists()
    print('S4C_SHARED_G65_NO_IMPLICIT_PRODUCTION=PASS_SYNTHETIC_ONLY')

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--binary',type=Path,required=True)
    args=parser.parse_args()
    if not args.binary.is_file():
        parser.error('same compiled S4B2 binary required')
    test_cli(args.binary)
