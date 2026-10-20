"""#46 D4: bind genuine original Wolsong MAKEGEO parity to P3 B-0 inputs.

No physics computation, no rewriting earlier D2 producer manifests, and never
claim P1/P2 original parity or #42 S3 combined five-product acceptance.
Only one pinned real Wolsong selected no-snow 38→14 Fortran branch admitted.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

from .plan import ContractError

ORIGINAL_MAKEGEO_SOURCE_SHA256 = "8c4fb11db36d4b976b54f470b7a06ce4e38ab09e934951b0e2c613bddc34e347"
WOLSONG_SRTMGL1_SHA256 = "b9b44e6936d45a738ead91429804048e6fa095abbee98e1792b7c42dbecf0769"
WOLSONG_GLC30M_SHA256 = "2a1a208c5386735692d788066f730c7391e87f0981e7b9ad099442af2e217711"
FULL_ORIGINAL_COAST_BNL_SHA256 = "67da93d441e7defe3eb46627ed9ce896c0a91ffd89fd5e4363d834d8108e11f9"
FROZEN_30M_POLICY_SHA256 = "a5fa157f57feb1aa160dd96d920a22d267fea78c5828c6040fa95e86536544ed"
SELECTED_P2C = "P2_C_GLC30M_SOURCE_SUBPOINT_GLAZAS_LUGRID_R4_HITS_V1"
FIELDS = ("category","elevation_m","z0_m","albedo","bowen",
          "soil_heat","anthropogenic_heat","lai")
SELECTED_STATUS = "P3_WOLSONG_SELECTED_ORIGINAL_MAKEGEO_ACCEPTED_SCOPED"


def need(predicate: bool, detail: str) -> None:
    if not predicate:
        raise ContractError("P3_D4_ACCEPTANCE_BLOCKED: " + detail)


def sha(path: Path) -> str:
    need(path.is_file() and not path.is_symlink() and 0 < path.stat().st_size < 500_000_000,
         "required independent artifact missing, symlink, empty or too large: " + str(path))
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1<<20),b""):
            h.update(chunk)
    return h.hexdigest()


def load(path: Path) -> dict:
    sha(path)
    obj=json.loads(path.read_text(encoding="utf-8"))
    need(isinstance(obj,dict),"attestation is not JSON object")
    return obj


def accept(*, case_root: Path, original_geo: Path,
           comparison_path: Path, destination: Path) -> dict:
    """Fail-closed promotion of one scoped D3 result, not a mutable P3 overwrite."""
    root=case_root.resolve(strict=True)
    p2_path=root/"evidence/p2.json"
    p3_path=root/"evidence/p3.json"
    lu_path=root/"geo/ctgproc/p2c_case/lu.dat"
    geo_path=root/"geo/makegeo/p3_case/geo.dat"
    csv_path=root/"geo/makegeo/p3_case/p3.csv"
    ctrl_path=root/"geo/makegeo/p3_case/makegeo.inp"
    for path in (p2_path,p3_path,lu_path,geo_path,csv_path,ctrl_path):
        need(path.resolve(strict=True).is_relative_to(root),"file escapes case workspace")
    p2=load(p2_path)
    p3=load(p3_path)
    cmp=load(comparison_path)
    need(destination.resolve().is_relative_to(root),"D4 output must be inside case root")
    need(not destination.exists() and not destination.is_symlink(),"D4 fresh output only")
    need(destination.parent.is_dir() and not destination.parent.is_symlink(),
         "D4 evidence parent directory must already exist")

    need(p2.get("status")=="P2C_GENERIC_CASE_PRODUCED_UNVERIFIED"
         and p2.get("method")==SELECTED_P2C and p2.get("mode")=="coastal",
         "not the selected coastal original-style P2-C input")
    hits_sha=p2.get("hits_csv_sha256")
    need(isinstance(hits_sha,str) and len(hits_sha)==64 and
         all(ch in "0123456789abcdef" for ch in hits_sha),
         "P2 native integer HITS CSV SHA missing or malformed")
    need(p2.get("source_tiff_sha256")==WOLSONG_GLC30M_SHA256 and
         p2.get("source_bln_sha256")==FULL_ORIGINAL_COAST_BNL_SHA256 and
         p2.get("mapping_policy_sha256")==FROZEN_30M_POLICY_SHA256,
         "P2-C genuine 2022/Full coastline SHA not pinned")
    need(p3.get("status")=="P3_NATIVE_SAME_CASE_PRODUCED_UNVERIFIED" and
         p3.get("p2_kind")=="C" and p3.get("p2_method")==SELECTED_P2C and
         p3.get("p1_tif_sha256")==WOLSONG_SRTMGL1_SHA256 and
         p3.get("p3_original_makegeo_science")=="NOT_RUN",
         "native D2 production status/source not pinned")

    for key in ("case_name","case_yaml_sha256","grid_cmn_sha256","research_time_sha256",
                "utm_epsg","nx","ny"):
        need(p2.get(key)==p3.get(key),"P2/P3 B-0 mismatch: "+key)
    need(p2.get("case_name")=="p3_d2_wolsong_2022" and
         p2.get("utm_epsg")==32652 and
         p2.get("nx")==200 and p2.get("ny")==200 and
         p3.get("xrefkm")=="533.215" and p3.get("yrefkm")=="3942.629" and
         abs(p3.get("dgridkm",-1)-.100)<1e-12,
         "D3 source grid not independently accepted Wolsong 200x200 @100m")
    need(p3.get("p2_attestation_sha256")==sha(p2_path) and
         p3.get("p2_lu_dat_sha256")==p2.get("lu_dat_sha256")==sha(lu_path),
         "P2 LU bytes not preserved into native P3")
    need(p3.get("geo_dat_sha256")==sha(geo_path) and
         p3.get("p3_csv_sha256")==sha(csv_path) and
         p3.get("makegeo_controls_sha256")==sha(ctrl_path),
         "native P3/MAKEGEO output bytes not preserved")
    need(all(isinstance(p3.get(k),str) and len(p3[k])==64 for k in
             ("p1_bin_sha256","p3_bin_sha256","dat_bin_sha256",
              "terrel_dat_sha256","makegeo_template_sha256")),
         "native product/provenance SHA incomplete")
    need(cmp.get("status")=="P3_NONHEFEI_ORIGINAL_MAKEGEO_PASS" and
         cmp.get("failures")==0 and cmp.get("values_compared")==320000 and
         cmp.get("formatted_values_compared")==320000,
         "D3 original Fortran scientific acceptance not PASS")
    need((cmp.get("nx"),cmp.get("ny"),cmp.get("utm_zone"),cmp.get("utm_hemisphere"))==
         (200,200,52,"N") and
         abs(cmp.get("xrefkm",-1)-533.215)<1e-9 and
         abs(cmp.get("yrefkm",-1)-3942.629)<1e-9 and
         abs(cmp.get("dgridkm",-1)-.1)<1e-9,
         "D3 comparison reference grid not pinned")
    need(cmp.get("native_geo_sha256")==sha(geo_path) and
         cmp.get("native_csv_sha256")==sha(csv_path) and
         cmp.get("original_geo_sha256")==sha(original_geo),
         "D3 comparison GEO bytes not the same verified actual files")
    metrics=cmp.get("metrics",{})
    need(set(metrics)==set(FIELDS),"D3 report missing or extra accepted physical field")
    for field in FIELDS:
        row=metrics[field]
        need(isinstance(row,dict) and row.get("compared_cells")==40000 and
             row.get("displayed_value_mismatches")==0 and
             row.get("csv_outside_fixed_precision_tolerance")==0,
             "D3 field failed science: "+field)
    # Never conflate a source/product producer attestation with independent
    # original verification; the separate D4 certificate is only for P3.
    result={
        "schema":"cteas.p3.selected_science_d4_handoff.v1",
        "status":SELECTED_STATUS,
        "original_makegeo_source_ref":"RRain001/CTEAS@dfad99a78ed84d655e21411c9d25eb0d2583bf13",
        "original_makegeo_source_sha256":ORIGINAL_MAKEGEO_SOURCE_SHA256,
        "p3_supported_physical_options":"LTERR=T;LLU2=F;LSNOW=F;NSPLIT=0;38_TO_14",
        "site":"Wolsong",
        "year":2022,
        "nx":200,"ny":200,"utm_epsg":32652,
        "case_yaml_sha256":p3["case_yaml_sha256"],
        "grid_cmn_sha256":p3["grid_cmn_sha256"],
        "research_time_sha256":p3["research_time_sha256"],
        "research_begin_utc":p3.get("research_begin_utc"),
        "research_end_utc":p3.get("research_end_utc"),
        "p1_real_srtmgl1_sha256":WOLSONG_SRTMGL1_SHA256,
        "p2_real_glc30m_sha256":WOLSONG_GLC30M_SHA256,
        "p2_original_coast_bln_sha256":FULL_ORIGINAL_COAST_BNL_SHA256,
        "p2_mapping_policy_sha256":FROZEN_30M_POLICY_SHA256,
        "p2_lu_dat_sha256":sha(lu_path),
        "p2_integer_hits_csv_sha256":hits_sha,
        "terrel_dat_sha256":p3["terrel_dat_sha256"],
        "p3_native_geo_dat_sha256":sha(geo_path),
        "p3_original_geo_dat_sha256":sha(original_geo),
        "p3_original_comparison_report_sha256":sha(comparison_path),
        "p3_native_attestation_sha256":sha(p3_path),
        "p2_native_attestation_sha256":sha(p2_path),
        "fields_compared":list(FIELDS),
        "original_displayed_values_compared":320000,
        "original_displayed_value_mismatches":0,
        "csv_outside_predeclared_tolerance":0,
        "p1_source_pixels_original_numerical_science":"NOT_CLAIMED",
        "p2_input_mapping_other_sources":"NOT_CLAIMED",
        "p4_up_dat":"NOT_RUN",
        "p5_surf_dat":"NOT_RUN",
        "p6_g19_source_only":"NOT_RUN",
        "s3_five_product_stack":"NOT_ACCEPTED",
        "docker":"DEFERRED",
    }
    with destination.open("x",encoding="utf-8") as out:
        json.dump(result,out,indent=2,sort_keys=True)
        out.write("\n")
    return result


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-root",type=Path,required=True)
    parser.add_argument("--original-geo",type=Path,required=True)
    parser.add_argument("--comparison",type=Path,required=True)
    parser.add_argument("--destination",type=Path,required=True)
    args=parser.parse_args()
    try:
        print(json.dumps(accept(case_root=args.case_root,original_geo=args.original_geo,
             comparison_path=args.comparison,destination=args.destination),sort_keys=True))
        return 0
    except (ContractError,OSError,ValueError,KeyError,TypeError,json.JSONDecodeError) as exc:
        print(json.dumps({"status":"P3_D4_ACCEPTANCE_BLOCKED","reason":str(exc)}))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
