#!/usr/bin/env python3
"""Issue #53 GLC35->USGS92 review-only, fail-closed quantitative source audit.

Does NOT apply a mapping to a LU.DAT file. Candidate entries are not approvals.
Input histogram is the 172x172 buffered source TIFF, NOT target-grid fractions.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

class AuditError(ValueError):
    pass

CROSSWALK_STATUS="P2_MAPPING_REVIEW_REQUIRED"
SCHEMA="cteas.p2.glc_crosswalk_review.v1"
USGS38={11,12,13,14,15,16,17,21,22,23,24,31,32,33,41,42,43,51,52,
        53,54,55,61,62,71,72,73,74,75,76,77,81,82,83,84,85,91,92}

def ensure(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as fp:
        for buf in iter(lambda:fp.read(1<<20),b""):
            h.update(buf)
    return h.hexdigest()

def audit(metadata: dict, proposal: dict, *, source_tif: Path | None = None) -> dict:
    ensure(proposal.get("schema")==SCHEMA, "WRONG_MAPPING_SCHEMA")
    ensure(proposal.get("scientific_approval")==CROSSWALK_STATUS and
           proposal.get("is_approved") is False, "UNAUTHORIZED_MAPPING_APPROVAL")
    ensure(proposal.get("source_data_sha256")==metadata.get("sha256"),
           "SOURCE_SHA_MISMATCH")
    ensure(metadata.get("width")==172 and metadata.get("height")==172 and
           metadata.get("pixel_resolution")==[30.0,30.0],
           "SOURCE_GRID_UNEXPECTED")
    ensure(metadata.get("crs")=="EPSG:32650" and metadata.get("year")==2022,
           "SOURCE_CRS_YEAR_MISMATCH")
    allowed=metadata.get("allowed_class_codes")
    classes=proposal.get("classes")
    ensure(isinstance(allowed,list) and len(allowed)==35 and
           isinstance(classes,list) and len(classes)==35, "NOT_35_CLASSES")
    codes=[r.get("code") for r in classes]
    ensure(codes==allowed and len(set(codes))==35, "GLC_CLASS_ORDER_OR_DUPLICATE")
    histogram=metadata.get("classes_histogram")
    ensure(isinstance(histogram,dict), "MISSING_REAL_HISTOGRAM")
    hist={int(k):v for k,v in histogram.items()}
    ensure(set(hist).issubset(set(allowed)) and len(hist)==12,
           "HISTOGRAM_UNKNOWN_CLASS")
    ensure(all(type(v)==int and v>0 for v in hist.values()),"HISTOGRAM_BAD_COUNT")
    ensure(sum(hist.values())==172*172, "HISTOGRAM_PIXEL_TOTAL_MISMATCH")
    if source_tif is not None:
        ensure(source_tif.is_file() and not source_tif.is_symlink(),
               "SOURCE_TIF_MISSING_OR_SYMLINK")
        ensure(source_tif.stat().st_size==metadata["size_bytes"],
               "SOURCE_TIF_WRONG_SIZE")
        ensure(sha256(source_tif)==metadata["sha256"],
               "SOURCE_TIF_SHA_MISMATCH")
    tiers={"candidate","site_evidence","blocked"}
    grouped={tier:[] for tier in tiers}
    observed_grouped={tier:0 for tier in tiers}
    for row in classes:
        code=row["code"];target=row.get("candidate_target_usgs92")
        tier=row.get("evidence_tier")
        ensure(row.get("approval")=="NOT_APPROVED" and tier in tiers,
               "UNAUTHORIZED_CLASS_MAPPING_APPROVAL")
        ensure(isinstance(row.get("source_label"),str) and row["source_label"] and
               isinstance(row.get("reason"),str) and row["reason"],
               "MISSING_EVIDENCE_REASON")
        ensure(row.get("observed_buffered_pixels")==hist.get(code,0),
               "HISTOGRAM_CANDIDATE_MISMATCH")
        ensure((target is None if tier=="blocked" else type(target)==int and target in USGS38),
               "INVALID_CANDIDATE_USGS92")
        grouped[tier].append(code)
        observed_grouped[tier]+=hist.get(code,0)
    for code,target in [(51,42),(52,42),(61,41),(62,41),(71,42),
                        (72,42),(81,41),(82,41),(91,43),(92,43)]:
        row=next(r for r in classes if r["code"]==code)
        ensure(row["candidate_target_usgs92"]==target,"FOREST_CANDIDATE_DRIFT")
        ensure(row["source_label"].startswith("Closed " if code%10==1 else "Open "),
               "FOREST_CLOSED_OPEN_LEGEND_REVERSED")
    for code in (183,210):
        row=next(r for r in classes if r["code"]==code)
        ensure(row["evidence_tier"]=="blocked" and
               row["candidate_target_usgs92"] is None,
               "FLOODED_FLAT_OR_WATER_UNAPPROVED_FALLBACK")
    for code in (182,190):
        row=next(r for r in classes if r["code"]==code)
        ensure(row["evidence_tier"]=="site_evidence",
               "WETLAND_OR_URBAN_SITE_EVIDENCE_BYPASS")
    n=172*172
    return {
       "status":CROSSWALK_STATUS,
       "input_kind":"real_2022_GLC_FCS30D_172x172_metadata_histogram",
       "source_sha256":metadata["sha256"],
       "source_tif_bytes_verified":source_tif is not None,
       "total_buffered_pixels":n,
       "actual_class_count":12,
       "full_legend_class_count":35,
       "candidate_only_classes":grouped["candidate"],
       "site_evidence_required_classes":grouped["site_evidence"],
       "blocked_unmapped_classes":grouped["blocked"],
       "pixels_by_review_tier":observed_grouped,
       "blocked_unmapped_buffered_pixels":observed_grouped["blocked"],
       "blocked_unmapped_fraction":observed_grouped["blocked"]/n,
       "site_evidence_buffered_fraction":observed_grouped["site_evidence"]/n,
       "not_model_grid_area_fractions":True,
       "GLC_TO_USGS92_LU_DAT":"NOT_AUTHORIZED",
       "P3_GEO_DAT":"NOT_RUN",
       "science_review":"NEEDS_SITE_EVIDENCE_AND_P3_PARAMETER_IMPACT_REVIEW",
    }

def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--metadata",required=True,type=Path)
    p.add_argument("--proposal",required=True,type=Path)
    p.add_argument("--source-tif",type=Path)
    p.add_argument("--out",required=True,type=Path)
    a=p.parse_args()
    ensure(not a.out.exists() and not a.out.is_symlink(),"REPORT_OVERWRITE_REFUSED")
    result=audit(json.loads(a.metadata.read_text()),json.loads(a.proposal.read_text()),
                 source_tif=a.source_tif)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\n")
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
