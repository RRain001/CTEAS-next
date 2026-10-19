#!/usr/bin/env python3
"""P2-B REVIEW ONLY: source GLC35 -> historical USGS38 -> frozen MAKEGEO14.

Never constructs 38-class production LU.DAT and never approves a class mapping.
Loads the ACTUAL frozen MAKEGEO X table, not a guessed 14-class lookup.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path

from scripts.s2g.audit_glc_crosswalk_review import (
    AuditError, USGS38, audit,
)

CANDIDATE_ALTERNATIVES = {
    # Frozen Hefei site-only representative and physically distinct alternatives.
    # These lists are *comparisons*, not global accepted policies.
    182: (61, 62, 52),       # forested wetland / marsh / open water
    183: (62, 77, 52),       # marsh / unvegetated flat / inundation
    190: (11, 16),           # low-density urban vs mixed built-up
    200: (74, 77),           # exposed consolidated rock vs mixed barren
    210: (51, 52, 53, 54),   # river / lake / reservoir / marine/bay
}
PARAMS = ("z0_m", "albedo", "bowen", "soil_heat", "anthro_heat_wm2", "lai")
USGS_ORDER = (11,12,13,14,15,16,17,21,22,23,24,31,32,33,41,42,43,
              51,52,53,54,55,61,62,71,72,73,74,75,76,77,81,82,83,84,85,91,92)
REVIEW_STATE = "P2_MAPPING_REVIEW_REQUIRED"


def need(ok: bool, why: str) -> None:
    if not ok:
        raise AuditError(why)


def hash_file(path: Path) -> str:
    need(path.is_file() and not path.is_symlink(), "P2B_MAKEGEO_FILE_MISSING")
    h=hashlib.sha256()
    with path.open("rb") as f:
        for x in iter(lambda:f.read(65536), b""):
            h.update(x)
    return h.hexdigest()


def parse_original_makegeo(path: Path):
    """Parse active ! X=...! records and ! OUTCAT=...! from the selected control."""
    source=path.read_text(encoding="utf-8")
    inputs={}
    output_ids=[]
    water=[]
    controls={}
    for line in source.splitlines():
        m=re.search(r"!\s*(X|OUTCAT|IWAT|NINCAT|NOUTCAT|NSPLIT|CFRACT|FLUMIN)\s*=\s*([^!]+)!",line)
        if not m:
            continue
        key,values=m.groups()
        parts=[v.strip() for v in values.split(",") if v.strip()]
        if key=="X":
            need(len(parts)==8, "P2B_MAKEGEO_BAD_X_WIDTH")
            code=int(parts[0])
            nums=[float(v) for v in parts[1:7]]
            need(all(math.isfinite(x) for x in nums) and nums[0]>0,
                 "P2B_MAKEGEO_INVALID_PARAM")
            item={"usgs92":code,**dict(zip(PARAMS,nums)),
                  "output_14":int(parts[7])}
            need(code not in inputs,"P2B_MAKEGEO_DUPLICATE_X")
            inputs[code]=item
        elif key=="OUTCAT":
            output_ids.extend(int(v) for v in parts)
        elif key=="IWAT":
            water.extend(int(v) for v in parts)
        else:
            need(key not in controls,"P2B_MAKEGEO_DUPLICATE_CONTROL")
            controls[key]=float(parts[0])
    need(tuple(inputs)==USGS_ORDER and set(inputs)==USGS38 and
         len(inputs)==38,"P2B_MAKEGEO_NOT_SELECTED_38_CLASSES")
    need(len(output_ids)==14 and len(set(output_ids))==14 and
         int(controls.get("NINCAT",0))==38 and
         int(controls.get("NOUTCAT",0))==14 and
         int(controls.get("NSPLIT",-1))==0,
         "P2B_MAKEGEO_NOT_SELECTED_14_CLASS_PATH")
    # The signed -20 entry in the output category list is original syntax;
    # it is not an additional source class or a mapping target.
    need(set(item["output_14"] for item in inputs.values()).issubset(
         set(output_ids)),"P2B_MAKEGEO_X_OUTCAT_CONFLICT")
    need(water==[51,52,53,54,55] and
         abs(controls["CFRACT"]-.5)<1e-9 and
         abs(controls["FLUMIN"]-.96)<1e-9,
         "P2B_MAKEGEO_WATER_RULES_DRIFT")
    for code,item in inputs.items():
        item["is_water_for_CFraCT"] = code in water
    return dict(input_38=inputs, output_14=output_ids,
                input_water=water, selected_controls=controls,
                original_makegeo_control_sha256=hash_file(path))


def surface_fingerprint(item: dict):
    return tuple(item[k] for k in PARAMS)+(
        item["output_14"],item["is_water_for_CFraCT"])


def evaluate(proposal: dict, source_meta: dict, original: dict, *,
             modelgrid: dict | None = None) -> dict:
    """Compare actual physical tuples by original MAKEGEO X entries."""
    source_audit=audit(source_meta,proposal)
    need(proposal["scientific_approval"]==REVIEW_STATE
         and not proposal["is_approved"],"P2B_CANNOT_PREAPPROVE_MAPPING")
    areas={}
    area_total=None
    if modelgrid is not None:
        need(modelgrid.get("status")==REVIEW_STATE and
             modelgrid.get("source_data_sha256")==source_meta["sha256"] and
             modelgrid.get("comparison_basis")==
             "REAL_MODEL_GRID_AREA_M2_NOT_BUFFERED_PIXEL_COUNTS" and
             modelgrid.get("GLC_TO_USGS92_LU_DAT")=="NOT_AUTHORIZED" and
             modelgrid.get("model_cells")==2500,
             "P2B_MAKEGEO_UNTRUSTED_MODELGRID_REVIEW")
        area_total=float(modelgrid["model_area_m2"])
        need(math.isfinite(area_total) and area_total>0,
             "P2B_MAKEGEO_BAD_MODEL_AREA")
        areas={int(k):float(v) for k,v in
               modelgrid["raw_area_by_glc_class_m2"].items()}
        need(set(areas)==set(source_meta["allowed_class_codes"]) and
             all(math.isfinite(v) and v>=0 for v in areas.values()) and
             abs(sum(areas.values())-area_total)<1e-5,
             "P2B_MAKEGEO_UNTRUSTED_CLASS_AREAS")
    original_x=original["input_38"]
    need(set(original_x)==USGS38,"P2B_MAKEGEO_NOT_FULL_USGS38")
    rows=[]
    for rec in proposal["classes"]:
        src=rec["code"]
        target=rec["candidate_target_usgs92"]
        item=original_x.get(target) if target is not None else None
        options=CANDIDATE_ALTERNATIVES.get(src,())
        option_rows=[original_x[t] for t in options]
        family={}
        for x in option_rows:
            key=json.dumps(surface_fingerprint(x))
            family.setdefault(key,[]).append(x["usgs92"])
        row={
          "glc_code":src,
          "source_label":rec["source_label"],
          "review_tier":rec["evidence_tier"],
          "candidate_usgs92_NOT_APPROVED":target,
          "candidate_output_14_NOT_APPROVED":item["output_14"] if item else None,
          "candidate_surface_params_NOT_APPROVED":
              {k:item[k] for k in PARAMS} if item else None,
          "model_area_m2":areas.get(src) if area_total is not None else None,
          "model_fraction":areas.get(src,0)/area_total if area_total else None,
          "alternative_inputs_FOR_REVIEW":list(options),
          "alternative_fingerprints":{
             str(x["usgs92"]):{
               "output_14":x["output_14"],
               "input_water":x["is_water_for_CFraCT"],
               **{k:x[k] for k in PARAMS}
             } for x in option_rows
          },
          "identical_physically_and_output_groups":{
             "/".join(map(str,codes)):codes for codes in family.values()},
          "all_alternatives_identical":len(family)==1 if options else None,
          "source_mapping_is_approved":False,
        }
        rows.append(row)
    # Exact equalities belong to the *selected* control only.
    fresh=[original_x[k] for k in (51,52,53)]
    need(surface_fingerprint(fresh[0])==
         surface_fingerprint(fresh[1])==
         surface_fingerprint(fresh[2]) and
         fresh[0]["output_14"]==51,
         "P2B_MAKEGEO_FRESHWATER_EQUIVALENCE_NOT_TRUE")
    urban=[original_x[k] for k in (11,16)]
    need(urban[0]["output_14"]==urban[1]["output_14"]==10 and
         urban[0]["z0_m"]!=urban[1]["z0_m"],
         "P2B_MAKEGEO_URBAN_SENSITIVITY_DRIFT")
    return {
      "status":REVIEW_STATE,
      "site_science_approval":"NOT_GRANTED",
      "source_glc35_legend":"GLC_FCS30D_2022",
      "source_glc35_sha256":source_meta["sha256"],
      "source_review":"source class legend and unapproved 35-class candidate",
      "original_makegeo_source_sha256":original["original_makegeo_control_sha256"],
      "n_original_input_usgs92":38,"n_original_output_categories":14,
      "output_categories_original_as_written":original["output_14"],
      "input_water_CFraCT_categories":original["input_water"],
      "strict_freshwater_selected_profile_equivalent_USGS92":[51,52,53],
      "freshwater_all_same_six_surface_params_and_output_51":True,
      "urban_usgs11_vs_16_different_roughness":True,
      "model_total_area_m2":area_total,
      "mapping_review_by_source_class":rows,
      "review_required_observed_classes":[r["glc_code"] for r in rows
             if (r["model_area_m2"] or 0)>0 and
             r["review_tier"]!="candidate"],
      "next_decision":"CONFIRM_FRESHWATER_IDENTITY_FLOODED_FLAT_CONDITION_AND_IMPERVIOUS_SUBTYPE",
      "lu_dat_38_production":"NOT_AUTHORIZED",
      "p3_makegeo_14_production":"NOT_RUN",
    }


def main():
    p=argparse.ArgumentParser()
    for arg in ("makegeo-inp","proposal","metadata","out"):
        p.add_argument("--"+arg,required=True,type=Path)
    p.add_argument("--real-modelgrid-review",type=Path)
    args=p.parse_args()
    need(not args.out.exists() and not args.out.is_symlink(),
         "P2B_MAKEGEO_REPORT_EXISTS")
    for path in (args.proposal,args.metadata):
        hash_file(path)
    src=json.loads(args.metadata.read_text())
    proposal=json.loads(args.proposal.read_text())
    model=json.loads(args.real_modelgrid_review.read_text()) if args.real_modelgrid_review else None
    orig=parse_original_makegeo(args.makegeo_inp)
    result=evaluate(proposal,src,orig,modelgrid=model)
    result["candidate_proposal_sha256"]=hash_file(args.proposal)
    result["real_modelgrid_review_sha256"]=(
       hash_file(args.real_modelgrid_review) if args.real_modelgrid_review else None)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({
        "status":result["status"],
        "original_input":38,"original_output":14,
        "freshwater_51_52_53_physics_equivalent":
            result["freshwater_all_same_six_surface_params_and_output_51"],
        "urban_11_vs_16_roughness_different":
            result["urban_usgs11_vs_16_different_roughness"],
        "review_required_observed_classes":result["review_required_observed_classes"],
        "lu_dat":result["lu_dat_38_production"],
    },ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
