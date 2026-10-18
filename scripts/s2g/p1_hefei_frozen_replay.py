"""#54 D4: genuine frozen Hefei P1 regression against independently rerun CTEAS.

Only run through explicit, manual GitHub Actions against main. All original
vendor code and user-origin DEM remain in the checked-out CTEAS scratch tree;
publish only bounded SHA/count/error metadata, never data or binaries.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
import subprocess
import sys

VENDOR_REF="dfad99a78ed84d655e21411c9d25eb0d2583bf13"
CROP="calpuff_terrain_and_landuse_data_crop/hefei_5km/china_srtm/srtm_60_06_hefei_5km.tif"
CROP_SHA="c4211914fce527d2ad41ecac1e668d7faa2904bbbfd9135868ee83ef0d32123f"
ORIGINAL_DAT_SHA="d74a5a1045ea4cf25e120099196a3962ab012aaebdf37354ec8264fad0e27678"
ORIGINAL_SAV_SHA="5b09c27974eb5e77e3a0fc2126836e0c46f57a3558da5e1083930bcb6267cd74"
GRID_X,GRID_Y="510.885","3531.269"
CROPPED_SOURCE_PIXELS=90*77
FROZEN_ACCEPTED_HITS=3456

def sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def run(argv:list[str],*,cwd:Path,timeout:int=600)->None:
    p=subprocess.run(argv,cwd=cwd,capture_output=True,text=True,timeout=timeout,check=False)
    if p.returncode:
        raise RuntimeError("historical regression subprocess nonzero: "+Path(argv[0]).name)

def replay(original_root:Path,next_root:Path,exe:Path,out:Path)->dict:
    from native_cpp.reference.compare_p1_terrain import (
        cpp, original, original_save,
    )
    import math
    if out.exists():
        raise RuntimeError("historical evidence output already exists")
    out.mkdir(parents=True)
    tif=original_root/CROP
    if not tif.is_file() or tif.is_symlink() or sha(tif)!=CROP_SHA:
        raise RuntimeError("frozen original Hefei TIFF bytes not verified")
    # The original historical independent capture compiles and executes the
    # original untouched TERREL AND its separate original CTGPROC dependency.
    reference=out/"reference"
    run([sys.executable,str(original_root/"native_cpp/reference/capture_p1_p2.py"),
         "--output",str(reference)],cwd=original_root,timeout=850)
    dat=reference/"p1/terrel.dat"
    sav=reference/"p1/terrel.sav"
    if sha(dat)!=ORIGINAL_DAT_SHA or sha(sav)!=ORIGINAL_SAV_SHA:
        raise RuntimeError("original reference differs from pinned 2026-10-10 accepted SHA")
    manifest=json.loads((reference/"manifest.json").read_text())
    if (manifest.get("grid",{}).get("nx")!=50 or
        manifest.get("grid",{}).get("ny")!=50 or
        abs(manifest["grid"]["x0_km"]-510.8846439571007)>0.000001 or
        abs(manifest["grid"]["y0_km"]-3531.2689269678035)>0.000001):
        raise RuntimeError("original reference frozen grid/source differs")
    # The 2026-10-10 reference uses the raw center-derived grid origin,
    # e.g. 510.8846439571km, 3531.2689269678km. Since #42, the
    # authoritative case grid strictly uses 3-decimal km 510.885/3531.269.
    # Comparing these DIFFERENT control grids cell-by-cell is invalid and
    # previously produced 20 false historical-regression hit mismatches.
    # First independently retain the historical exact-bit-for-bit fixture,
    # then rerun the ORIGINAL TERREL with the reviewed canonical origin.
    historical_heights=original(dat)
    historical_sums,historical_hits=original_save(sav)
    if len(historical_heights)!=2500 or sum(historical_hits)!=FROZEN_ACCEPTED_HITS:
        raise RuntimeError("historical 2026-10-10 original source baseline differs")
    legacy_dat_sha,legacy_sav_sha=sha(dat),sha(sav)
    canonical=out/"original_canonical_grid"
    canonical.mkdir()
    control=canonical/"terrel.inp"
    shutil.copyfile(reference/"p1/terrel.inp",control)
    selected=reference/"data/srtm_60_06_hefei_5km.tif"
    if not selected.is_file() or sha(selected)!=CROP_SHA:
        raise RuntimeError("historical selected TIFF differs before canonical original")
    update_code="""
import json,sys
from pathlib import Path
from engine.preprocess.terrel.auto_select_srtm_to_terrel import GridDef,update_terrel
v=json.loads(sys.argv[1])
g=GridDef(imap='UTM',iutmzn=50,lsohem='N',datum='WGS-84',
          xrefkm=float(v['x']),yrefkm=float(v['y']),
          nx=50,ny=50,dgridkm=0.1)
