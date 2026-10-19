#!/usr/bin/env python3
"""#53 P2-B: model-grid actual-area crosswalk QUANTIFICATION, not approval.

Reads offline native D2's model-cell raw fractions/area and 35-class unapproved
review proposal. Produces an explicit incomplete candidate-only USGS38 preview
plus site-evidence/unresolved shares; NEVER emits LU.DAT or claims P3 ready.
No remote data access, no interpolation of categorical pixels.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

from scripts.s2g.audit_glc_crosswalk_review import audit, AuditError, USGS38


def require(ok: bool, name: str) -> None:
    if not ok:
        raise AuditError(name)


def digest(path: Path) -> str:
    require(path.is_file() and not path.is_symlink(),
            "MODEL_GRID_SOURCE_MISSING_OR_SYMLINK")
    sha=hashlib.sha256()
    with path.open("rb") as stream:
        for data in iter(lambda: stream.read(1<<20), b""):
            sha.update(data)
    return sha.hexdigest()


def csv_rows(path: Path, expected_header: list[str]):
    require(path.is_file() and not path.is_symlink(),
            "MODEL_GRID_CSV_MISSING_OR_SYMLINK")
    with path.open(newline="", encoding="utf-8") as stream:
        reader=csv.DictReader(stream)
        require(reader.fieldnames == expected_header, "MODEL_GRID_CSV_SCHEMA_DRIFT")
        rows=list(reader)
    require(rows and all(None not in row and None not in row.values()
                         for row in rows), "MODEL_GRID_TRUNCATED_CSV")
    return rows


def exact_number(raw: str) -> float:
    try:
        number=float(raw)
    except (ValueError,TypeError):
        raise AuditError("MODEL_GRID_INVALID_NUMBER") from None
    require(math.isfinite(number), "MODEL_GRID_NONFINITE_NUMBER")
    return number


def compute(metadata: dict, proposal: dict, manifest: dict,
            fractions: Path, areas: Path, *, source_tif: Path | None = None):
    """Return (report, preview_rows) with exact actual-model-area accounting."""
    source_audit=audit(metadata,proposal,source_tif=source_tif)
    require(manifest.get("producer")=="cteas_p2_glc_raw" and
            manifest.get("source_kind")=="GLC_FCS30D_2022_30m" and
            manifest.get("source_sha256")==metadata.get("sha256") and
            manifest.get("raw_category_namespace")=="GLC_FCS30D_35" and
            manifest.get("method")=="exact_north_up_same_utm_pixel_cell_rectangle_intersection" and
            manifest.get("coverage_policy")=="REJECT_ANY_NODATA_OR_INCOMPLETE_CELL" and
            manifest.get("evidence_status")=="PRODUCED_UNVERIFIED" and
            manifest.get("crosswalk_status")=="P2_MAPPING_REVIEW_REQUIRED" and
            manifest.get("usgs92_lu_dat")=="NOT_RUN" and
            manifest.get("p3_geo_dat")=="NOT_RUN",
            "MODEL_GRID_D2_PROVENANCE_UNTRUSTED")
    nx,ny=manifest.get("nx"),manifest.get("ny")
    spacing=manifest.get("dgridkm")
    require(type(nx)==int and type(ny)==int and 1<=nx*ny<=2000000 and
            type(spacing) in (int,float) and
            math.isfinite(spacing) and spacing>0,
            "MODEL_GRID_INVALID_DIMENSIONS")
    require(type(manifest.get("utm_epsg"))==int and
            ((32601<=manifest["utm_epsg"]<=32660) or
             (32701<=manifest["utm_epsg"]<=32760)),
            "MODEL_GRID_INVALID_UTM")
    allowed=metadata["allowed_class_codes"]
    hdr=["i","j","cell_area_m2","valid_area_m2","coverage_fraction"]+[
        f"glc{x}" for x in allowed]
    area_hdr=["i","j"]+[f"glc{x}" for x in allowed]
    raw_rows=csv_rows(fractions,hdr)
    area_rows=csv_rows(areas,area_hdr)
    require(len(raw_rows)==len(area_rows)==nx*ny,"MODEL_GRID_ROW_COUNT")
    cases={int(x["code"]):x for x in proposal["classes"]}
    require(list(cases)==allowed,"MODEL_GRID_PROPOSAL_CLASS_ORDER")
    candidate_columns=sorted(USGS38)
    buffered=source_audit["pixels_by_review_tier"]
    tiers={"candidate":0.,"site_evidence":0.,"blocked":0.}
    area_class={code:0. for code in allowed}
    positive_cells={code:0 for code in allowed}
    candidate_target={t:0. for t in candidate_columns}
    blocked_cells=0
    site_cells=0
    first_issues=[]
    out=[]
    total_model_area=0.
    for idx,(raw,are) in enumerate(zip(raw_rows,area_rows)):
        i,j=idx%nx+1,idx//nx+1
        require(raw["i"]==are["i"]==str(i) and
                raw["j"]==are["j"]==str(j),"MODEL_GRID_CELL_ORDER")
        cell_area=exact_number(raw["cell_area_m2"])
        valid=exact_number(raw["valid_area_m2"])
        cover=exact_number(raw["coverage_fraction"])
        expected=(spacing*1000.)**2
        require(abs(cell_area-expected)<=max(1e-6,expected*1e-9) and
                abs(valid-cell_area)<=max(1e-6,expected*1e-9) and
                abs(cover-1.)<=1e-9,
                "MODEL_GRID_SOURCE_INCOMPLETE_COVERAGE")
        total_model_area+=cell_area
        tier_fraction={t:0. for t in tiers}
        candidate={code:0. for code in candidate_columns}
        fraction_total=0.
        area_total=0.
        issues={}
        for code in allowed:
            k=f"glc{code}"
            fraction=exact_number(raw[k])
            area=exact_number(are[k])
            require(-1e-11<=fraction<=1+1e-11 and area>=-1e-7,
                    "MODEL_GRID_NEGATIVE_OR_OVERFULL_CATEGORY")
            require(abs(fraction-area/valid)<=2e-9,
                    "MODEL_GRID_FRACTION_AREA_MISMATCH")
            fraction_total+=fraction
            area_total+=area
            if area>1e-8:
                positive_cells[code]+=1
                area_class[code]+=area
                row=cases[code]
                tier=row["evidence_tier"]
                tiers[tier]+=area
                tier_fraction[tier]+=fraction
                if tier=="candidate":
                    target=row["candidate_target_usgs92"]
                    candidate[target]+=fraction
                    candidate_target[target]+=area
                else:
                    issues[str(code)]=round(fraction,12)
        require(abs(area_total-valid)<=max(1e-6,valid*1e-9) and
                abs(fraction_total-1.)<=1e-8 and
                abs(sum(tier_fraction.values())-1.)<=1e-8 and
                abs(sum(candidate.values())-tier_fraction["candidate"])<=1e-8,
                "MODEL_GRID_AREA_OR_TIER_CONSERVATION")
        blocked_cells+=tier_fraction["blocked"]>1e-10
        site_cells+=tier_fraction["site_evidence"]>1e-10
        if issues and len(first_issues)<30:
            first_issues.append({"i":i,"j":j,"unapproved_glc_fraction":issues})
        record={"i":str(i),"j":str(j),
                "candidate_only_fraction":f'{tier_fraction["candidate"]:.12f}',
                "site_evidence_fraction":f'{tier_fraction["site_evidence"]:.12f}',
                "unmapped_blocked_fraction":f'{tier_fraction["blocked"]:.12f}'}
        record.update({f"candidate_usgs{x}":f"{candidate[x]:.12f}"
                       for x in candidate_columns})
        out.append(record)
    require(abs(sum(tiers.values())-total_model_area)<=
            max(1e-5,total_model_area*1e-10),
            "MODEL_GRID_TOTAL_TIER_CONSERVATION")
    require(abs(sum(area_class.values())-total_model_area)<=
            max(1e-5,total_model_area*1e-10),
            "MODEL_GRID_TOTAL_RAW_AREA_CONSERVATION")
    report={
        "status":"P2_MAPPING_REVIEW_REQUIRED",
        "source_data_sha256":metadata["sha256"],
        "proposal_sha256":None,  # added by CLI after reading raw bytes
        "d2_raw_fractions_sha256":digest(fractions),
        "d2_raw_class_area_m2_sha256":digest(areas),
        "source_tif_bytes_verified":source_audit["source_tif_bytes_verified"],
        "comparison_basis":"REAL_MODEL_GRID_AREA_M2_NOT_BUFFERED_PIXEL_COUNTS",
        "grid":{"nx":nx,"ny":ny,"utm_epsg":manifest["utm_epsg"],
                "dgridkm":spacing,"xrefkm":manifest.get("xrefkm"),
                "yrefkm":manifest.get("yrefkm")},
        "model_cells":nx*ny,
        "model_area_m2":total_model_area,
        "buffered_pixel_tiers_for_context_only":buffered,
        "area_by_review_tier_m2":tiers,
        "fraction_by_review_tier":{
            k:v/total_model_area for k,v in tiers.items()},
        "raw_area_by_glc_class_m2":{str(k):v for k,v in area_class.items()},
        "model_cells_by_glc_class":{str(k):n for k,n in positive_cells.items()
                                    if n},
        "candidate_only_usgs_area_m2":{str(k):v for k,v in candidate_target.items()
                                       if v>0},
        "cells_requiring_site_evidence":site_cells,
        "cells_containing_blocked_mapping":blocked_cells,
        "first_30_unapproved_cells":first_issues,
        "candidate_usgs_preview":"PARTIAL_UNAPPROVED_NOT_LU_DAT",
        "GLC_TO_USGS92_LU_DAT":"NOT_AUTHORIZED",
        "P3_GEO_DAT":"NOT_RUN",
        "next_decision":"REVIEW_ACTUAL_MODEL_GRID_WETLAND_FLOODPLAIN_URBAN_AND_WATER_CELLS"
    }
    return report,out


def main() -> int:
    p=argparse.ArgumentParser()
    for key in ("metadata","proposal","d2-manifest","d2-fractions",
                "d2-areas","out-dir"):
        p.add_argument("--"+key,required=True,type=Path)
    p.add_argument("--source-tif",type=Path)
    args=p.parse_args()
    require(not args.out_dir.exists() and not args.out_dir.is_symlink(),
            "MODEL_GRID_REPORT_OUTPUT_EXISTS")
    for path in (args.metadata,args.proposal,args.d2_manifest):
        digest(path)
    metadata=json.loads(args.metadata.read_text())
    proposal=json.loads(args.proposal.read_text())
    manifest=json.loads(args.d2_manifest.read_text())
    report,preview=compute(metadata,proposal,manifest,
                           args.d2_fractions,args.d2_areas,
                           source_tif=args.source_tif)
    report["proposal_sha256"]=digest(args.proposal)
    report["d2_manifest_sha256"]=digest(args.d2_manifest)
    args.out_dir.mkdir(parents=True)
    with (args.out_dir/"p2_usgs92_candidate_only_NOT_APPROVED.csv").open(
            "w",newline="",encoding="utf-8") as fp:
        writer=csv.DictWriter(fp,fieldnames=list(preview[0]))
        writer.writeheader()
        writer.writerows(preview)
    report["preview_csv_sha256"]=digest(
        args.out_dir/"p2_usgs92_candidate_only_NOT_APPROVED.csv")
    (args.out_dir/"review.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+"\n")
    print(json.dumps({
        k:report[k] for k in ("status","model_cells","model_area_m2",
                              "fraction_by_review_tier",
                              "cells_containing_blocked_mapping",
                              "GLC_TO_USGS92_LU_DAT")},sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
