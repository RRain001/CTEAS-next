#!/usr/bin/env python3
"""Run SMERGE and monitor execution results.

Purpose:
- Execute: engine/vendor/bin/smerge.x smerge.inp
- Check run status via return code, log keywords, and output files.
"""

from __future__ import annotations

import csv
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from engine.core.paths import BIN_ROOT, VENDOR_BIN_DIR, case_path, current_case_name, current_project_path, resolve_executable
from engine.core.runner import run_binary


CASE_ROOT = current_project_path().resolve()
WORK_DIR = CASE_ROOT / "run" / "smerge"
SMERGE_INP = WORK_DIR / "smerge.inp"
RUNTIME_LOG = WORK_DIR / "smerge_runtime.log"
SURFACE_FINAL_DIR = CASE_ROOT / "met" / "surface" / "final"
SURFACE_FINAL_DAT = SURFACE_FINAL_DIR / "surf.dat"
SURFACE_STATIONS_CSV = SURFACE_FINAL_DIR / "stations.csv"


def set_case_paths(case_name: str | None) -> None:
    global CASE_ROOT, WORK_DIR, SMERGE_INP, RUNTIME_LOG, SURFACE_FINAL_DIR, SURFACE_FINAL_DAT, SURFACE_STATIONS_CSV
    if not case_name:
        return
    CASE_ROOT = case_path(case_name).resolve()
    WORK_DIR = CASE_ROOT / "run" / "smerge"
    SMERGE_INP = WORK_DIR / "smerge.inp"
    RUNTIME_LOG = WORK_DIR / "smerge_runtime.log"
    SURFACE_FINAL_DIR = CASE_ROOT / "met" / "surface" / "final"
    SURFACE_FINAL_DAT = SURFACE_FINAL_DIR / "surf.dat"
    SURFACE_STATIONS_CSV = SURFACE_FINAL_DIR / "stations.csv"


def parse_inp_assignment(inp_text: str, key: str) -> str | None:
    # match lines like: ! SURFDAT = /path/to/surf.dat !
    m = re.search(rf"!\s*{re.escape(key)}\s*=\s*([^!]+?)\s*!", inp_text, flags=re.IGNORECASE)
    if not m:
        return None
    return m.group(1).strip()


def resolve_inp_path(base_dir: Path, path_str: str | None, fallback: Path) -> Path:
    if not path_str:
        return fallback
    path = Path(path_str)
    if path.is_absolute():
        return path
    return (base_dir / path).resolve()


def parse_station_records(inp_text: str) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    current: dict[str, str] = {}

    for raw_line in inp_text.splitlines():
        for key in ("SFCMET", "IFSTN", "XELEV", "ASTZ"):
            m = re.search(rf"!\s*{re.escape(key)}\s*=\s*([^!]+?)\s*!", raw_line, flags=re.IGNORECASE)
            if m:
                current[key.lower()] = m.group(1).strip()
        if "!END!" in raw_line and current:
            if "ifstn" in current and "sfcmet" in current:
                records.append(current)
            current = {}

    return records


def parse_surface_station_metadata() -> dict[str, dict[str, str]]:
    meta: dict[str, dict[str, str]] = {}
    raw_dir = CASE_ROOT / "met" / "surface" / "isd_raw"
    for path in sorted(raw_dir.glob("surf_station_list_*.txt")):
        for idx, raw_line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines()):
            if idx == 0 or not raw_line.strip():
                continue
            parts = [part.strip() for part in raw_line.split(",")]
            if len(parts) < 5:
                continue
            station_full_id, name, lat, lon, elev_m = parts[:5]
            station_id = station_full_id[:6]
            meta.setdefault(
                station_id,
                {
                    "station_name": name,
                    "lat": lat,
                    "lon": lon,
                    "elev_m": elev_m,
                },
            )
    return meta


def parse_astz_hours(value: str) -> int:
    m = re.fullmatch(r"UTC([+-])(\d{2})(\d{2})", value.strip().upper())
    if not m:
        raise ValueError(f"Unsupported ASTZ format: {value}")
    sign = 1 if m.group(1) == "+" else -1
    hours = int(m.group(2))
    minutes = int(m.group(3))
    if minutes != 0:
        raise ValueError(f"Only whole-hour ASTZ is supported: {value}")
    return sign * hours


def publish_final_surface_outputs(inp_text: str, surfdat: Path) -> tuple[Path, Path]:
    if not surfdat.exists():
        raise FileNotFoundError(f"SURFDAT not found: {surfdat}")

    station_records = parse_station_records(inp_text)
    if not station_records:
        raise RuntimeError("No station records parsed from smerge.inp")
    station_meta = parse_surface_station_metadata()

    SURFACE_FINAL_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(surfdat, SURFACE_FINAL_DAT)

    with SURFACE_STATIONS_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["station_id", "station_name", "lat", "lon", "xelev_m", "tz_hour", "anem_m", "source_file"],
        )
        writer.writeheader()
        for rec in station_records:
            station_id = rec["ifstn"]
            meta = station_meta.get(station_id) or {}
            if not str(meta.get("lat", "")).strip() or not str(meta.get("lon", "")).strip():
                raise RuntimeError(
                    f"站点 {station_id} 缺少经纬度元数据: 未在 "
                    f"{CASE_ROOT / 'met' / 'surface' / 'isd_raw'}/surf_station_list_*.txt 中找到该站。"
                    "请确认下载步骤(含站点清单)已执行,且清单与当前案例的站点选择一致。"
                )
            source_path = resolve_inp_path(WORK_DIR, rec.get("sfcmet"), WORK_DIR / rec.get("sfcmet", ""))
            try:
                source_rel = str(source_path.relative_to(CASE_ROOT))
            except ValueError:
                source_rel = str(source_path)
            writer.writerow(
                {
                    "station_id": station_id,
                    "station_name": meta.get("station_name", station_id),
                    "lat": meta.get("lat", ""),
                    "lon": meta.get("lon", ""),
                    "xelev_m": rec.get("xelev") or meta.get("elev_m", ""),
                    "tz_hour": parse_astz_hours(rec.get("astz", "UTC+0000")),
                    "anem_m": "10.0",
                    "source_file": source_rel,
                }
            )

    return SURFACE_FINAL_DAT, SURFACE_STATIONS_CSV


