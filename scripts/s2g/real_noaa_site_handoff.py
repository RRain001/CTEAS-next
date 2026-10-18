#!/usr/bin/env python3
"""Real 2022-2023 NOAA two-station P4/P5 -> independent non-Hefei site contract.

Uses existing S3-F *actual production-selector* NOAA observation replay (not
invented source counts), and checks candidate lists against ONE shared UTM
footprint before invoking the new S2-G0 non-executable input handoff.
Never compiles/executes P6, P7 or G5. The result is NOT a native P1-P7 PASS.
"""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from engine.run_met.station_grid import load_strict_utm_grid
from native_cpp.modules.p4_read62.data_prep import download_igra as p4
from native_cpp.modules.p5_smerge.data_prep import download_isd_by_grid as p5
from native_cpp.orchestration.plan import FROZEN_MET_CONTROLS, FROZEN_PUFF_CONTROLS
from native_cpp.orchestration.site_plan import plan_site
from scripts.s3f.verify_real_noaa_2022_2023_station_selection import (
    P4_STATIONS, P5_STATIONS, generate_grid, p4_check, p5_check,
)


def run():
    with tempfile.TemporaryDirectory(prefix="s2g-authentic-noaa-source-handoff-") as td:
        top = Path(td)
        p4_provenance = p4_check(top / "p4")
        p5_provenance = p5_check(top / "p5")
        p4catalog = p4.load_station_list(ROOT / "engine/resources/igra/igra2-station-list.txt")
        p5catalog = p5.parse_history_txt(ROOT / "engine/resources/isd/isd-history.txt")
        p4_data = {s["id"]: s for s in p4catalog if s["id"] in P4_STATIONS}
        p5_data = {s.sid: s for s in p5catalog if s.sid in P5_STATIONS}
        if set(p4_data) != set(P4_STATIONS) or set(p5_data) != set(P5_STATIONS):
            raise ValueError("NOAA source catalogs missing one or more actual stations")
        positions = [
            (s["lat"], s["lon"]) for s in p4_data.values()
        ] + [(s.lat, s.lon) for s in p5_data.values()]
        case = top / "independent_four_station_2022_2023"
        grid_file, _, _ = generate_grid(case / "grid", positions)
        grid = load_strict_utm_grid(grid_file, context="S2G real shared domain")
        center_lat = sum(lat for lat, _ in positions) / len(positions)
        center_lon = sum(lon for _, lon in positions) / len(positions)
        for year in (2022, 2023):
            p4_inside, _ = p4.candidate_groups(
                p4catalog, center_lat, center_lon, grid, year)
            assert {x["id"] for x in p4_inside} == set(P4_STATIONS), (
                "Unexpected P4 NOAA candidate in unified geographic footprint",
                year, [x["id"] for x in p4_inside])
            p5_inside = [
                st for st in p5catalog if p5.station_in_utm_grid(st, grid)
                and st.begin[:4] <= str(year) <= st.end[:4]
            ]
            assert {x.sid for x in p5_inside} == set(P5_STATIONS), (
                "Unexpected P5 NOAA candidate in unified geographic footprint",
                year, [x.sid for x in p5_inside])
        doc = {
            "schema_version": 1,
            "case_name": case.name,
            "settings": {"timezone": "UTC+0000"},
            "preprocess": {
                "grid": {
                    "utm_zone": grid.iutmzn,
                    "hemisphere": grid.lsohem,
                    "center": {"latitude": center_lat, "longitude": center_lon},
                    "domain": {"length_km": grid.nx * grid.dgridkm,
                               "width_km": grid.ny * grid.dgridkm},
                    "resolution_km": grid.dgridkm,
                    "nz": grid.nz,
                },
                "research_time": {"begin": "20220101-000000", "end": "20231231-230000"},
                "upperair": {"station_id": "auto", "pstop_hpa": 500},
                "surface": {"auto_select_all": True},
            },
            "met": {"options": FROZEN_MET_CONTROLS},
            "puff": {
                "options": FROZEN_PUFF_CONTROLS,
                "point_sources": [{
                    "name": "INDEPENDENT_TEST_STACK",
                    "latitude": center_lat, "longitude": center_lon,
                    "stack_height_m": 40.0, "stack_diameter_m": 1.6,
                    "exit_velocity_mps": 12.0, "exit_temp_k": 300.0,
                    "emissions": [1.0, 0.0],
                }],
            },
        }
        config = case / "case.yaml"
        config.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
        handoff = plan_site(
            config, top / "p4/upperair", top / "p5/surface")
        assert handoff["status"] == "SITE_STATION_INPUTS_VERIFIED_P6_P7_BLOCKED"
        assert len(handoff["selector_manifest_evidence"]["p4"]) == 2
        assert len(handoff["selector_manifest_evidence"]["p5"]) == 2
        assert not handoff["ready"] and not handoff["model_executed"]
        # Persist only generated text manifest evidence and source SHA, not
        # privately cached original NOAA binaries or MET/puff outputs.
        return {
            "status": "S2G_NONHEFEI_REAL_NOAA_STATION_HANDOFF_PASS_SCOPED",
            "case_scope": "new East-China four-station shared WGS84 UTM footprint, NOT frozen Hefei 5km",
            "case_yaml": doc,
            "case_sha256": hashlib.sha256(config.read_bytes()).hexdigest(),
            "p4_real_original_data": p4_provenance,
            "p5_real_original_data": p5_provenance,
            "metadata_plan": handoff,
            "accepted_only": "P4/P5 source-backed selection and static contract compatibility",
            "P6": "BLOCKED_NOT_RUN",
            "P7": "BLOCKED_NOT_RUN",
            "G5": "BLOCKED_NOT_RUN",
        }


def main():
    out = run()
    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("s2g-noaa-new-site-input-contract.json")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    print("S2G_REAL_NOAA_SITE_HANDOFF=" + out["status"])
    print("S2G_P6=BLOCKED_NOT_RUN S2G_P7=BLOCKED_NOT_RUN")
    print("S2G_EVIDENCE=" + str(dest))


if __name__ == "__main__":
    main()
