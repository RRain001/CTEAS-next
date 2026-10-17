#!/usr/bin/env python3
"""Real-data gate: the P7 2022 ledger must refuse the historical 2023 case.

The immutable original case project/cases/smoke5d_coldstart_20260701 is a real
2023 50x50 1 km CALMET/CALPUFF run, not the 2022 100 m reference. This test
feeds its real MET.DAT and control file to the native 2022 ledger and requires
a fail-closed refusal with the observed geometry/time reported verbatim, so a
historical case can never be relabelled as the 2022 evidence.

It is file-driven, not a physics test. When the case is absent (for example a
sparse CI checkout) the CTest registration skips; the P7 scoped workflow runs
the same script with --require after downloading the immutable blobs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
CASE_RUN = REPO_ROOT / "project/cases/smoke5d_coldstart_20260701/run"
MET_REL = "met/met.dat"
CONTROL_REL = "puff/puff.inp"
# Git blob SHA1 identities of the immutable historical case, matching
# reference/legacy_2023_case.py. Source bytes are verified before they are used.
GIT_BLOB_SHA1 = {
    MET_REL: "cd0af6fed77639a5e7205bc1fc4f9e4421b41926",
    CONTROL_REL: "67dcdb856c0af92d30de346d4877af3b7d80db6f",
}


def git_blob_sha1(path: Path) -> str:
    size = path.stat().st_size
    digest = hashlib.sha1(f"blob {size}\0".encode())  # noqa: S324 - Git object identity
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def fail(message: str) -> None:
    print(f"P7_2022_LEDGER_REAL_2023_GATE=FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, required=True,
                        help="built cteas_p7_2022_case_ledger executable")
    parser.add_argument("--report", type=Path, help="where to keep the refusal ledger JSON")
    parser.add_argument("--require", action="store_true",
                        help="fail instead of skipping when the historical case is absent")
    args = parser.parse_args()
    if not args.binary.is_file():
        fail(f"ledger binary missing: {args.binary}")
    met = CASE_RUN / MET_REL
    control = CASE_RUN / CONTROL_REL
    if not (met.is_file() and control.is_file()):
        if args.require:
            fail(f"historical 2023 case absent under {CASE_RUN}")
        print("P7_2022_LEDGER_REAL_2023_GATE=SKIPPED_HISTORICAL_CASE_ABSENT")
        return 0
    for relative, expected in GIT_BLOB_SHA1.items():
        observed = git_blob_sha1(CASE_RUN / relative)
        if observed != expected:
            fail(f"historical identity drift {relative}: {observed} != {expected}")

    holder = None
    if args.report:
        report = args.report
        report.parent.mkdir(parents=True, exist_ok=True)
    else:
        holder = tempfile.TemporaryDirectory(prefix="p7-2022-ledger-")
        report = Path(holder.name) / "ledger.json"

    run = subprocess.run(
        [str(args.binary), "--met", str(met), "--control", str(control), "--report", str(report)],
        capture_output=True, text=True)
    ledger = json.loads(report.read_text())
    if run.returncode != 4 or ledger.get("exit_code") != 4:
        fail(f"historical 2023 case was not refused: exit={run.returncode} status={ledger.get('status')}")
    if ledger.get("status") != "REJECTED_NOT_CANONICAL_2022":
        fail(f"unexpected ledger status {ledger.get('status')}")
    if ledger.get("canonical_2022") is not False or ledger.get("reference_class") != "NOT_CANONICAL_2022":
        fail("ledger claimed a canonical 2022 class for the historical 2023 case")
    if ledger.get("missing_roles"):
        fail(f"inputs were reported missing instead of evaluated: {ledger['missing_roles']}")

    checks = {row["check"]: row for row in ledger["checks"]}
    observed = {
        "met_nx": "50", "met_ny": "50", "met_nz": "9",
        "met_dx_m": "1000.000", "met_hourly_intervals": "119",
        "met_first_begin_unix_seconds": "1672531200",
        "met_final_end_unix_seconds": "1672959600",
    }
    for name, expected in observed.items():
        if checks.get(name, {}).get("observed") != expected:
            fail(f"{name} observed {checks.get(name, {}).get('observed')!r}, expected {expected!r}")
    for name in ("met_dx_m", "met_hourly_intervals", "met_first_begin_unix_seconds",
                 "met_final_end_unix_seconds", "met_origin_inside_2022_crop_window",
                 "control_start_date", "control_end_date", "control_dgrid_km"):
        if checks.get(name, {}).get("result") != "FAIL":
            fail(f"{name} did not fail for the historical case")
    for name in ("met_nx", "met_ny", "met_nz", "calpuff_control_contract", "original_met_dat_contract"):
        if checks.get(name, {}).get("result") != "PASS":
            fail(f"{name} did not pass for the historical case")
    roles = {artifact["role"]: artifact for artifact in ledger["artifacts"]}
    if len(roles.get("original_met_dat", {}).get("sha256", "")) != 64:
        fail("MET.DAT evidence hash was not recorded")
    if "NO_ORIGINAL" not in " ".join(ledger.get("limitations", [])) and \
       "HISTORICAL_OR_FOREIGN_CASES_CANNOT_BE_RELABELLED" not in " ".join(ledger.get("limitations", [])):
        fail("refusal limitation was not recorded")

    print("P7_2022_LEDGER_REAL_2023_REFUSAL=PASS"
          " DX_M=1000 INTERVALS=119 FIRST_UNIX_SEC=1672531200"
          " STATUS=REJECTED_NOT_CANONICAL_2022")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
