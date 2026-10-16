#!/usr/bin/env python3
"""Capture untouched original TERREL and CTGPROC at 100m; no C++ parity assertion."""
from __future__ import annotations
import argparse,hashlib,json,re,shutil,subprocess,sys,time
from pathlib import Path

def hash_file(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda:f.read(1<<20),b""):h.update(c)
    return h.hexdigest()

def command(args,cwd,prefix,timeout):
    begun=time.monotonic()
    try:
        r=subprocess.run(args,cwd=cwd,text=True,capture_output=True,timeout=timeout)
        rc,out,err=r.returncode,r.stdout,r.stderr
    except subprocess.TimeoutExpired as exc:
        rc,out,err=124,str(exc.stdout or ""),str(exc.stderr or "")
    prefix.with_suffix(".stdout.txt").write_text(out)
    prefix.with_suffix(".stderr.txt").write_text(err)
    return {"command":args,"returncode":rc,"elapsed_s":time.monotonic()-begun,
            "stdout_sha256":hash_file(prefix.with_suffix(".stdout.txt")),
            "stderr_sha256":hash_file(prefix.with_suffix(".stderr.txt"))}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",type=Path,required=True)
    root=Path(__file__).resolve().parents[2]
    sys.path.insert(0,str(root))
    from engine.preprocess.terrel.auto_select_srtm_to_terrel import (
        GridDef as TGrid,pick_tiles,grid_bbox_wgs84,update_terrel)
    from engine.preprocess.ctgproc.auto_select_landuse_to_ctgproc import (
        GridDef as LGrid,update_ctgproc)
    out=ap.parse_args().output.resolve()
    out.mkdir(parents=True,exist_ok=False)
    p1,p2,data,binaries=(out/x for x in ("p1","p2","data","bin"))
    for d in (p1,p2,data,binaries):d.mkdir()
    crop=json.loads((root/"calpuff_terrain_and_landuse_data_crop/hefei_5km/crop_info.json").read_text())
    if crop["utm_crs"]!="EPSG:32650" or crop["study_side_km"]!=5.0:
        raise RuntimeError("unexpected source crop")
    tif_src=root/crop["terrain"][0]["output"]
    gen_src=root/crop["landuse"]["generic"]["output"]
    for f,digest in ((tif_src,crop["terrain"][0]["sha256"]),(gen_src,crop["landuse"]["generic"]["sha256"])):
        if hash_file(f)!=digest:raise RuntimeError("source data SHA mismatch "+str(f))
    tif=data/"srtm_60_06_hefei_5km.tif"
    tif.symlink_to(tif_src)
    (data/"srtm_60_06_hefei_5km.bbox").symlink_to(tif_src.with_suffix(".bbox"))
    gen=data/"generic_landuse.txt"
    gen.symlink_to(gen_src)
    x0=crop["center"]["utm_e"]-2.5
    y0=crop["center"]["utm_n"]-2.5
    tg=TGrid(imap="UTM",iutmzn=50,lsohem="N",datum="WGS-84",
             xrefkm=x0,yrefkm=y0,nx=50,ny=50,dgridkm=0.1)
    lg=LGrid(imap="UTM",iutmzn=50,lsohem="N",datum="WGS-84",
             xrefkm=x0,yrefkm=y0,nx=50,ny=50,dgridkm=0.1)
    vals={"IMAP":"UTM","IUTMZN":"50","LSOHEM":"N","DATUM":"WGS-84",
          "XREFKM":f"{x0:.10f}","YREFKM":f"{y0:.10f}",
          "NX":"50","NY":"50","NZ":"9","DGRIDKM":"0.1"}
    lines=(root/"engine/vendor/src/grid/grid.cmn").read_text().splitlines()
    found=set()
    for i,line in enumerate(lines):
        for k,v in vals.items():
            match=re.match(r"^(\s*!\s*"+re.escape(k)+r"\s*=\s*)([^!]*)(!.*)$",line)
            if match:
                if k in found:raise RuntimeError("duplicate grid key "+k)
                lines[i]=match.group(1)+v+" "+match.group(3)
                found.add(k)
    if found!=set(vals):raise RuntimeError("grid template missing keys: "+str(set(vals)-found))
    (out/"grid.cmn").write_text("\n".join(lines)+"\n")
    s1=root/"engine/vendor/src/TERREL_v7.0.0_L141010"
    s2=root/"engine/vendor/src/CTGPROC_v7.0.0_L150211"
    shutil.copy2(s1/"terrel.inp",p1/"terrel.inp")
    shutil.copy2(s2/"ctgproc.inp",p2/"ctgproc.inp")
    if pick_tiles(data,grid_bbox_wgs84(tg,1))!=[tif]:
        raise RuntimeError("P1 cropped GeoTIFF coverage mismatch")
    update_terrel(p1/"terrel.inp",tg,[tif],dry_run=False)
    update_ctgproc(p2/"ctgproc.inp",lg,gen,"GEN",dry_run=False,generic_datum="ESR-S")
    for f in (p1/"terrel.inp",p2/"ctgproc.inp"):
        ctrl=f.read_text()
        for k,v in (("NX","50"),("NY","50"),("DGRIDKM","0.1"),("IUTMZN","50")):
            m=re.search(r"!\s*"+k+r"\s*=\s*([^!]+)!",ctrl)
            if not m or m.group(1).strip()!=v:raise RuntimeError("mismatch "+f.name+" "+k)
    if not re.search(r"!\s*DNZGEN\s*=\s*ESR-S\s*!",(p2/"ctgproc.inp").read_text()):
        raise RuntimeError("GEN datum not ESR-S")
    if max(len(str(tif)),len(str(gen)))>120:raise RuntimeError("input path exceeds Fortran safety budget")
    compiler=command(["gfortran","--version"],out,out/"compiler",10)
    if compiler["returncode"]:raise RuntimeError("gfortran not available")
    common=["-std=legacy","-fno-automatic","-fno-align-commons","-fallow-argument-mismatch","-O0"]
    builds=[]
    # Linux is case-sensitive while vendor Fortran INCLUDE names may differ
    # from their tracked filename case. Symlink aliases are read-only and
    # created in fresh output space; originals under vendor/src are unchanged.
    alias_roots={}
    for stage,source_dir in (("terrel",s1),("ctgproc",s2)):
        alias=out/("include_alias_"+stage)
        alias.mkdir()
        for source_file in source_dir.iterdir():
            if source_file.is_file():
                name=source_file.name.lower()
                target=alias/name
                if not target.exists():
                    target.symlink_to(source_file)
        alias_roots[stage]=alias
    for name,folder,source,extra in (("terrel",s1,"terrel.for","-ffixed-line-length-none"),
                                     ("ctgproc",s2,"ctgproc.for","-ffixed-line-length-72")):
        binary=binaries/(name+".x")
        result=command(["gfortran",*common,extra,"-I"+str(alias_roots[name]),"-I"+str(folder),str(folder/source),"-o",str(binary)],
                       out,out/(name+"_compile"),120)
        builds.append(result)
        if result["returncode"] or not binary.is_file():
            (out/"STATUS.txt").write_text(name+" BUILD_FAILED\n")
            raise RuntimeError(name+" build failed (see logs)")
    runs=[]
    for name,work,control,target in (("terrel",p1,"terrel.inp","terrel.dat"),
                                     ("ctgproc",p2,"ctgproc.inp","lu.dat")):
        result=command([str(binaries/(name+".x")),control],work,out/(name+"_run"),150)
        runs.append(result)
        if result["returncode"] or not (work/target).is_file() or not (work/target).stat().st_size:
            (out/"STATUS.txt").write_text(name+" RUN_BLOCKED\n")
            raise RuntimeError(name+" run blocked (see logs)")
    inventory={}
    for f in sorted(out.rglob("*")):
        if f.is_file():inventory[str(f.relative_to(out))]={"bytes":f.stat().st_size,"sha256":hash_file(f)}
    manifest={"status":"REFERENCE_CAPTURED_NOT_PARSED_NOT_COMPARED",
              "frozen_main":"66e30ffb1ff4638a97af8a060748ce30b7578350",
              "grid":{"nx":50,"ny":50,"spacing_km":0.1,"x0_km":x0,"y0_km":y0,
                      "projection":"UTM50N WGS84","cell_reference":"SW corner IGRID=1"},
              "original_source_sha256":{"terrel":hash_file(s1/"terrel.for"),
                                        "ctgproc":hash_file(s2/"ctgproc.for")},
              "input_sha256":{"terrain":hash_file(tif_src),"landuse":hash_file(gen_src)},
              "compiler":compiler,"builds":builds,"runs":runs,"outputs":inventory}
    (out/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    (out/"STATUS.txt").write_text(manifest["status"]+"\n")
    for k,d,n in (("P1",p1,"terrel.dat"),("P2",p2,"lu.dat")):
        f=d/n
        print(f"REFERENCE_CAPTURE {k} size={f.stat().st_size} sha256={hash_file(f)}")
    print("REFERENCE_CAPTURED_NOT_PARSED_NOT_COMPARED")
    return 0

if __name__=="__main__":raise SystemExit(main())
