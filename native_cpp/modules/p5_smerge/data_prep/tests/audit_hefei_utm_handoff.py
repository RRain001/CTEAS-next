#!/usr/bin/env python3
"""Offline, read-only P5 strict-UTM migration impact audit for frozen Hefei 2022.

Compare the old geographic bounding-box station candidates with the actual
published UTM grid.cmn candidates BEFORE any NOAA downloads or interpolation.
If candidate membership changes, stop: regenerate P5, met.inp and the
unchanged-original Fortran reference in a separately versioned case.
If unchanged, the frozen original input bytes must retain their SHA256 hashes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from native_cpp.modules.p5_smerge.data_prep import download_isd_by_grid as d


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for part in iter(lambda: f.read(2 ** 20), b""):
            digest.update(part)
    return digest.hexdigest()


def old_bbox_candidates(stations: list[d.Station], center: tuple[float, float],
                        grid: d.GridDef) -> list[str]:
    """Previous selector reproduced only for forensic comparison, never production."""
    lon0, lat0 = center
    half_w = grid.dgridkm * grid.nx / 2
    half_h = grid.dgridkm * grid.ny / 2
    dlon = half_w / (111.32 * math.cos(math.radians(lat0)))
    dlat = half_h / 111.32
    return sorted(s.sid for s in stations
                  if lon0 - dlon <= s.lon <= lon0 + dlon
                  and lat0 - dlat <= s.lat <= lat0 + dlat)


def main(case: Path, history_file: Path, report: Path) -> int:
    grid = d.load_utm_grid(case / "grid/grid.cmn")
    center = d.parse_center(case / "grid/center_location")
    start, end = d.parse_research_time(case / "grid/research_time")
    if (start, end) != (datetime(2022, 1, 1, 0), datetime(2022, 1, 6, 23)):
        raise AssertionError("unexpected locked reference period")
    if not history_file.is_file() or history_file.stat().st_size < 1000:
        raise AssertionError(f"NOAA history unavailable: {history_file}")
    stations = [st for st in d.parse_history_txt(history_file)
                if d.covers_interval(st.begin, st.end, start, end)]
    if not stations:
        raise AssertionError("NOAA station history produced no eligible candidates")
    old_ids = old_bbox_candidates(stations, center, grid)
    new_ids = sorted(st.sid for st in stations if d.station_in_utm_grid(st, grid))
    archived = json.loads((case / "met/surface/isd_raw/station_selection_2022.json").read_text())
    manifest = json.loads((case / "run_manifest.json").read_text())
    frozen = {entry["path"]: entry["sha256"] for entry in manifest["artifacts"]}
    paths = (
        "met/surface/isd_raw/station_selection_2022.json",
        "met/surface/final/stations.csv",
        "met/surface/final/surf.dat",
        "run/met/met.inp",
    )
    hashes = {
        p: {"frozen_sha256": frozen[p], "observed_sha256": sha256(case / p)}
        for p in paths
    }
    hashes_match = all(v["frozen_sha256"] == v["observed_sha256"]
                       for v in hashes.values())
    candidates_unchanged = old_ids == new_ids
    expected_mode = "OBSERVED" if new_ids else "VIRTUAL_RELOCATED"
    mode_unchanged = archived["mode"] == expected_mode
    # Both policies use identical distance/coverage sorting when no in-domain
    # candidate exists. Never replace original out-of-domain station coords.
    source_is_external = all(not d.station_in_utm_grid(
        d.Station(row["sid"], row["source_lat"], row["source_lon"], row["elev"],
                  row["name"], row["country"], row["begin"], row["end"]), grid)
        for row in archived["stations"])
    pass_gate = (candidates_unchanged and mode_unchanged and hashes_match and
                 (bool(new_ids) or source_is_external))
    result = {
        "status": "PASS_P5_UTM_NO_FROZEN_INPUT_CHANGE" if pass_gate
                  else "BLOCK_REFERENCE_REGENERATION_REQUIRED",
        "case": case.name,
        "history_sha256": sha256(history_file),
        "eligible_noaa_stations": len(stations),
        "utm_zone": grid.iutmzn,
        "utm_hemisphere": grid.lsohem,
        "utm_bounds_km": d.utm_bounds_km(grid),
        "legacy_geo_candidate_ids": old_ids,
        "strict_utm_candidate_ids": new_ids,
        "only_legacy": sorted(set(old_ids) - set(new_ids)),
        "only_strict_utm": sorted(set(new_ids) - set(old_ids)),
        "frozen_mode": archived["mode"],
        "new_mode": expected_mode,
        "frozen_primary_station": archived["primary_sid"],
        "frozen_hashes": hashes,
        "reference_regeneration_required": not pass_gate,
        "note": "If the candidate set/mode changes, rebuild P5 and recapture original Fortran; never relabel old met.dat as new reference.",
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not pass_gate:
        raise AssertionError("strict UTM selection impacts frozen reference or hashes: regenerate before merge")
    print("PASS_P5_UTM_NO_FROZEN_INPUT_CHANGE")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", type=Path, required=True)
    ap.add_argument("--history", type=Path, default=ROOT / "engine/resources/isd/isd-history.txt")
    ap.add_argument("--report", type=Path, required=True)
    args = ap.parse_args()
    raise SystemExit(main(args.case.resolve(), args.history.resolve(), args.report.resolve()))
