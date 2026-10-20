"""#42 S3-0 five module source-lineage preflight: NO G19 or physics.

This only checks byte SHA and one authoritative B0 case for existing P2/P3
(native P1 embedded), P4 genuine IGRA and P5 genuine ISD producer outputs.
Never silently reuses prior frozen site data, nor upgrades original-science
or G19 statuses. Missing/changed producer files fail closed.
"""
from __future__ import annotations
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re

from .case_admission import admit_case, verify_immutable
from .plan import ContractError

HEX = re.compile(r"[a-f0-9]{64}\Z")
P2_KINDS = {"A":"P2A_GENERIC_CASE_PRODUCED_UNVERIFIED",
            "C":"P2C_GENERIC_CASE_PRODUCED_UNVERIFIED"}
STATUS = "S3_B0_SAME_CASE_FIVE_PRODUCERS_SOURCE_LINEAGE_PASS_NOT_G19"

def need(ok,why):
    if not ok:
        raise ContractError("S3_B0_FIVE_SOURCE_REJECTED: "+why)

def _path(root:Path,relative:str)->Path:
    need(isinstance(relative,str) and
         not relative.startswith("/") and ".." not in Path(relative).parts,
         "unsafe source-relative path")
    p=root/relative
    need(p.is_file() and not p.is_symlink() and p.stat().st_size>0 and
         p.stat().st_size<=500_000_000,"missing/empty/oversized source: "+relative)
    here=p
    while here!=root:
        need(not here.is_symlink(),"symlink in module source path")
        here=here.parent
    return p

def digest(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1<<20),b""):
            h.update(chunk)
    return h.hexdigest()

def load(root:Path,relative:str)->tuple[dict,str]:
    p=_path(root,relative)
    raw=p.read_bytes()
    doc=json.loads(raw)
    need(isinstance(doc,dict),"producer manifest is not an object")
    return doc,hashlib.sha256(raw).hexdigest()

def validate(admission,p2,p3,p4,p5,files:dict)->dict:
    """Pure producer-proof join; actual filesystem SHA checked by collect."""
    root=admission.case_path.parent
    sha=(admission.case_sha256,admission.grid_sha256,admission.time_sha256)
    for label,proof in (("P2",p2),("P3",p3)):
        need(proof.get("case_name")==admission.case_name and
             (proof.get("case_yaml_sha256"),
              proof.get("grid_cmn_sha256"),
              proof.get("research_time_sha256"))==sha,
             label+" wrong B0 case SHA")
        need(proof.get("utm_epsg")==admission.utm_zone+
             (32600 if admission.hemisphere=="N" else 32700) and
             (proof.get("nx"),proof.get("ny"))==(admission.nx,admission.ny),
             label+" wrong grid/UTM")
    kind=p3.get("p2_kind")
    need(kind in P2_KINDS and p2.get("status")==P2_KINDS[kind] and
         p3.get("status")=="P3_NATIVE_SAME_CASE_PRODUCED_UNVERIFIED" and
         p3.get("p2_method")==p2.get("method"),
         "P2/P3 selected paths differ or forbidden retired P2-B")
    need(p3.get("p2_attestation_sha256")==files["p2_attestation_sha256"] and
         p3.get("p2_lu_dat_sha256")==files["p2_lu_dat_sha256"],
         "P3 consumed another P2 artifact")
    for name in ("p1_tif_sha256","p1_csv_sha256",
                 "terrel_dat_sha256","geo_dat_sha256"):
        need(isinstance(p3.get(name),str) and HEX.fullmatch(p3[name]) is not None,
             "P3 lacks true native P1/P3 SHA "+name)
    need(p3.get("p1_csv_sha256")==files["p1_csv_sha256"] and
         p3.get("terrel_dat_sha256")==files["terrel_dat_sha256"] and
         p3.get("geo_dat_sha256")==files["geo_dat_sha256"],
         "P3 current new-case TERREL/GEO byte drift")
    a=p4.get("admission",{})
    need(p4.get("status")=="PRODUCED_UNVERIFIED" and
         isinstance(a,dict) and
         a.get("case_root")==str(root.resolve()) and
         a.get("upperair_root")==str((root/"met/upperair").resolve()) and
         tuple(a.get(k) for k in ("case.yaml","grid/grid.cmn",
                                  "grid/research_time"))==sha,
         "P4 not bound to same B0 and independent scratch")
    need(p4.get("pstop_hpa")==500.0 and p4.get("jdat")==2 and
         p4.get("ifmt")==1 and isinstance(p4.get("candidate_final"),dict),
         "P4 only selected READ62 with produced final candidate")
    cand=p4["candidate_final"]
    need(cand.get("status")=="PRODUCED_UNVERIFIED" and
         cand.get("station_count",0)>0 and
         cand.get("station_count")==len(cand.get("files",[])),
         "P4 station count/final status invalid")
    need(len(files["upperair"])==cand["station_count"] and
         all(item.get("wmo") in files["upperair"] and
             item.get("sha256")==files["upperair"][item["wmo"]]
             for item in cand["files"]) and
         cand.get("stations_csv_sha256")==files["upperair_stations_sha256"],
         "P4 native UP bytes/station index do not match producer")
    need(p5.get("status")=="PRODUCED_UNVERIFIED" and
         p5.get("case_name")==admission.case_name and
         (p5.get("case_sha256"),p5.get("grid_sha256"),
          p5.get("research_time_sha256"))==sha,
         "P5 not bound to same B0 source")
    need(p5.get("published_surf_sha256")==files["surf_sha256"] and
         p5.get("produced_output_sha256",{}).get(
             "met/surface/final/stations.csv")==files["surface_stations_sha256"],
         "P5 actual SURF or station index changed")
    begin=datetime.strptime(admission.research_begin,"%Y%m%d-%H%M%S")
    end=datetime.strptime(admission.research_end,"%Y%m%d-%H%M%S")
    total=(end-begin).total_seconds()
    need(total>0 and total%3600==0 and
         p5.get("SURF_hour_ending_expected_records")==int(total/3600),
         "P5 hourly window disagrees with B0")
    need(p4.get("writer_utc",{}).get("begin") <= begin.strftime("%Y-%m-%dT%H:%M:%SZ") and
         p4.get("writer_utc",{}).get("end") >= end.strftime("%Y-%m-%dT%H:%M:%SZ"),
         "P4 observed 00/12 brackets do not cover requested window")
    need(len(p5.get("ordered_ifstn",[]))>0 and
         len(p5["ordered_ifstn"])==len(set(p5["ordered_ifstn"])),
         "P5 station identities missing or duplicated")
    return {"schema":"cteas.s3.b0.five_source_join.v1",
            "status":STATUS,"case_name":admission.case_name,
            "case_yaml_sha256":sha[0],"grid_cmn_sha256":sha[1],
            "research_time_sha256":sha[2],
            "geometry":{"utm_epsg":p3["utm_epsg"],"nx":admission.nx,
                        "ny":admission.ny,"dgridkm":admission.dgridkm},
            "native_paths":["P1","P2-"+kind,"P3","P4","P5"],
            "actual_source_sha256":files,
            "p3_original_newsite_science":"NOT_ASSERTED",
            "p4_p5_original_newsite_science":"NOT_ASSERTED",
            "s3_g19_native_reader":"NOT_RUN",
            "s3_five_product_scientific_acceptance":"NOT_ACCEPTED",
            "p6_p7_physics":"NOT_RUN","docker":"DEFERRED"}

