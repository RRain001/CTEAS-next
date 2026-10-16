#!/usr/bin/env python3
"""P3-only deterministic mixed-LU benchmark: leave original inputs untouched."""
from __future__ import annotations
import argparse,hashlib,json,os,re,shutil,subprocess
from pathlib import Path

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--reference-dir",required=True,type=Path)
    a=p.parse_args()
    root=a.reference_dir.resolve()
    source=root/"p2/lu.dat"
    text=source.read_text().splitlines()
    if len(text)!=2511 or text[0].split()[:2]!=["LU.DAT","2.1"]:
        raise ValueError("unexpected original LU.DAT reference format")
    cats=[int(v) for v in text[10].split()]
    if len(cats)!=38:raise ValueError("unexpected category header")
    idx={c:k for k,c in enumerate(cats)}
    mixed=root/"p3-mixed"
    mixed.mkdir(exist_ok=False)
    (mixed/"run").mkdir()
    generated=mixed/"lu.dat"
    with generated.open("w") as out:
        out.write("\n".join(text[:11])+"\n")
        for n in range(2500):
            i,j=n%50+1,n//50+1
            code=n%17
            if code==0: weights={51:.4,52:.3,21:.3}  # majority water
            elif code==1: weights={51:.4,21:.3,22:.3} # minority water
            elif code==2: weights={11:.4,21:.3,31:.3}
            elif code==3: weights={51:.5,21:.5}       # exact threshold
            elif code==4: weights={51:.501,21:.499}   # above threshold
            elif code==5: weights={51:.499,21:.501}   # below threshold
            else:
                keys=[cats[(n+3)%38],cats[(7*n+9)%38],cats[(13*n+11)%38]]
                weights={}
                for k,w in zip(keys,(.5,.3,.2)):
                    weights[k]=weights.get(k,0.)+w
            data=[0.0]*38
            for k,v in weights.items():data[idx[k]]=v
            if abs(sum(data)-1.)>1.e-10:raise RuntimeError("not normalized")
            out.write(f"{i:5d}{j:5d} "+" ".join(f"{f:.3f}" for f in data)+"   .\n")
    control=(root/"p3/makegeo.inp").read_text()
    # Keep all physical controls and full original category parameter table;
    # update just the two source filenames, with isolated working directory.
    def replace(s,key,new):
        rg=re.compile(r"(!\s*"+re.escape(key)+r"\s*=\s*)([^!]*?)(\s*!)")
        if len(rg.findall(s))!=1:raise RuntimeError("unexpected P3 control key "+key)
        return rg.sub(lambda m:m.group(1)+new+" "+m.group(3),s,count=1)
    control=replace(control,"LUDAT","../lu.dat")
    control=replace(control,"TERRDAT","../../p1/terrel.dat")
    cfile=mixed/"run/makegeo.inp"
    cfile.write_text(control)
    exe=root/"bin/makegeo.x"
    p=subprocess.run([str(exe),cfile.name],cwd=cfile.parent,
                     capture_output=True,text=True,timeout=120)
    (mixed/"fortran.stdout.txt").write_text(p.stdout)
    (mixed/"fortran.stderr.txt").write_text(p.stderr)
    geo=cfile.parent/"geo.dat"
    if p.returncode or not geo.is_file() or geo.stat().st_size<30000:
        raise RuntimeError("original mixed MAKEGEO failed")
    detail={"status":"SYNTHETIC_MIXED_P3_ORIGINAL_READY",
        "source":"Original no-snow MAKEGEO binary compiled in same CI; only LU.DAT row fractions changed",
        "original_lu_sha256":sha(source),"synthetic_lu_sha256":sha(generated),
        "synthetic_geo_sha256":sha(geo),"original_exit_code":p.returncode,
        "cells":2500,"input_categories":38,"cases":"water threshold, mixed classes, geometric z0 and arithmetic weights"}
    (mixed/"manifest.json").write_text(json.dumps(detail,indent=2)+"\n")
    print(json.dumps(detail,indent=2))
if __name__=="__main__":
    main()
