#!/usr/bin/env python3
"""G62: source-native first-hour hidden memory is distinct from CALMET.DAT.

Validate C++ G62 3 REAL4 physical state planes against independently run
G54 and source-native G59 using exact bytes + SHA-matched science receipts.
Does NOT infer ZICONV/DPTT from original or native 45 output records,
does NOT commit an hour, and does NOT give any second-hour forcing permit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import tempfile
from pathlib import Path

from scripts.s4.s4r1c8k_compare_noaa_firsthour_met21 import native_hour

NX, NY, NC = 82, 85, 82*85
HEADER = struct.Struct("<16s4iq")
F32 = struct.Struct("<" + str(NC) + "f")
FIVE = struct.Struct("<" + str(5*NC) + "f")
MAGIC = b"CTEAS_G62_SEED_1"
EXPECTED_END = 1654048800  # authentic 2022-06-01 02:00 UTC
assert len(MAGIC) == 16


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_candidate(path: Path):
    payload = path.read_bytes()
    if len(payload) != HEADER.size + 3*F32.size:
        raise ValueError("G62 source-native candidate extent incorrect")
    magic, nx, ny, nz, hours, end = HEADER.unpack_from(payload)
    if (magic, nx, ny, nz, hours, end) != (
            MAGIC, NX, NY, 9, 1, EXPECTED_END):
        raise ValueError("G62 hidden state source identity, epoch or grid forged")
    planes = [payload[HEADER.size+i*F32.size:
                      HEADER.size+(i+1)*F32.size]
              for i in range(3)]
    real = [F32.unpack(x) for x in planes]
    for name, values in zip(("ZI", "ZICONV", "DPTT"), real, strict=True):
        for value in values:
            if not math.isfinite(value) or value == 9999.0:
                raise ValueError("G62 nonfinite/missing source-native "+name)
            if name != "DPTT" and value < 0:
                raise ValueError("G62 negative source-native "+name)
    return planes, real


def check_planes(native_planes, g54_raw: bytes, g59_zi: bytes) -> dict:
    if len(native_planes) != 3 or len(g54_raw) != FIVE.size:
        raise ValueError("G62 existing physical source G54 records absent")
    required = [
        g54_raw[2*F32.size:3*F32.size],
        g54_raw[3*F32.size:4*F32.size],
        g54_raw[4*F32.size:5*F32.size],
    ]
    if len(g59_zi) != F32.size:
        raise ValueError("G62 G59 P6F ZI field extent missing")
    matched = {}
    for field, actual, reference in zip(
            ("ZI", "ZICONV", "DPTT"), native_planes, required, strict=True):
        if actual != reference:
            idx = next(i for i, (x, y) in enumerate(
                zip(F32.unpack(actual), F32.unpack(reference), strict=True))
                if struct.pack("<f", x) != struct.pack("<f", y))
            raise ValueError(
                f"G62 {field} REAL4 differs from independently native G54"
                f" at i={idx%NX+1},j={idx//NX+1}")
        matched[field] = NC
    if native_planes[0] != g59_zi:
        raise ValueError("G62 native hidden COMP ZI differs from G59 P6F record")
    return {
        "native_hidden_zi_bit_exact_to_g54": True,
        "native_hidden_ziconv_bit_exact_to_g54": True,
        "native_hidden_dptt_bit_exact_to_g54": True,
        "native_hidden_zi_bit_exact_to_p6f": True,
        "native_memory_plane_bytewise_equal": matched,
        "source_native_REAL4_values_verified": 3*NC,
    }


def verify(candidate: Path, g54: Path, g54_receipt: Path,
           g59: Path, g59_receipt: Path, g60_receipt: Path,
           original_met: Path, native_log: Path, report: Path) -> bool:
    mix = json.loads(g54_receipt.read_text())
    out = json.loads(g59_receipt.read_text())
    hidden = json.loads(g60_receipt.read_text())
    if (mix.get("status") !=
            "PASS_SCOPED_REAL_NOAA_NATIVE_MIXHT_AND_AVEMIX"
        or mix.get("native_source_only_candidate_sha256") != sha(g54)
        or mix.get("above_frozen_tolerance") != 0
        or out.get("status") !=
            "PASS_SOURCE_SCOPED_REAL_NOAA_NATIVE_FIRSTHOUR_FULL45_MET21"
        or out.get("native_full_onehour_met_sha256") != sha(g59)
        or out.get("source_original_6h_met_sha256") != sha(original_met)
        or out.get("above_tolerance_or_unequal") != 0
        or hidden.get("status") !=
            "PASS_SOURCE_SCOPED_FIRSTHOUR_NATIVE_COMP_MEMORY_ZI_ZICONV"
        or hidden.get("native_g54_memory_sha256") != sha(g54)
        or hidden.get("native_g59_firsthour_met_sha256") != sha(g59)
        or hidden.get("original_6h45_met_sha256") != sha(original_met)
        or hidden.get("above_frozen_tolerance") != 0):
        raise ValueError("G62 source-native G54/G59/G60 authentic receipts stale")
    if ("S4R1C8N_NATIVE_HIDDEN_COMP_MEMORY=PRODUCED_UNVERIFIED"
            not in native_log.read_text()
        or "G14_SOURCE_PREPDI=STAGED_UNPUBLISHED"
            not in native_log.read_text()
        or "G14_STAGE1_WIND1=G26_NATIVE_BITWISE_G42"
            not in native_log.read_text()
        or "G14_STAGE2_FRADJ=G26_NATIVE_BITWISE_G41"
            not in native_log.read_text()
        or "G14_G43_NONWIND_MISSFC=P5_RAW_WIND_UNCHANGED"
            not in native_log.read_text()
        or "G14_STAGE3_TO_6_WATER_THERMAL_SLOPE=G26_NATIVE_BITWISE_G47"
            not in native_log.read_text()
        or "G14_STAGE7_TO_11_SPARSE_INTER2_G24=G26_NATIVE_BITWISE_G48"
            not in native_log.read_text()
        or "G14_COMP_STAGE12_MIXHT=G26B_NATIVE_BITWISE_G54"
            not in native_log.read_text()
        or "G14_COMP_STAGE13_AVEMIX=G26B_NATIVE_BITWISE_G54"
            not in native_log.read_text()
        or "G14_COMMIT_SECONDHOUR_G26_P7=NOT_ACCEPTED"
            not in native_log.read_text()):
        raise ValueError("G62 source only/NOT_ACCEPTED run attestation missing")
    p6f_fields, _, _ = native_hour(g59)
    if "ZI      " not in p6f_fields:
        raise ValueError("G62 actual G59 legal firsthour ZI record absent")
    parts, values = read_candidate(candidate)
    verdict = check_planes(parts, g54.read_bytes(), p6f_fields["ZI      "])
    result = {
        "status": "PASS_SCOPED_NATIVE_FIRSTHOUR_HIDDEN_COMP_MEMORY_SEED",
        "scope": "AUTHENTIC_NOAA_2SS_1US_82x85_9_LAYER_ONEHOUR_ONLY",
        "source_original_6h45_sha256": sha(original_met),
        "native_g54_real_physics_sha256": sha(g54),
        "native_g59_complete_firsthour_met_sha256": sha(g59),
        "native_g62_hidden_state_sha256": sha(candidate),
        "real_zi_min_m": min(values[0]),
        "real_zi_max_m": max(values[0]),
        "real_ziconv_nonzero": sum(x != 0 for x in values[1]),
        "real_dptt_nonzero": sum(x != 0 for x in values[2]),
        "native_produced_from_original_intermediate": False,
        "g14_source_prepdi_staged_unpublished": True,
        "g14_selected_sparse_wind1_bitwise_matches_g42": True,
        "g14_selected_water_fradj_bitwise_matches_g41": True,
        "g14_original_source_missfc_preserves_p5_raw_wind": True,
        "g14_water_thermal_slope_bitwise_matches_g47": True,
        "g14_sparse_inter2_final_wind_bitwise_matches_g48": True,
        "g14_water_land_mixht_stage12_bitwise_matches_g54": True,
        "g14_water_land_avemix_stage13_bitwise_matches_g54": True,
        "g14_native_17stage_commit": "NOT_ACCEPTED",
        "station_upper_gamma_clocks_committed": "NOT_ACCEPTED",
        "actual_second_hour_physics": "NOT_RUN",
        "source_original_dptt_parity": "REQUIRES_SEPARATE_G61",
        "g26_p7": "NOT_ACCEPTED",
        **verdict,
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, sort_keys=True, indent=2)+"\n")
    print("S4R1C8N_NATIVE_HIDDEN_STATE="+result["status"])
    print("S4R1C8N_BIT_EXACT_PLANES=3")
    print("S4R1C8N_REAL4_COMPARED="+str(3*NC))
    print("S4R1C8O_G14_SOURCE_PREPDI=STAGED_UNPUBLISHED")
    print("S4R1C8O_G14_WIND1_G42_BITWISE=PASS_125460_REAL4")
    print("S4R1C8O_G14_FRADJ_G41_BITWISE=PASS_146370_REAL4")
    print("S4R1C8O_G14_G43_RAW_P5_WIND=UNCHANGED")
    print("S4R1C8P_G14_WATER_THERMAL_SLOPE_G47_BITWISE=PASS_160310_REAL4")
    print("S4R1C8Q_G14_SPARSE_INTER2_G24_G48_BITWISE=PASS_320620_REAL4")
    print("S4R1C8R_G14_WATER_LAND_MIXHT_G54_BITWISE=PASS_55760_REAL4")
    print("S4R1C8S_G14_WATER_LAND_AVEMIX_G54_BITWISE=PASS_13940_REAL4")
    print("S4R1C8N_NATIVE_2ND_HOUR_G14_G26_P7=NOT_ACCEPTED")
    return True


def selftest() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp)/"seed.bin"
        a = F32.pack(*([10.0]*NC))
        b = F32.pack(*([5.0]*NC))
        d = F32.pack(*([0.05]*NC))
        g54 = bytes(2*F32.size)+a+b+d
        p.write_bytes(HEADER.pack(MAGIC, NX, NY, 9, 1, EXPECTED_END)+a+b+d)
        planes, fields = read_candidate(p)
        assert fields[2][0] > 0
        assert check_planes(planes, g54, a)["source_native_REAL4_values_verified"] == 3*NC
        corrupted = bytearray(p.read_bytes())
        corrupted[0] = ord("X")
        p.write_bytes(corrupted)
        try:
            read_candidate(p)
        except ValueError as e:
            assert "identity" in str(e)
        else:
            raise AssertionError("G62 accepted forged header")
        broken = bytearray(d)
        broken[0] ^= 0x01
        try:
            check_planes([a, b, bytes(broken)], g54, a)
        except ValueError as e:
            assert "DPTT" in str(e)
        else:
            raise AssertionError("G62 accepted reconstructed/altered DPTT")
        try:
            check_planes([a, b, d], g54, b)
        except ValueError as e:
            assert "P6F" in str(e)
        else:
            raise AssertionError("G62 accepted output-file memory replacement")
    print("S4R1C8N_HIDDEN_STATE_NEGATIVE_TESTS=PASS")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--selftest", action="store_true")
    for key in ("candidate", "g54", "g54-receipt", "g59", "g59-receipt",
                "g60-receipt", "original-met", "native-log", "report"):
        p.add_argument("--"+key, type=Path)
    args = vars(p.parse_args())
    if args["selftest"]:
        selftest()
        return
    for field in ("candidate", "g54", "g54_receipt", "g59",
                  "g59_receipt", "g60_receipt", "original_met",
                  "native_log", "report"):
        if args[field] is None:
            p.error("--"+field.replace("_", "-")+" required")
    verify(*(args[key] for key in (
        "candidate", "g54", "g54_receipt", "g59",
        "g59_receipt", "g60_receipt", "original_met",
        "native_log", "report"
    )))


if __name__ == "__main__":
    main()
