#!/usr/bin/env python3
"""Locate first *source stage* disagreement for frozen Hefei first-hour H-3.

Compare original instrumented CALCPF and independent source/MET-driven C++
CALCPF; the original puff.con must remain an immutable post-run oracle.
This reports actual errors and does not loosen any acceptance tolerance.
"""
import argparse
import json
import math
from pathlib import Path
import struct

RECORD = struct.Struct("<3i13f")
FRACTION = struct.Struct("<3if")
NAMES = ("syrec", "szrec", "zpr", "zrpole", "f1", "xi1", "xi2",
         "t1", "t2", "qold", "qnew", "xtemp", "conc")
SOURCE_ORDER = ("qold", "qnew", "syrec", "szrec", "zpr", "zrpole", "f1",
                "xi1", "xi2", "t1", "t2", "xtemp", "conc")


def check(rows: list, origin: str) -> dict:
    seen = {}
    for seq, ii, ksam, values in rows:
        if not (1 <= seq <= 1275 and 1 <= ii <= 54 and
                1 <= ksam <= 54 and len(values) == 13 and
                all(math.isfinite(x) for x in values)):
            raise ValueError(f"bad {origin} CALCPF trace {(seq, ii, ksam)}")
        if seq in seen:
            raise ValueError(f"duplicate {origin} physical step {seq}")
        seen[seq] = (ii, ksam, dict(zip(NAMES, values)))
    if not seen:
        raise ValueError(f"empty {origin} CALCPF trace")
    if list(seen) != sorted(seen):
        raise ValueError(f"{origin} CALCPF records not in COMP canonical order")
    return seen


def load_original(path: Path) -> dict:
    rows = []
    with path.open("rb") as fp:
        while chunk := fp.read(RECORD.size):
            if len(chunk) != RECORD.size:
                raise ValueError("truncated vendor receiver record")
            extra = fp.read(FRACTION.size)
            if len(extra) != FRACTION.size:
                raise ValueError("truncated paired original receptor FRAC")
            seq, ii, ksam, *floats = RECORD.unpack(chunk)
            vseq, vid, vksam, frec = FRACTION.unpack(extra)
            if (seq, ii, ksam) != (vseq, vid, vksam):
                raise ValueError("vendor PUFRECS FRAC key does not match CALCPF")
            if not math.isfinite(frec):
                raise ValueError("non-finite original PUFRECS FRAC")
            rows.append((seq, ii, ksam, floats))
    return check(rows, "ORIGINAL")


def load_native(path: Path) -> dict:
    rows = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        words = line.split()
        if len(words) != 16:
            raise ValueError(f"native CALCPF trace must have 3 keys/13 floats: {line}")
        rows.append((int(words[0]), int(words[1]), int(words[2]),
                     tuple(float(word) for word in words[3:])))
    return check(rows, "NATIVE")


