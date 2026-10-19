"""#54 and #118: genuine source (owner SRTM90m / OpenTopography GL1 or GL3) -> native P1.

Only for manually dispatched GitHub Actions. Real bytes, non-Hefei UTM50
seam case, B-0 admitted, actual #49 source adapter, actual native binary.
No original TERREL execution or independent parity claimed.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path

from rasterio.warp import transform
from native_cpp.orchestration.case_admission import admit_case, verify_immutable
from scripts.s2g.p1_real_srtm90_admission import admit as admit_90m
from scripts.s2g.p1_terrain_source import prepare, P1SourceError
from scripts.s2g.p1_native_case import run_case

CASE_NAME="issue54_p1_seam_2022"
LAT,LON=31.94,115.0
ZONE=50
NX=NY=50
DX_KM=0.1
FILES=("srtm_59_06.tif","srtm_60_06.tif")

def stage_case(out_root:Path)->Path:
    case_root=out_root/CASE_NAME
    if case_root.exists() or case_root.is_symlink():
        raise ValueError("independent case directory already exists")
    (case_root/"grid").mkdir(parents=True)
    (case_root/"geo/terrel").mkdir(parents=True)
    xs,ys=transform("EPSG:4326","EPSG:32650",[LON],[LAT])
    # Exact original three decimal km / 1m positions with a domain
    # centered across the real 115E SRTM source tile seam.
    xref=f"{(xs[0]/1000-NX*DX_KM/2):.3f}"
    yref=f"{(ys[0]/1000-NY*DX_KM/2):.3f}"
    grid=(case_root/"grid/grid.cmn")
    grid.write_text("\n".join((
        "! IMAP = UTM !","! IUTMZN = 50 !","! LSOHEM = N !",
        "! DATUM = WGS-84 !",f"! XREFKM = {xref} !",
        f"! YREFKM = {yref} !","! NX = 50 !","! NY = 50 !",
        "! DGRIDKM = 0.100 !","! NZ = 1 !",
        "! ZFACE = 0 !","! ZFACE = 100 !","")),encoding="utf-8")
    (case_root/"grid/research_time").write_text(
        "BEGIN:20220101-000000\nEND:20220101-030000\n",encoding="utf-8")
    (case_root/"case.yaml").write_text("\n".join((
        f"case_name: {CASE_NAME}",
        "settings:","  timezone: UTC+0000","preprocess:",
        "  grid:","    utm_zone: 50","    hemisphere: N","    nz: 1",
        "    resolution_km: 0.1","    domain:",
        "      length_km: 5","      width_km: 5",
        "    center:","      latitude: 31.94","      longitude: 115.0",
        "  research_time:","    begin: 20220101-000000",
        "    end: 20220101-030000","")),encoding="utf-8")
    admit_case(case_root/"case.yaml")
    return case_root

def run(*,root:Path,route:str,binary:Path,tif_dir:Path|None)->dict:
    case_root=stage_case(root)
    case_yaml=case_root/"case.yaml"
    admission=admit_case(case_yaml)
    src_out=case_root/"geo/terrel/p1_source"
    if route=="P1_A_90M_LOCAL":
        if tif_dir is None:
            raise ValueError("90m real LFS source directory required")
        inventory=admit_90m(case_root/"grid/grid.cmn",tif_dir)
        names=[x["name"] for x in inventory["required_tiles"]]
        if names!=list(FILES):
            raise ValueError("real seam grid did not select the exact expected two 90m tiles")
        source=prepare(case_root/"grid/grid.cmn",src_out,"local",
                       tifs=[tif_dir/name for name in names])
        # A route classification only. Actual official product version is
        # not authenticated by this supplied 3-arcsec TIFF hash.
        product="CGIAR-CSI-SRTM-v4.1"
    elif route in ("P1_B_30M_DOWNLOAD","P1_B_90M_DOWNLOAD"):
        product=("SRTMGL1" if route=="P1_B_30M_DOWNLOAD" else "SRTMGL3")
        source=prepare(case_root/"grid/grid.cmn",src_out,"opentopography",
                       dem=product,allow_public_bulk_fallback=True)
        inventory={"status":"P1_B_ACTUAL_REQUEST_SOURCE_ONLY","required_tiles":[]}
    else:
        raise ValueError("forbidden P1 source route")
    actual=run_case(case_yaml=case_yaml,
                    source_manifest=src_out/"p1_source_manifest.json",
                    source_product=product,binary=binary,
                    out_dir=case_root/"geo/terrel/p1_native")
    verify_immutable(admission)
    if actual["row_count"]!=NX*NY:
        raise ValueError("P1 real native output grid denominator wrong")
    return {
      "schema_version":"p1-issue54-real-actions-native-unverified-v1",
      "status":"P1_REAL_TIFF_NATIVE_PRODUCED_UNVERIFIED",
      "route":route,
      "case_name":CASE_NAME,
      "case_grid_sha256":actual["grid_sha256"],
      "case_sha256":actual["case_sha256"],
      "time_sha256":actual["time_sha256"],
      "source_manifest_sha256":actual["source_manifest_sha256"],
      "selected_tif_sha256":actual["selected_tif_sha256"],
      "native_terrain_csv_sha256":actual["terrain_csv_sha256"],
      "source_pixel_hits":actual["source_pixel_hits"],
      "row_count":actual["row_count"],
      "source_case_valid_pixels":source["case_window_valid_pixels"],
      "source_case_nodata_pixels":source["case_window_nodata_pixels"],
      "source_mosaic_created":source["mosaic_created"],
      "source_transport":source["transport"],
      "official_bulk_recovery_used":source["bulk_recovery_used"],
      "owner_90m_input_byte_gate":inventory["status"],
      "source_product_declaration":product,
      "official_dataset_documentation":source.get("official_dataset_documentation"),
      "source_product_version_authenticated":False,
      "height_vertical_datum_authenticated":False,
      "original_terrel_executed":False,
      "original_native_parity":"NOT_RUN",
      "science_acceptance":"NOT_ACCEPTED"
    }

# Only fixed literals from our downloader/validator may reach public metadata.
# Never persist an untrusted provider body, request URL, API key or traceback.
_SOURCE_FAILURES = {
    "OPENTOPOGRAPHY_API_KEY is not configured": ("SOURCE_PRECHECK", "API_KEY_MISSING"),
    "SRTM available only ~56S..60N, no DEM substitute": ("SOURCE_PRECHECK", "SRTM_COVERAGE_REJECTED"),
    "OpenTopography selected DEM exceeds product-specific API area limit": ("SOURCE_PRECHECK", "API_AREA_LIMIT_EXCEEDED"),
    "selected DEM case pixels exceed input staging memory budget": ("SOURCE_PRECHECK", "SOURCE_PIXEL_BUDGET_EXCEEDED"),
    "OpenTopography unexpected redirect refused (API key protected)": ("OPENTOPOGRAPHY_API", "API_REDIRECT_REFUSED"),
    "OpenTopography network/IO error (request URL withheld)": ("OPENTOPOGRAPHY_API", "API_NETWORK_IO_ERROR"),
    "OpenTopography exceeds configured byte budget": ("OPENTOPOGRAPHY_API", "API_BYTE_BUDGET_EXCEEDED"),
    "OpenTopography returned empty/non-TIFF response": ("OPENTOPOGRAPHY_API", "API_EMPTY_RESPONSE"),
    "public S3 bulk mirror redirect refused": ("S3_BULK_DOWNLOAD", "BULK_REDIRECT_REFUSED"),
    "official public SRTM tile network/IO failure": ("S3_BULK_DOWNLOAD", "BULK_NETWORK_IO_ERROR"),
    "SRTM bulk tile absent/truncated": ("S3_BULK_DOWNLOAD", "BULK_TILE_TRUNCATED"),
    "SRTM tile exceeds bounded source bytes": ("S3_BULK_DOWNLOAD", "BULK_TILE_BYTE_BUDGET_EXCEEDED"),
    "SRTMGL1 bulk total byte budget exhausted": ("S3_BULK_DOWNLOAD", "BULK_TOTAL_BYTE_BUDGET_EXCEEDED"),
    "bulk transport restricted to nine 1-degree tiles": ("S3_BULK_PRECHECK", "BULK_TILE_COUNT_REJECTED"),
    "SRTM bulk bbox outside supported geographic range": ("S3_BULK_PRECHECK", "BULK_COVERAGE_REJECTED"),
    "official bulk SRTM resolution does not match selected product": ("GEOTIFF_VALIDATION", "BULK_RESOLUTION_MISMATCH"),
    "unexpected SRTM tile dimensions": ("GEOTIFF_VALIDATION", "BULK_TILE_DIMENSION_REJECTED"),
    "OpenTopography returned resolution inconsistent with requested DEM": ("GEOTIFF_VALIDATION", "SOURCE_RESOLUTION_MISMATCH"),
    "P1 local GeoTIFF must exist and not be a symlink": ("GEOTIFF_VALIDATION", "SOURCE_FILE_ABSENT"),
    "P1 GeoTIFF corrupt or unreadable": ("GEOTIFF_VALIDATION", "GEOTIFF_UNREADABLE"),
    "P1 native reader requires single-band Int16 WGS84 EPSG:4326 GeoTIFF": ("GEOTIFF_VALIDATION", "SOURCE_FORMAT_UNSUPPORTED"),
    "P1 source missing valid int16 NoData metadata": ("GEOTIFF_VALIDATION", "SOURCE_NODATA_METADATA_MISSING"),
    "P1 source geographic bounds invalid": ("GEOTIFF_VALIDATION", "SOURCE_BOUNDS_INVALID"),
    "rotated/south-up/nonfinite GeoTIFF source unsupported": ("GEOTIFF_VALIDATION", "SOURCE_GEOTRANSFORM_UNSUPPORTED"),
    "P1 source mosaic/DEM does not cover buffered case bbox": ("CASE_RASTER_ADMISSION", "SOURCE_COVERAGE_INSUFFICIENT"),
    "P1 source case window exceeds pixel memory budget": ("CASE_RASTER_ADMISSION", "CASE_PIXEL_BUDGET_EXCEEDED"),
    "P1 case DEM has no valid elevation pixels": ("CASE_RASTER_ADMISSION", "CASE_ALL_NODATA"),
}


def classify_source_failure(exc:P1SourceError)->dict:
    """Map only recognized safe strings to structured reason/stage; fail closed."""
    detail=str(exc)
    api=re.fullmatch(
        r"OpenTopography HTTP ([1-5]\d{2}) \[([A-Z_]+)\]; key, URL and (?:provider )?body withheld",
        detail)
    allowed={"API_KEY_REJECTED","QUOTA_OR_RATE_LIMIT","REQUEST_BBOX_REJECTED",
             "DATASET_UNAVAILABLE","UNCLASSIFIED_PROVIDER_REJECTION"}
    if api and api.group(2) in allowed:
        return {"source_provider_http_code":int(api.group(1)),
                "provider_failure_category":api.group(2),
                "source_failure_stage":"OPENTOPOGRAPHY_API",
                "source_failure_reason_code":"API_HTTP_REJECTED"}
    bulk=re.fullmatch(
        r"official public SRTM tile HTTP ([1-5]\d{2}), body withheld",detail)
    if bulk:
        return {"source_provider_http_code":int(bulk.group(1)),
                "provider_failure_category":"BULK_TILE_HTTP_REJECTED",
                "source_failure_stage":"S3_BULK_DOWNLOAD",
                "source_failure_reason_code":"BULK_TILE_HTTP_REJECTED"}
    value=_SOURCE_FAILURES.get(detail)
    if value is None and re.fullmatch(
            r"P1 DEM has \d+ NoData pixels in buffered case; "
            r"use --allow-nodata only after documenting void handling",detail):
        value=("CASE_RASTER_ADMISSION","CASE_NODATA_PRESENT")
    if value is None:
        value=("UNCLASSIFIED_SOURCE_STAGE","UNCLASSIFIED_SOURCE_FAILURE")
    return {"source_provider_http_code":None,
            "provider_failure_category":"SOURCE_CHECK_BLOCKED",
            "source_failure_stage":value[0],
            "source_failure_reason_code":value[1]}


def main(argv=None)->int:
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,required=True)
    p.add_argument("--route",choices=["P1_A_90M_LOCAL","P1_B_30M_DOWNLOAD",
                                       "P1_B_90M_DOWNLOAD"],required=True)
    p.add_argument("--binary",type=Path,required=True)
    p.add_argument("--tif-dir",type=Path)
    p.add_argument("--report",type=Path,required=True)
    a=p.parse_args(argv)
    if a.report.exists() or a.root.exists():
        raise SystemExit("refusing to overwrite P1 existing case or report")
    a.root.mkdir(parents=True)
    try:
        result=run(root=a.root,route=a.route,binary=a.binary,tif_dir=a.tif_dir)
    except P1SourceError as exc:
        # Never print provider response, secret, full request URL or raw
        # exception. Preserve bounded, categorical failed-at-source proof.
        diagnosis=classify_source_failure(exc)
        report={
          "schema_version":"p1-issue54-real-actions-source-blocker-v2",
          "route":a.route,
          "status":"BLOCKED_REAL_SOURCE_INPUT",
          **diagnosis,
          "source_product_authenticated":False,
          "native_p1_executed":False,
          "original_terrel_executed":False,
          "science_acceptance":"NOT_ACCEPTED"
        }
        a.report.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print(json.dumps({"status":report["status"],"route":a.route,
                          "http_status":report["source_provider_http_code"],
                          "category":report["provider_failure_category"],
                          "stage":report["source_failure_stage"],
                          "reason_code":report["source_failure_reason_code"]}))
        return 2
    a.report.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"status":result["status"],"route":result["route"],
                      "rows":result["row_count"],"nodata":result["source_case_nodata_pixels"],
                      "science":result["science_acceptance"]}))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
