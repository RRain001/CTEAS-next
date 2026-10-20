#!/usr/bin/env python3
"""S3-B6: render existing original-format CALMET input and parse actual P1–P5 via G19.

This program is source-only: not P6D/E/F numeric wind and never P7. It
requires real same-case source-preflight evidence, reuses the *existing*
CALMET input renderer rather than introducing a parallel deck/physics kernel,
and calls the existing native G19 file-backed parser with exact on-disk SHA.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys

import yaml

from engine.run_met.prepare_met import render_met_inp
from engine.run_met.station_grid import load_strict_utm_grid
from native_cpp.orchestration.case_admission import admit_case, verify_immutable
from native_cpp.orchestration.p6_g19_handoff import prepare_g19, execute_source_preflight
from native_cpp.orchestration.plan import ContractError


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as inp:
        for block in iter(lambda: inp.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def run(case_yaml: Path, native_binary: Path) -> dict:
    admission = admit_case(case_yaml)
    root = admission.case_path.parent
    if (admission.research_begin, admission.research_end) != (
        "20220601-000000", "20220602-000000"
    ):
        raise ValueError("S3-B6 requires exact original-science June Huoshan 2022 case")
    join = root / "evidence/s3-b0-five-source-preflight.json"
    if join.is_symlink() or not join.is_file():
        raise ValueError("S3-B6 original five-source SHA admission not run")
    receipt = json.loads(join.read_text())
    if receipt.get("status") != "S3_B0_SAME_CASE_FIVE_PRODUCERS_SOURCE_LINEAGE_PASS_NOT_G19":
        raise ValueError("S3-B6 cannot elevate unaccepted five-source preflight")
    for key, expected in (
        ("case_yaml_sha256", admission.case_sha256),
        ("grid_cmn_sha256", admission.grid_sha256),
        ("research_time_sha256", admission.time_sha256),
    ):
        if receipt.get(key) != expected:
            raise ValueError("S3-B6 previous five-producer same B0 SHA changed: " + key)
    if not native_binary.is_absolute() or native_binary.is_symlink() or not native_binary.is_file():
        raise ValueError("S3-B6 explicit native G19 source-only executable absent")
    output = root / "evidence/s3-b6-g19-source-only.json"
    deck = root / "run/met/met.inp"
    if output.exists() or deck.exists() or output.is_symlink() or deck.is_symlink():
        raise ValueError("S3-B6 refuses old/previously staged MET inputs")
    config = yaml.safe_load(case_yaml.read_text(encoding="utf-8"))
    paths = {
        "geo_makegeo_dir": root / "geo/makegeo/p3_case",
        "met_surface_dir": root / "met/surface",
        "met_upperair_dir": root / "met/upperair",
        "run_met_dir": root / "run/met",
    }
    paths["run_met_dir"].mkdir(parents=True, exist_ok=False)
    fmt = "%Y%m%d-%H%M%S"
    content, source = render_met_inp(
        admission.case_name, config, paths["run_met_dir"],
        source_paths=paths,
        source_grid=load_strict_utm_grid(admission.grid_path, context="S3-B6"),
        source_times=(datetime.strptime(admission.research_begin, fmt),
                      datetime.strptime(admission.research_end, fmt)),
    )
    if source["nssta"] <= 0 or source["nusta"] <= 0:
        raise ValueError("S3-B6 true source roles missing observed stations")
    deck.write_text(content, encoding="utf-8")
    p4_root, p5_root = root / "met/upperair", root / "met/surface/isd_raw"
    plan = prepare_g19(case_yaml, p4_root, p5_root, root, native_binary)
    result = execute_source_preflight(plan)
    if not result.get("native_input_parsed") or result.get("model_executed"):
        raise ValueError("S3-B6 G19 native did not pass source-only semantics")
    if result["status"] != "P6_G19_DYNAMIC_FILE_INPUT_PARSED_NO_PHYSICS_EXECUTED":
        raise ValueError("S3-B6 unexpected native source parser conclusion")
    verify_immutable(admission)
    receipt2 = json.loads(join.read_text())
    if receipt2 != receipt:
        raise ValueError("S3-B6 source admission receipt changed during G19")
    # The S3 claim is stronger than a bare source parser sentinel: genuine
    # independent B0, P1-P5 source receipt, parser identities/order and hashes.
    evidence = {
        "status": "S3_B6_HUOSHAN_GENUINE_FIVE_SOURCE_NATIVE_G19_PARSED_SCOPED",
        "case_name": admission.case_name,
        "case_yaml_sha256": admission.case_sha256,
        "grid_cmn_sha256": admission.grid_sha256,
        "research_time_sha256": admission.time_sha256,
        "five_producer_receipt_sha256": digest(join),
        "met_deck_sha256": digest(deck),
        "g19_native_executable_sha256": digest(native_binary),
        "p4_source_stations": result["ordered_upper_station_ids"],
        "p5_source_stations": result["ordered_surface_station_ids"],
        "p4_effective_wmo": result["ordered_upper_wmo_ids"],
        "p5_effective_ifstn": result["ordered_surface_ifstn_ids"],
        "actual_native_source_roles_sha256": result["roles"],
        "actual_source_parser_status": result["status"],
        "actual_source_parser_stdout_tail": result["native_g19_stdout"][-2000:],
        "source_only_parsed": True,
        "p6d_e_f_numerical_wind": "NOT_RUN",
        "p7_numerical_diffusion": "NOT_RUN",
        "independent_second_s3_configuration": "NOT_RUN",
        "complete_S3_final_science": "NOT_ACCEPTED",
        "docker": "DEFERRED",
    }
    output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-yaml", type=Path, required=True)
    parser.add_argument("--native-g19", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = run(args.case_yaml, args.native_g19)
    except (ValueError, OSError, KeyError, TypeError, ContractError, RuntimeError, yaml.YAMLError) as exc:
        print(json.dumps({"status": "S3_B6_REAL_G19_BLOCKED",
                          "reason": str(exc)[:1800]}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps({"status": report["status"],
                      "p4": report["p4_source_stations"],
                      "p5": report["p5_source_stations"],
                      "s3_final": report["complete_S3_final_science"]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
