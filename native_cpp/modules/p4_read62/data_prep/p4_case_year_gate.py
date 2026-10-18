"""P4 #55: source-backed yearly identity and authentic 00/12 bracket admission.

Checks existing selector output; does not modify READ62 sounding QA, the
same-day/previous-day clones, FSL or C++ writer. Rejects before native UP
execution when the static CALMET upper-air station array or authentic AA/BB
calendar is unsupported. An acceptance here is only software/source lineage.
"""
from __future__ import annotations

import calendar
import csv
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

from native_cpp.orchestration.plan import ContractError
from .p4_case_d1 import sha256_file


def writer_window(begin: datetime, end: datetime) -> tuple[datetime, datetime]:
    """Include the exact original 00/12 UTC brackets, even across years."""
    if begin.minute or begin.second or end.minute or end.second or end <= begin:
        raise ContractError("P4 requires a positive whole-hour UTC interval")
    left = begin.replace(hour=(begin.hour // 12) * 12)
    right = end.replace(hour=(end.hour // 12) * 12)
    if right < end:
        right += timedelta(hours=12)
    return left, right


def boundary_years(begin: datetime, end: datetime) -> list[int]:
    lo, hi = writer_window(begin, end)
    return list(range(lo.year, hi.year + 1))


def _parse_slot(raw: str, year: int) -> datetime:
    if not isinstance(raw, str) or not re.fullmatch(r"\d{10}", raw):
        raise ContractError("original source 00/12 slot malformed")
    try:
        stamp = datetime.strptime(raw, "%Y%m%d%H")
    except ValueError as exc:
        raise ContractError("original UTC 00/12 slot calendar invalid") from exc
    if stamp.year != year or stamp.hour not in (0, 12):
        raise ContractError("original UTC 00/12 slot outside annual observed calendar")
    return stamp


def _hourly_brackets(begin: datetime, end: datetime):
    """Hour ending labels; no simulated 00/12 source or extrapolation."""
    for n in range(1, int((end - begin).total_seconds() / 3600) + 1):
        hour = begin + timedelta(hours=n)
        if hour.hour in (0, 12):
            left = hour - timedelta(hours=12)
            right = hour
        else:
            left = hour.replace(hour=(hour.hour // 12) * 12)
            right = left + timedelta(hours=12)
        yield hour, left, right


def admit_annual_source_lineage(records: list[dict], upperair_root: Path,
                                offline_archive_root: Path,
                                begin: datetime, end: datetime) -> dict:
    """Bind selected CSV, NOAA, QA, cleaned CSV and FSL before C++ execution.

    The source lists must be statically identical across boundary years.
    A missing authentic bracket blocks publishing rather than using cloned CSV.
    """
    if not records:
        raise ContractError("no selected P4 station records")
    expected_years = boundary_years(begin, end)
    archive = offline_archive_root.resolve(strict=True)
    grouped: dict[int, dict[str, dict]] = {}
    evidence: dict[str, dict] = {}
    authentic_slots: dict[str, set[datetime]] = {}
    identities: dict[str, tuple] = {}
    station_sets: list[set[str]] = []
    for year in expected_years:
        year_dir = upperair_root / str(year)
        audit_path = year_dir / "p4_station_selection_audit.json"
        csv_path = year_dir / "upperair_station_used_list.txt"
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        with csv_path.open(encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        chosen = audit.get("selected")
        if audit.get("year") != year or not isinstance(chosen, list) or not chosen:
            raise ContractError(f"P4 {year} selection has no authentic annual stations")
        if len(rows) != len(chosen):
            raise ContractError(f"P4 {year} selected CSV and annual QA count mismatch")
        selected = {}
        for s in chosen:
            sid = s.get("id")
            if not isinstance(sid, str) or not re.fullmatch(r"[A-Z0-9]{8,20}", sid):
                raise ContractError(f"P4 {year} source station identity malformed")
            if sid in selected:
                raise ContractError(f"P4 {year} duplicate selected source identity")
            selected[sid] = s
        row_ids = [r.get("id") for r in rows]
        if set(row_ids) != set(selected) or len(set(row_ids)) != len(row_ids):
            raise ContractError(f"P4 {year} CSV station set does not match QA audit")
        expected_slots = (366 if calendar.isleap(year) else 365) * 2
        grouped[year] = {}
        for row in rows:
            sid = row["id"]
            entry = selected[sid]
            wmo = sid[-5:]
            if not re.fullmatch(r"\d{5}", wmo):
                raise ContractError("P4 cannot map source to five-digit numeric WMO")
            raw_slots = entry.get("original_utc_slots")
            if not isinstance(raw_slots, list) or len(raw_slots) != len(set(raw_slots)):
                raise ContractError(f"P4 {year}/{sid} lacks immutable original slot evidence")
            slots = {_parse_slot(s, year) for s in raw_slots}
            good_count = int(entry["valid_original_slots"])
            if (good_count != len(slots)
                    or int(row["valid_original_slots"]) != good_count
                    or int(row["expected_slots"]) != expected_slots
                    or good_count * 5 <= expected_slots * 4):
                raise ContractError(f"P4 {year}/{sid} original >80% 00/12 gate mismatch")
            if (entry.get("site_type") != row.get("site_type")
                    or any(abs(float(entry[p]) - float(row[c])) > 1e-6
                           for p, c in (("source_lat", "source_lat"),
                                        ("source_lon", "source_lon"),
                                        ("effective_lat", "lat"),
                                        ("effective_lon", "lon")))):
                raise ContractError(f"P4 {year}/{sid} source/effective location mismatch")
            source = Path(row["raw_txt"])
            if source.is_symlink() or not source.is_file():
                raise ContractError("P4 source path missing or symlink")
            source = source.resolve(strict=True)
            if archive not in source.parents or source.name != sid + "-data.txt":
                raise ContractError("P4 NOAA source escaped required archived identity")
            sha = sha256_file(source)
            if sha != entry.get("raw_sha256"):
                raise ContractError(f"P4 {year}/{sid} source changed since annual selection/QA")
            fingerprint = (
                sid, row["name"], row["lat"], row["lon"], row["elev_m"],
                row["source_lat"], row["source_lon"], row["site_type"])
            old = identities.setdefault(wmo, fingerprint)
            if old != fingerprint:
                raise ContractError(f"P4 {year}/{wmo} changed real/effective station identity")
            original = authentic_slots.setdefault(wmo, set())
            if original.intersection(slots):
                raise ContractError(f"P4 {year}/{wmo} duplicate original slot timestamps")
            original.update(slots)
            # The existing preparer creates CSV clones. Record their lineage
            # as not authentic, never allow them to satisfy AA/BB.
            csv_dir = year_dir / (sid + "_igra_every_moment")
            profiles = sorted(csv_dir.glob(f"{wmo}_*.csv"))
            if not profiles:
                raise ContractError(f"P4 {year}/{wmo} no cleaned profiles")
            digests = []
            for f in profiles:
                stamp = f.stem.removeprefix(wmo + "_")
                instant = _parse_slot(stamp, year)
                digests.append({
                    "utc": stamp,
                    "original_observed": instant in slots,
                    "cleaned_csv_sha256": sha256_file(f),
                })
            fsl = year_dir / "igra2fsl" / (wmo + ".txt")
            grouped[year][wmo] = {
                "source_station_id": sid,
                "source_sha256": sha,
                "annual_audit_sha256": sha256_file(audit_path),
                "annual_station_csv_sha256": sha256_file(csv_path),
                "fsl_sha256": sha256_file(fsl),
                "original_valid_utc_slots": sorted(raw_slots),
                "cleaned_profiles": digests,
                "effective_station": {
                    "lat": row["lat"], "lon": row["lon"],
                    "source_lat": row["source_lat"], "source_lon": row["source_lon"],
                    "site_type": row["site_type"],
                },
            }
        station_sets.append(set(grouped[year]))
    if not station_sets or any(s != station_sets[0] for s in station_sets):
        raise ContractError("P4 selected upper-air station WMO set varies across years")
    if len(identities) != len(station_sets[0]):
        raise ContractError("P4 overlapping WMO source identity conflict")
    if len(records) != sum(len(v) for v in grouped.values()):
        raise ContractError("P4 generated annual job count != selected annual stations")
    for job in records:
        year = int(Path(job["output_updat"]).parent.parent.name)
        wmo = job["station_id"]
        if year not in grouped or wmo not in grouped[year]:
            raise ContractError("P4 unselected annual native station job")
        reference = grouped[year][wmo]
        if (job["source_station_id"] != reference["source_station_id"]
                or sha256_file(Path(job["input_fsl"])) != reference["fsl_sha256"]):
            raise ContractError("P4 annual job source/FSL identity mismatch")
    for wmo, slots in authentic_slots.items():
        for hour, a, b in _hourly_brackets(begin, end):
            if a not in slots or b not in slots:
                raise ContractError(
                    f"P4 {wmo} missing genuine AA/BB for hour-ending {hour.isoformat()}: "
                    f"{a.isoformat()} / {b.isoformat()} (cloned 00/12 not admissible)")
    return {
        "status": "INPUT_CHECKED_SOURCE_AND_BRACKETS_ONLY",
        "years_with_boundary_inputs": expected_years,
        "station_wmo": sorted(station_sets[0]),
        "hour_ending_count": int((end - begin).total_seconds() / 3600),
        "real_aa_bb_each_hour": True,
        "source_and_cleaning_evidence": grouped,
    }