def bits(value: float) -> int:
    return struct.unpack("<I", struct.pack("<f", value))[0]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--original", required=True, type=Path)
    p.add_argument("--native", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    original, native = load_original(args.original), load_native(args.native)
    orig_keys, native_keys = set(original), set(native)
    both = sorted(orig_keys & native_keys)
    if not both:
        raise ValueError("no aligned original/native H-3 receptor physical steps")
    first = None
    equal_per_field = {field: 0 for field in NAMES}
    # Compare per-index absolute/relative differences without thresholding.
    errors = {field: {"max_abs": 0.0, "max_relative": 0.0} for field in NAMES}
    for seq in sorted(orig_keys | native_keys):
        if seq not in original or seq not in native:
            if first is None:
                first = {"seq": seq, "reason": "different receptor coverage",
                         "vendor_included": seq in original,
                         "native_included": seq in native}
            continue
        oid, oksam, oval = original[seq]
        nid, nksam, nval = native[seq]
        if (oid, oksam) != (nid, nksam):
            if first is None:
                first = {"seq": seq, "reason": "different puff identity/KSAM",
                         "vendor": [oid, oksam], "native": [nid, nksam]}
            continue
        for field in NAMES:
            before, after = oval[field], nval[field]
            err = abs(before-after)
            errors[field]["max_abs"] = max(errors[field]["max_abs"], err)
            if before != 0.0:
                errors[field]["max_relative"] = max(
                    errors[field]["max_relative"], err/abs(before))
            if bits(before) == bits(after):
                equal_per_field[field] += 1
        if first is None:
            for field in SOURCE_ORDER:
                before, after = oval[field], nval[field]
                if bits(before) != bits(after):
                    first = {
                        "seq": seq, "puff": oid, "ksam": oksam,
                        "first_differing_field_by_source_priority": field,
                        "vendor_bits": hex(bits(before)),
                        "native_bits": hex(bits(after)),
                        "vendor": before, "native": after,
                        "abs_error": abs(before-after),
                        "all_stage_values_original": oval,
                        "all_stage_values_native": nval,
                    }
                    break
    # Independent original-stage equivalence for the specifically supported
    # 196 CALCPF first-hour H-3 hotspot events. These are exact source
    # contracts, not a replacement for full concentration field acceptance.
    mandatory_fields=("qold","qnew","syrec","szrec","zpr","zrpole","f1",
                      "xi1","xi2","t1","t2","xtemp","conc")
    if (len(original)!=196 or len(native)!=196 or orig_keys!=native_keys):
        raise AssertionError("frozen first-hour H3 CALCPF event set diverged")
    for field in mandatory_fields:
        if equal_per_field[field]!=len(both):
            raise AssertionError(
                f"frozen H3 CALCPF mandatory original stage {field} "
                f"only {equal_per_field[field]}/{len(both)} REAL4 equal")
    print("P7_HEFEI_H3_PUFRECS_PFSAMP_CALCPF_REAL4=PASS"
          " RECEPTOR_I=19 RECEPTOR_J=50 SUBSTEPS=196"
          " MASS_QOLD_QNEW=BITWISE"
          " RECEPTOR_SIGTY_SIGTZ=BITWISE"
          " ZPR_ZRPOLE_VCOUP=BITWISE"
          " PFSAMP_XI1_XI2=BITWISE"
          " CALCPF_T1_T2_AND_CONCENTRATION=BITWISE"
          " FULL_2500_RECEPTOR_GATE=SEPARATE"
          " FULL_143H=NOT_YET_ACCEPTED")
    summary = {
        "status": "DIAGNOSTIC_WITH_EXACT_UPSTREAM_PARITY_GATE",
        "original_sampled_substeps": len(original),
        "native_sampled_substeps": len(native),
        "exactly_aligned_step_keys": len(both),
        "original_only_steps": sorted(orig_keys-native_keys),
        "native_only_steps": sorted(native_keys-orig_keys),
        "first_stage_difference": first,
        "bitwise_equal_per_field": equal_per_field,
        "field_errors": errors,
        "full_hour_field_parity": "OPEN_NOT_CLAIMED",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2) + "\n")
    print("P7_HEFEI_H3_CALCPF_FIRST_DIVERGENCE=DIAGNOSTIC"
          f" VENDOR_SAMPLES={len(original)}"
          f" NATIVE_SAMPLES={len(native)}"
          f" ALIGNED={len(both)}"
          f" SOURCE_ONLY={len(orig_keys-native_keys)}"
          f" NATIVE_ONLY={len(native_keys-orig_keys)}"
          f" FIRST={json.dumps(first, sort_keys=True) if first else 'NONE'}"
          " FULL_FIELD_PARITY=OPEN")
    print("P7_HEFEI_H3_CALCPF_STAGE_BITWISE=" +
          " ".join(f"{field}:{equal_per_field[field]}/{len(both)}"
                   for field in SOURCE_ORDER))


if __name__ == "__main__":
    main()
