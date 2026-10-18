"""#56 D1-B: fail-closed, offline *preselected NOAA* P5 native SURF producer.

This does not choose annual stations anew. It independently re-counts original
NOAA hours for the staged selection, then executes the already-approved science
stages as package subprocesses in an isolated admitted case. D2 must still
replay dynamic source selection on genuinely new sites; D3 original parity and
D4 full #42 G19 handoff are separate acceptance gates.

Usage:
  python -m native_cpp.modules.p5_smerge.data_prep.p5_case_producer \\
    --case-yaml /outside/repo/newsite/case.yaml \\
    --history-file /archives/isd-history.txt \\
    --native-cpp-bin /build/cteas_p5_smerge
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from native_cpp.orchestration.case_admission import admit_case, verify_immutable
from native_cpp.orchestration.plan import ContractError
from .case_archive_gate import admit_p5_archive
from .download_isd_by_grid import original_coverage
from .isd_lite_wind import lite_time_coverage
from .p5_case_paths import ROOT_ENV, HISTORY_ENV
from .run_smerge_and_monitor import parse_station_records

REPO = Path(__file__).resolve().parents[4]
MODULE = "native_cpp.modules.p5_smerge.data_prep"
PREP_STAGES = (
    "isd_to_smerge_and_fill", "clean_merge_filled_by_research_time",
    "convert_cleaned_to_smerge_ready", "generate_smerge_input_sections",
)
CONTROLS = {
    "JDAT": "8", "IOFORM": "2", "IOPACK": "0",
    "LPREV": "F", "LPCALC": "F", "ABTZ": "UTC+0000",
}
UTC_FIELDS = ("IBYR", "IBMO", "IBDY", "IBHR", "IBSEC",
              "IEYR", "IEMO", "IEDY", "IEHR", "IESEC")


def digest(path: Path) -> str:
    if path.is_symlink() or not path.is_file() or path.stat().st_size <= 0:
        raise ContractError(f"P5 missing or unsafe source/output file: {path}")
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_fresh_outputs(root: Path) -> None:
    # Input archive is the only allowed pre-existing stage. No accidental reuse
    # of stale GENERIC, copied SURF, or outputs belonging to another case.
    for rel in (
        "met/surface/isd2smerge_and_fill",
        "met/surface/isd2smerge_cleaned",
        "met/surface/isd2smerge_ready",
        "met/surface/final",
        "run/smerge",
        "evidence/p5.json",
    ):
        target = root / rel
        if target.exists() or target.is_symlink():
            raise ContractError("P5 D1-B requires entirely fresh output: " + rel)


def check_hour_ending_control(path: Path, begin: datetime, end: datetime,
                              expected_aliases: set[str]) -> list[str]:
    content = path.read_text(encoding="utf-8")
    def value(key: str) -> str:
        # Exactly one active group assignment; duplicates are unacceptable.
        matches = re.findall(r"!\s*" + re.escape(key) + r"\s*=\s*([^!]+?)\s*!", content, re.I)
        if len(matches) != 1:
            raise ContractError(f"P5 ambiguous or missing SMERGE control: {key}")
        return matches[0].strip().strip("'").upper()
    for k, required in CONTROLS.items():
        if value(k) != required:
            raise ContractError(f"P5 unsupported SMERGE option: {k}")
    stamp = lambda x, keys: tuple(int(value(k)) for k in keys)
    first = stamp(begin, UTC_FIELDS[:5])
    last = stamp(end, UTC_FIELDS[5:])
    if first != (begin.year, begin.month, begin.day, begin.hour, begin.second):
        raise ContractError("P5 SMERGE begin clock differs from requested UTC label")
    if last != (end.year, end.month, end.day, end.hour, end.second):
        raise ContractError("P5 SMERGE end clock differs from requested UTC label")
    station_records = parse_station_records(content)
    actual = [r.get("ifstn") for r in station_records]
    if (not actual or len(actual) != len(set(actual)) or
            set(actual) != expected_aliases or int(value("NFF")) != len(actual)):
        raise ContractError("P5 SMERGE station count/order identities inconsistent with selector")
    # Existing SMERGE semantics produce hour-ending records for (BEGIN,END].
    # Do not invent a BEGIN record; #42/G19 must interpret this mapping.
    return actual


def count_raw_source_hours(evidence: dict) -> dict:
    checked = {}
    for annual in evidence["years"]:
        year = annual["year"]
        for station in annual["stations"]:
            sid = station["sid"]
            full = Path(station["full_isd"]["path"])
            lite = Path(station["isd_lite"]["path"])
            found, denominator = original_coverage(full, year, sid)
            wind_found, wind_denominator = lite_time_coverage(lite, year, sid)
            if (found != station["full_isd_raw_hours_reported"] or
                    wind_found != station["isd_lite_raw_hours_reported"] or
                    denominator != station["expected_hours"] or
                    wind_denominator != denominator):
                raise ContractError(
                    f"P5 reported NOAA source coverage differs from actual raw UTC hours: {sid}/{year}"
                )
            checked[f"{sid}/{year}"] = {
                "original_isd_hours": found, "original_isd_lite_hours": wind_found,
                "calendar_hours": denominator,
                "raw_source_recount": "PASS",
            }
    return checked


def preflight(case_yaml: Path, history: Path, native: Path, template: Path) -> tuple:
    admission = admit_case(case_yaml)
    root = admission.case_path.parent
    proof = admit_p5_archive(case_yaml, root / "met/surface/isd_raw", history)
    if admission.research_begin == admission.research_end:
        raise ContractError("P5 selected SURF hour-ending window must span at least one hour")
    for label, path in (("native binary", native), ("control template", template)):
        if not path.is_absolute() or path.is_symlink() or not path.is_file():
            raise ContractError(f"P5 explicit {label} must be regular absolute file")
    validate_fresh_outputs(root)
    proof["independent_raw_hour_coverage"] = count_raw_source_hours(proof)
    verify_immutable(admission)
    return admission, proof


def _hash_outputs(root: Path, paths: list[Path]) -> dict[str, str]:
    return {str(p.relative_to(root)): digest(p) for p in paths}


def produce(case_yaml: Path, history: Path, native: Path, template: Path,
            *, admit_only: bool = False) -> dict:
    admission, evidence = preflight(case_yaml, history, native, template)
    root = admission.case_path.parent
    if admit_only:
        evidence["P5_SOURCE_SELECTION"] = "PRESELECTED_MANIFEST_RAW_HOURS_RECOUNTED"
        evidence["P5_GENERIC_CASE_EXECUTION"] = "NOT_RUN"
        evidence["scope"] = "D1B_OFFLINE_PREFLIGHT_ONLY"
        return evidence

    run = root / "run/smerge"
    run.mkdir(parents=True, exist_ok=False)
    control = run / "smerge.inp"
    shutil.copyfile(template, control)
    control_template_sha = digest(template)
    env = os.environ.copy()
    env[ROOT_ENV] = str(root.absolute())
    env[HISTORY_ENV] = str(history.absolute())
    env["PYTHONPATH"] = str(REPO) + os.pathsep + env.get("PYTHONPATH", "")
    steps = []
    for stage in PREP_STAGES:
        cmd = [sys.executable, "-m", f"{MODULE}.{stage}"]
        completed = subprocess.run(cmd, cwd=REPO, env=env,
                                   text=True, capture_output=True, timeout=7200, check=False)
        steps.append({"stage": stage, "exit_code": completed.returncode,
                      "stdout_tail": completed.stdout[-1600:],
                      "stderr_tail": completed.stderr[-1600:]})
        if completed.returncode:
            raise ContractError(f"P5 production stage {stage} exited {completed.returncode}: "
                                f"{completed.stderr[-1000:]} {completed.stdout[-1000:]}")
    begin = datetime.strptime(admission.research_begin, "%Y%m%d-%H%M%S")
    end = datetime.strptime(admission.research_end, "%Y%m%d-%H%M%S")
    aliases = set(evidence["global_ifstn"].values())
    order = check_hour_ending_control(control, begin, end, aliases)
    command = [sys.executable, "-m", f"{MODULE}.run_smerge_and_monitor",
               "--native-cpp-bin", str(native)]
    completed = subprocess.run(command, cwd=REPO, env=env,
                               text=True, capture_output=True, timeout=7200, check=False)
    steps.append({"stage": "native_cpp_smerge_and_publish",
                  "exit_code": completed.returncode,
                  "stdout_tail": completed.stdout[-1600:],
                  "stderr_tail": completed.stderr[-1600:]})
    if completed.returncode:
        raise ContractError(f"P5 native SMERGE writer or publication failed: "
                            f"{completed.stderr[-1000:]} {completed.stdout[-1000:]}")
    surf = run / "surf.dat"
    final = root / "met/surface/final/surf.dat"
    stations = root / "met/surface/final/stations.csv"
    ready = sorted((root / "met/surface/isd2smerge_ready").glob("*.csv"))
    if not ready or not surf.is_file() or not final.is_file() or not stations.is_file():
        raise ContractError("P5 native producer omitted mandatory SURF or station metadata")
    verify_immutable(admission)
    # Verify every original source remains identical to the admitted SHA.
    for annual in evidence["years"]:
        for station in annual["stations"]:
            for key in ("full_isd", "isd_lite"):
                if digest(Path(station[key]["path"])) != station[key]["sha256"]:
                    raise ContractError("P5 NOAA input changed during production")
    evidence.update({
        "status": "PRODUCED_UNVERIFIED",
        "scope": "D1B_PRESELECTED_NOAA_OFFLINE_NATIVE_SURF_ONLY",
        "P5_SOURCE_SELECTION": "PRESELECTED_MANIFEST_RAW_HOURS_RECOUNTED",
        "P5_NATIVE_SURF": "PRODUCED_UNVERIFIED",
        "P5_GENERIC_CASE_EXECUTION": "D1B_PRESELECTED_ONLY",
        "P5_ORIGINAL_PARITY": "NOT_RUN_NEW_GENERIC",
        "P5_TO_G19": "NOT_RUN",
        "science_acceptance": False,
        "producer_steps": steps,
        "sm_input_control_template_sha256": control_template_sha,
        "native_executable_sha256": digest(native),
        "SURF_hour_ending_window": "(BEGIN,END]",
        "SURF_hour_ending_expected_records": int((end - begin) / timedelta(hours=1)),
        "ordered_ifstn": order,
        "raw_native_surf_sha256": digest(surf),
        "published_surf_sha256": digest(final),
        "produced_output_sha256": _hash_outputs(root, [control, surf, final, stations, *ready]),
    })
    dest = root / "evidence/p5.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_symlink() or dest.exists():
        raise ContractError("P5 D1-B cannot replace prior evidence")
    dest.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return evidence


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="P5 isolated offline preselected real NOAA SURF.DAT writer")
    ap.add_argument("--case-yaml", type=Path, required=True)
    ap.add_argument("--history-file", type=Path, required=True)
    ap.add_argument("--native-cpp-bin", type=Path, required=True)
    ap.add_argument("--smerge-template", type=Path, default=REPO / "engine/templates/smerge.inp")
    ap.add_argument("--admit-only", action="store_true",
                    help="Verify raw original hours and source control without creating any files")
    args = ap.parse_args(argv)
    try:
        result = produce(args.case_yaml, args.history_file, args.native_cpp_bin,
                         args.smerge_template, admit_only=args.admit_only)
    except (ContractError, OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"P5_D1B_PRESELECTED=BLOCKED reason={exc}", file=sys.stderr)
        return 2
    print("P5_D1B_PRESELECTED=" + result["status"])
    print("P5_ORIGINAL_PARITY=NOT_RUN_NEW_GENERIC P5_TO_G19=NOT_RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
