#!/usr/bin/env python3
"""S3-B7 read-only independent audit of three *actual Actions* source artifacts.

No simulated observation, new physics, or retrospective self-attested PASS.
The isolated audit job consumes separately uploaded scientific reports from the
Jan48, Jun24 and Jun6 real-run matrix, enforcing original/numeric/source SHA.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

PERIODS = ("jan_48h", "jun_24h", "jun_6h")
PREFIX = "issue42-s3-b1b2-huoshan-"
SUFFIX = "-source-original-science"
SOURCE_JOIN = "S3_B0_SAME_CASE_FIVE_PRODUCERS_SOURCE_LINEAGE_PASS_NOT_G19"
G19_PASS = "S3_B6_HUOSHAN_GENUINE_FIVE_SOURCE_NATIVE_G19_PARSED_SCOPED"
G19_NEG = "S3_B7_REAL_24H_G19_UPPER_BRACKET_REJECTED_EXPECTED"
CLOCKS = {
    "jan_48h": ("20220101-000000", "20220103-000000"),
    "jun_24h": ("20220601-000000", "20220602-000000"),
    "jun_6h": ("20220601-010000", "20220601-070000"),
}

def need(test: bool, reason: str) -> None:
    if not test:
        raise ValueError("S3-B7 independent evidence REJECTED: " + reason)

def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1<<20), b""):
            h.update(block)
    return h.hexdigest()

def unique(root: Path, name: str) -> tuple[dict, str]:
    found = [p for p in root.rglob(name) if p.name == name]
    need(len(found) == 1, f"{root.name}: missing/duplicate authentic {name}")
    f = found[0]
    need(not f.is_symlink() and f.is_file() and 0 < f.stat().st_size < 8_000_000,
         f"{root.name}: unsafe/empty/oversized {name}")
    need(not any(p.is_symlink() for p in f.parents if p != root.parent),
         f"{root.name}: parent symlink in {name}")
    value = json.loads(f.read_text("utf-8"))
    need(isinstance(value,dict), f"{root.name}: invalid JSON object {name}")
    return value,sha(f)

def accept(artifacts:Path, output:Path, *, expected_sha:str|None) -> dict:
    need(artifacts.is_absolute() and artifacts.is_dir() and not artifacts.is_symlink(),
         "missing independent real-run artifact directory")
    if expected_sha:
        need(len(expected_sha)==40 and all(c in "0123456789abcdef" for c in expected_sha),
             "invalid exact producer checkout SHA")
    cases={}
    for period in PERIODS:
        folder=artifacts / (PREFIX+period+SUFFIX)
        need(folder.is_dir() and not folder.is_symlink(),
             "not all THREE true original-sci matrix jobs uploaded artifacts: "+period)
        p2,_=unique(folder,"p2.json")
        p3,_=unique(folder,"p3.json")
        cmp,_=unique(folder,"s3-huoshan-original-geo-80k.json")
        original,_=unique(folder,"s3-huoshan-original-p3-science.json")
        need(cmp.get("status")=="P3_NONHEFEI_ORIGINAL_MAKEGEO_PASS" and
             cmp.get("values_compared")==80000 and cmp.get("failures")==0 and
             all(metric.get("displayed_value_mismatches")==0 and
                 metric.get("csv_outside_fixed_precision_tolerance")==0
                 for metric in cmp.get("metrics",{}).values()) and
             len(cmp.get("metrics",{}))==8,
             period+": original independent 80,000 field numerical science does NOT pass")
        need(original.get("status")=="S3_HUOSHAN_SELECTED_P3_ORIGINAL_MAKEGEO_80K_SCIENCE_PASS_SCOPED"
             and original.get("native_geo_fields_compared")==80000
             and original.get("numerical_errors")==0
             and original.get("native_geo_sha256")==cmp.get("native_geo_sha256")
             and original.get("original_geo_sha256")==cmp.get("original_geo_sha256"),
             period+": native/original scientific certificate and original report disagree")
        common=("case_yaml_sha256","grid_cmn_sha256","research_time_sha256")
        need(all(p2.get(k)==p3.get(k)==original.get(k) for k in common),
             period+": real P2/P3/original scientific B0 SHA mismatch")
        need(original.get("source_glcc_sha256")=="4f2a1977d141e2040da4d36ec6a4826c5c960c84686eaf10f226f388cb3ab90a" and
             original.get("source_srtm90_parent_sha256")=="913a082c79df74ff4189fec9d94b678618b395a6fb0a64ee94e14c532362eae4",
             period+": actual real historical GLCC or original SRTM source changed")
        report={
            "case_yaml_sha256":p3["case_yaml_sha256"],
            "grid_cmn_sha256":p3["grid_cmn_sha256"],
            "research_time_sha256":p3["research_time_sha256"],
            "original_report_status":cmp["status"],
            "compared_values":cmp["values_compared"],
            "numeric_failures":cmp["failures"],
            "native_geo_sha256":cmp["native_geo_sha256"],
            "original_geo_sha256":cmp["original_geo_sha256"],
            "p2_method":p3.get("p2_kind"),
        }
        need(report["p2_method"]=="A",period+": retired P2-B or non-approved source used")
        if period != "jan_48h":
            join,_=unique(folder,"s3-b0-five-source-preflight.json")
            p5,_=unique(folder,"p5.json")
            p4,_=unique(folder,"p4_d1a_annual_manifest.json")
            need(join.get("status")==SOURCE_JOIN
                 and all(join.get(k)==report[k] for k in common),
                 period+": source-only five-producer join missing or another case B0")
            need(p5.get("status")=="PRODUCED_UNVERIFIED" and
                 p5.get("published_surf_sha256")==
                 join.get("actual_source_sha256",{}).get("surf_sha256"),
                 period+": actual real NOAA published SURF receipt mismatch")
            need(p4.get("status")=="PRODUCED_UNVERIFIED" and
                 p4.get("candidate_final",{}).get("station_count")==1 and
                 p4.get("jdat")==2 and p4.get("ifmt")==1,
                 period+": real original P4 READ62 candidate missing/wrong option")
            report["real_p1_to_p5_same_site_sha_join"]=SOURCE_JOIN
            report["p4_original_2022_qualified_stations"]=[
                x.get("wmo") for x in p4["candidate_final"]["files"]]
            report["p5_published_surface_sha256"]=p5["published_surf_sha256"]
            need(report["p4_original_2022_qualified_stations"]==["58424"],
                 period+": actual real P4 upper station unexpected")
            if period=="jun_6h":
                g19,_=unique(folder,"s3-b6-g19-source-only.json")
                need(g19.get("status")==G19_PASS
                     and g19.get("source_only_parsed") is True
                     and g19.get("p4_source_stations")==["CHM00058424"]
                     and g19.get("p5_source_stations")==["58321099999"]
                     and g19.get("p6d_e_f_numerical_wind")=="NOT_RUN"
                     and all(g19.get(k)==report[k] for k in common)
                     and "PASS_P6G_G19_FILE_SOURCE_CONTRACT" in
                         g19.get("actual_source_parser_stdout_tail",""),
                     "real six-hour native G19 positive case not original-source verified")
                report["actual_g19_source_only"]=G19_PASS
            else:
                reject,_=unique(folder,"s3-b7-g19-rejected-24h.json")
                need(reject.get("status")==G19_NEG
                     and reject.get("source_only_parsed") is False
                     and reject.get("g19_24h_science")=="NOT_ACCEPTED"
                     and reject.get("real_original_parser_error")==
                         "P6G model hour lacks bracketing upper sounding"
                     and all(reject.get(k)==report[k] for k in common),
                     "real 24h native G19 scientific rejection not reproduced exactly")
                report["actual_g19_source_only"]=G19_NEG
        cases[period]=report

    all_cases=[cases[k] for k in PERIODS]
    need(len({x["research_time_sha256"] for x in all_cases})==3,
         "distinct 48h/24h/6h original real time configurations must have distinct raw SHA")
    need(len({x["case_yaml_sha256"] for x in all_cases})==3,
         "distinct actual B0 case YAML bytes required")
    need(len({x["grid_cmn_sha256"] for x in all_cases})==1 and
         len({x["native_geo_sha256"] for x in all_cases})==1,
         "P1/P2/P3 geometry changed while assessing alternative time intervals")
    need(cases["jun_6h"]["actual_g19_source_only"]==G19_PASS and
         cases["jun_24h"]["actual_g19_source_only"]==G19_NEG,
         "one genuine positive + one genuine negative G19 is required")
    if output.exists() or output.is_symlink():
        raise ValueError("never overwrite a previous S3-B7 independent verdict")
    verdict={
        "schema":"cteas.s3.b7.independent_real_scoped_exit.v1",
        "status":"S3_P1_P5_NEW_SITE_STACK_PASS_SCOPED_6H",
        "real_new_site":"HUOSHAN_WGS84_UTM50N_100x100_100m",
        "actual_matrix_cases":cases,
        "one_real_site_selected_physics":"PASS_SCOPED_6H",
        "second_different_time_configuration":"PASS_SOURCE_ONLY_24H_G19_REJECTED",
        "full_24h_g19_science":"NOT_ACCEPTED",
        "arbitrary_site_station_year_scope":"NOT_ACCEPTED",
        "original_other_option_paths":"NOT_ACCEPTED",
        "p6_hourly_45_field_wind":"NOT_RUN",
        "p7_transport":"NOT_RUN",
        "wet_deposition":"NOT_RUN",
        "s5_capacity":"DEFERRED",
        "docker":"DEFERRED",
        "exact_pr_head_sha":expected_sha or "UNBOUND_NOT_CI",
    }
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(verdict,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    return verdict

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--artifacts",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--expected-head-sha",default=None)
    args=p.parse_args()
    try:
        x=accept(args.artifacts,args.output,expected_sha=args.expected_head_sha)
    except (ValueError,KeyError,TypeError,OSError,UnicodeError,json.JSONDecodeError) as ex:
        print("S3_B7_INDEPENDENT_REAL_EXIT_REJECTED "+str(ex)[:1500],file=sys.stderr)
        return 2
    print(json.dumps({"status":x["status"],
                      "real_matrix_cases":list(x["actual_matrix_cases"]),
                      "jun_24h":x["full_24h_g19_science"],
                      "P6":x["p6_hourly_45_field_wind"]},sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
