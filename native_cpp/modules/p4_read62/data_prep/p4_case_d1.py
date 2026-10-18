"""P4 D1-A: fail-closed staged-case admission and read-only offline IGRA locator.

Only the existing JDAT=2, IFMT=1, PSTOP=500 route is admitted here.
This module neither selects sounding stations nor alters QA or READ62 physics.
Final CALMET UP publication remains blocked pending #55 D2/D3.
"""
from __future__ import annotations

import hashlib
import re
from datetime import timedelta
from pathlib import Path

import yaml

from native_cpp.orchestration.plan import CASE_ID, ContractError, child, mapping
from native_cpp.orchestration.site_plan import _geography, _time


def sha256_file(path: Path) -> str:
    if path.is_symlink() or not path.is_file() or path.stat().st_size == 0:
        raise ContractError(f"source missing, empty or symlink: {path}")
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _within(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents


def admit_staged_case(case_root: Path, upperair_root: Path, archive_root: Path,
                      repo_root: Path) -> dict[str, str]:
    """Admit a physically isolated, already-staged #42 B-0 case before any P4 writes."""
    if case_root.is_symlink() or not case_root.is_dir():
        raise ContractError("staged case must be an existing ordinary directory")
    if archive_root.is_symlink() or not archive_root.is_dir():
        raise ContractError("offline NOAA archive directory missing or symlink")
    case = case_root.resolve(strict=True)
    repo = repo_root.resolve(strict=True)
    output = upperair_root.resolve(strict=False)
    if _within(case, repo) or _within(output, repo):
        raise ContractError("P4 case and output must be outside repository worktree")
    if output != case / "met" / "upperair" or upperair_root.is_symlink():
        raise ContractError("isolated P4 output must be staged_case/met/upperair")
    if output.exists():
        raise ContractError("P4 scratch must not preexist; refusing overwrite or reuse")
    if not (case / "met").is_dir() or (case / "met").is_symlink():
        raise ContractError("staged case met directory missing or symlink")
    paths = [case / "case.yaml", case / "grid" / "grid.cmn",
             case / "grid" / "research_time", case / "grid" / "center_location"]
    for path in paths:
        if path.is_symlink() or not path.is_file():
            raise ContractError(f"staged immutable input missing or symlink: {path}")
    cfg = yaml.safe_load(paths[0].read_text(encoding="utf-8"))
    cfg = mapping(cfg, "case.yaml")
    name = child(cfg, "case_name")
    if (not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", name)
            or name != case.name or name == CASE_ID):
        raise ContractError("case_name must be independent, non-frozen and match case directory")
    if child(cfg, "settings", "timezone") != "UTC+0000":
        raise ContractError("P4 requires UTC+0000")
    _geography(cfg, paths[0])  # reuse #42's authoritative UTM/grid precision gate
    t0 = _time(child(cfg, "preprocess", "research_time", "begin"))
    t1 = _time(child(cfg, "preprocess", "research_time", "end"))
    if t1 < t0 or t1 - t0 > timedelta(days=731):
        raise ContractError("invalid case UTC interval")
    published = paths[2].read_text(encoding="utf-8")
    begin = re.search(r"BEGIN\s*:\s*(\d{8}-\d{6})", published)
    end = re.search(r"END\s*:\s*(\d{8}-\d{6})", published)
    if (not begin or not end
            or begin.group(1) != t0.strftime("%Y%m%d-%H%M%S")
            or end.group(1) != t1.strftime("%Y%m%d-%H%M%S")):
        raise ContractError("case.yaml and research_time UTC mismatch")
    source = child(cfg, "puff", "point_sources")
    if not isinstance(source, list) or len(source) != 1:
        raise ContractError("P4 D1-A requires a single physical stack for relocation")
    station_center = paths[3].read_text(encoding="utf-8")
    lon = re.search(r"longitude\s*:\s*([-+]?\d+(?:\.\d+)?)", station_center)
    lat = re.search(r"latitude\s*:\s*([-+]?\d+(?:\.\d+)?)", station_center)
    if not lon or not lat:
        raise ContractError("center_location missing physical coordinates")
    if (abs(float(lon.group(1)) - float(child(source[0], "longitude"))) > 1e-5
            or abs(float(lat.group(1)) - float(child(source[0], "latitude"))) > 1e-5):
        raise ContractError("P4 selector center differs from the physical stack")
    result = {str(path.relative_to(case)): sha256_file(path) for path in paths}
    result["case_root"] = str(case)
    result["upperair_root"] = str(output)
    return result


def offline_igra(archive_root: Path, station_id: str, year: int):
    """Return a real, immutable extracted NOAA data-por text or fail without network.

    Accept either archive/<station>-data.txt or archive/<year>/<station>-data.txt.
    The existing selector still performs all annual raw-slot QA before use.
    """
    if not re.fullmatch(r"[A-Z0-9]{8,20}", station_id) or not 1900 <= year <= 2100:
        return None, False, {"error": "invalid station identity or year"}
    archive = archive_root.resolve(strict=True)
    name = station_id + "-data.txt"
    candidates = [archive / name, archive / str(year) / name]
    existing = [p for p in candidates if p.exists() or p.is_symlink()]
    if len(existing) != 1:
        return None, False, {"error": "missing or ambiguous immutable NOAA archive", "station_id": station_id}
    path = existing[0]
    try:
        if not _within(path.resolve(strict=True), archive):
            raise ContractError("NOAA path escapes archive")
        sha256_file(path)
    except (OSError, ContractError) as exc:
        return None, False, {"error": str(exc), "station_id": station_id}
    return path, True, None
