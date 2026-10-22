#!/usr/bin/env python3
"""S4-R1c7c: source-exact real NOAA station columns and post-INTER2 grid.

This is an independent, write-only Fortran oracle. No oracle wind enters C++.
Never infer invalid station identity from a zero wind or remove station columns.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess
import tempfile

ORIGINAL_BLOB = "437f43bb7f0e51a1919e56664663e1a046986ed0"
PRE_NAME = "s4r1c7c-original-before-inter2.bin"
POST_NAME = "s4r1c7c-original-after-inter2.bin"
NX, NY, NZ, NS, NU, HOURS = 82, 85, 9, 2, 1, 6
STATIONS = NS + NU
HEADER = struct.Struct("<6i")
STATION_DATA = struct.Struct("<" + str(2 * NZ * STATIONS) + "f")
GRID_DATA = struct.Struct("<" + str(2 * NX * NY * NZ) + "f")
FIRST_HOUR = datetime(2022, 6, 1, 1, tzinfo=timezone.utc)

# Only append tracing routines, never replace any original calculation.
HELPER = r"""
c --- S4-R1c7c original DIAGNO US/VS immediately before INTER2
      subroutine s4c7c_before
      include 'params.met'
      include 'gen.met'
      include 'grid.met'
      include 'd1.met'
      integer k,l
      logical opened
      save opened
      data opened/.false./
      if(.not.opened)then
         open(93,file='s4r1c7c-original-before-inter2.bin',
     1        form='unformatted',access='stream',status='replace')
         opened=.true.
      endif
      write(93) 51,ndathrb,nsecb,nx,ny,nz
      write(93) ((us(k,l),l=1,3),k=1,nz)
      write(93) ((vs(k,l),l=1,3),k=1,nz)
      return
      end
c --- S4-R1c7c original DIAGNO U/V immediately after both INTER2
      subroutine s4c7c_after
      include 'params.met'
      include 'gen.met'
      include 'grid.met'
      include 'd1.met'
      integer i,j,k
      logical opened
      save opened
      data opened/.false./
      if(.not.opened)then
         open(92,file='s4r1c7c-original-after-inter2.bin',
     1        form='unformatted',access='stream',status='replace')
         opened=.true.
      endif
      write(92) 52,ndathrb,nsecb,nx,ny,nz
      write(92) (((u(i,j,k),i=1,nx),j=1,ny),k=1,nz)
      write(92) (((v(i,j,k),i=1,nx),j=1,ny),k=1,nz)
      return
      end
