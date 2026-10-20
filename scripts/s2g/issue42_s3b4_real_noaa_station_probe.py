#!/usr/bin/env python3
"""S3-B4 real NOAA station *geometry* screening on the actual June Huoshan B0.

This does not download or produce observations: original IGRA/ISD selectors
and authentic station catalogs determine only candidate order and location.
Annual observation coverage and final selected station identity are NOT_RUN
until the original-source P4/P5 producers execute on this exact case.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys

import yaml

from engine.run_met.station_grid import load_strict_utm_grid, lon_lat_in_utm_grid
from native_cpp.orchestration.case_admission import admit_case, verify_immutable
from native_cpp.modules.p4_read62.data_prep import download_igra as p4
from native_cpp.modules.p5_smerge.data_prep import download_isd_by_grid as p5

REPO = Path(__file__).resolve().parents[2]
P4_CATALOG = REPO / "engine/resources/igra/igra2-station-list.txt"
P5_CATALOG = REPO / "engine/resources/isd/isd-history.txt"


def sha(path: Path) -> str:
    if path.is_symlink() or not path.is_file() or path.stat().st_size < 1000:
        raise ValueError("S3-B4 genuine catalog absent, symlinked or empty: " + str(path))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize_station(row: dict, *, category: str) -> dict:
    return {
        "id": row["id"], "category": category,
        "latitude": row["lat"], "longitude": row["lon"],
        "distance_from_center_km": row["dist_km"],
        "catalog_first_year": row["first_year"],
        "catalog_last_year": row["last_year"],
    }


def probe(case_yaml: Path, destination: Path) -> dict:
    admission = admit_case(case_yaml)
    root = admission.case_path.parent
    if destination != root / "evidence/s3-b4-real-noaa-candidate-screen.json":
        raise ValueError("S3-B4 output must be inside the case's new evidence directory")
    if destination.exists() or destination.is_symlink() or destination.parent.is_symlink():
        raise ValueError("S3-B4 must emit fresh and unlinked evidence")
    if (admission.research_begin, admission.research_end) not in {
        ("20220601-000000", "20220602-000000"),
        ("20220601-010000", "20220601-070000"),
    }:
        raise ValueError("S3-B4 requires independently verified June 2022 real-source B0")
    if (admission.utm_zone, admission.hemisphere, admission.nx, admission.ny,
        admission.xrefkm_text, admission.yrefkm_text) != (
            50, "N", 100, 100, "462.305", "3501.570"
        ) or abs(admission.dgridkm - 0.1) > 1e-12:
        raise ValueError("S3-B4 geometry does not match original-science Huoshan June grid")

    case = yaml.safe_load(case_yaml.read_text())
    centre = case["preprocess"]["grid"]["center"]
    lat, lon = float(centre["latitude"]), float(centre["longitude"])
    grid = load_strict_utm_grid(admission.grid_path, context="S3-B4 genuine Huoshan")
    if not lon_lat_in_utm_grid(lon, lat, grid):
        raise ValueError("actual admitted center is outside authoritative grid")
    p4_sha, p5_sha = sha(P4_CATALOG), sha(P5_CATALOG)

    station_year = 2022
    upper = p4.load_station_list(P4_CATALOG)
    inside_upper, outside_upper = p4.candidate_groups(upper, lat, lon, grid, station_year)
    if not inside_upper and not outside_upper:
        raise ValueError("no real IGRA catalog candidates cover 2022")
    # The real P4 selector tests *all* qualifying in-domain stations' original
    # 00/12 slots, otherwise tries outside candidates in the actual distance order.
    # Never label catalog-eligible as truly selected before archived-obs QA.
    next_upper = (inside_upper if inside_upper else outside_upper)
    p4_rows = [summarize_station(row, category="IN_DOMAIN" if inside_upper else "OUTSIDE")
               for row in next_upper[:10]]

    first = datetime.strptime(admission.research_begin, "%Y%m%d-%H%M%S")
    last = datetime.strptime(admission.research_end, "%Y%m%d-%H%M%S")
    surface = p5.parse_history_txt(P5_CATALOG)
    eligible = [s for s in surface if p5.covers_interval(s.begin, s.end, first, last)]
    inside_surface = sorted((s for s in eligible if p5.station_in_utm_grid(s, grid)),
                            key=lambda s: s.sid)
    if inside_surface:
        ordered_surface = inside_surface
        mode = "OBSERVED"
    else:
        mode = "VIRTUAL_RELOCATED"
        ordered_surface = sorted(
            eligible, key=lambda s: (p5.haversine_km(lat, lon, s.lat, s.lon), s.sid))
    if not ordered_surface:
        raise ValueError("no real ISD catalog candidates cover the actual June interval")
    surface_rows = [{
        "id": s.sid, "latitude": s.lat, "longitude": s.lon,
        "catalog_first_date": s.begin, "catalog_last_date": s.end,
        "distance_from_stack_km": p5.haversine_km(lat, lon, s.lat, s.lon),
    } for s in ordered_surface[:10]]
    verify_immutable(admission)

    report = {
        "schema": "cteas.s3.b4.real_station_catalog_gate.v1",
        "status": "S3_B4_TRUE_CATALOG_GEOMETRY_ACCEPTED_NO_NOAA_OBSERVATION_QA",
        "case_name": admission.case_name,
        "b0": {
            "case_yaml_sha256": admission.case_sha256,
            "grid_cmn_sha256": admission.grid_sha256,
            "research_time_sha256": admission.time_sha256,
            "site_center_lonlat": [lon, lat],
            "grid": {"utm_zone": admission.utm_zone, "hemisphere": admission.hemisphere,
                     "nx": admission.nx, "ny": admission.ny,
                     "spacing_km": admission.dgridkm,
                     "origin_km": [admission.xrefkm_text, admission.yrefkm_text]},
            "utc": [admission.research_begin, admission.research_end],
        },
        "original_noaa_igra_catalog_sha256": p4_sha,
        "original_noaa_isd_catalog_sha256": p5_sha,
        "p4": {
            "total_year_eligible": len(p4.filter_by_year(upper, station_year)),
            "in_domain_candidates": len(inside_upper),
            "outside_candidates": len(outside_upper),
            "next_candidates_original_selector_order_first10": p4_rows,
            "actual_noaa_profile_coverage": "NOT_RUN",
            "actual_selected_stations": "NOT_ESTABLISHED",
            "original_read62_up_dat": "NOT_RUN",
        },
        "p5": {
            "total_time_eligible": len(eligible),
            "in_domain_candidates": len(inside_surface),
            "original_selector_mode": mode,
            "next_candidates_original_selector_order_first10": surface_rows,
            "actual_full_isd_lite_raw_coverage": "NOT_RUN",
            "actual_selected_stations": "NOT_ESTABLISHED",
            "original_smerge_surf_dat": "NOT_RUN",
        },
        "actual_s3_five_producer_join": "NOT_RUN",
        "native_g19_parser": "NOT_RUN",
        "p6_p7_physics": "NOT_RUN",
        "docker": "DEFERRED",
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-yaml", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = probe(args.case_yaml, args.destination)
    except (KeyError, TypeError, OSError, ValueError, yaml.YAMLError) as exc:
        print("S3_B4_CATALOG_SOURCE_REJECTED: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps({
        "status": report["status"],
        "b0": report["b0"],
        "p4": report["p4"],
        "p5": report["p5"],
        "s3_stack": report["actual_s3_five_producer_join"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
