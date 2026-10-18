"""#56 P5 D4 strict hourly source quality ledger for original-compatible SURF 2.1.

Independent *observational-data QA*, not SMERGE numerical reconstruction.
The thresholds mirror the already-frozen P6 read_surface_dynamic.hpp validity
rules. Store boolean flags, never replicate/export the original hourly weather.
The legacy published ICC=9999 -> 0 fallback is explicitly distinguished.
"""
from __future__ import annotations

from datetime import datetime, timedelta
import math
from pathlib import Path

from native_cpp.orchestration.plan import ContractError

FLAGS = ("wind", "temperature", "humidity", "pressure", "ceiling",
         "cloud", "precipitation_code")


def _timestamp(parts: list[str], *, end: bool) -> datetime:
    try:
        year, jday, hour, second = map(int, parts)
        if not 1900 <= year <= 2100 or not 0 <= hour <= 24 or second != 0:
            raise ValueError("invalid UTC Julian fields")
        if hour == 24 and not end:
            raise ValueError("invalid starting hour 24")
        dt = datetime(year, 1, 1) + timedelta(days=jday - 1, hours=hour)
        if not 1 <= jday <= (datetime(year + 1, 1, 1) -
                            datetime(year, 1, 1)).days:
            raise ValueError("invalid calendar day")
        return dt
    except (ValueError, OverflowError) as exc:
        raise ContractError("P5 D4 SURF invalid UTC Julian hour") from exc


def _bounds(row: str) -> tuple[datetime, datetime]:
    words = row.split()
    if len(words) != 8:
        raise ContractError("P5 D4 SURF hourly UTC record must have eight fields")
    a, b = _timestamp(words[:4], end=False), _timestamp(words[4:], end=True)
    if b - a != timedelta(hours=1):
        raise ContractError("P5 D4 SURF hour record not exactly one hour")
    return a, b


def _station_flags(line: str) -> tuple[dict[str, bool], tuple]:
    parts = line.split()
    if len(parts) != 8:
        raise ContractError("P5 D4 SURF station observation requires eight fields")
    try:
        ws, wd, tmp, pre = (float(parts[i]) for i in (0, 1, 4, 6))
        ceiling, cloud, rh, code = (int(parts[i]) for i in (2, 3, 5, 7))
    except ValueError as exc:
        raise ContractError("P5 D4 SURF invalid numeric observation") from exc
    if any(not math.isfinite(n) or abs(n) > 9999.99 for n in (ws, wd, tmp, pre)):
        raise ContractError("P5 D4 SURF observation out of supported range")
    valid = {
        "wind": 0 <= ws < 9998 and 0 <= wd <= 360 and wd < 9998,
        "temperature": 0 < tmp < 9998,
        "humidity": 0 <= rh <= 100 and rh < 9998,
        "pressure": 0 < pre < 9998,
        "ceiling": 0 <= ceiling < 9998,
        "cloud": 0 <= cloud <= 10 and cloud < 9998,
        "precipitation_code": 0 <= code < 9998,
    }
    return valid, (ws, wd, ceiling, cloud, tmp, rh, pre, code)