def fill_missing_cloud_cover_in_surfdat(path: Path) -> tuple[int, int]:
    """Replace missing opaque cloud cover (9999) with clear sky (0).

    CALMET aborts if all surface stations have missing cloud cover for an
    hour. The final published SURF.DAT is the stable interface into CALMET,
    so apply the fallback here instead of mutating SMERGE generic inputs.
    """
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    if len(lines) < 7:
        raise ValueError(f"Invalid SURF.DAT header: {path}")

    header_parts = lines[5].split()
    if len(header_parts) < 9:
        raise ValueError(f"Cannot parse NSSTA from SURF.DAT header: {path}")
    nssta = int(header_parts[-1])
    data_start = 6 + nssta
    if data_start >= len(lines):
        raise ValueError(f"SURF.DAT has no data records: {path}")

    fixed_values = 0
    fixed_hours = 0
    out_lines = lines[:data_start]
    idx = data_start

    while idx < len(lines):
        out_lines.append(lines[idx])
        idx += 1
        if idx + nssta > len(lines):
            raise ValueError(f"Truncated SURF.DAT station block near line {idx + 1}: {path}")

        block_changed = False
        for _ in range(nssta):
            raw = lines[idx]
            idx += 1
            parts = raw.split()
            if len(parts) != 8:
                raise ValueError(f"Unexpected SURF.DAT data line format at line {idx}: {raw!r}")

            ws = float(parts[0])
            wd = float(parts[1])
            iceil = int(parts[2])
            icc = int(parts[3])
            tempk = float(parts[4])
            irh = int(parts[5])
            pres = float(parts[6])
            ipcode = int(parts[7])

            if icc == 9999:
                icc = 0
                fixed_values += 1
                block_changed = True

            out_lines.append(
                f"{ws:9.3f} {wd:8.3f} {iceil:4d} {icc:4d} {tempk:8.3f} {irh:4d} {pres:8.3f} {ipcode:4d}"
            )

        if block_changed:
            fixed_hours += 1

    path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    return fixed_values, fixed_hours


def find_keywords(text: str, keywords: list[str]) -> list[str]:
    found = []
    lower = text.lower()
    for kw in keywords:
        if kw.lower() in lower:
            found.append(kw)
    return found


def main() -> int:
    case_name = current_case_name()
    set_case_paths(case_name)
    try:
        resolve_executable("smerge")
    except (FileNotFoundError, ValueError) as exc:
        print(f"[ERROR] {exc}")
        return 1
    if not SMERGE_INP.exists():
        print(f"[ERROR] smerge.inp not found: {SMERGE_INP}")
        return 1

    inp_text = SMERGE_INP.read_text(encoding="utf-8", errors="ignore")
    runlst_path_str = parse_inp_assignment(inp_text, "RUNLST")
    surfdat_path_str = parse_inp_assignment(inp_text, "SURFDAT")

    # fallback if keys are missing
    runlst = resolve_inp_path(WORK_DIR, runlst_path_str, WORK_DIR / "smerge.lst")
    surfdat = resolve_inp_path(WORK_DIR, surfdat_path_str, WORK_DIR / "surf.dat")

    # clear old runtime log
    if RUNTIME_LOG.exists():
        RUNTIME_LOG.unlink()

    start_time = datetime.now()

    with RUNTIME_LOG.open("w", encoding="utf-8") as logf:
        proc = run_binary(
            "smerge",
            str(SMERGE_INP),
            cwd=WORK_DIR,
            stdout=logf,
            stderr=subprocess.STDOUT,
            text=True,
            bin_root=BIN_ROOT,
            legacy_bin_root=VENDOR_BIN_DIR,
        )

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    # Load logs for checks
    runtime_text = RUNTIME_LOG.read_text(encoding="utf-8", errors="ignore") if RUNTIME_LOG.exists() else ""
    runlst_text = runlst.read_text(encoding="utf-8", errors="ignore") if runlst.exists() else ""
    combined = runtime_text + "\n" + runlst_text

    err_keywords = ["fatal", "error", "abort", "segmentation fault", "forrtl", "cannot open"]
    warn_keywords = ["warning"]
    found_err = find_keywords(combined, err_keywords)
    found_warn = find_keywords(combined, warn_keywords)

    surf_exists = surfdat.exists()
    surf_size = surfdat.stat().st_size if surf_exists else 0
    runlst_exists = runlst.exists()
    runlst_size = runlst.stat().st_size if runlst_exists else 0

    # Final status
    ok = proc.returncode == 0 and surf_exists and surf_size > 0 and not found_err
    if ok:
        final_dat, final_csv = publish_final_surface_outputs(inp_text, surfdat)
        fixed_values, fixed_hours = fill_missing_cloud_cover_in_surfdat(final_dat)
        _ = (end_time, duration, runlst, runlst_size, final_csv, fixed_values, fixed_hours)
        print("数据结构处理完成")
        return 0

    print("[RESULT] SMERGE run failed or is suspicious. Check logs:")
    print(f"         - {RUNTIME_LOG}")
    print(f"         - {runlst}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
