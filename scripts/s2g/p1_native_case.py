"""#54 P1 native case adapter: consume #42 admission + #49 source manifest.

Only two routes: user-declared local SRTM 3 arc-sec, or cached OpenTopography
SRTMGL1 1 arc-sec. Does not download, mosaic, substitute DEM or modify physics.
No scientific equivalence is asserted by a successful run.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess

from native_cpp.orchestration.case_admission import admit_case, verify_immutable
from native_cpp.orchestration.plan import ContractError

LOCAL_PRODUCTS = {"CGIAR-CSI-SRTM-v4.1", "NASA-SRTMGL3-v003"}
API_PRODUCT = "SRTMGL1"
MAX_PIXELS = 30_000_000


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _regular_file(path: Path) -> None:
    if path.is_symlink() or not path.is_file() or path.stat().st_size == 0:
        raise ContractError("P1 source/binary/manifest absent, symlinked or empty")


def run_case(*, case_yaml: Path, source_manifest: Path, source_product: str,
             binary: Path, out_dir: Path) -> dict:
    admission = admit_case(case_yaml)
    _regular_file(source_manifest)
    _regular_file(binary)
    data = json.loads(source_manifest.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ContractError("P1 source manifest must be a mapping")
    if data.get("status") != "P1_TERRAIN_SOURCE_VERIFIED_NATIVE_NUMERICS_NOT_RUN":
        raise ContractError("P1 requires the reviewed #49 source-only manifest")
    if data.get("nodata_allowed_explicitly") is not False or data.get("case_window_nodata_pixels") != 0:
        raise ContractError("P1 void/NoData source cannot become native terrain")
    mode = data.get("mode")
    if mode == "local":
        if data.get("dataset") != "USER_PROVIDED_GEOTIFF" or source_product not in LOCAL_PRODUCTS:
            raise ContractError("P1-A requires a declared 3-arc-sec SRTM version")
        spacing = 3.0 / 3600.0
        route = "P1_A_90M_LOCAL"
    elif mode == "opentopography":
        if data.get("dataset") != "SRTMGL1" or source_product != API_PRODUCT:
            raise ContractError("P1-B requires cached SRTMGL1 1-arc-sec source")
        spacing = 1.0 / 3600.0
        route = "P1_B_30M_DOWNLOAD"
    else:
        raise ContractError("P1 route is neither local 90m nor cached SRTMGL1 30m")
    original_grid = Path(data.get("case_grid", ""))
    _regular_file(original_grid)
    if sha256(original_grid) != admission.grid_sha256:
        raise ContractError("P1 source manifest grid differs from B0 numeric authority")
    selected = Path(data.get("selected_tif", ""))
    _regular_file(selected)
    selected_sha = sha256(selected)
    if selected_sha != data.get("selected_tif_sha256"):
        raise ContractError("P1 selected GeoTIFF SHA differs from #49 manifest")
    properties = data.get("selected_tif_properties")
    if not isinstance(properties, dict) or properties.get("sha256") != selected_sha:
        raise ContractError("P1 source raster properties inconsistent with SHA")
    width,height=properties.get("width"),properties.get("height")
    if (type(width) is not int or type(height) is not int or
            width <= 0 or height <= 0 or width*height > MAX_PIXELS):
        raise ContractError("P1 selected raster exceeds native input budget")
    resolutions=properties.get("resolution_degrees")
    if (not isinstance(resolutions,list) or len(resolutions)!=2 or
            any(type(x) not in (int,float) or not math.isfinite(x) or
                abs(x-spacing)>5e-7 for x in resolutions)):
        raise ContractError("P1 declared route and actual angular resolution disagree")
    if not selected.suffix.lower() in {".tif",".tiff"}:
        raise ContractError("P1 native input must be GeoTIFF")
    case_root=admission.case_path.parent
    expected_parent=case_root / "geo/terrel"
    if (out_dir.parent != expected_parent or out_dir.name not in {"p1_native", "p1_native_test"}
            or not expected_parent.is_dir() or expected_parent.is_symlink()
            or out_dir.exists() or out_dir.is_symlink()):
        raise ContractError("P1 output must be a fresh producer directory under staged case")
    manifest_sha = sha256(source_manifest)
    before_binary=sha256(binary)
    out_dir.mkdir(exist_ok=False)
    try:
        output=out_dir/"terrain.csv"
        cmd=[str(binary),str(selected),admission.xrefkm_text,admission.yrefkm_text,
             str(admission.nx),str(admission.ny),str(admission.dgridkm),
             str(admission.utm_zone),admission.hemisphere,str(output)]
        completed=subprocess.run(cmd,capture_output=True,text=True,timeout=1200,check=False)
        if completed.returncode:
            # Do not leak source paths, raw CLI stderr or any credentials.
            raise ContractError("P1 native executable rejected source/grid or coverage")
        verify_immutable(admission)
        if sha256(original_grid)!=admission.grid_sha256 or sha256(selected)!=selected_sha or sha256(source_manifest)!=manifest_sha:
            raise ContractError("P1 source changed during native execution")
        if sha256(binary)!=before_binary:
            raise ContractError("P1 native executable changed during execution")
        with output.open(newline="",encoding="utf-8") as stream:
            reader=csv.DictReader(stream)
            if reader.fieldnames != ["i","j","hits","elevation_m"]:
                raise ContractError("P1 output CSV columns/order invalid")
            hits=0
            n=0
            for row in reader:
                i=n%admission.nx+1
                j=n//admission.nx+1
                if row["i"]!=str(i) or row["j"]!=str(j):
                    raise ContractError("P1 output spatial row order wrong")
                points=int(row["hits"])
                elevation=float(row["elevation_m"])
                if points<=0 or not math.isfinite(elevation):
                    raise ContractError("P1 uncovered/nonfinite model cell")
                hits+=points
                n+=1
            if n!=admission.nx*admission.ny:
                raise ContractError("P1 incomplete grid rows")
        report={
          "schema_version":"p1-native-preliminary-v1",
          "producer_issue":54,
          "status":"PRODUCED_UNVERIFIED",
          "original_parity":"NOT_RUN",
          "science_acceptance":"NOT_RUN",
          "source_authenticity":"USER_OR_ADAPTER_DECLARED_UNVERIFIED",
          "route":route,
          "product_declaration":source_product,
          "case_name":admission.case_name,
          "case_sha256":admission.case_sha256,
          "grid_sha256":admission.grid_sha256,
          "time_sha256":admission.time_sha256,
          "source_manifest_sha256":manifest_sha,
          "selected_tif_sha256":selected_sha,
          "binary_sha256":before_binary,
          "grid":{"zone":admission.utm_zone,"hemisphere":admission.hemisphere,
                  "xrefkm":admission.xrefkm_text,"yrefkm":admission.yrefkm_text,
                  "nx":admission.nx,"ny":admission.ny,"dgridkm":admission.dgridkm},
          "row_order":"j south-to-north; i west-to-east fastest; indices 1-based",
          "height_unit":"m", "row_count":n, "source_pixel_hits":hits,
          "terrain_csv_sha256":sha256(output)
        }
        (out_dir/"p1_native_manifest.json").write_text(
            json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        return report
    except BaseException:
        shutil.rmtree(out_dir)
        raise


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-yaml",required=True,type=Path)
    parser.add_argument("--source-manifest",required=True,type=Path)
    parser.add_argument("--source-product",required=True)
    parser.add_argument("--binary",required=True,type=Path)
    parser.add_argument("--out-dir",required=True,type=Path)
    options=parser.parse_args(argv)
    try:
        report=run_case(case_yaml=options.case_yaml,source_manifest=options.source_manifest,
                        source_product=options.source_product,binary=options.binary,out_dir=options.out_dir)
    except (ContractError,ValueError,OSError,subprocess.SubprocessError,TimeoutError) as exc:
        # No sensitive path or provider token is logged.
        print(json.dumps({"status":"BLOCKED_P1_NATIVE_CASE",
                          "reason_type":type(exc).__name__,"science":"NOT_RUN"}))
        return 2
    print(json.dumps({"status":report["status"],"route":report["route"],
                      "row_count":report["row_count"],"science":report["science_acceptance"]}))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
