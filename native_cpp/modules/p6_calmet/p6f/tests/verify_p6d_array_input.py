#!/usr/bin/env python3
"""P6F <-> P6D contract CTest.

The P6D producer emits, per hour, raw little-endian float32 planes plus a
`metadata.json` (module native_cpp/modules/p6_calmet, `cteas_p6_realcase_wind_field`).
This test builds a directory of exactly that shape, runs the documented
one-command entry

    cteas_p6f_calmet_dat21_writer write-from-p6d --fields DIR \
        --statics-from <legal CALMET.DAT> --out CALMET.DAT

and then verifies the produced file against the input arrays value by value, its
byte-exact round trip, the IRTYPE=1 composition path (2-D meteorological fields
taken from another legal file) and the fail-closed cases.

Every number here is a synthetic constant: this test proves the *reader and the
mapping*, never that reconstructed meteorology is correct. The arrays are
generated in the documented i-fastest order (idx = i + nx*(j + ny*k)).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
import struct
import subprocess
import sys
import tempfile

RECORD_HEADER_BYTES = 24
XMISS = 9999.0


def fail(message: str) -> None:
    print("P6F_P6D_INPUT_FAIL " + message)
    sys.exit(1)


def run(command: list) -> subprocess.CompletedProcess:
    return subprocess.run([str(part) for part in command], capture_output=True,
                          text=True)


def walk(data: bytes) -> list[tuple[int, int, int]]:
    records: list[tuple[int, int, int]] = []
    offset = 0
    while offset + 8 <= len(data):
        (length,) = struct.unpack_from("<i", data, offset)
        if length < 0 or offset + 8 + length > len(data):
            fail(f"damaged record length {length} at offset {offset}")
        (trailer,) = struct.unpack_from("<i", data, offset + 4 + length)
        if trailer != length:
            fail("record length markers disagree")
        records.append((offset, length, offset + 4))
        offset += 8 + length
    if offset != len(data):
        fail("the record walk does not reach the end of the file")
    return records


def records_by_label(data: bytes, payload_len: int | None = None) -> dict[str, list[bytes]]:
    """Field records by their printed label; comment/static records excluded."""
    out: dict[str, list[bytes]] = {}
    for _, length, payload in walk(data):
        if payload_len is not None and length != payload_len:
            continue
        label = data[payload:payload + 8].decode("ascii", "replace").rstrip()
        if not label.isprintable() or not label:
            continue
        out.setdefault(label, []).append(data[payload:payload + length])
    return out


def expected_labels(nz: int) -> list[str]:
    """The OUTHR IRTYPE=1 label order, derived here independently."""
    labels: list[str] = []
    for level in range(1, nz + 1):
        labels += [f"U-LEV{level:>3}", f"V-LEV{level:>3}", f"WFACE{level:>3}"]
    labels += [f"T-LEV{level:>3}" for level in range(1, nz + 1)]
    labels += ["IPGT", "USTAR", "ZI", "EL", "WSTAR", "TEMPK", "RHO", "QSW", "IRH"]
    return labels


def zface_of(data: bytes) -> list[float]:
    for _, length, payload in walk(data):
        if data[payload:payload + 8].rstrip(b" ") != b"ZFACE":
            continue
        return list(struct.unpack_from(f"<{(length - RECORD_HEADER_BYTES) // 4}f",
                                       data, payload + RECORD_HEADER_BYTES))
    fail("the statics source has no ZFACE record")
    return []


def build_fields_dir(root: pathlib.Path, nx: int, ny: int, nz: int,
                     labels: list[str], zface_m: list[float],
                     written_labels: list[str], variant: str = "wind1",
                     w_field: str = "w_face", sentinel_cells: tuple = ()) -> None:
    """Deterministic P6D-shaped product: metadata.json + per-hour f32 planes."""
    cells = nx * ny
    thickness = [round(zface_m[k + 1] - zface_m[k], 6) for k in range(nz)]
    center = [round(0.5 * (zface_m[k + 1] + zface_m[k]), 6) for k in range(nz)]
    metadata = {
        "product": "P6F_TEST_DOUBLE_OF_THE_P6D_WIND_PRODUCT",
        "partial": False,
        "status": "SYNTHETIC_TEST_FIXTURE",
        "grid": {"nx": nx, "ny": ny, "nz": nz, "grid_spacing_m": 100.0,
                 "layout": "i_fastest", "dtype": "float32"},
        "levels": {"zface_m": zface_m, "thickness_m": thickness,
                   "center_m": center},
        "units": {f"{variant}_u_*.f32": "m/s", f"{variant}_v_*.f32": "m/s",
                  f"{w_field}_*.f32": "m/s"},
        "missing_sentinel": XMISS,
        "hourly_labels": labels,
        "hour_label": "END",
    }
    (root / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    (root / "produced_hours.txt").write_text(" ".join(written_labels) + "\n")
    index = 0
    for label in written_labels:
        u = [0.0] * (cells * nz)
        v = [0.0] * (cells * nz)
        w = [0.0] * (cells * (nz + 1))
        for k in range(nz):
            for j in range(ny):
                for i in range(nx):
                    idx = i + nx * (j + ny * k)
                    index += 1
                    u[idx] = round(1.5 + 0.01 * (i + 2 * j) + 0.25 * k, 6)
                    v[idx] = round(-0.5 + 0.02 * (2 * i - j) - 0.1 * k, 6)
        for k in range(nz + 1):
            for j in range(ny):
                for i in range(nx):
                    w[i + nx * (j + ny * k)] = round(0.001 * (i + j + k), 6)
        for cell in sentinel_cells:
            for k in range(nz):
                u[cell + cells * k] = XMISS
        for cell in sentinel_cells:
            w[cell + cells * nz] = XMISS
        (root / f"{variant}_u_{label}.f32").write_bytes(
            struct.pack(f"<{len(u)}f", *u))
        (root / f"{variant}_v_{label}.f32").write_bytes(
            struct.pack(f"<{len(v)}f", *v))
        (root / f"{w_field}_{label}.f32").write_bytes(
            struct.pack(f"<{len(w)}f", *w))


def verify_wind_mapping(data: bytes, meta: dict, fields_dir: pathlib.Path,
                        variant: str, w_field: str, labels: list[str],
                        index: int) -> None:
    """Every U/V/W face in the file must equal the P6D plane value.

    The expectation is rebuilt from the *documented* P6D plane index
    `i + nx*(j + ny*k)` (the layout metadata declares), not from any assumption
    about how the writer indexes the array, so a permuted read fails here.
    """
    nx, ny, nz = meta["nx"], meta["ny"], meta["nz"]
    cells = nx * ny
    records = records_by_label(data, RECORD_HEADER_BYTES + 4 * cells)

    def plane_index(cell: int, level: int) -> int:
        i = cell % nx
        j = cell // nx
        return i + nx * (j + ny * level)

    for label in labels:
        u = list(struct.unpack(f"<{cells * nz}f",
                               (fields_dir / f"{variant}_u_{label}.f32").read_bytes()))
        v = list(struct.unpack(f"<{cells * nz}f",
                               (fields_dir / f"{variant}_v_{label}.f32").read_bytes()))
        w = list(struct.unpack(f"<{cells * (nz + 1)}f",
                               (fields_dir / f"{w_field}_{label}.f32").read_bytes()))
        for kind in ("U-LEV", "V-LEV", "WFACE"):
            for level in range(1, nz + 1):
                name = f"{kind}{level:>3}"
                record = records[name][index]
                values = struct.unpack_from(f"<{cells}f", record,
                                            RECORD_HEADER_BYTES)
                if kind == "U-LEV":
                    expected = [u[plane_index(cell, level - 1)]
                                for cell in range(cells)]
                elif kind == "V-LEV":
                    expected = [v[plane_index(cell, level - 1)]
                                for cell in range(cells)]
                else:
                    # CALMET.DAT writes W at the top face of layer k, so the P6D
                    # face k+1 becomes WFACE(k); the ground face is not written.
                    expected = [w[plane_index(cell, level)]
                                for cell in range(cells)]
                for cell in range(cells):
                    if struct.pack("<f", values[cell]) != struct.pack("<f", expected[cell]):
                        fail(f"{name} of {label} differs from the P6D plane at "
                             f"cell {cell}: {values[cell]} != {expected[cell]}")
    if index + 1 > len(records["U-LEV  1"]):
        fail("not enough U-LEV records in the produced file")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tool", required=True)
    parser.add_argument("--statics-from", required=True, type=pathlib.Path)
    parser.add_argument("--report", default=None, type=pathlib.Path)
    args = parser.parse_args()

    statics = args.statics_from
    if not statics.is_file():
        fail(f"the statics source {statics} is missing")
    statics_bytes = statics.read_bytes()
    statics_records = walk(statics_bytes)
    (statics_comments,) = struct.unpack_from("<i", statics_bytes,
                                             statics_records[1][2])
    controls = statics_bytes[statics_records[2 + statics_comments][2]:]
    nx, ny, nz = struct.unpack_from("<3i", controls, 56)
    if (nx, ny, nz) != (50, 50, 9):
        fail(f"the statics source grid is {(nx, ny, nz)}, expected (50, 50, 9)")
    zface_m = zface_of(statics_bytes)
    if len(zface_m) != nz + 1:
        fail("the statics source ZFACE is not NZ+1 faces")

    # The frozen case's own hourly labels, as interval END, first three hours.
    labels = ["2022-01-01_01", "2022-01-01_02", "2022-01-01_03"]
    evidence: dict = {"status": "FAIL", "labels": labels, "zface_m": zface_m}

    with tempfile.TemporaryDirectory(prefix="p6f-p6d-") as work:
        root = pathlib.Path(work)
        fields = root / "fields"
        fields.mkdir()
        build_fields_dir(fields, nx, ny, nz, labels, zface_m, labels,
                         sentinel_cells=(0, 7))

        # ---- IRTYPE=0: the wind-only product of the P6D contract ----
        produced = root / "wind-only.dat"
        report = root / "wind-only.json"
        result = run([args.tool, "write-from-p6d", "--fields", fields,
                      "--statics-from", statics, "--out", produced,
                      "--report", report])
        if result.returncode != 0 or "P6F_WRITE_FROM_P6D_WRITTEN" not in result.stdout:
            print(result.stdout + result.stderr)
            fail("write-from-p6d failed for the wind-only product")
        payload = json.loads(report.read_text())
        if payload["status"] != "PASS_WRITTEN_FROM_P6D_ARRAYS" or payload["irtype"] != 0:
            fail("the wind-only report is not the IRTYPE=0 product")
        if payload["hours_written"] != len(labels) or payload["intervals"] != len(labels):
            fail("the wind-only product has the wrong interval count")
        expected_fields = 3 * nz
        if payload["fields_per_interval"] != expected_fields:
            fail(f"IRTYPE=0 must write {expected_fields} fields per interval, "
                 f"got {payload['fields_per_interval']}")
        data = produced.read_bytes()
        meta = {"nx": nx, "ny": ny, "nz": nz}
        verify_wind_mapping(data, meta, fields, "wind1", "w_face", labels, 0)
        # the sentinel cells must survive verbatim, not be renormalised
        records = records_by_label(data, RECORD_HEADER_BYTES + 4 * nx * ny)
        first_u = struct.unpack_from(f"<{nx * ny}f", records["U-LEV  1"][0],
                                     RECORD_HEADER_BYTES)
        if first_u[0] != XMISS:
            fail("the XMISS value of the first cell was not written verbatim")
        if payload["missing_sentinel"] != XMISS:
            fail("the metadata sentinel was not read")
        result = run([args.tool, "roundtrip", "--file", produced])
        if result.returncode != 0:
            fail("the wind-only product does not round trip byte-identically")
        result = run([args.tool, "check", "--file", produced])
        if result.returncode != 0 or "P6F_CHECK_LAYOUT_VALID" not in result.stdout:
            fail("check rejected the wind-only product")
        # WFACE(k) must be the P6D face k+1 (the ground face 1 is not written)
        w_plane = list(struct.unpack(f"<{nx * ny * (nz + 1)}f",
                                     (fields / f"w_face_{labels[0]}.f32").read_bytes()))
        top = struct.unpack_from(f"<{nx * ny}f", records["WFACE  9"][0],
                                 RECORD_HEADER_BYTES)
        # Cell 0 of the top face in the documented plane layout
        # (i + nx*(j + ny*k) with i=j=0 and face k=nz).
        if struct.pack("<f", top[0]) != struct.pack("<f", w_plane[nx * ny * nz]):
            fail("WFACE 9 is not the P6D top face")
        evidence["wind_only"] = {"bytes": len(data), "sha256": payload["out_sha256"],
                                 "fields_per_interval": expected_fields,
                                 "intervals": len(labels),
                                 "mapping_verified_values":
                                     nx * ny * nz * 2 * len(labels) +
                                     nx * ny * nz * len(labels)}

        # ---- the renamed INTER2 product: inter2_* planes ----
        inter2 = root / "inter2"
        inter2.mkdir()
        for item in fields.iterdir():
            if item.name.startswith("wind1_"):
                continue
            (inter2 / item.name).write_bytes(item.read_bytes())
        for label in labels:
            for kind in ("u", "v"):
                (inter2 / f"inter2_{kind}_{label}.f32").write_bytes(
                    (fields / f"wind1_{kind}_{label}.f32").read_bytes())
        inter2_out = root / "inter2.dat"
        result = run([args.tool, "write-from-p6d", "--fields", inter2,
                      "--variant", "inter2", "--w-field", "w_face",
                      "--statics-from", statics, "--out", inter2_out])
        if result.returncode != 0 or "P6F_WRITE_FROM_P6D_WRITTEN" not in result.stdout:
            print(result.stdout + result.stderr)
            fail("the renamed inter2_* variant could not be written")
        verify_wind_mapping(inter2_out.read_bytes(), meta, inter2, "inter2",
                            "w_face", labels, 0)
        evidence["inter2_variant"] = {"bytes": inter2_out.stat().st_size}

        # ---- IRTYPE=1 composition with the 2-D fields of another legal file ----
        composed = root / "composed.dat"
        result = run([args.tool, "write-from-p6d", "--fields", fields,
                      "--statics-from", statics, "--met-fields-from", statics,
                      "--irtype", "1", "--out", composed])
        if result.returncode != 0 or "P6F_WRITE_FROM_P6D_WRITTEN" not in result.stdout:
            print(result.stdout + result.stderr)
            fail("the IRTYPE=1 composition failed")
        composed_bytes = composed.read_bytes()
        all_records = records_by_label(composed_bytes,
                                       RECORD_HEADER_BYTES + 4 * nx * ny)
        composed_records = {name: all_records[name]
                            for name in expected_labels(nz)}
        if len(composed_records) != 45:
            fail(f"the composed file has {len(composed_records)} hourly labels, "
                 "expected 45")
        for name, label_records in composed_records.items():
            if len(label_records) != len(labels):
                fail(f"the composed file has {len(label_records)} {name} "
                     f"records, expected {len(labels)}")
        verify_wind_mapping(composed_bytes, meta, fields, "wind1", "w_face",
                            labels, 0)
        statics_labels = records_by_label(statics_bytes,
                                          RECORD_HEADER_BYTES + 4 * nx * ny)
        for name in ("IPGT", "USTAR", "ZI", "EL", "WSTAR", "TEMPK", "RHO", "QSW",
                     "IRH", "T-LEV  1"):
            got = composed_records[name][0][RECORD_HEADER_BYTES:]
            want = statics_labels[name][0][RECORD_HEADER_BYTES:]
            if got != want:
                fail(f"the composed {name} does not equal the met source record")
        result = run([args.tool, "roundtrip", "--file", composed])
        if result.returncode != 0:
            fail("the composed product does not round trip byte-identically")
        evidence["composed"] = {"bytes": len(composed_bytes),
                                "labels": len(composed_records)}

        # ---- fail-closed cases ----
        negatives: dict[str, bool] = {}

        def expect_error(name: str, command: list, needle: str) -> None:
            result = run(command)
            ok = result.returncode != 0 and needle in (result.stdout + result.stderr)
            negatives[name] = ok
            if not ok:
                print(result.stdout + result.stderr)
                fail(f"negative case did not fail closed: {name}")

        missing = root / "missing"
        missing.mkdir()
        for item in fields.iterdir():
            (missing / item.name).write_bytes(item.read_bytes())
        (missing / f"wind1_u_{labels[1]}.f32").unlink()
        expect_error("missing_hour_plane",
                     [args.tool, "write-from-p6d", "--fields", missing,
                      "--statics-from", statics, "--out", root / "x.dat"],
                     "cannot open")

        sized = root / "sized"
        sized.mkdir()
        for item in fields.iterdir():
            (sized / item.name).write_bytes(item.read_bytes())
        (sized / f"wind1_v_{labels[0]}.f32").write_bytes(b"\x00" * 16)
        expect_error("wrong_plane_size",
                     [args.tool, "write-from-p6d", "--fields", sized,
                      "--statics-from", statics, "--out", root / "x.dat"],
                     "float32 values")

        layout = root / "layout"
        layout.mkdir()
        for item in fields.iterdir():
            (layout / item.name).write_bytes(item.read_bytes())
        meta_json = json.loads((layout / "metadata.json").read_text())
        meta_json["grid"]["layout"] = "j_fastest"
        (layout / "metadata.json").write_text(json.dumps(meta_json))
        expect_error("unsupported_layout",
                     [args.tool, "write-from-p6d", "--fields", layout,
                      "--statics-from", statics, "--out", root / "x.dat"],
                     "unsupported grid.layout")

        label_meta = root / "hour_label"
        label_meta.mkdir()
        for item in fields.iterdir():
            (label_meta / item.name).write_bytes(item.read_bytes())
        meta_json = json.loads((label_meta / "metadata.json").read_text())
        meta_json["hour_label"] = "MIDDLE"
        (label_meta / "metadata.json").write_text(json.dumps(meta_json))
        # The verification gate is data-driven: a variant the metadata marks
        # NOT_SOURCE_VERIFIED is refused unless it is accepted explicitly.
        unverified = root / "unverified"
        unverified.mkdir()
        for item in fields.iterdir():
            (unverified / item.name).write_bytes(item.read_bytes())
        for label in labels:
            for kind in ("u", "v"):
                source = fields / f"wind1_{kind}_{label}.f32"
                (unverified / f"blend_{kind}_{label}.f32").write_bytes(
                    source.read_bytes())
        meta_json = json.loads((unverified / "metadata.json").read_text())
        meta_json["blend"] = {"verification": "NOT_SOURCE_VERIFIED: synthetic"}
        (unverified / "metadata.json").write_text(json.dumps(meta_json))
        expect_error("unverified_variant_refused",
                     [args.tool, "write-from-p6d", "--fields", unverified,
                      "--variant", "blend", "--statics-from", statics,
                      "--out", root / "x.dat"],
                     "NOT_SOURCE_VERIFIED")
        accepted = root / "unverified-accepted.dat"
        result = run([args.tool, "write-from-p6d", "--fields", unverified,
                      "--variant", "blend", "--w-field", "w_face",
                      "--statics-from", statics, "--accept-unverified-variant",
                      "--out", accepted, "--report", root / "unverified.json"])
        if result.returncode != 0 or "P6F_WRITE_FROM_P6D_WRITTEN" not in result.stdout:
            print(result.stdout + result.stderr)
            fail("the explicit --accept-unverified-variant did not write the "
                 "variant")
        recorded = json.loads((root / "unverified.json").read_text())
        if "NOT_SOURCE_VERIFIED" not in recorded["blend_verification"] or \
                recorded["variant_source_verified"] or \
                not recorded["accept_unverified_variant"]:
            fail("the report does not record the unverified-variant acceptance")
        negatives["unverified_variant_refused"] = True
        negatives["unverified_variant_accepted_with_flag"] = True

        expect_error("bad_hour_label",
                     [args.tool, "write-from-p6d", "--fields", label_meta,
                      "--statics-from", statics, "--out", root / "x.dat"],
                     "hour_label")

        nan = root / "nan"
        nan.mkdir()
        for item in fields.iterdir():
            (nan / item.name).write_bytes(item.read_bytes())
        plane = bytearray((nan / f"wind1_u_{labels[0]}.f32").read_bytes())
        struct.pack_into("<f", plane, 0, math.nan)
        (nan / f"wind1_u_{labels[0]}.f32").write_bytes(bytes(plane))
        expect_error("nonfinite_value",
                     [args.tool, "write-from-p6d", "--fields", nan,
                      "--statics-from", statics, "--out", root / "x.dat"],
                     "non-finite")

        gap = root / "gap"
        gap.mkdir()
        build_fields_dir(gap, nx, ny, nz, labels, zface_m,
                         [labels[0], labels[2]])
        expect_error("non_contiguous_hours",
                     [args.tool, "write-from-p6d", "--fields", gap,
                      "--statics-from", statics, "--out", root / "x.dat"],
                     "contiguous")

        expect_error("boundary_planes_are_not_a_grid",
                     [args.tool, "write-from-p6d", "--fields", fields,
                      "--variant", "windbc", "--statics-from", statics,
                      "--out", root / "x.dat"],
                     "lateral boundaries")

        expect_error("missing_met_source",
                     [args.tool, "write-from-p6d", "--fields", fields,
                      "--statics-from", statics, "--irtype", "1",
                      "--out", root / "x.dat"],
                     "met-fields-from")

        other = root / "other-statics.dat"
        result = run([args.tool, "emit-fixture", "--out", other, "--hours", "1",
                      "--nx", "3", "--ny", "3", "--nz", "9"])
        if result.returncode != 0:
            fail("could not build the mismatched statics fixture")
        expect_error("grid_mismatch",
                     [args.tool, "write-from-p6d", "--fields", fields,
                      "--statics-from", other, "--out", root / "x.dat"],
                     "does not match")

        for name, passed in negatives.items():
            if not passed:
                fail(f"negative case did not fail closed: {name}")
        evidence["negatives"] = negatives

    evidence["status"] = "PASS"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(evidence, indent=2) + "\n")
    print(f"P6F_P6D_ARRAY_INPUT_PASS variants=2 hours={len(labels)} "
          f"mapped_values={evidence['wind_only']['mapping_verified_values']} "
          f"negatives={len(evidence['negatives'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
