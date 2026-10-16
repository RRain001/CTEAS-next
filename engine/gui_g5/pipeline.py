"""CTEAS G5-only execution authority.

Every stage must resolve to an explicitly supported reconstructed implementation.
Never delegate to engine.orchestrator.cli or engine.run_met.run_met/run_puff.run_puff.
P6 generalization and P7 full scientific acceptance are intentionally blocked.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from engine.core.paths import case_dir, case_yaml_path, current_case_name

STAGES = {
    "preprocess": "P1/P2/P3 reconstructed terrain, land use and GEO",
    "upperair": "P4 reconstructed IGRA/READ62/UP.DAT",
    "surface": "P5 reconstructed NOAA/SMERGE/SURF.DAT",
    "met": "P6 reconstructed CALMET",
    "puff": "P7 reconstructed CALPUFF",
    "all": "P1–P7 complete native pipeline",
}
BLOCKED = {
    "preprocess": "P1–P3 lack an accepted arbitrary-case native input/output coordinator; original pipeline is prohibited",
    "upperair": "P4 yearly native data preparation exists, but generic multistation UP.DAT publication is not integrated and accepted",
    "met": "P6 numeric acceptance is frozen Hefei 143h only; generic dimensions/stations/time not accepted",
    "puff": "P7 end-to-end native multi-hour physical acceptance is incomplete",
    "all": "P1–P7 native full-case orchestration is not accepted; refusing partial legacy fallback",
}


def _positive(value: Any, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"{name} must be finite and positive")
    return number


def _coords(data: dict[str, Any]) -> tuple[float, float]:
    source = (data.get("preprocess") or {}).get("stack") or {}
    if "latitude" not in source or "longitude" not in source:
        raise ValueError("G5 requires preprocess.stack.latitude/longitude; do not substitute grid center")
    lat = float(source["latitude"])
    lon = float(source["longitude"])
    if not (math.isfinite(lat) and math.isfinite(lon) and -80 <= lat <= 84 and -180 <= lon <= 180):
        raise ValueError("G5 stack longitude/latitude are outside WGS-84 UTM bounds")
    return lat, lon


def validate_case(data: dict[str, Any]) -> None:
    pre = data.get("preprocess") or {}
    grid = pre.get("grid") or {}
    center = grid.get("center") or {}
    domain = grid.get("domain") or {}
    lat = float(center.get("latitude", float("nan")))
    lon = float(center.get("longitude", float("nan")))
    if not (math.isfinite(lat) and math.isfinite(lon) and -80 <= lat <= 84 and -180 <= lon <= 180):
        raise ValueError("G5 center location outside supported WGS-84 UTM coordinates")
    _coords(data)
    _positive(domain.get("length_km"), "preprocess.grid.domain.length_km")
    _positive(domain.get("width_km"), "preprocess.grid.domain.width_km")
    spacing = _positive(grid.get("resolution_km"), "preprocess.grid.resolution_km")
    _positive(grid.get("nz"), "preprocess.grid.nz")
    if math.ceil(float(domain["length_km"]) / spacing) <= 0:
        raise ValueError("G5 grid NX is invalid")
    times = pre.get("research_time") or {}
    begin = datetime.strptime(str(times.get("begin", "")), "%Y%m%d-%H%M%S")
    end = datetime.strptime(str(times.get("end", "")), "%Y%m%d-%H%M%S")
    if begin >= end:
        raise ValueError("G5 research_time must have at least one interval")


def _native_p5_bin() -> Path:
    configured = os.environ.get("CTEAS_G5_P5_BIN", "").strip()
    if not configured:
        raise ValueError("G5 P5 requires explicit CTEAS_G5_P5_BIN (native cteas_p5_smerge binary)")
    result = Path(configured).expanduser().resolve()
    if not result.is_file() or not os.access(result, os.X_OK):
        raise ValueError(f"G5 native P5 executable missing or not executable: {result}")
    return result


def stage_readiness(stage: str, data: dict[str, Any], case_name: str, resume: bool = False) -> tuple[bool, str]:
    try:
        if stage not in STAGES:
            raise ValueError(f"Unknown G5 stage: {stage}")
        if resume:
            raise ValueError("G5 native restart/--resume is not accepted for this stage")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", case_name):
            raise ValueError("Invalid G5 case name")
        if current_case_name() != case_name:
            raise ValueError("G5 selected case differs from project/current; explicit case sync required")
        root = case_dir(case_name)
        if not (root / "case.yaml").is_file():
            raise ValueError("G5 case.yaml is missing")
        validate_case(data)
        if stage in BLOCKED:
            raise ValueError(f"{stage}: {BLOCKED[stage]}")
        if stage == "surface":
            _native_p5_bin()
            from engine.run_met.station_grid import load_strict_utm_grid
            load_strict_utm_grid(root / "grid" / "grid.cmn", context="G5_P5")
        return True, "G5 native stage ready"
    except (ValueError, OSError, TypeError) as exc:
        return False, str(exc)


def native_command(stage: str, data: dict[str, Any]) -> list[str]:
    if stage != "surface":
        raise ValueError(f"No accepted generic native executor for G5 {stage}")
    lat, lon = _coords(data)
    cmd = [
        sys.executable, "-m",
        "native_cpp.modules.p5_smerge.data_prep.prepare_inputs",
        "--native-cpp-bin", str(_native_p5_bin()),
        "--stack-lat", str(lat), "--stack-lon", str(lon),
        "--execute",
    ]
    if ((data.get("preprocess") or {}).get("surface") or {}).get("skip_download", False):
        cmd.append("--skip-download")
    return cmd


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="CTEAS G5 explicit native-only stage dispatcher")
    ap.add_argument("action", choices=("run", "plan"))
    ap.add_argument("--case", required=True)
    ap.add_argument("--stage", choices=sorted(STAGES), required=True)
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args(argv)

    try:
        path = case_yaml_path(args.case)
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        ready, reason = stage_readiness(args.stage, data, args.case, resume=args.resume)
        payload: dict[str, Any] = {
            "backend": "G5_NATIVE_ONLY",
            "case": args.case, "stage": args.stage,
            "component": STAGES[args.stage],
            "ready": ready, "reason": reason,
            "legacy_fallback": False,
        }
        if ready:
            payload["command"] = native_command(args.stage, data)
        print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)
        if args.action == "plan":
            return 0
        if not ready:
            return 2
        subprocess.run(payload["command"], check=True)
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError, yaml.YAMLError) as exc:
        print(f"G5 FAIL_CLOSED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