"""


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source(path: Path) -> list[str]:
    actual = subprocess.run(
        ["git", "hash-object", str(path)], check=True,
        capture_output=True, text=True
    ).stdout.strip()
    if actual != ORIGINAL_BLOB:
        raise ValueError("original CALMET blob changed: " + actual)
    lines = path.read_text().splitlines(keepends=True)
    if not (
        lines[6054].strip() == "CALL INTER2(US,NWIND,UTMXST,UTMYST,"
        and lines[6058].strip() == "CALL INTER2(VS,NWIND,UTMXST,UTMYST,"
        and lines[6071].strip() == "ENDIF"
        and "Lake breeze region" in lines[6075]
    ):
        raise ValueError("pinned original INTER2 source anchors drifted")
    return lines


def prepare(vendor: Path, destination: Path, receipt: Path) -> None:
    lines = source(vendor)
    # Both offsets refer to UNMODIFIED source, not sequentially shifted lines.
    patched = (
        "".join(lines[:6054])
        + "      call s4c7c_before\n"
        + "".join(lines[6054:6072])
        + "      call s4c7c_after\n"
        + "".join(lines[6072:])
        + HELPER
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(patched)
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps({
        "status": "PINNED_ORIGINAL_INTER2_WRITE_ONLY_PREPARED",
        "original_blob": ORIGINAL_BLOB,
        "original_sha256": sha(vendor),
        "instrumented_sha256": sha(destination),
        "source_anchor_before_first_inter2": 6055,
        "source_anchor_after_both_inter2": 6072,
        "input_station_columns": STATIONS,
        "scientific_result": "NOT_RUN",
        "native_sparse_inter2": "NOT_ACCEPTED",
        "p5_wind_mask": "UNCHANGED",
    }, indent=2, sort_keys=True) + "\n")
    print("S4R1C7C_ORIGINAL_SOURCE_PIN_AND_WRITE_ONLY=PASS")


def unpack_records(path: Path, marker: int, payload: struct.Struct) -> list[tuple[int, tuple[float, ...]]]:
    raw = path.read_bytes()
    record_bytes = HEADER.size + payload.size
    if len(raw) != HOURS * record_bytes:
        raise ValueError(f"original {path.name} has incorrect six-hour record size")
    result = []
    for hour in range(HOURS):
        offset = hour * record_bytes
        tag, packed, secs, nx, ny, nz = HEADER.unpack_from(raw, offset)
        if (tag, secs, nx, ny, nz) != (marker, 0, NX, NY, NZ):
            raise ValueError(f"original {path.name} header/matrix drift at {hour}")
        start = FIRST_HOUR + timedelta(hours=hour)
        expected = start.year * 100000 + start.timetuple().tm_yday * 100 + start.hour
        if packed != expected:
            raise ValueError(f"original {path.name} UTC clock drift at {hour}: {packed} != {expected}")
        vals = payload.unpack_from(raw, offset + HEADER.size)
        if not all(math.isfinite(x) for x in vals):
            raise ValueError(f"nonfinite original {path.name} values at hour {hour}")
        result.append((packed, vals))
    return result


def verify(
    vendor: Path, pristine: Path, scratch: Path, pre: Path, post: Path,
    station_oracle: Path, report: Path
) -> None:
    source(vendor)
    if sha(pristine) != sha(scratch):
        raise ValueError("write-only INTER2 instrumented original MET.DAT differs from pristine")
    original = json.loads(station_oracle.read_text())
    if (
        original.get("status") != "PASS_ORIGINAL_STATION_PROFILE_REFERENCE_ONLY"
        or original.get("original_ELUSTR2_SIMILT_call_events") != 8
        or original.get("original_byte_identical") is not True
        or len(original.get("original_events", [])) != 8
    ):
        raise ValueError("independent original STHEOR event oracle absent")
    stations = unpack_records(pre, 51, STATION_DATA)
    fields = unpack_records(post, 52, GRID_DATA)
    if [x[0] for x in stations] != [x[0] for x in fields]:
        raise ValueError("original pre/post INTER2 hour keys differ")

    # Cross-check SAME original first-hour station SIMILT against its distinct
    # write-only station array immediately before INTER2. No source rewrites.
    first = original["original_events"][0]
    ordinal = first["original_SIMILT_station_ordinal"]
    if not 1 <= ordinal <= NS:
        raise ValueError("invalid source SIMILT station ordinal")
    observed = first["original_profile_uv_mps"]
    uv = stations[0][1]
    max_station_residual = 0.0
    for k in range(NZ):
        for component in range(2):
            array_index = component * NZ * STATIONS + k * STATIONS + ordinal - 1
            reference = float(observed[2 * k + component])
            delta = abs(uv[array_index] - reference)
            max_station_residual = max(max_station_residual, delta)
    if max_station_residual > 2e-5:
        raise ValueError("original SIMILT column changed before INTER2")

    by_hour = []
    post_nonzero = 0
    post_negative = 0
    for hour, ((packed, profiles), (_, grid)) in enumerate(zip(stations, fields, strict=True)):
        nonzero = sum(1 for x in grid if 1e-8 < abs(x) < 900)
        negative = sum(x < -1e-8 for x in grid)
        post_nonzero += nonzero
        post_negative += negative
        # Report both SS/US separately. >900 is an observation only, not a
        # hard-coded missing/calm interpretation.
        columns = []
        for idx in range(STATIONS):
            u = [profiles[k * STATIONS + idx] for k in range(NZ)]
            v = [profiles[NZ * STATIONS + k * STATIONS + idx] for k in range(NZ)]
            columns.append({
                "source_ordinal_1based": idx + 1,
                "role": "SS" if idx < NS else "US",
                "first_level_u_mps": u[0],
                "first_level_v_mps": v[0],
                "values_abs_ge_900_diagnostic_only": sum(abs(x) >= 900 for x in u + v),
                "levels_with_both_abs_lt_900_diagnostic_only": sum(
                    abs(x) < 900 and abs(y) < 900 for x, y in zip(u, v, strict=True)
                ),
            })
        by_hour.append({
            "utc_start": (FIRST_HOUR + timedelta(hours=hour)).isoformat(),
            "original_packed_hour": packed,
            "source_original_station_columns": columns,
            "post_inter2_uv_nonzero_components": nonzero,
            "post_inter2_uv_negative_components": negative,
            "post_inter2_uv_components": len(grid),
        })
    if post_nonzero <= 0 or post_negative <= 0:
        raise ValueError("original INTER2 output unexpectedly constant/zero")
    result = {
        "status": "PASS_ORIGINAL_REAL_SPARSE_INTER2_PRE_POST_REFERENCE_ONLY",
        "source": "UNMODIFIED_CALMET_6_5_0_SCRATCH_INSTRUMENTATION",
        "original_git_blob": ORIGINAL_BLOB,
        "original_pristine_met_sha256": sha(pristine),
        "original_instrumented_met_sha256": sha(scratch),
        "original_met_byte_identical": True,
        "original_pre_inter2_trace_sha256": sha(pre),
        "original_post_inter2_trace_sha256": sha(post),
        "six_distinct_hours": HOURS,
        "original_station_columns": STATIONS,
        "grid_shape": [NX, NY, NZ],
        "post_inter2_uv_components_checked": HOURS * GRID_DATA.size // 4,
        "original_stheor_first_event_station_column_max_abs_mps": max_station_residual,
        "original_post_inter2_nonzero_components": post_nonzero,
        "original_post_inter2_negative_components": post_negative,
        "hourly_diagnostic": by_hour,
        "missing_station_column_semantics": "SOURCE_VALUES_RECORDED_NOT_YET_NATIVE_ACCEPTED",
        "native_full_grid_inter2": "NOT_RUN",
        "native_g14_water_comp": "NOT_ACCEPTED",
        "native_g26_45fields": "NOT_ACCEPTED",
        "p7": "NOT_ACCEPTED",
        "p5_raw_wind_mask": "UNCHANGED",
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("S4R1C7C_REAL_NOAA_ORIGINAL_SPARSE_INTER2=PASS_REFERENCE_ONLY")
    print("S4R1C7C_ORIGINAL_6H_45FIELD_MET=BYTE_IDENTICAL")
    print("S4R1C7C_NATIVE_INTER2_G24_G26_P7=NOT_ACCEPTED")


def selftest() -> None:
    with tempfile.TemporaryDirectory() as directory:
        p = Path(directory) / PRE_NAME
        with p.open("wb") as out:
            for i in range(HOURS):
                t = FIRST_HOUR + timedelta(hours=i)
                packed = t.year * 100000 + t.timetuple().tm_yday * 100 + t.hour
                out.write(HEADER.pack(51, packed, 0, NX, NY, NZ))
                out.write(STATION_DATA.pack(*([1.0] * (2 * NZ * STATIONS))))
        assert len(unpack_records(p, 51, STATION_DATA)) == HOURS
        corrupt = bytearray(p.read_bytes())
        corrupt[0] = 50
        p.write_bytes(corrupt)
        try:
            unpack_records(p, 51, STATION_DATA)
        except ValueError:
            pass
        else:
            raise AssertionError("corrupted original INTER2 trace was accepted")
    print("S4R1C7C_SIXHOUR_ORACLE_SCHEMA_NEGATIVE_SELFTEST=PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("prepare")
    for key in ("vendor", "destination", "receipt"):
        a.add_argument("--" + key, type=Path, required=True)
    b = sub.add_parser("verify")
    for key in ("vendor", "pristine", "scratch", "pre", "post", "station-oracle", "report"):
        b.add_argument("--" + key, type=Path, required=True)
    sub.add_parser("selftest")
    args = parser.parse_args()
    if args.cmd == "prepare":
        prepare(args.vendor, args.destination, args.receipt)
    elif args.cmd == "verify":
        verify(
            args.vendor, args.pristine, args.scratch, args.pre, args.post,
            args.station_oracle, args.report
        )
    else:
        selftest()


if __name__ == "__main__":
    main()
