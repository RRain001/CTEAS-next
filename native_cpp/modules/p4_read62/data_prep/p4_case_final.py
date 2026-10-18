"""#55 D2 staged, source-only CALMET UP candidate from validated annual native UP.

Strictly reuses the existing original-compatible normalizer. Never invokes
the legacy merger's synthetic +12h boundary append or glob over stale files.
The resulting files are PRODUCED_UNVERIFIED until independent P4 original
parity and the shared #42 G19 source audit both pass.
"""
from __future__ import annotations

import csv
import json
from datetime import datetime, timedelta
from pathlib import Path

from native_cpp.orchestration.plan import ContractError
from .merge_final_upperair import (
    HEADER_LINES, normalize_updat_records, update_header_line,
)
from .p4_case_d1 import sha256_file
from .p4_case_year_gate import writer_window


def _read_blocks(up_path: Path, expected_wmo: str):
    raw = up_path.read_text(encoding="utf-8").splitlines()
    if len(raw) < HEADER_LINES + 2:
        raise ContractError(f"P4 annual raw UP truncated: {up_path}")
    normalized, clipped = normalize_updat_records(raw, expected_wmo, up_path)
    header = normalized[:HEADER_LINES]
    blocks = []
    current = []
    for line in normalized[HEADER_LINES:]:
        if line.split()[:1] == ["6201"]:
            if current:
                blocks.append(current)
            current = [line]
        elif current:
            current.append(line)
        else:
            raise ContractError("P4 UP levels appear before first 6201 sounding")
    if current:
        blocks.append(current)
    result = []
    for block in blocks:
        parts = block[0].split()
        if len(parts) < 14 or parts[0] != "6201" or parts[1] != expected_wmo:
            raise ContractError("P4 normalized 6201 station identity invalid")
        try:
            y, m, d, h, minute_field = map(int, parts[2:7])
            t = datetime(y, m, d, h, 0, minute_field)
            y2, m2, d2, h2, sec2 = map(int, parts[7:12])
            te = datetime(y2, m2, d2, h2, 0, sec2)
        except ValueError as exc:
            raise ContractError("P4 normalized 6201 UTC time invalid") from exc
        if t != te or t.hour not in (0, 12) or minute_field != 0 or sec2 != 0:
            raise ContractError("P4 6201 is not original 00/12 UTC sounding")
        result.append((t, block))
    return header, result, clipped


def publish_source_only_candidate(records: list[dict], lineage: dict,
                                  upperair_root: Path,
                                  model_begin: datetime, model_end: datetime) -> dict:
    """Publish only fully authentic source-normalized candidate UP, no P6 science."""
    if lineage.get("real_aa_bb_each_hour") is not True:
        raise ContractError("P4 source AA/BB gate not admitted")
    if len(lineage["station_wmo"]) < 1:
        raise ContractError("no original upper-air sources")
    target = upperair_root / "final"
    if target.exists() or target.is_symlink():
        raise ContractError("P4 final target must not preexist")
    writer_start, writer_end = writer_window(model_begin, model_end)
    expected = set()
    when = writer_start
    while when <= writer_end:
        expected.add(when)
        when += timedelta(hours=12)
    outputs = {}
    # Entire contents are normalized/validated before any final file write.
    for wmo in lineage["station_wmo"]:
        pairs = sorted(
            ((int(Path(r["output_updat"]).parent.parent.name), Path(r["output_updat"]))
             for r in records if r["station_id"] == wmo),
            key=lambda item: item[0],
        )
        if [year for year, _ in pairs] != lineage["years_with_boundary_inputs"]:
            raise ContractError(f"P4 {wmo} raw UP annual years missing")
        first_header = None
        stamps = {}
        clipped_count = 0
        for year, path in pairs:
            header, blocks, clipped = _read_blocks(path, wmo)
            clipped_count += clipped
            if first_header is None:
                first_header = header
            real = set(lineage["source_and_cleaning_evidence"][year][wmo]["original_valid_utc_slots"])
            for stamp, block in blocks:
                if stamp.year != year:
                    raise ContractError(f"P4 {wmo} raw UP record outside declared calendar year")
                if stamp < writer_start or stamp > writer_end:
                    raise ContractError(f"P4 {wmo} raw UP contains unrequested original time")
                if stamp.strftime("%Y%m%d%H") not in real:
                    raise ContractError(f"P4 {wmo} UP record is cloned/unproven sounding")
                if stamp in stamps:
                    raise ContractError(f"P4 {wmo} duplicate native UP 6201 at {stamp}")
                stamps[stamp] = block
        if set(stamps) != expected:
            raise ContractError(f"P4 {wmo} missing or extra genuine native UP 00/12 records")
        lines = list(first_header)
        lines[5] = update_header_line(lines[5], model_begin, model_end)
        for instant in sorted(stamps):
            lines.extend(stamps[instant])
        outputs[wmo] = {
            "content": "\n".join(lines) + "\n",
            "soundings": len(stamps), "clipped_99level_profiles": clipped_count,
        }
    anchor_year = lineage["years_with_boundary_inputs"][0]
    year_csv = upperair_root / str(anchor_year) / "upperair_station_used_list.txt"
    with year_csv.open(encoding="utf-8", newline="") as stream:
        catalog = {row["id"][-5:]: row for row in csv.DictReader(stream)}
    if set(catalog) != set(outputs):
        raise ContractError("P4 candidate station metadata mismatches source WMO array")
    # No partial publication if preflight checks above fail.
    target.mkdir(parents=True, exist_ok=False)
    for wmo, item in sorted(outputs.items()):
        (target / f"up_{wmo}.dat").write_text(item["content"], encoding="utf-8")
    with (target / "stations.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=[
            "station_id", "station_name", "lat", "lon", "elev_m",
            "tz_hour", "source_file",
        ])
        writer.writeheader()
        for wmo, row in sorted(catalog.items()):
            writer.writerow({
                "station_id": wmo, "station_name": row["name"],
                "lat": row["lat"], "lon": row["lon"], "elev_m": row["elev_m"],
                "tz_hour": "0",
                "source_file": f"met/upperair/final/up_{wmo}.dat",
            })
    proof = {
        "status": "PRODUCED_UNVERIFIED",
        "scope": "P4_SOURCE_ONLY_CANDIDATE_NOT_ORIGINAL_PARITY",
        "original_parity": "NOT_RUN_THIS_GENERIC_CASE",
        "p4_to_g19": "NOT_RUN",
        "station_count": len(outputs),
        "stations_csv_sha256": sha256_file(target / "stations.csv"),
        "files": [
            {"wmo": wmo, "name": f"up_{wmo}.dat",
             "sha256": sha256_file(target / f"up_{wmo}.dat"),
             "soundings": item["soundings"],
             "clipped_99level_profiles": item["clipped_99level_profiles"]}
            for wmo, item in sorted(outputs.items())
        ],
        "model_utc": {"begin": model_begin.isoformat(), "end": model_end.isoformat()},
    }
    (target / "p4_candidate_manifest.json").write_text(
        json.dumps(proof, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return proof
