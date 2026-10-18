"""#54: genuine source (owner SRTM90m / OpenTopography SRTMGL1) -> native P1.

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
    elif route=="P1_B_30M_DOWNLOAD":
        source=prepare(case_root/"grid/grid.cmn",src_out,"opentopography",
                       allow_public_bulk_fallback=True)
        inventory={"status":"P1_B_ACTUAL_REQUEST_SOURCE_ONLY","required_tiles":[]}
        product="SRTMGL1"
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
      "source_product_version_authenticated":False,
      "height_vertical_datum_authenticated":False,
      "original_terrel_executed":False,
      "original_native_parity":"NOT_RUN",
      "science_acceptance":"NOT_ACCEPTED"
    }

def main(argv=None)->int:
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,required=True)
    p.add_argument("--route",choices=["P1_A_90M_LOCAL","P1_B_30M_DOWNLOAD"],required=True)
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
        detail=str(exc)
        matched=re.search(
            r"OpenTopography HTTP (\d{3}) \[([A-Z_]+)\]",detail)
        report={
          "schema_version":"p1-issue54-real-actions-source-blocker-v1",
          "route":a.route,
          "status":"BLOCKED_REAL_SOURCE_INPUT",
          "source_provider_http_code":int(matched.group(1)) if matched else None,
          "provider_failure_category":matched.group(2) if matched else "SOURCE_CHECK_BLOCKED",
          "source_product_authenticated":False,
          "native_p1_executed":False,
          "original_terrel_executed":False,
          "science_acceptance":"NOT_ACCEPTED"
        }
        a.report.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print(json.dumps({"status":report["status"],"route":a.route,
                          "http_status":report["source_provider_http_code"],
                          "category":report["provider_failure_category"]}))
        return 2
    a.report.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"status":result["status"],"route":result["route"],
                      "rows":result["row_count"],"nodata":result["source_case_nodata_pixels"],
                      "science":result["science_acceptance"]}))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
