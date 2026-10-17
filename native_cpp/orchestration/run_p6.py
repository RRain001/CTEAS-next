"""S2-2C locked-case native P6 process launcher (not a science gate).

This adapter consumes freshly staged P3/P4/P5 files, never the frozen original
CALMET MET.DAT, and can launch the EXISTING P6 C++ hourly process driver. It
does not relax that driver's 2022 limitations or authenticate self-declared
native producers. Real 1h/6h/143h numerical parity remains an independent gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from .handoff_gate import preflight
from .plan import CASE_ID, ContractError, plan_case

BINARIES = ("driver", "p6d", "p6e", "cgamma", "bridge", "p6e_source_builder")


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as reader:
        for block in iter(lambda: reader.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _within(candidate: Path, root: Path) -> bool:
    return candidate == root or root in candidate.parents


def prepare(
    case_yaml: Path, manifest: Path, work: Path,
    binaries: dict[str, Path], hours: int,
) -> dict[str, Any]:
    """Construct an immutable, explicit subprocess request without running it."""
    if type(hours) is not int or hours not in (1, 6, 143):
        raise ContractError("S2-2C currently permits only 1/6/143 hour checkpoints")
    scoped = plan_case(case_yaml)
    case_root = case_yaml.absolute().parent
    if case_root.name != CASE_ID:
        raise ContractError("not the Hefei frozen selected case")
    if case_root.is_symlink():
        raise ContractError("case staging directory symlink forbidden")
    # Explicitly exclude reference-only CALMET meteorology from the stage
    # even though the old P6 driver can read it in another, unaccepted mode.
    if (case_root / "run/met/met.dat").exists():
        raise ContractError("BLOCKED_ORIGINAL_MET_DEPENDENCY: original met.dat present in staging")
    files = preflight(case_root, manifest, "p6")
    if set(binaries) != (set(BINARIES) | ({"p6f_writer"} if hours == 143 else set())):
        raise ContractError("wrong P6 selected binary role set")
    exe: dict[str, str] = {}
    executable_evidence: dict[str, dict[str, Any]] = {}
    for name, supplied in sorted(binaries.items()):
        path = Path(supplied).absolute()
        if path.is_symlink() or not path.is_file() or not os.access(path, os.X_OK):
            raise ContractError("missing, non-executable or symlink P6 binary role: " + name)
        exe[name] = str(path)
        executable_evidence[name] = {
            "path": str(path), "sha256": _hash(path), "bytes": path.stat().st_size,
        }
    scratch = Path(work).absolute()
    if scratch.exists():
        raise ContractError("work must be a new, nonexistent path")
    if _within(scratch, case_root) or _within(case_root, scratch):
        raise ContractError("work and immutable case root overlap")
    if scratch.parent.is_symlink() or not scratch.parent.is_dir():
        raise ContractError("work parent must be an existing real directory")
    command = [
        exe["driver"], "--case", str(case_root),
        "--p6d", exe["p6d"], "--p6e", exe["p6e"],
        "--cgamma", exe["cgamma"], "--bridge", exe["bridge"],
        "--work", str(scratch), "--hours", str(hours),
        "--p6e-source-builder", exe["p6e_source_builder"],
    ]
    if hours == 143:
        command.extend([
            "--p6f-writer", exe["p6f_writer"], "--p6f-direct-hourly",
        ])
    return {
        "status": "P6_LAUNCH_PLAN_NOT_EXECUTED",
        "ready": False,
        "model_executed": False,
        "scientific_acceptance": "NOT_EVALUATED",
        "case_yaml_sha256": scoped["case_yaml_sha256"],
        "case_name": CASE_ID,
        "hours": hours,
        "command": command,
        "source_assertions_unverified": True,
        "files": files["verified_artifacts"],
        "executables": executable_evidence,
        "work": str(scratch),
        "legacy_fallback": False,
    }


def execute(request: dict[str, Any]) -> dict[str, Any]:
    """Run P6 C++ in a clean scratch; no automatic publishing or fallbacks."""
    if request.get("status") != "P6_LAUNCH_PLAN_NOT_EXECUTED":
        raise ContractError("unrecognized P6 launch request")
    work = Path(request["work"])
    if work.exists():
        raise ContractError("work appeared since validation")
    result = subprocess.run(request["command"], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise ContractError("P6 native hourly process failed, exit " + str(result.returncode) +
                            "; scratch retained for audit, no output published")
    report = work / "native_cpp_hourly_manifest.json"
    native = work / "native_causal_calmet.dat"
    if not report.is_file() or not native.is_file():
        raise ContractError("P6 process exited zero without native report/MET")
    try:
        observed = json.loads(report.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise ContractError("P6 produced malformed manifest") from exc
    if (observed.get("hours_completed") != request["hours"]
            or observed.get("native_wind") is not True
            or observed.get("native_previous_hour_comp_state") is not True
            or observed.get("original_met_role") != "NOT_REQUIRED_NOT_OPENED_BY_NATIVE_EXECUTION"
            or observed.get("p6e_reference_is_geo_deck_metadata_only") is not True):
        raise ContractError("P6 output manifest violates reference-independent selected contract")
    digest = _hash(native)
    if digest != observed.get("native_calmet_dat_sha256"):
        raise ContractError("P6 native MET output hash mismatches producer manifest")
    evidence: dict[str, Any] = {
        "status": "P6_EXECUTED_SCIENCE_NOT_ACCEPTED",
        "model_executed": True,
        "scientific_acceptance": "NOT_EVALUATED",
        "case_name": CASE_ID,
        "hours_completed": request["hours"],
        "native_met_sha256": digest,
        "native_met_bytes": native.stat().st_size,
        "source_assertions_unverified": True,
        "legacy_fallback": False,
    }
    if request["hours"] == 143:
        independent = work / "native_causal_independent_header_calmet.dat"
        if (not independent.is_file()
                or _hash(independent) != observed.get("independent_p6f_header_sha256")
                or observed.get("p6f_header_from_native_hour_manifest") is not True):
            raise ContractError("143h native independent P6F header missing/hash mismatch")
        evidence["independent_native_met_sha256"] = _hash(independent)
        evidence["independent_native_met_bytes"] = independent.stat().st_size
    # The report is scratch-only and explicitly not a scientific PASS.
    target = work / "s2c_execution_evidence.json"
    target.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return evidence


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="S2-2C frozen native P6 only, no G5 or legacy fallback")
    p.add_argument("--case-yaml", required=True, type=Path)
    p.add_argument("--manifest", required=True, type=Path)
    p.add_argument("--work", required=True, type=Path)
    p.add_argument("--hours", required=True, type=int, choices=(1, 6, 143))
    for name in (*BINARIES, "p6f_writer"):
        p.add_argument("--" + name.replace("_", "-"), type=Path, required=name != "p6f_writer")
    p.add_argument("--execute", action="store_true", help="opt in to actual native 1/6/143h P6 run")
    a = p.parse_args(argv)
    try:
        bins = {k: getattr(a, k) for k in (*BINARIES, "p6f_writer") if getattr(a, k) is not None}
        request = prepare(a.case_yaml, a.manifest, a.work, bins, a.hours)
        result = execute(request) if a.execute else request
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (ContractError, OSError, ValueError, UnicodeError) as exc:
        print(json.dumps({"status": "BLOCKED_NATIVE_P6",
                          "model_executed": False,
                          "scientific_acceptance": "NOT_EVALUATED",
                          "legacy_fallback": False, "error": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
