"""S2-G1A source-only P6 G19 handoff for variable UTM grids/stations.

Bridges G0 annual P4/P5 genuine-source *selection metadata* to the existing
C++ G19 file-backed CALMET reader (2-6 surface / 1-6 upper stations, nine layers). Independently verifies
the full original-format file roles and deck identities/geometry before
constructing a command. Optional --native-input-preflight executes ONLY G19
file ingestion, never P6D/P6E/P6F, P7 or the legacy Fortran runtime.

Neither syntactically valid manifests nor successful G19 parsing prove full
meteorological science or NOAA original-byte authenticity. Fail closed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from engine.run_met.common import lon_lat_to_utm_km
from .plan import ContractError
from .site_plan import plan_site

G19_REQUIRED_MIN = 2
G19_REQUIRED_MAX = 6
MAX_HASH_FILE_BYTES = 512 * 1024 * 1024
KEYS = ("NX", "NY", "NZ", "IUTMZN", "UTMHEM", "DGRIDKM", "XORIGKM", "YORIGKM",
        "NSSTA", "NUSTA")


def _safe_file(path: Path, root: Path) -> Path:
    """Only plain paths beneath an independent staging root, no symlinks."""
    if root.is_symlink() or not root.is_dir():
        raise ContractError("P6 G19 staging root missing or symlink")
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise ContractError("P6 G19 source role escapes case staging root") from exc
    if not relative.parts:
        raise ContractError("P6 G19 source role must be file")
    target = root
    for item in relative.parts:
        target = target / item
        if target.is_symlink():
            raise ContractError("P6 G19 source path contains symlink")
    if not path.is_file() or path.stat().st_size < 1:
        raise ContractError(f"P6 G19 source file missing or empty: {relative}")
    if path.stat().st_size > MAX_HASH_FILE_BYTES:
        raise ContractError(f"P6 G19 source file exceeds bounded hash size: {relative}")
    return path


def _digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def _control(deck: str, key: str) -> str:
    matches = re.findall(r"!\s*" + re.escape(key) + r"\s*=\s*([^!]+)!", deck, re.I)
    if len(matches) != 1:
        raise ContractError(f"met.inp missing or ambiguous {key}")
    return matches[0].strip().strip("'\"")


def _as_int(deck: str, key: str) -> int:
    val = _control(deck, key)
    if re.fullmatch(r"[+-]?\d+", val) is None:
        raise ContractError(f"met.inp {key} must be an integer")
    return int(val)


def _as_number(deck: str, key: str) -> float:
    try:
        val = float(_control(deck, key))
    except ValueError as exc:
        raise ContractError(f"met.inp {key} numeric field malformed") from exc
    if not math.isfinite(val):
        raise ContractError(f"met.inp {key} non-finite")
    return val


def _deck_site(deck: str, prefix: str, ordinal: int) -> tuple[int, float, float]:
    # Old CALMET-style SSn/USn records. Only read id, projected X/Y km;
    # full physical decoder remains the existing G19 native source loader.
    pattern = (r"!\s*" + prefix + str(ordinal)
               + r"\s*=\s*'[^'!]{1,20}'\s+(\d{1,7})\s+"
               + r"([+-]?\d+(?:\.\d+)?)\s+([+-]?\d+(?:\.\d+)?)\b[^!]*!")
    matches = re.findall(pattern, deck, re.I)
    if len(matches) != 1:
        raise ContractError(f"met.inp missing/ambiguous {prefix}{ordinal} station record")
    sid, x, y = matches[0]
    return int(sid), float(x), float(y)


def _station_wmo(sid: str) -> int:
    # Initial selected input-profile: genuine five-digit numeric IGRA/WMO
    # stations only. Arbitrary alphanumeric IGRA IDs require a separately
    # verified READ62/UP.DAT station-ID mapping, not guessing last digits.
    if not re.fullmatch(r"[A-Z]{3}000\d{5}", sid):
        raise ContractError(f"IGRA station ID has no accepted WMO mapping: {sid}")
    return int(sid[-5:])


def _compare_xy(deck_xy: tuple[float, float], lat: float, lon: float,
                zone: int, northern: bool, label: str) -> None:
    x, y = lon_lat_to_utm_km(lon, lat, zone, northern)
    # Deck station coordinates are serialized in km, commonly 3 decimals.
    # 2m tolerance permits the original one-meter UTM serialization
    # quantization; science-sensitive cell membership remains a G19 check.
    if abs(x - deck_xy[0]) > 0.002 or abs(y - deck_xy[1]) > 0.002:
        raise ContractError(f"{label}: source/effective station projected position mismatches met.inp")


def prepare_g19(
    case_yaml: Path, p4_root: Path, p5_root: Path,
    stage: Path, native_preflight_bin: Path | None = None,
) -> dict[str, Any]:
    """Verify selected-station IDs, projected met-deck geometry and raw file roles.

    No scientific model execution. The manifest validator itself cannot
    authenticate NOAA upstream data, so preserve explicit source caveat.
    """
    contract = plan_site(case_yaml, p4_root, p5_root)
    root = case_yaml.absolute().parent
    if root.is_symlink() or stage != root:
        raise ContractError("P6 G19 stage must be the independent real case root")
    accepted = contract["selector_manifest_evidence"]
    years = contract["research_time"]["calendar_years_with_source_selection"]
    for branch in ("p4", "p5"):
        sets = [tuple(v["station_ids"]) for v in accepted[branch]]
        if len(sets) != len(years) or len(set(sets)) != 1:
            raise ContractError(
                f"P6 G19 static met deck cannot silently change {branch} station identities across years")
    upper_ids = accepted["p4"][0]["station_ids"]
    surface_ids = accepted["p5"][0]["station_ids"]
    if not 1 <= len(upper_ids) <= G19_REQUIRED_MAX:
        raise ContractError("G19 only accepts 1-6 genuine upper-air stations")
    if not G19_REQUIRED_MIN <= len(surface_ids) <= G19_REQUIRED_MAX:
        raise ContractError("G19 only accepts 2-6 surface stations")
    p4raw = json.loads((p4_root / str(years[0]) / "p4_station_selection_audit.json").read_text())
    p5raw = json.loads((p5_root / f"station_selection_{years[0]}.json").read_text())
    p4rows = {v["id"]: v for v in p4raw["selected"]}
    p5rows = {v["sid"]: v for v in p5raw["stations"]}
    if set(p4rows) != set(upper_ids) or set(p5rows) != set(surface_ids):
        raise ContractError("P6 G19 metadata identities differ from G0 source selections")

    m = _safe_file(root / "run/met/met.inp", root)
    geo = _safe_file(root / "geo/makegeo/geo.dat", root)
    surf = _safe_file(root / "met/surface/final/surf.dat", root)
    deck = m.read_text(encoding="utf-8", errors="replace")
    # C++ G19 additionally verifies original CALMET control branches,
    # station order, date range and original binary/text records.
    g = contract["grid"]
    for key, value in (("NX", g["nx"]), ("NY", g["ny"]), ("NZ", g["nz"]),
                       ("IUTMZN", int(g["crs"].split("UTM")[1][:-1])),
                       ("NSSTA", len(surface_ids)), ("NUSTA", len(upper_ids))):
        if _as_int(deck, key) != value:
            raise ContractError(f"met.inp {key} differs from new-site case/grid.cmn")
    if _control(deck, "UTMHEM") != g["crs"][-1]:
        raise ContractError("met.inp UTMHEM disagrees with new-site hemisphere")
    for key, v in (("DGRIDKM", g["dgridkm"]),
                   ("XORIGKM", float(g["xrefkm"])), ("YORIGKM", float(g["yrefkm"]))):
        if abs(_as_number(deck, key) - v) > 1e-8:
            raise ContractError(f"met.inp {key} differs from published grid.cmn")
    if g["nz"] != 9 or g["nx"] > 400 or g["ny"] > 400:
        raise ContractError("G19 source loader is limited to nine layers and <=400x400 horizontal cells")
    zone = int(g["crs"].split("UTM")[1][:-1])
    northern = g["crs"][-1] == "N"
    ordered_up = []
    ordered_upper_ids = []
    for ordinal in range(1, len(upper_ids) + 1):
        station_id, x, y = _deck_site(deck, "US", ordinal)
        matching = [(sid, row) for sid, row in p4rows.items()
                    if _station_wmo(sid) == station_id]
        if len(matching) != 1:
            raise ContractError(f"US{ordinal} {station_id} does not match selected original IGRA station")
        sid, row = matching[0]
        _compare_xy((x, y), float(row["effective_lat"]), float(row["effective_lon"]),
                    zone, northern, f"US{ordinal}")
        name = f"up_{station_id}.dat"
        up = _safe_file(root / "met/upperair/final" / name, root)
        ordered_up.append(up)
        ordered_upper_ids.append(sid)
    seen_surface = set()
    for ordinal in range(1, len(surface_ids) + 1):
        station_id, x, y = _deck_site(deck, "SS", ordinal)
        matches = [(sid, row) for sid, row in p5rows.items()
                   if int(row["ifstn"]) == station_id]
        if len(matches) != 1:
            raise ContractError(f"SS{ordinal} {station_id} mismatches P5 IFSTN identity")
        sid, row = matches[0]
        if sid in seen_surface:
            raise ContractError("duplicate original surface station in met.inp")
        seen_surface.add(sid)
        _compare_xy((x, y), float(row["lat"]), float(row["lon"]),
                    zone, northern, f"SS{ordinal}")
    if set(ordered_upper_ids) != set(upper_ids) or seen_surface != set(surface_ids):
        raise ContractError("missing dynamically selected original station in met.inp")
    roles = {
        "met_deck": m, "p3_geo": geo, "p5_surface": surf,
    }
    roles.update({f"p4_upper_us{i + 1}": v for i, v in enumerate(ordered_up)})
    checked = {
        label: {"path": str(path.relative_to(root)), "size_bytes": path.stat().st_size,
                "sha256": _digest(path)}
        for label, path in roles.items()
    }
    command: list[str] = []
    native_executable_evidence = None
    if native_preflight_bin is not None:
        b = native_preflight_bin.absolute()
        if b.is_symlink() or not b.is_file() or not os.access(b, os.X_OK):
            raise ContractError("native G19 source-only preflight executable absent")
        native_executable_evidence = {"path": str(b), "sha256": _digest(b)}
        command = [str(b), str(m), str(geo), str(surf), *[str(p) for p in ordered_up]]
    return {
        "status": "P6_G19_DYNAMIC_SOURCE_ROLES_HASH_VERIFIED_NATIVE_SOURCE_NOT_RUN",
        "contract_version": "S2-G1A-G19-INPUT-ONLY-1",
        "case_name": contract["case_name"],
        "source_root": str(root),
        "research_years": years,
        "source_selection_sha256": {
            "p4": [x["audit_sha256"] for x in accepted["p4"]],
            "p5": [x["manifest_sha256"] for x in accepted["p5"]],
        },
        "ordered_upper_station_ids": ordered_upper_ids,
        "ordered_surface_station_ids": [sid for _, sid in sorted(
            ((i, next(sid for sid, row in p5rows.items()
                      if int(row["ifstn"]) == _deck_site(deck, "SS", i)[0]))
             for i in range(1, len(surface_ids) + 1)))],
        "grid": g, "roles": checked,
        "native_g19_command": command,
        "native_g19_executable": native_executable_evidence,
        "ordered_upper_wmo_ids": [_station_wmo(sid) for sid in ordered_upper_ids],
        "ordered_surface_ifstn_ids": [_deck_site(deck, "SS", i)[0]
                                      for i in range(1, len(surface_ids) + 1)],
        "native_input_parsed": False,
        "model_executed": False, "P6D_P6E_P6F": "NOT_RUN",
        "P7": "NOT_RUN",
        "ready": False, "legacy_fallback": False,
        "source_authenticity": contract["selector_source_authenticity"],
        "scientific_acceptance": "NOT_EVALUATED",
    }


def execute_source_preflight(plan: dict[str, Any]) -> dict[str, Any]:
    """G19 parses original file inputs only; never invokes P6 numerical driver."""
    command = plan["native_g19_command"]
    if not command:
        raise ContractError("no explicit C++ source-only G19 preflight executable was provided")
    evidence = plan["native_g19_executable"]
    exe = Path(command[0])
    if (not isinstance(evidence, dict) or exe.is_symlink()
            or not exe.is_file() or _digest(exe) != evidence.get("sha256")):
        raise ContractError("G19 preflight executable changed after source-plan SHA capture")
    case_root = Path(plan["source_root"])
    for record in plan["roles"].values():
        p = _safe_file(case_root / record["path"], case_root)
        if p.stat().st_size != record["size_bytes"] or _digest(p) != record["sha256"]:
            raise ContractError("G19 physical source bytes changed after source-plan SHA capture")
    run = subprocess.run(command, capture_output=True, text=True, check=False, timeout=180)
    if run.returncode != 0 or "PASS_P6G_G19_FILE_SOURCE_CONTRACT" not in run.stdout:
        raise ContractError(
            "native G19 source preflight rejected file-backed meteorology "
            + f"(exit={run.returncode}): " + run.stderr[-1000:])
    # Validate the actual C++ source-file parser's reported identities and
    # geometry, not just its PASS sentinel or an untrusted exit code.
    expected_site_lines = {
        "SS_IDS": ",".join(str(x) for x in plan["ordered_surface_ifstn_ids"]),
        "US_IDS": ",".join(str(x) for x in plan["ordered_upper_wmo_ids"]),
    }
    for name, ids in expected_site_lines.items():
        observed = re.search(r"(?m)^" + name + r"=([0-9,]+)\s*$", run.stdout)
        if observed is None or observed.group(1) != ids:
            raise ContractError(f"native G19 parser {name} differs from authenticated deck order")
    counts = re.search(r"\bNSSTA=(\d+)\s+NUSTA=(\d+)\b", run.stdout)
    if counts is None or (int(counts.group(1)), int(counts.group(2))) != (
            len(plan["ordered_surface_station_ids"]), len(plan["ordered_upper_station_ids"])):
        raise ContractError("native G19 parser station counts differ from authenticated deck")
    geo = plan["grid"]
    for name, value in (("NX", geo["nx"]), ("NY", geo["ny"])):
        field = re.search(r"\b" + name + r"=(\d+)\b", run.stdout)
        if field is None or int(field.group(1)) != value:
            raise ContractError(f"native G19 {name} differs from case grid")
    result = dict(plan)
    result["status"] = "P6_G19_DYNAMIC_FILE_INPUT_PARSED_NO_PHYSICS_EXECUTED"
    result["native_input_parsed"] = True
    result["native_g19_stdout"] = run.stdout[-8192:]
    # Even after genuine G19 input parsing, no native P6 meteorology exists.
    result["ready"] = False
    result["model_executed"] = False
    result["scientific_acceptance"] = "NOT_EVALUATED"
    return result


def main(argv: list[str] | None = None) -> int:
    a = argparse.ArgumentParser(description="S2-G1A P6 G19 dynamic source files, NOT physics")
    a.add_argument("--case-yaml", type=Path, required=True)
    a.add_argument("--p4-selection-root", type=Path, required=True)
    a.add_argument("--p5-selection-root", type=Path, required=True)
    a.add_argument("--g19-native-bin", type=Path, default=None)
    a.add_argument("--execute-input-preflight", action="store_true")
    args = a.parse_args(argv)
    try:
        result = prepare_g19(args.case_yaml, args.p4_selection_root,
                             args.p5_selection_root, args.case_yaml.absolute().parent,
                             args.g19_native_bin)
        if args.execute_input_preflight:
            result = execute_source_preflight(result)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (ContractError, OSError, ValueError, RuntimeError, UnicodeError) as exc:
        print(json.dumps({
            "status": "BLOCKED_P6_G19_DYNAMIC_INPUT",
            "model_executed": False, "ready": False, "legacy_fallback": False,
            "error": str(exc),
        }, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