update_terrel(Path(v['control']),g,[Path(v['tif'])],dry_run=False)
"""
    run([sys.executable,"-c",update_code,json.dumps(
            {"x":GRID_X,"y":GRID_Y,"control":str(control),"tif":str(selected)})],
        cwd=original_root,timeout=35)
    original_exe=reference/"bin/terrel.x"
    if not original_exe.is_file():
        raise RuntimeError("original independently compiled TERREL binary absent")
    run([str(original_exe),"terrel.inp"],cwd=canonical,timeout=300)
    dat=canonical/"terrel.dat"
    sav=canonical/"terrel.sav"
    heights=original(dat)
    sums,old_hits=original_save(sav)
    csv=out/"native_hefei.csv"
    run([str(exe),str(tif),GRID_X,GRID_Y,str(csv)],cwd=next_root)
    native_hits,native_height=cpp(csv)
    count_bad=sum(a!=b for a,b in zip(old_hits,native_hits))
    missing_bad=sum((a==0)!=(b==0) for a,b in zip(old_hits,native_hits))
    raw_errors=[abs((s/k if k else -999.0)-v)
                for s,k,v in zip(sums,old_hits,native_height)]
    fmt_errors=[abs(a-b) for a,b in zip(heights,native_height)]
    raw_bad=sum(e>0.00001 for e in raw_errors)
    fmt_bad=sum(e>0.0500001 for e in fmt_errors)
    status="PASS_FROZEN_HEFEI_ORIGINAL" if not any(
        (count_bad,missing_bad,raw_bad,fmt_bad)) else "FAIL_FROZEN_HEFEI_ORIGINAL"
    result={
        "schema_version":"issue54-hefei-original-regression-v1",
        "status":status,
        "original_vendor_ref":VENDOR_REF,
        "source_tiff_sha256":sha(tif),
        "source_width":90,"source_height":77,
        "historical_2026_10_10_dat_sha256":legacy_dat_sha,
        "historical_2026_10_10_sav_sha256":legacy_sav_sha,
        "historical_2026_10_10_grid_xrefkm":manifest["grid"]["x0_km"],
        "historical_2026_10_10_grid_yrefkm":manifest["grid"]["y0_km"],
        "historical_2026_10_10_accepted_hits":sum(historical_hits),
        "original_canonical_dat_sha256":sha(dat),
        "original_canonical_sav_sha256":sha(sav),
        "native_csv_sha256":sha(csv),"grid_xrefkm":GRID_X,
        "grid_yrefkm":GRID_Y,"grid_nx":50,"grid_ny":50,
        "grid_spacing_m":100,
        "original_accepted_hits":sum(old_hits),
        "native_accepted_hits":sum(native_hits),
        "cell_hit_mismatches":count_bad,"missing_mask_mismatches":missing_bad,
        "unrounded_mean_bad_cells":raw_bad,
        "unrounded_mean_max_abs_error_m":max(raw_errors),
        "formatted_dat_bad_cells":fmt_bad,
        "formatted_dat_max_abs_error_m":max(fmt_errors),
        "original_real4_mean_tolerance_m":0.00001,
        "original_formatted_f8_1_tolerance_m":0.0500001,
        "no_data_or_vendor_source_artifact":True,
    }
    (out/"historical_regression_metadata_only.json").write_text(
        json.dumps(result,indent=2,sort_keys=True)+"\n")
    return result

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--original-root",type=Path,required=True)
    p.add_argument("--next-root",type=Path,required=True)
    p.add_argument("--binary",type=Path,required=True)
    p.add_argument("--workspace",type=Path,required=True)
    p.add_argument("--report",type=Path,required=True)
    a=p.parse_args()
    try:
        result=replay(a.original_root.resolve(),a.next_root.resolve(),
                      a.binary.resolve(),a.workspace.resolve())
    except (OSError,RuntimeError,ValueError,KeyError,subprocess.SubprocessError) as e:
        result={"status":"BLOCKED_OR_FAILED_HISTORIC_REGRESSION",
                "reason_type":type(e).__name__,
                "science_acceptance":"NOT_ACCEPTED"}
    if a.report.exists():
        raise SystemExit("existing history report cannot be replaced")
    a.report.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("ISSUE54_FROZEN_HEFEI_STATUS="+result["status"])
    return 0 if result["status"]=="PASS_FROZEN_HEFEI_ORIGINAL" else 2

if __name__=="__main__":
    raise SystemExit(main())
