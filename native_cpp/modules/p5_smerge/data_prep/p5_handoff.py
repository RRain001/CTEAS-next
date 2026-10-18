"""#56 P5 -> #42 D4 *source-only* handoff evidence, not a G19 execution.

No meteorological numerical algorithm is reimplemented here. The shared #42
case authority, existing P5 producer, station index and independent compiled
P6 SURF source-reader results are bound with SHA and cardinality checks.
"""
from __future__ import annotations

import csv
from datetime import datetime, timedelta
import hashlib
from pathlib import Path
import re

from native_cpp.orchestration.case_admission import admit_case, verify_immutable
from native_cpp.orchestration.plan import ContractError


def sha256(path: Path) -> str:
    if path.is_symlink() or not path.is_file() or path.stat().st_size <= 0:
        raise ContractError(f"P5 D4 output not a regular nonempty file: {path}")
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_station_index(path: Path) -> list[dict]:
    if path.is_symlink() or not path.is_file():
        raise ContractError("P5 D4 station CSV absent or symlinked")
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        mandatory = {"station_id", "station_name", "lat", "lon", "xelev_m",
                     "tz_hour", "anem_m", "source_file"}
        if reader.fieldnames is None or not mandatory.issubset(reader.fieldnames):
            raise ContractError("P5 D4 published station index schema invalid")
        rows = list(reader)
    if not rows or len(rows) != len({r["station_id"] for r in rows}):
        raise ContractError("P5 D4 missing/duplicate published surface station ID")
    return rows


def _source_reader_stats(value: dict) -> dict:
    if value.get("source_reader") != "PASS_SCOPED_INPUT_ONLY":
        raise ContractError("P5 D4 requires previously passed independent P6 source-only reader")
    line = value.get("stdout_tail", "")
    if not isinstance(line, str) or not re.search(
            r"PASS_P6G_REAL_NOAA_NATIVE_SURF_SOURCE_HOURLY\b", line):
        raise ContractError("P5 D4 source-reader proof missing")
    fields = {}
    for k in ("HOURS", "NSSTA", "POPULATED_STATION_HOURS",
              "MISSING_STATION_HOURS", "VALID_WIND_STATION_HOURS"):
        matches = re.findall(r"(?:^|\s)" + k + r"=(\d+)(?:\s|$)", line)
        if len(matches) != 1:
            raise ContractError(f"P5 D4 ambiguous source-reader metric: {k}")
        fields[k.lower()] = int(matches[0])
    ids = re.findall(r"(?:^|\s)SS_IDS=([0-9,]+)(?:\s|$)", line)
    if len(ids) != 1:
        raise ContractError("P5 D4 independent source reader station list missing")
    fields["ordered_ifstn"] = ids[0].split(",")
    if (fields["hours"] < 1 or fields["nssta"] < 1 or
            fields["populated_station_hours"] + fields["missing_station_hours"]
                != fields["hours"] * fields["nssta"] or
            fields["valid_wind_station_hours"] > fields["hours"] * fields["nssta"]):
        raise ContractError("P5 D4 source-reader completeness count inconsistent")
    return fields


