#!/usr/bin/env python3
"""S4-R1c5b0: audit ONLY native G14 COMP memory provenance after successful commit.

Never feed this trace back to any C++ or original Fortran model. It is
not an original-vs-native scientific parity test; it is a fail-closed
software/clock handoff verifier for the existing unified native actor.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import struct
import tempfile
from pathlib import Path

HEADER = ("hour_index", "end_epoch_s", "stage", "i", "j",
          "zi_m", "ziconv_m", "dptt_k")
STAGES = ("PRE_DIAGNO", "POST_COMP")


def bits(value: float) -> bytes:
    return struct.pack("!f", value)


def verify(path: Path, nx: int, ny: int, hours: int) -> dict:
    if nx < 2 or ny < 2 or hours < 1:
        raise ValueError("invalid positive grid/clock dimensions")
    n = nx * ny
    total = 0
    first_epoch = None
    previous_post = None
    current_post = [None] * n
    per_hour = [{"hour": h, "post_positive_ziconv": 0,
                 "post_positive_zi": 0, "changed_during_hour": 0}
                for h in range(hours)]
    with path.open(newline="") as file:
        rows = csv.reader(file)
        if tuple(next(rows, ())) != HEADER:
            raise ValueError("native COMP trace schema mismatch")
        for raw in rows:
            if total >= 2 * n * hours:
                raise ValueError("extra native COMP state rows")
            hour = total // (2 * n)
            stage_number = (total // n) % 2
            idx = total % n
            i, j = idx % nx + 1, idx // nx + 1
            if len(raw) != 8:
                raise ValueError("wrong native COMP record width")
            if (int(raw[0]), raw[2], int(raw[3]), int(raw[4])) != (
                hour, STAGES[stage_number], i, j
            ):
                raise ValueError("misordered or repeated native COMP row")
            epoch = int(raw[1])
            if first_epoch is None:
                first_epoch = epoch
            if epoch != first_epoch + 3600 * hour:
                raise ValueError("non-contiguous source model-hour UTC")
            values = tuple(float.fromhex(x) for x in raw[5:])
            if not all(math.isfinite(x) for x in values):
                raise ValueError("nonfinite native model state")
            if values[0] < 0 or values[1] < 0:
                raise ValueError("negative native mixing height")
            current_bits = tuple(bits(x) for x in values)
            if stage_number == 0:
                if previous_post is not None and previous_post[idx] != current_bits:
                    raise ValueError(f"previous committed COMP state not carried at hour {hour}, cell {(i,j)}")
            else:
                current_post[idx] = current_bits
                per_hour[hour]["post_positive_ziconv"] += values[1] > 0
                per_hour[hour]["post_positive_zi"] += values[0] > 0
                if previous_post is not None and previous_post[idx] != current_bits:
                    per_hour[hour]["changed_during_hour"] += 1
            total += 1
            if total % (2 * n) == 0:
                if any(v is None for v in current_post):
                    raise ValueError("incomplete native POST_COMP hour")
                previous_post = current_post
                current_post = [None] * n
    if total != 2 * n * hours:
        raise ValueError(f"short native COMP state trace: {total} rows")
    result = {
        "status": "PASS_SOFTWARE_CAUSAL_STATE_TRACE_ONLY",
        "source": "NATIVE_G14_COMMITTED_STATE_NOT_VENDOR_ORACLE",
        "hours": hours, "nx": nx, "ny": ny,
        "rows": total, "handoff_cell_pairs": n * (hours - 1),
        "all_previous_post_to_next_pre_bit_exact": True,
        "hourly_diagnostics": per_hour,
        "native_original_45_field_parity": "NOT_RUN",
        "real_2SS1US_82x85_water_native_6h": "NOT_ACCEPTED",
        "P5_missing_calm_policy": "NOT_MODIFIED",
        "P7_production": "NOT_ACCEPTED"
    }
    return result


def selftest() -> None:
    nx, ny, hours = 2, 2, 2
    epoch = 1792569600
    lines = [",".join(HEADER)]
    for h in range(hours):
        for stage in STAGES:
            for j in range(1, ny + 1):
                for i in range(1, nx + 1):
                    zi = 0.0 if (h == 0 and stage == STAGES[0]) else (
                        5.0 if h == 0 or stage == STAGES[0] else 6.0
                    )
                    ziconv = zi
                    vals = [str(h), str(epoch + h * 3600), stage, str(i), str(j),
                            zi.hex(), ziconv.hex(), (0.0).hex()]
                    lines.append(",".join(vals))
    with tempfile.TemporaryDirectory() as d:
        trace = Path(d) / "trace.csv"
        trace.write_text("\n".join(lines) + "\n")
        assert verify(trace, nx, ny, hours)["handoff_cell_pairs"] == 4
        tampered = lines.copy()
        # Hour 2 PRE must equal hour 1 POST, not a zero or forged reset.
        target = 1 + 2 * nx * ny
        fields = tampered[target].split(",")
        fields[6] = (0.0).hex()
        tampered[target] = ",".join(fields)
        trace.write_text("\n".join(tampered) + "\n")
        try:
            verify(trace, nx, ny, hours)
        except ValueError as err:
            assert "not carried" in str(err), str(err)
        else:
            raise AssertionError("native COMP history reset was accepted")
        tampered = lines.copy()
        tampered[2] = tampered[1]
        trace.write_text("\n".join(tampered) + "\n")
        try:
            verify(trace, nx, ny, hours)
        except ValueError as err:
            assert "misordered" in str(err), str(err)
        else:
            raise AssertionError("duplicate/out-of-order state accepted")
    print("S4R1C5B0_NATIVE_TRACE_NEGATIVE_SELFTEST=PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("selftest")
    check = sub.add_parser("verify")
    check.add_argument("--trace", required=True, type=Path)
    check.add_argument("--nx", required=True, type=int)
    check.add_argument("--ny", required=True, type=int)
    check.add_argument("--hours", required=True, type=int)
    check.add_argument("--report", type=Path)
    args = parser.parse_args()
    if args.command == "selftest":
        selftest()
    else:
        result = verify(args.trace, args.nx, args.ny, args.hours)
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(result, indent=2) + "\n")
        print("S4R1C5B0_NATIVE_COMMITTED_ZI_ZICONV_DPTT=PASS_SOFTWARE_CAUSAL_ONLY")
        print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
