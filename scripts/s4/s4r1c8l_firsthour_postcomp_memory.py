#!/usr/bin/env python3
"""S4-R1c8l: independent first-hour post-COMP memory handoff gate.

G54 produces native ZI/ZICONV/DPTT from real source, G59 serializes
that hour's verified 45 CALMET records. The independently run pristine
Fortran COMP stage trace is read ONLY by this subsequent comparator.
Nothing here commits G14 or computes another hour.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import tempfile
from pathlib import Path

from scripts.s4.s4r1c8e_original_mixht_avemix_stages import (
    NC, NX, NY, HEAD, PLANE, STAGES, decode, sha,
)
from scripts.s4.s4r1c8k_compare_noaa_firsthour_met21 import native_hour

FIVE = struct.Struct("<" + str(5 * NC) + "f")
F32 = struct.Struct("<" + str(NC) + "f")
ABS_ZI_M = 5e-3
REL_ZI = 5e-5


def audit_arrays(original_zi, original_zc, native_zi, native_zc,
                 native_dptt, serialized_zi) -> dict:
    if not all(len(x) == NC for x in (
        original_zi, original_zc, native_zi, native_zc,
        native_dptt, serialized_zi
    )):
        raise ValueError("G60 original/native 6970-cell memory extent changed")
    if F32.pack(*native_zi) != F32.pack(*serialized_zi):
        raise ValueError("G60 G54 post-AVEMIX ZI differs bitwise from native P6F ZI")
    for name, vals in (("native ZI", native_zi),
                       ("native ZICONV", native_zc)):
        if not all(math.isfinite(v) and 0 <= v <= 100000 for v in vals):
            raise ValueError("G60 nonfinite/negative native " + name)
    if not all(math.isfinite(v) and v != 9999.0 for v in native_dptt):
        raise ValueError("G60 uncomputed/nonfinite native DPTT memory")
    errors = []
    per = {}
    total = 0
    for label, orig, calculated in (
        ("ZI", original_zi, native_zi),
        ("ZICONV", original_zc, native_zc)
    ):
        above = 0
        maxabs = 0.0
        worst = None
        for idx, (a, b) in enumerate(zip(orig, calculated, strict=True)):
            if not math.isfinite(a) or a < 0:
                raise ValueError("G60 original post-COMP state invalid")
            delta = abs(a-b)
            if delta > maxabs:
                maxabs = delta
                worst = {"i": idx%NX+1, "j": idx//NX+1,
                         "original": a, "native": b, "abs_error": delta}
            if delta > ABS_ZI_M + REL_ZI*max(abs(a), abs(b)):
                above += 1
                if len(errors) < 20:
                    errors.append({"field": label, "i": idx%NX+1,
                                   "j": idx//NX+1, "original": a,
                                   "native": b, "abs_error": delta})
        per[label] = {
            "compared": NC, "above_frozen_tolerance": above,
            "max_abs_m": maxabs, "worst": worst
        }
        total += above
    return {
        "native_firsthour_zi_bitwise_identical_to_p6f": True,
        "zi_ziconv_original_native_comparisons": 2*NC,
        "above_frozen_tolerance": total,
        "fields": per, "first_exceedances": errors,
        "native_dptt_count": len(native_dptt),
        "native_dptt_min_k": min(native_dptt),
        "native_dptt_max_k": max(native_dptt),
        "native_dptt_original_parity": "NOT_ACCEPTED",
    }


def compare(original: Path, original_receipt: Path, native_g54: Path,
            native_g54_receipt: Path, native_g59: Path,
            native_g59_receipt: Path, original_met: Path,
            report: Path) -> bool:
    prev = json.loads(original_receipt.read_text())
    mixed = json.loads(native_g54_receipt.read_text())
    assembled = json.loads(native_g59_receipt.read_text())
    if (prev.get("status") !=
            "PASS_ORIGINAL_NOAA_WATER_TO_LAND_MIXHT_TO_AVEMIX_SOURCE_ONLY"
        or prev.get("original_trace_sha256") != sha(original)
        or prev.get("original_6h_45_met_byte_identical") is not True
        or prev.get("original_pristine_sha256") != sha(original_met)
        or mixed.get("status") !=
            "PASS_SCOPED_REAL_NOAA_NATIVE_MIXHT_AND_AVEMIX"
        or mixed.get("original_trace_sha256") != sha(original)
        or mixed.get("native_source_only_candidate_sha256") != sha(native_g54)
        or mixed.get("above_frozen_tolerance") != 0
        or assembled.get("status") !=
            "PASS_SOURCE_SCOPED_REAL_NOAA_NATIVE_FIRSTHOUR_FULL45_MET21"
        or assembled.get("above_tolerance_or_unequal") != 0
        or assembled.get("native_full_onehour_met_sha256") != sha(native_g59)
        or assembled.get("source_original_6h_met_sha256") != sha(original_met)
        or assembled.get("real_compared") != 43*NC
        or assembled.get("integer_compared") != 2*NC):
        raise ValueError("G60 lacks matching exact-source G54/G59/original receipts")
    if native_g54.stat().st_size != FIVE.size:
        raise ValueError("G60 G54 existing five-plane native COMP artifact malformed")
    values = FIVE.unpack(native_g54.read_bytes())
    # G54 five planes are before ZI, before ZICONV, after ZI,
    # after ZICONV, after MIXHT DPTT, all in original GEO i-fastest order.
    zi = values[2*NC:3*NC]
    zc = values[3*NC:4*NC]
    dptt = values[4*NC:5*NC]
    native_fields, _, _ = native_hour(native_g59)
    if "ZI      " not in native_fields:
        raise ValueError("G60 G59 legal P6F file missing ZI")
    source = decode(original)
    # Hour 2 in the immutable original trace is the first 01-02 UTC
    # record; stage 3 is after original full-domain AVEMIX.
    original_zi, original_zc = source[2, 3]
    verdict = audit_arrays(
        original_zi, original_zc, zi, zc, dptt,
        F32.unpack(native_fields["ZI      "])
    )
    result = {
        "status": (
            "PASS_SOURCE_SCOPED_FIRSTHOUR_NATIVE_COMP_MEMORY_ZI_ZICONV"
            if verdict["above_frozen_tolerance"] == 0 else
            "FAIL_SOURCE_SCOPED_FIRSTHOUR_COMP_MEMORY"
        ),
        "scope": "REAL_NOAA_2SS1US_FIRSTHOUR_ONLY_NO_G14_COMMIT",
        "original_6h45_met_sha256": sha(original_met),
        "original_comp_stage_trace_sha256": sha(original),
        "native_g54_memory_sha256": sha(native_g54),
        "native_g59_firsthour_met_sha256": sha(native_g59),
        "physical_original_intermediates_in_native": False,
        "native_firsthour_state_built": True,
        "g14_transaction_commit": "NOT_ACCEPTED",
        "next_hour_prior_state_used": "NOT_ACCEPTED",
        "sixhour_original_native_45field": "NOT_ACCEPTED",
        "g26_production": "NOT_ACCEPTED",
        "p7": "NOT_ACCEPTED",
        **verdict,
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2, sort_keys=True)+"\n")
    print("S4R1C8L_NATIVE_COMP_MEMORY=" + result["status"])
    print("S4R1C8L_COMP_STATE_EXCEED=" + str(verdict["above_frozen_tolerance"]))
    print("S4R1C8L_NATIVE_DPTT_ORIGINAL_PARITY=NOT_ACCEPTED")
    print("S4R1C8L_NEXT_HOUR_G14_G26_P7=NOT_ACCEPTED")
    return verdict["above_frozen_tolerance"] == 0


def selftest() -> None:
    ones = (50.0,) * NC
    zeros = (0.0,) * NC
    state = audit_arrays(ones, zeros, ones, zeros, zeros, ones)
    assert state["above_frozen_tolerance"] == 0
    assert state["zi_ziconv_original_native_comparisons"] == 2*NC
    bad = list(ones)
    bad[NC//2] += 1
    try:
        audit_arrays(ones, zeros, ones, zeros, zeros, bad)
    except ValueError as e:
        assert "bitwise" in str(e)
    else:
        raise AssertionError("G60 accepted forged P6F ZI")
    try:
        audit_arrays(ones, zeros, ones, zeros,
                     (float("nan"),) + zeros[1:], ones)
    except ValueError as e:
        assert "DPTT" in str(e)
    else:
        raise AssertionError("G60 accepted nonfinite native DPTT")
    corrupted = list(ones)
    corrupted[4] += 0.2
    out = audit_arrays(ones, zeros, corrupted, zeros, zeros, corrupted)
    assert out["above_frozen_tolerance"] == 1
    print("S4R1C8L_MEMORY_NEGATIVE_TESTS=PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selftest", action="store_true")
    for key in ("original", "original-receipt", "native-g54",
                "native-g54-receipt", "native-g59", "native-g59-receipt",
                "original-met", "report"):
        parser.add_argument("--"+key, type=Path)
    args = vars(parser.parse_args())
    if args["selftest"]:
        selftest()
        return
    for key in ("original", "original_receipt", "native_g54",
                "native_g54_receipt", "native_g59", "native_g59_receipt",
                "original_met", "report"):
        if args[key] is None:
            parser.error("--" + key.replace("_", "-") + " required")
    if not compare(
        args["original"], args["original_receipt"], args["native_g54"],
        args["native_g54_receipt"], args["native_g59"],
        args["native_g59_receipt"], args["original_met"], args["report"]
    ):
        raise SystemExit(3)


if __name__ == "__main__":
    main()
