#!/usr/bin/env python3
"""Read-only original CALPUFF 2022 H9/P585/KSAM1 LCALM DGM audit.

This tool only decodes the pinned, independently generated vendor 143-hour
DGM. It never supplies native winds, sigmas, puff state or concentration.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct

RECORD = struct.Struct("<24i64f")
EXPECTED_ORIGINAL_DGM_SHA = "cbbdaa29c6222e6ca6aefe9f605ad13e7dd6d258f6ad243afcac07cb578108c6"
EXPECTED_TOTAL = 254687
H9_PACKED = 202200108
PUFF = 585
KSAM = 1


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--original-dgm", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    digest = hashlib.sha256()
    selected = []
    count = 0
    with args.original_dgm.open("rb") as source:
        while raw := source.read(RECORD.size):
            if len(raw) != RECORD.size:
                raise AssertionError("original full DGM record truncated")
            digest.update(raw)
            count += 1
            values = RECORD.unpack(raw)
            integers, floats = values[:24], values[24:]
            if (integers[1], integers[3], integers[16]) != (
                H9_PACKED, PUFF, KSAM
            ):
                continue
            selected.append({
                "global_record_1based": count,
                "packed_date_hour": integers[1],
                "puff_id": integers[3],
                "ksam": integers[16],
                "icode": integers[4],
                "start_cell_i": integers[5],
                "start_cell_j": integers[6],
                "PGT": integers[8],
                "lcalm": integers[17],
                "u_advect_ms": floats[9],
                "v_advect_ms": floats[10],
                "comp_wind_speed_ms": floats[11],
                "adjusted_u_ms": floats[12],
                "adjusted_v_ms": floats[13],
                "x_begin_cells": floats[0],
                "y_begin_cells": floats[1],
                "x_after_cells": floats[38],
                "y_after_cells": floats[39],
                "sigy_after_m": floats[42],
                "sigz_after_m": floats[43],
                "tsamp_effective_s": floats[62],
            })

    actual_sha = digest.hexdigest()
    if count != EXPECTED_TOTAL or actual_sha != EXPECTED_ORIGINAL_DGM_SHA:
        raise AssertionError(
            f"original full DGM provenance changed: count={count} sha256={actual_sha}"
        )
    if not selected:
        raise AssertionError("pinned original H9 puff585 KSAM1 is missing")
    # The first actual unsupported native calm/terrain/dry/receptor boundary
    # is part of the immutable ORIGINAL 143-hour source trace. Check it as
    # binary32, never as rounded decimal output or a fitted tolerance.
    if len(selected) != 1:
        raise AssertionError(f"expected one original H9 puff585 KSAM1 record, got {len(selected)}")
    first = selected[0]
    source_identity = {
        "global_record_1based": 16420,
        "packed_date_hour": H9_PACKED,
        "puff_id": PUFF,
        "ksam": KSAM,
        "icode": 1,
        "PGT": 3,
        "lcalm": 1,
    }
    for field, expected in source_identity.items():
        if first[field] != expected:
            raise AssertionError(
                f"original H9 calm source identity changed: {field}="
                f"{first[field]} expected={expected}"
            )
    expected_real4 = {
        "comp_wind_speed_ms": 0x3EB70DE3,
        "x_begin_cells": 0x424623BE,
        "y_begin_cells": 0x41E5A121,
        "x_after_cells": 0x4249BE4C,
        "y_after_cells": 0x41E7182F,
        "sigy_after_m": 0x438FB1D8,
        "sigz_after_m": 0x4313E71E,
    }
    def real4_bits(value: float) -> int:
        return struct.unpack("<I", struct.pack("<f", value))[0]

    for field, expected in expected_real4.items():
        actual = real4_bits(first[field])
        if actual != expected:
            raise AssertionError(
                f"original H9 calm REAL4 source drift: {field}="
                f"0x{actual:08x} expected=0x{expected:08x}"
            )
    if not (0.001 <= first["comp_wind_speed_ms"] < 0.5):
        raise AssertionError("original H9 LCALM and selected WSCALM=0.5 disagree")
    report = {
        "status": "ORIGINAL_FORTRAN_SOURCE_ONLY",
        "full_dgm_rows": count,
        "full_dgm_sha256": actual_sha,
        "key": {"hour": 9, "puff": PUFF, "ksam": KSAM},
        "records": selected,
        "original_h9_source_bitwise": "PASS",
        "expected_real4_bits": {k: f"0x{v:08x}" for k, v in expected_real4.items()},
        "native_state_injected": False,
        "source_fortran_modified": False,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    first = selected[0]
    print(
        "P7_ORIGINAL_H9_PUFF585_KSAM1=SOURCE_ONLY"
        f" GLOBAL_DGM={first['global_record_1based']}"
        f" RECORDS={len(selected)}"
        f" LCALM={first['lcalm']}"
        f" ICODE={first['icode']}"
        f" PGT={first['PGT']}"
        f" WS={first['comp_wind_speed_ms']:.9g}"
        f" XY_BEGIN={first['x_begin_cells']:.9g},{first['y_begin_cells']:.9g}"
        f" XY_AFTER={first['x_after_cells']:.9g},{first['y_after_cells']:.9g}"
        f" SIGY={first['sigy_after_m']:.9g}"
        f" SIGZ={first['sigz_after_m']:.9g}"
        " ORIGINAL_REAL4_SOURCE=BITWISE_PASS"
        " NATIVE_PHYSICS_PARITY=NOT_YET_ACCEPTED"
    )


if __name__ == "__main__":
    main()
