#!/usr/bin/env python3
"""S2-G0: genuine NOAA P4 outside-grid fallback + P5 two inside-grid sites.

One new, shared physical WGS84 UTM footprint around observed Huoshan and Hefei
surface sites. The full production P4 IGRA selector independently chooses a
real eligible out-of-grid 00/12 radiosonde source. The full P5 NOAA surface
selector chooses the two genuine in-grid observations across 2022 and 2023.
Their resulting annual manifests feed the non-executable case.yaml handoff.

A separate S3-F P4 two-in-grid genuine multi-year test is preserved as
separate scientific evidence; NEVER claim those upper-air stations are inside
this smaller P5-grid experiment. No CALMET P6 or CALPUFF P7 executions.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from engine.run_met.station_grid import load_strict_utm_grid
from native_cpp.modules.p4_read62.data_prep import download_igra as p4
from native_cpp.modules.p5_smerge.data_prep import download_isd_by_grid as p5
from native_cpp.orchestration.plan import FROZEN_MET_CONTROLS, FROZEN_PUFF_CONTROLS
from native_cpp.orchestration.site_plan import plan_site
from scripts.s3f.verify_real_noaa_2022_2023_station_selection import (
    HEFEI, SMOKE, P4_STATIONS, P5_STATIONS, p4_check, p5_check,
)


def run() -> dict:
    with tempfile.TemporaryDirectory(prefix="s2g-authentic-noaa-source-handoff-") as td:
        top = Path(td)
        # Independent genuine P4 two-in-domain cross-year proof, NOT this
        # new non-Hefei shared-site upper-air selection.
        separate_p4_multisite = p4_check(top / "separate_p4_two_in_domain")
        p5_sources = p5_check(top / "p5")
        p5catalog = p5.parse_history_txt(ROOT / "engine/resources/isd/isd-history.txt")
        p5stations = {s.sid: s for s in p5catalog if s.sid in P5_STATIONS}
        assert set(p5stations) == set(P5_STATIONS)

        # Adopt the exact *actually tested P5* two-station footprint, instead
        # of widening it to an area that introduces extra NOAA P5 candidates.
        case = top / "independent_huoshan_xinqiao_2022_2023"
        (case / "grid").mkdir(parents=True)
        source_grid = top / "p5/grid/grid.cmn"
        shutil.copyfile(source_grid, case / "grid/grid.cmn")
        grid_file = case / "grid/grid.cmn"
        grid = load_strict_utm_grid(grid_file, context="S2G actual shared site")
        positions = [(s.lat, s.lon) for s in p5stations.values()]
        center_lat = sum(lat for lat, _ in positions) / len(positions)
        center_lon = sum(lon for _, lon in positions) / len(positions)
        (case / "grid/center_location").write_text(
            f"latitude: {center_lat:.9f}\nlongitude: {center_lon:.9f}\n", encoding="utf-8")
        for year in (2022, 2023):
            first = __import__("datetime").datetime(year, 1, 1)
            last = __import__("datetime").datetime(year, 12, 31, 23)
            eligible = [s for s in p5catalog
                        if p5.covers_interval(s.begin, s.end, first, last)
                        and p5.station_in_utm_grid(s, grid)]
            assert {s.sid for s in eligible} == set(P5_STATIONS), (
                "Unexpected extra P5 candidate in new site; must fetch real observation source",
                year, [s.sid for s in eligible])

        # REAL upstream P4 algorithm with full original IGRA catalog:
        # the physically small P5 grid should contain no active sounding
        # station, so P4 selects nearest genuinely eligible outside source
        # for each year and relocates it at the new stack/center.
        p4catalog = p4.load_station_list(ROOT / "engine/resources/igra/igra2-station-list.txt")
        raw_p4 = {
            "CHM00058203": SMOKE / "met/upperair/2023/CHM00058203-data.txt",
            "CHM00058424": HEFEI / "met/upperair/2022/CHM00058424-data.txt",
        }
        archive_hashes = {}
        for sid, f in raw_p4.items():
            assert f.is_file()
            archive_hashes[sid] = hashlib.sha256(f.read_bytes()).hexdigest()

        def archived_source_transport(sid: str, outdir: Path):
            if sid not in raw_p4:
                raise ValueError(
                    f"Unarchived nearest original IGRA source {sid}; no mock or silent catalog restriction")
            return raw_p4[sid], True, None

        p4_selected = []
        p4root = top / "p4_shared_site/upperair"
        for year in (2022, 2023):
            inside, outside = p4.candidate_groups(
                p4catalog, center_lat, center_lon, grid, year)
            assert not inside, (year, [s["id"] for s in inside])
            assert outside and outside[0]["id"] in raw_p4, (
                "Nearest IGRA source not in our authentic archived original samples",
                year, [(x["id"], x["dist_km"]) for x in outside[:4]])
            with patch.object(p4, "DATA_ROOT", p4root), \
                 patch.object(p4, "current_project_path",
                              side_effect=lambda *args: case.joinpath(*args)), \
                 patch.object(p4, "download_igra_data",
                              side_effect=archived_source_transport), \
                 patch.object(sys, "argv",
                              ["download_igra", "--year", str(year), "--pstop", "500"]):
                assert p4.main() == 0, f"P4 original selector failed in {year}"
            report = json.loads(
                (p4root / str(year) / "p4_station_selection_audit.json").read_text())
            assert report["in_domain_candidates"] == 0
            assert len(report["selected"]) == 1
            st = report["selected"][0]
            assert st["site_type"] == "VIRTUAL_RELOCATED"
            assert st["id"] in P4_STATIONS
            assert st["valid_original_slots"] * 5 > 4 * 730
            p4_selected.append({
                "year": year, "sid": st["id"],
                "valid_original_slots": st["valid_original_slots"],
                "source_lat": st["source_lat"], "source_lon": st["source_lon"],
                "effective_lat": st["effective_lat"],
                "effective_lon": st["effective_lon"],
            })

        data = {
            "schema_version": 1, "case_name": case.name,
            "settings": {"timezone": "UTC+0000"},
            "preprocess": {
                "grid": {
                    "utm_zone": grid.iutmzn, "hemisphere": grid.lsohem,
                    "center": {"latitude": center_lat, "longitude": center_lon},
                    "domain": {
                        "length_km": grid.nx * grid.dgridkm,
                        "width_km": grid.ny * grid.dgridkm,
                    },
                    "resolution_km": grid.dgridkm, "nz": grid.nz,
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
        config.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        handoff = plan_site(config, p4root, top / "p5/surface")
        assert handoff["status"] == "SITE_STATION_INPUTS_VERIFIED_P6_P7_BLOCKED"
        assert len(handoff["selector_manifest_evidence"]["p4"]) == 2
        assert len(handoff["selector_manifest_evidence"]["p5"]) == 2
        assert all(len(x["station_ids"]) == 1 for x in handoff["selector_manifest_evidence"]["p4"])
        assert all(len(x["station_ids"]) == 2 for x in handoff["selector_manifest_evidence"]["p5"])
        assert not handoff["ready"] and not handoff["model_executed"]
        return {
            "status": "S2G_NONHEFEI_REAL_NOAA_STATION_HANDOFF_PASS_SCOPED",
            "case_scope": "real two in-domain P5 and one virtual fallback P4, on one new WGS84 UTM footprint",
            "case_yaml": data,
            "case_sha256": hashlib.sha256(config.read_bytes()).hexdigest(),
            "p4_case_original_noaa_external_station": p4_selected,
            "p4_source_sha256": archive_hashes,
            "separate_real_two_in_domain_P4_evidence": separate_p4_multisite,
            "p5_real_two_station_two_year_evidence": p5_sources,
            "metadata_plan": handoff,
            "accepted_only": "P4/P5 original-source selection plus new-site static metadata compatibility",
            "P6": "BLOCKED_NOT_RUN", "P7": "BLOCKED_NOT_RUN", "G5": "BLOCKED_NOT_RUN",
        }


def main():
    out = run()
    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("s2g-noaa-new-site-input-contract.json")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("S2G_REAL_NOAA_SITE_HANDOFF=" + out["status"])
    print("S2G_P6=BLOCKED_NOT_RUN S2G_P7=BLOCKED_NOT_RUN")
    print("S2G_EVIDENCE=" + str(dest))


if __name__ == "__main__":
    main()
