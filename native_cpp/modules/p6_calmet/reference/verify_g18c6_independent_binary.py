#!/usr/bin/env python3
"""G18C6 independent Fortran-sequential CALMET.DAT 2.1 binary walk.

Use no C++ P6F decoder and no original/reference MET.DAT weather payload.
The file is built by the G17C→G18C5 selected *fixture*, not full CALMET.
"""
import argparse
import datetime as dt
import json
import pathlib
import struct


def fortran_records(data: bytes) -> list[bytes]:
    records: list[bytes] = []
    offset = 0
    while offset < len(data):
        if offset + 8 > len(data):
            raise AssertionError("truncated original Fortran record")
        (size,) = struct.unpack_from("<i", data, offset)
        if not 0 <= size <= 200000000 or offset + 8 + size > len(data):
            raise AssertionError("invalid Fortran record payload")
        (end_size,) = struct.unpack_from("<i", data, offset + 4 + size)
        if size != end_size:
            raise AssertionError("Fortran record prefix/suffix mismatch")
        records.append(data[offset + 4:offset + 4 + size])
        offset += size + 8
    if offset != len(data):
        raise AssertionError("unexpected trailing original binary bytes")
    return records


def check(file: pathlib.Path) -> dict:
    records = fortran_records(file.read_bytes())
    if records[0][:16].decode("ascii").strip() != "CALMET.DAT":
        raise AssertionError("P6F declaration is not CALMET.DAT")
    if records[0][16:32].decode("ascii").strip() != "2.1":
        raise AssertionError("P6F file version not original v2.1")
    if len(records[0]) != 96:
        raise AssertionError("original Fortran header record not 96 bytes")
    (comments,) = struct.unpack("<i", records[1])
    if not 1 <= comments <= 1000:
        raise AssertionError("G18C6 provenance comments not present")
    comment_rows = records[2:2 + comments]
    if any(len(row) != 132 for row in comment_rows):
        raise AssertionError("P6F comment size not 132")
    if not any(b"test-only" in row for row in comment_rows):
        raise AssertionError("G18C6 simulation scope warning absent")
    control = records[2 + comments]
    if len(control) != 176:
        raise AssertionError("original P6F controls byte length changed")
    begin, end = struct.unpack_from("<5i", control, 0), struct.unpack_from("<5i", control, 20)
    timezone = control[40:48].decode("ascii")
    irlg, irtype, nx, ny, nz = struct.unpack_from("<5i", control, 48)
    spacing, xorig, yorig = struct.unpack_from("<3f", control, 68)
    iwfcod, nssta, nusta, npsta = struct.unpack_from("<4i", control, 80)
    if ((irlg, irtype, nx, ny, nz, iwfcod, nssta, nusta, npsta)
            != (1, 1, 12, 12, 9, 1, 2, 2, 0)):
        raise AssertionError("source GEO and 2SS/2US declarations mismatch")
    if timezone != "UTC+0000" or (spacing, xorig, yorig) != (
            10000.0, 510885.0, 3531269.0):
        raise AssertionError("source grid CRS, spacing or origin mismatch")
    if (begin[:4], end[:4]) != ((2024, 1, 1, 2), (2024, 1, 1, 3)):
        raise AssertionError("original real model clock not 2024-01-01 02–03 UTC")
    if begin[-1] or end[-1]:
        raise AssertionError("source UTC begin/end seconds not zero")
    static, hourly = {}, []
    for payload in records[3 + comments:]:
        if len(payload) < 24:
            raise AssertionError("short Fortran static/hourly field")
        label = payload[:8].decode("ascii")
        bpack, bsec, epack, esec = struct.unpack_from("<4i", payload, 8)
        if bpack == 0 and epack == 0:
            static[label.strip()] = payload[24:]
        else:
            hourly.append((label, bpack, bsec, epack, esec, payload[24:]))
    for key in ("ZFACE", "XSSTA", "YSSTA", "XUSTA", "YUSTA",
                "Z0", "ILANDU", "ELEV", "XLAI", "NEARS"):
        if key not in static:
            raise AssertionError(f"missing reference-independent original GEO static {key}")
    def floats(name: str) -> tuple[float, ...]:
        raw = static[name]
        if len(raw) % 4:
            raise AssertionError("unaligned REAL*4 static")
        return struct.unpack(f"<{len(raw)//4}f", raw)
    def ints(name: str) -> tuple[int, ...]:
        raw = static[name]
        if len(raw) % 4:
            raise AssertionError("unaligned INT static")
        return struct.unpack(f"<{len(raw)//4}i", raw)
    if floats("XSSTA") != (10000., 100000.) or floats("YSSTA") != (
            10000., 100000.):
        raise AssertionError("original two SURF sources not in SS order")
    if floats("XUSTA") != (20000., 50000.) or floats("YUSTA") != (
            20000., 50000.):
        raise AssertionError("original two UP sources not in US order")
    faces = floats("ZFACE")
    if len(faces) != 10 or any(a >= b for a, b in zip(faces, faces[1:])):
        raise AssertionError("original met.inp ZFACE not present")
    if len(floats("Z0")) != nx * ny or len(floats("ELEV")) != nx * ny:
        raise AssertionError("GEO static grid shape invalid")
    if len(floats("XLAI")) != nx * ny or len(ints("ILANDU")) != nx * ny:
        raise AssertionError("GEO categories or leaf area shape invalid")
    if set(ints("ILANDU")) != {20}:
        raise AssertionError("unexpected fixture original GEO land use")
    if max(floats("ELEV")) == min(floats("ELEV")):
        raise AssertionError("terrain elevation was replaced with a constant")
    if len(ints("NEARS")) != nx * ny or not set(ints("NEARS")).issubset({1, 2}):
        raise AssertionError("SETCOM one-based SS NEARS invalid")
    labels = []
    for level in range(1, 10):
        labels += [f"U-LEV{level:3d}", f"V-LEV{level:3d}", f"WFACE{level:3d}"]
    labels += [f"T-LEV{level:3d}" for level in range(1, 10)]
    labels += ["IPGT    ", "USTAR   ", "ZI      ", "EL      ",
               "WSTAR   ", "TEMPK   ", "RHO     ", "QSW     ", "IRH     "]
    if len(labels) != 45 or len(hourly) != 45:
        raise AssertionError("not exactly 45 original CALMET hourly records")
    per_label = {}
    for index, (label, bpack, bsec, epack, esec, data) in enumerate(hourly):
        if label != labels[index]:
            raise AssertionError(f"wrong original OUTHR label at {index}: {label!r}")
        if (bpack, bsec, epack, esec) != (202400102, 0, 202400102, 3600):
            raise AssertionError("unexpected original CALMET hourly clock")
        if len(data) != nx * ny * 4:
            raise AssertionError("wrong original per-field REAL4/INT4 payload")
        if label.strip() in ("IPGT", "IRH"):
            v = struct.unpack(f"<{nx*ny}i", data)
            if label.strip() == "IPGT" and not all(1 <= n <= 6 for n in v):
                raise AssertionError("source Turner class outside 1–6")
            if label.strip() == "IRH" and not all(0 <= n <= 100 for n in v):
                raise AssertionError("source SURFVAR relative humidity outside 0–100")
        else:
            v = struct.unpack(f"<{nx*ny}f", data)
            if any(not (-1.e35 < n < 1.e35) or n == 9999. for n in v):
                raise AssertionError("source hourly REAL4 missing or invalid")
        per_label[label] = len(v)
    return {
        "status": "PASS_G18C6_INDEPENDENT_SOURCE_BINARY_WALK",
        "not_scientifically_accepted": "selected 1h physics fixture, not G14 multi-hour/45-field original Fortran parity",
        "hours": irlg, "fields_per_hour": len(hourly), "grid": [nx, ny, nz],
        "surface_stations": nssta, "upper_stations": nusta,
        "run_clock_utc": ["2024-01-01T02:00:00Z", "2024-01-01T03:00:00Z"],
        "total_fortran_records": len(records), "labels_verified": list(per_label),
        "byte_size": file.stat().st_size
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--candidate", type=pathlib.Path, required=True)
    p.add_argument("--out", type=pathlib.Path, required=True)
    args = p.parse_args()
    result = check(args.candidate)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(result["status"], result["byte_size"], "bytes; 45 original labels")


if __name__ == "__main__":
    main()
