#!/usr/bin/env python3
"""P6E COORDLIB UTM original-source parity.

Compiles the *unmodified* CALMET 6.5.0 `coordlib.for` (GCTP 2.0.2, pinned by
sha256) together with `coordlib_utm_driver.f`, which replays exactly the
`MICROI -> GLOBE1 -> GLOBE -> COORDS -> GTPZ0 -> PJ01Z0 -> PJ09Z0` chain that
produces the CALMET grid geometry (`calmet.for` L9575-9603), and compares the
resulting per-cell N.latitude / E.longitude REAL*4 bit patterns with the P6E
C++20 port (`cteas/p6e/coordlib_pj09z0.hpp` via `surface_solar_grid`).

The comparison is bit-exact by construction: both sides are reduced to the
REAL*4 the original stores in `XLAT/XLON`, so the acceptance metric is the
number of differing bit patterns (0 required), with the absolute/relative
error in degrees reported alongside.
"""
import argparse
import hashlib
import json
import math
import struct
import subprocess
import tempfile
from pathlib import Path

# engine/vendor/src/CALMET_v6.5.0_L150223/coordlib.for
COORDLIB_SHA256 = \
    "abe1d9a69ed7a4b8fa98bf1092cd668feef9f5612619ae3a8b565ec5b9be3c93"
DRIVER = Path(__file__).with_name("coordlib_utm_driver.f")

# (nx, ny, utm zone, XORIG km, YORIG km, DGRID km)
CASES = [
    (50, 50, 50, 510.885, 3531.269, 0.1),      # frozen 2022 real case
    (4, 4, 1, 200.0, 500.0, 1.0),
    (4, 4, 17, 300.123, 900.456, 0.25),
    (4, 4, 50, 510.885, 3531.269, 0.1),
    (4, 4, 60, 100.5, 200.75, 2.0),
    (3, 3, 50, 510.885, 3531.269, 0.05),
    (3, 3, 50, 510.885, 3531.269, 1.0),
    (3, 3, 50, 0.0, 0.0, 0.1),
    (3, 3, 50, 1234.567, 4567.891, 0.333),
    (1, 1, 50, 510.885, 3531.269, 0.1),
    (2, 5, 50, 510.885, 3531.269, 0.1),
]


def f32(value):
    return struct.unpack("<f", struct.pack("<f", value))[0]


def run(command, inp=None):
    return subprocess.run([str(x) for x in command], input=inp, text=True,
                          capture_output=True, check=True).stdout


def parse(raw, cells):
    values = {}
    for line in raw.splitlines():
        parts = line.split()
        if len(parts) != 4:
            raise RuntimeError("COORDLIB UTM comparator schema: " + line)
        i, j = int(parts[0]), int(parts[1])
        values[(i, j)] = (int(parts[2], 16), int(parts[3], 16))
    if len(values) != cells:
        raise RuntimeError("COORDLIB UTM output size mismatch")
    return values


def as_float(word):
    return struct.unpack("<f", struct.pack("<I", word))[0]


def main():
    parser = argparse.ArgumentParser()
    for flag in ("vendor", "cpp", "out"):
        parser.add_argument("--" + flag, required=True, type=Path)
    parser.add_argument("--gfortran", default="gfortran")
    parser.add_argument("--coordlib-hash", default=COORDLIB_SHA256,
                        help="expected sha256 of the unmodified coordlib.for")
    args = parser.parse_args()
    raw = args.vendor.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != args.coordlib_hash:
        raise RuntimeError("COORDLIB original source drift: " + digest)
    vendor_dir = args.vendor.parent
    for include in ("nima.crd", "blockdat.crd"):
        if not (vendor_dir / include).is_file():
            raise RuntimeError("missing COORDLIB include: " + include)

    values = 0
    mismatches = 0
    largest_abs = 0.0
    largest_rel = 0.0
    samples = []
    with tempfile.TemporaryDirectory(prefix="cteas-p6e-coordlib-") as work:
        d = Path(work)
        (d / "coordlib_utm_driver.f").write_bytes(DRIVER.read_bytes())
        run([args.gfortran, "-O0", "-std=legacy", "-fno-automatic",
             "-ffixed-line-length-none", "-I" + str(vendor_dir),
             "-I" + str(d),
             d / "coordlib_utm_driver.f", args.vendor,
             "-o", d / "original"])
        for nx, ny, zone, xorig_km, yorig_km, dgrid_km in CASES:
            request = (f"{nx} {ny} {zone}\n"
                       f"{xorig_km} {yorig_km} {dgrid_km}\nWGS-84\n")
            expected = parse(run([d / "original"], request), nx * ny)
            xorigin_m = f32(1000.0 * f32(xorig_km))
            yorigin_m = f32(1000.0 * f32(yorig_km))
            dgrid_m = f32(1000.0 * f32(dgrid_km))
            actual = parse(run([args.cpp, nx, ny, zone, xorigin_m, yorigin_m,
                                dgrid_m]), nx * ny)
            for key in expected:
                original_lat, original_lon = expected[key]
                port_lat, port_lon = actual[key]
                values += 2
                if (original_lat, original_lon) != (port_lat, port_lon):
                    mismatches += 1
                    if len(samples) < 20:
                        samples.append({
                            "zone": zone, "i": key[0], "j": key[1],
                            "original_lat_bits": f"{original_lat:08X}",
                            "port_lat_bits": f"{port_lat:08X}",
                            "original_lon_bits": f"{original_lon:08X}",
                            "port_lon_bits": f"{port_lon:08X}"})
                a_lat, a_lon = as_float(original_lat), as_float(original_lon)
                b_lat, b_lon = as_float(port_lat), as_float(port_lon)
                for a, b in ((a_lat, b_lat), (a_lon, b_lon)):
                    largest_abs = max(largest_abs, abs(a - b))
                    if a != 0.0:
                        largest_rel = max(largest_rel, abs(a - b) / abs(a))
    report = {
        "status": "PASS" if mismatches == 0 else "FAIL",
        "cases": len(CASES),
        "values": values,
        "max_abs_error_deg": largest_abs,
        "max_rel_error": largest_rel,
        "real4_bit_pattern_mismatches": mismatches,
        "first_mismatches": samples,
        "vendor_sha256": digest,
        "unmodified_source": "engine/vendor/src/CALMET_v6.5.0_L150223/"
                             "coordlib.for (whole file, compiled as-is)",
        "ported_routine": "PJ09Z0 inverse (via PJ01Z0/UTM); NOT PJ07Z0 "
                          "(polyconic)",
        "driver": DRIVER.name,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if mismatches:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