def build_p5_handoff(case: Path, producer: dict, reader: dict) -> dict:
    """Freeze the actual source/coordinate/IFSTN/time evidence to hand to #42.

    Does not claim the other four modules exist; no dynamic met.inp is created.
    Does not classify missing cloud coverage as physically measured.
    """
    admission = admit_case(case / "case.yaml")
    root = admission.case_path.parent
    if root.resolve() != case.resolve():
        raise ContractError("P5 D4 case authority differs from output root")
    if producer.get("case_name") != admission.case_name:
        raise ContractError("P5 D4 case producer name differs from admitted B0 case")
    for key, expected in (
        ("case_sha256", admission.case_sha256),
        ("grid_sha256", admission.grid_sha256),
        ("research_time_sha256", admission.time_sha256),
    ):
        if producer.get(key) != expected:
            raise ContractError("P5 D4 source evidence immutable B0 SHA mismatch: " + key)
    if producer.get("P5_NATIVE_SURF") != "PRODUCED_UNVERIFIED":
        raise ContractError("P5 D4 needs actual native SURF producer output")
    first = datetime.strptime(admission.research_begin, "%Y%m%d-%H%M%S")
    last = datetime.strptime(admission.research_end, "%Y%m%d-%H%M%S")
    hours = int((last - first) / timedelta(hours=1))
    if first + timedelta(hours=hours) != last or hours < 1:
        raise ContractError("P5 D4 UTC time window is not a whole-hour ending interval")
    source_stats = _source_reader_stats(reader)
    global_aliases = producer.get("global_ifstn")
    ids = producer.get("ordered_ifstn")
    if not isinstance(global_aliases, dict) or not global_aliases or not isinstance(ids, list):
        raise ContractError("P5 D4 source station alias map missing")
    if (len(ids) != len(global_aliases) or len(ids) != len(set(ids)) or
            set(ids) != set(global_aliases.values()) or
            source_stats["ordered_ifstn"] != ids or
            source_stats["nssta"] != len(ids) or source_stats["hours"] != hours):
        raise ContractError("P5 D4 original source reader versus P5 station/time mismatch")
    native = root / "run/smerge/surf.dat"
    published = root / "met/surface/final/surf.dat"
    stations_path = root / "met/surface/final/stations.csv"
    if (sha256(native) != producer.get("raw_native_surf_sha256") or
            sha256(published) != producer.get("published_surf_sha256")):
        raise ContractError("P5 D4 raw versus published SURF source custody changed")
    index = _read_station_index(stations_path)
    if [r["station_id"] for r in index] != ids:
        raise ContractError("P5 D4 published stations.csv order differs from reader")
    produced_shas = producer.get("produced_output_sha256", {})
    if (not isinstance(produced_shas, dict) or
            produced_shas.get("met/surface/final/stations.csv") != sha256(stations_path)):
        raise ContractError("P5 D4 published station index SHA mismatch")
    # A station entry is a producer-owned GENERIC source, never a caller
    # controlled absolute path, old current case, or unverified out-of-case
    # file. Its bytes must be bound to the same P5 producer SHA ledger.
    for station in index:
        raw_file = Path(station["source_file"])
        if (raw_file.is_absolute() or ".." in raw_file.parts or
                not raw_file.parts[:3] == ("met", "surface", "isd2smerge_ready")):
            raise ContractError("P5 D4 untrusted GENERIC station source path")
        source_path = root / raw_file
        if (produced_shas.get(raw_file.as_posix()) is None or
                sha256(source_path) != produced_shas[raw_file.as_posix()]):
            raise ContractError("P5 D4 station GENERIC source SHA mismatch")
    annual = producer.get("years")
    if not isinstance(annual, list) or len(annual) == 0:
        raise ContractError("P5 D4 annual original NOAA station selection missing")
    expected_years = set(range(first.year, last.year + 1))
    if {y.get("year") for y in annual} != expected_years:
        raise ContractError("P5 D4 expected calendar selection years not equal original research window")

    station_metadata = {row["station_id"]: row for row in index}
    annual_records = []
    consistent_locations: dict[str, tuple] = {}
    for annual_year in annual:
        year, selected, primary = annual_year["year"], annual_year["stations"], annual_year["primary_sid"]
        if {row["ifstn"] for row in selected} != set(ids):
            raise ContractError("P5 D4 annual original source identities drifted")
        if [row["sid"] for row in selected if row["role"] == "COMPLETE_FILL_AND_CALM_REPLACE"] != [primary]:
            raise ContractError("P5 D4 annual primary source/wind treatment disagreement")
        station_records = []
        for row in selected:
            sid, ifstn = row["sid"], row["ifstn"]
            if global_aliases.get(sid) != ifstn:
                raise ContractError("P5 D4 original SID to IFSTN mapping unstable")
            pair = (tuple(row["source_latlon"]), tuple(row["effective_latlon"]), row["relocated"])
            if ifstn in consistent_locations and consistent_locations[ifstn] != pair:
                raise ContractError("P5 D4 source/effective location shifted across years")
            consistent_locations[ifstn] = pair
            meta = station_metadata[ifstn]
            if (abs(float(meta["lat"]) - pair[1][0]) > 1e-8 or
                    abs(float(meta["lon"]) - pair[1][1]) > 1e-8):
                raise ContractError("P5 D4 published coordinates differ from effective source station")
            for name in ("full_isd", "isd_lite"):
                evidence = row[name]
                if sha256(Path(evidence["path"])) != evidence["sha256"]:
                    raise ContractError("P5 D4 original NOAA source SHA changed")
            station_records.append({
                "source_station_id": sid,
                "ifstn": ifstn,
                "role": row["role"],
                "relocated": row["relocated"],
                "source_latlon": list(row["source_latlon"]),
                "effective_latlon": list(row["effective_latlon"]),
                "annual_calendar_hours": row["expected_hours"],
                "full_isd_original_hours": row["full_isd_raw_hours_reported"],
                "isd_lite_original_hours": row["isd_lite_raw_hours_reported"],
                "original_isd_sha256": row["full_isd"]["sha256"],
                "original_isd_lite_sha256": row["isd_lite"]["sha256"],
            })
        annual_records.append({
            "year": year, "mode": annual_year["mode"],
            "primary_sid": primary,
            "selection_manifest_sha256": annual_year["selection_manifest"]["sha256"],
            "stations": sorted(station_records, key=lambda r: ids.index(r["ifstn"])),
        })
    # The two published source forms are deliberately distinct: the legacy
    # cloud-cover fallback is not part of the original Fortran byte parity.
    verify_immutable(admission)
    return {
        "contract": "CTEAS_NEXT_P5_TO_ISSUE42_D4_SOURCE_HANDOFF_V1",
        "status": "PASS_SCOPED_SOURCE_ONLY_HANDOFF_NOT_G19",
        "producer_issue": 56,
        "consumer_issue": 42,
        "case_name": admission.case_name,
        "case_yaml_sha256": admission.case_sha256,
        "grid_cmn_sha256": admission.grid_sha256,
        "research_time_sha256": admission.time_sha256,
        "research_begin_utc": admission.research_begin,
        "research_end_utc": admission.research_end,
        "hour_semantics": "(BEGIN,END] SMERGE hour-ending",
        "hour_ending_records": hours,
        "hourly_record_count_proven_by_independent_source_reader": True,
        "per_hour_field_quality": "NOT_EXPORTED_ISSUE42_G19_MUST_AUDIT",
        "utm_grid": producer["grid"],
        "ordered_ifstn": ids,
        "station_index": [{
            "ifstn": r["station_id"],
            "name": r["station_name"],
            "effective_lat": float(r["lat"]), "effective_lon": float(r["lon"]),
            "xelev_m": r["xelev_m"], "timezone_hours": r["tz_hour"],
            "anemometer_height_m": r["anem_m"], "generic_source_file": r["source_file"],
        } for r in index],
        "annual_noaa_selections": annual_records,
        "source_reader_coverage_totals": source_stats,
        "raw_native_surf": {"path": str(native.relative_to(root)),
                            "sha256": sha256(native), "fortran_byte_parity": "SEPARATE_D3_EVIDENCE"},
        "published_surf": {"path": str(published.relative_to(root)),
                           "sha256": sha256(published),
                           "cloud_fallback": "MAY_DIFFER_FROM_RAW_ORIGINAL"},
        "stations_csv": {"path": str(stations_path.relative_to(root)), "sha256": sha256(stations_path)},
        "P5_TO_G19": "NOT_RUN",
        "P6_NUMERICAL": "NOT_RUN",
        "science_acceptance": False,
        "handoff_validated": True,
    }