def collect(case_yaml:Path,destination:Path)->dict:
    case=admit_case(case_yaml)
    root=case.case_path.parent
    need(destination==root/"evidence/s3-b0-five-source-preflight.json" and
         not destination.exists() and not destination.is_symlink(),
         "S3-0 output must be a fresh admitted evidence path")
    p2,p2hash=load(root,"evidence/p2.json")
    p3,p3hash=load(root,"evidence/p3.json")
    p4,p4hash=load(root,"met/upperair/p4_d1a_annual_manifest.json")
    p5,p5hash=load(root,"evidence/p5.json")
    kind=p3.get("p2_kind")
    need(kind in P2_KINDS,"S3 only supports retained P2 A/C")
    lu="geo/ctgproc/p2a_case/lu/lu.dat" if kind=="A" else "geo/ctgproc/p2c_case/lu.dat"
    files={
        "p2_attestation_sha256":p2hash,"p3_attestation_sha256":p3hash,
        "p4_attestation_sha256":p4hash,"p5_attestation_sha256":p5hash,
        "p2_lu_dat_sha256":digest(_path(root,lu)),
        "p1_csv_sha256":digest(_path(root,"geo/makegeo/p3_case/terrain.csv")),
        "terrel_dat_sha256":digest(_path(root,"geo/makegeo/p3_case/terrel.dat")),
        "geo_dat_sha256":digest(_path(root,"geo/makegeo/p3_case/geo.dat")),
        "surf_sha256":digest(_path(root,"met/surface/final/surf.dat")),
        "surface_stations_sha256":digest(_path(root,"met/surface/final/stations.csv")),
        "upperair_stations_sha256":digest(_path(root,"met/upperair/final/stations.csv")),
        "upperair":{}
    }
    for item in p4.get("candidate_final",{}).get("files",[]):
        wmo=item.get("wmo")
        need(isinstance(wmo,str) and re.fullmatch(r"\d{5}",wmo) and
             wmo not in files["upperair"],"P4 invalid/duplicate WMO")
        files["upperair"][wmo]=digest(_path(root,"met/upperair/final/up_"+wmo+".dat"))
    report=validate(case,p2,p3,p4,p5,files)
    verify_immutable(case)
    need(destination.parent.is_dir() and not destination.parent.is_symlink(),
         "S3 evidence directory missing or symlink")
    with destination.open("x",encoding="utf-8") as writer:
        json.dump(report,writer,sort_keys=True,indent=2)
        writer.write("\n")
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--case-yaml",type=Path,required=True)
    p.add_argument("--destination",type=Path,required=True)
    a=p.parse_args()
    try:
        v=collect(a.case_yaml,a.destination)
        print(json.dumps({"status":v["status"],"case_name":v["case_name"],
                          "s3_g19_native_reader":v["s3_g19_native_reader"]}))
        return 0
    except (OSError,KeyError,ValueError,TypeError,ContractError,json.JSONDecodeError) as ex:
        print(json.dumps({"status":"S3_B0_FIVE_SOURCE_REJECTED",
                          "error_type":type(ex).__name__}))
        return 2

if __name__=="__main__":
    raise SystemExit(main())
