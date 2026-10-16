#!/usr/bin/env python3
"""Control-variable proof: native P6E must not consume reference hourly payloads.

Both runs use identical native C++ P6D U/V/W, real P4/P5 observations,
GEO.DAT, original source-mode controls and station ELUSTR2 state. Only the
reference CALMET.DAT hourly float records are modified. The reference may
currently supply geometry, station coordinates and clock labels; no native
physical field should change when its original computed hourly values change.

This is deliberately NOT a claim that the complete P6 chain is original-free.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import pathlib
import struct
import subprocess
import sys

PINNED_ORIGINAL = "b1823cda92280888d70b00961ab39486036a3086e18637fff21efb4f4b237d30"
GRID_CELLS = 2500
LABELS = ("U-LEV  1", "V-LEV  1", "T-LEV  1", "USTAR", "EL", "WSTAR", "ZI")
MISSING = 9999.0


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def mutation_bytes(original: bytes) -> tuple[bytes, list[dict]]:
    image = bytearray(original)
    offset = 0
    mutated: dict[str, dict] = {}
    while offset < len(image):
        if len(image) - offset < 8:
            raise RuntimeError("truncated original Fortran sequential record")
        length = struct.unpack_from("<i", image, offset)[0]
        end = offset + length + 8
        if length < 0 or end > len(image):
            raise RuntimeError("bad original Fortran record framing")
        if struct.unpack_from("<i", image, end - 4)[0] != length:
            raise RuntimeError("mismatched original Fortran record markers")
        if length == 24 + GRID_CELLS * 4:
            label = bytes(image[offset + 4:offset + 12]).decode("ascii")
            name = label.rstrip()
            if name in LABELS and name not in mutated:
                # Leave temporal 24-byte header and all static cells unchanged;
                # only perturb one finite, non-missing reference meteorological
                # value. The independent C++ P6E native path must ignore it.
                first = offset + 4 + 24
                for cell in range(GRID_CELLS):
                    at = first + cell * 4
                    old = struct.unpack_from("<f", image, at)[0]
                    if old != MISSING and abs(old) < 1.0e10:
                        delta = max(0.5, abs(old) * 0.01)
                        new = struct.unpack("<f", struct.pack("<f", old + delta))[0]
                        if old == new:
                            raise RuntimeError("REAL4 mutation unexpectedly rounded away")
                        struct.pack_into("<f", image, at, new)
                        mutated[name] = {"cell": cell, "original": old, "mutated": new}
                        break
                if name not in mutated:
                    raise RuntimeError("could not mutate finite hourly " + name)
        offset = end
    if set(mutated) != set(LABELS):
        raise RuntimeError("missing target reference hourly labels: " +
                           repr(sorted(set(LABELS) - mutated.keys())))
    if len(image) != len(original) or image == original:
        raise RuntimeError("no source reference payload changed")
    return bytes(image), [dict(label=label, **mutated[label]) for label in LABELS]


def command(args: argparse.Namespace, reference: pathlib.Path, out: pathlib.Path):
    out.mkdir(parents=True, exist_ok=True)
    cmd = [str(args.p6e), "emit-realcase",
           "--reference", str(reference),
           "--observations", str(args.observations),
           "--geo-file", str(args.geo),
           "--native-hour-comp", "1",
           "--native-p6d-dir", str(args.diagno),
           "--station-flux-csv", str(args.station_flux),
           "--first-hour", "0", "--hours", "1",
           "--state-prefix", str(out / "comp"),
           "--out", str(out / "met_native_1h.dat"),
           "--report", str(out / "report.json")]
    completed = subprocess.run(cmd, text=True, capture_output=True, timeout=300)
    (out / "p6e.log").write_text(completed.stdout + completed.stderr)
    if completed.returncode:
        raise RuntimeError(f"P6E failed under {reference}: " +
                           (completed.stdout + completed.stderr)[-2600:])
    return {
        "met_sha256": sha256((out / "met_native_1h.dat").read_bytes()),
        "history_zi_sha256": sha256((out / "comp.zi.f32").read_bytes()),
        "history_ziconv_sha256": sha256((out / "comp.ziconv.f32").read_bytes()),
        "history_dptt_sha256": sha256((out / "comp.dptt.f32").read_bytes()),
        "report": json.loads((out / "report.json").read_text())
    }


def main() -> int:
    p = argparse.ArgumentParser()
    for flag in ("reference", "observations", "geo", "diagno", "station-flux",
                 "p6e", "work", "report"):
        p.add_argument("--" + flag, required=True, type=pathlib.Path)
    args = p.parse_args()
    for name in ("reference", "observations", "geo", "diagno", "station_flux", "p6e"):
        if not getattr(args, name).exists():
            raise FileNotFoundError(str(getattr(args, name)))
    source = args.reference.read_bytes()
    if sha256(source) != PINNED_ORIGINAL:
        raise RuntimeError("original 143h reference hash drift")
    payload, changes = mutation_bytes(source)
    args.work.mkdir(parents=True, exist_ok=True)
    changed = args.work / "original_hourly_values_perturbed.dat"
    changed.write_bytes(payload)
    result_a = command(args, args.reference, args.work / "unmodified")
    result_b = command(args, changed, args.work / "mutated")
    keys = ("met_sha256", "history_zi_sha256",
            "history_ziconv_sha256", "history_dptt_sha256")
    parity = {key: result_a[key] == result_b[key] for key in keys}
    report = {
        "status": "PASS" if all(parity.values()) else "FAIL",
        "scope": "native C++ P6E first hour with actual P6D wind; reference hourly-only mutation",
        "pinned_reference": PINNED_ORIGINAL,
        "reference_hourly_payload_mutations": changes,
        "reference_header_and_static_records_changed": False,
        "native_outputs_byte_equal": parity,
        "reference_meteorology_no_longer_required": False,
        "full_original_free_P6_accepted": False,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if not all(parity.values()):
        raise RuntimeError("P6E native path consumed reference hourly meteorological values")
    return 0


if __name__ == "__main__":
    sys.exit(main())