def _parse(path: Path, *, max_hours: int = 200000,
           max_station_hours: int = 4800000) -> tuple[list[str], list[dict]]:
    if path.is_symlink() or not path.is_file() or not path.stat().st_size:
        raise ContractError("P5 D4 SURF absent, empty or symlinked")
    with path.open(encoding="utf-8") as fd:
        first = fd.readline()
        if first[:16].strip() != "SURF.DAT" or first[16:32].strip() != "2.1":
            raise ContractError("P5 D4 SURF identity/version not 2.1")
        try:
            comment_count = int(fd.readline().strip())
        except ValueError as exc:
            raise ContractError("P5 D4 invalid SURF comment count") from exc
        if not 0 <= comment_count <= 10000:
            raise ContractError("P5 D4 excessive SURF comment count")
        for _ in range(comment_count):
            if not fd.readline():
                raise ContractError("P5 D4 truncated SURF comments")
        if fd.readline().strip() != "NONE" or fd.readline().strip() != "UTC+0000":
            raise ContractError("P5 D4 SURF unsupported PMAP/timezone")
        header = fd.readline().split()
        if len(header) != 9:
            raise ContractError("P5 D4 SURF metadata schema invalid")
        try:
            nss = int(header[8])
        except ValueError as exc:
            raise ContractError("P5 D4 SURF station count invalid") from exc
        if not 1 <= nss <= max_station_hours:
            raise ContractError("P5 D4 SURF station count out of budget")
        begin = _timestamp(header[:4], end=False)
        end = _timestamp(header[4:8], end=True)
        seconds = (end - begin).total_seconds()
        if seconds < 3600 or seconds % 3600:
            raise ContractError("P5 D4 SURF header has non-hourly duration")
        nh = int(seconds // 3600)
        if nh > max_hours or nh * nss > max_station_hours:
            raise ContractError("P5 D4 SURF hour-station budget exceeded")
        station_ids = []
        for _ in range(nss):
            try:
                line = fd.readline().split()
                if len(line) != 1 or int(line[0]) <= 0:
                    raise ValueError("bad IFSTN row")
                sid = str(int(line[0]))
            except ValueError as exc:
                raise ContractError("P5 D4 SURF station ID invalid") from exc
            station_ids.append(sid)
        if len(set(station_ids)) != nss:
            raise ContractError("P5 D4 SURF duplicate station IFSTN")
        result = []
        current = begin
        for _ in range(nh):
            row = fd.readline()
            if not row:
                raise ContractError("P5 D4 SURF missing hourly record")
            hstart, hend = _bounds(row)
            if hstart != current:
                raise ContractError("P5 D4 SURF missing/reordered/overlapping UTC hour")
            observations = []
            for sid in station_ids:
                line = fd.readline()
                if not line:
                    raise ContractError("P5 D4 SURF truncated station block")
                flags, values = _station_flags(line)
                observations.append({"ifstn": sid, "valid": flags, "values": values})
            result.append({"utc_end": hend.strftime("%Y%m%d-%H%M%S"),
                           "station_observations": observations})
            current = hend
        if current != end or any(s.strip() for s in fd):
            raise ContractError("P5 D4 SURF endpoint/trailing-record mismatch")
    return station_ids, result


def inspect_pair(raw: Path, published: Path, *, expected_ids: list[str],
                 expected_begin: str, expected_end: str,
                 reader: dict) -> dict:
    """Fail closed if either SURF differs beyond legacy ICC missing fallback.

    Returns a per-hour/per-station *validity bitmask* for P5 -> #42; source
    observations themselves are never written into evidence.
    """
    raw_ids, raw_hours = _parse(raw)
    final_ids, final_hours = _parse(published)
    if raw_ids != expected_ids or final_ids != expected_ids:
        raise ContractError("P5 D4 hourly quality station order mismatch")
    begin = datetime.strptime(expected_begin, "%Y%m%d-%H%M%S")
    end = datetime.strptime(expected_end, "%Y%m%d-%H%M%S")
    count = int((end - begin).total_seconds() / 3600)
    if begin + timedelta(hours=count) != end or count < 1:
        raise ContractError("P5 D4 hourly quality research time not whole UTC hours")
    if len(raw_hours) != count or len(final_hours) != count:
        raise ContractError("P5 D4 hourly quality SURF count outside requested time")
    if raw_hours[0]["utc_end"] != (begin + timedelta(hours=1)).strftime("%Y%m%d-%H%M%S"):
        raise ContractError("P5 D4 hourly quality first hour mismatch")
    if raw_hours[-1]["utc_end"] != expected_end:
        raise ContractError("P5 D4 hourly quality last hour mismatch")
    summaries = {"raw": {k: 0 for k in FLAGS},
                 "published": {k: 0 for k in FLAGS}}
    coverage = {"populated_station_hours": 0, "missing_station_hours": 0,
                "valid_wind_station_hours": 0}
    fallback = 0
    ledger = []
    for a, b in zip(raw_hours, final_hours):
        if a["utc_end"] != b["utc_end"]:
            raise ContractError("P5 D4 hourly quality raw/published clock mismatch")
        hour = {"utc_end": a["utc_end"], "stations": []}
        for source, final in zip(a["station_observations"], b["station_observations"]):
            if source["ifstn"] != final["ifstn"]:
                raise ContractError("P5 D4 hourly quality station identity mismatch")
            before, after = source["values"], final["values"]
            if before[:3] != after[:3] or before[4:] != after[4:]:
                raise ContractError("P5 D4 published SURF changed meteorology beyond cloud fallback")
            changed = before[3] == 9999 and after[3] == 0
            if before[3] != after[3] and not changed:
                raise ContractError("P5 D4 unapproved published cloud modification")
            fallback += int(changed)
            original_flags, final_flags = source["valid"], final["valid"]
            if (original_flags["temperature"] or original_flags["humidity"] or
                    original_flags["pressure"]):
                coverage["populated_station_hours"] += 1
            else:
                coverage["missing_station_hours"] += 1
            coverage["valid_wind_station_hours"] += int(original_flags["wind"])
            for flag in FLAGS:
                summaries["raw"][flag] += int(original_flags[flag])
                summaries["published"][flag] += int(final_flags[flag])
            hour["stations"].append({
                "ifstn": source["ifstn"], "raw_valid": original_flags,
                "published_valid": final_flags, "cloud_fallback": changed,
            })
        ledger.append(hour)
    for key in coverage:
        if coverage[key] != reader.get(key):
            raise ContractError("P5 D4 per-hour validity counts disagree with independent P6 source reader")
    return {
        "status": "PASS_SCOPED_PER_HOUR_FLAG_AUDIT_NOT_G19",
        "flag_semantics": "P6 frozen read_surface_dynamic validity thresholds",
        "utc_hour_ending": "(BEGIN,END]",
        "hourly_station_flags": ledger,
        "raw_valid_station_hours_by_field": summaries["raw"],
        "published_valid_station_hours_by_field": summaries["published"],
        "raw_to_published_cloud_fallback_count": fallback,
        "raw_to_published_other_meteorology_changes": 0,
        "reader_aggregate_count_agreement": True,
        "weather_values_exported": False,
    }
