#!/usr/bin/env python3
"""P6E E42: frozen 143 h real-case full-field verdict (original-wind driving).

Runs the whole P6E chain on the frozen 2022 reference case and requires the
acceptance the E42 ticket names, so the local gate reproduces it by itself:

  1. `p6e_p6c_hourly_bridge` -> the SURF/UP 2022 observation contract CSV;
  2. `p6e_calmet_dat21 emit-realcase --reference <met.dat> --wind-file
     <met.dat> --geo-file <GEO.DAT>` -> the candidate CALMET.DAT 2.1;
  3. `dump-field --field QSW` on both files must be **bit-identical for all
     143 hours** (the `dQSW == 0` acceptance, hours 6/9/33 included);
  4. `reference/compare_calmet_dat21.py` against the frozen reference
     (sha256 pinned) must report `PASS` with **0 total exceedances** over the
     18 P6E-owned fields.

Fail-closed: a missing case input is an error (exit 3, BLOCKED), never a
silent skip.  The case directory is resolved from the checkout first and then
from the shared local-gate driver checkout, because the p6e feature branch
predates the tracked `project/` tree.
"""
import argparse
import array
import hashlib
import json
import os
import pathlib
import subprocess
import sys

MET_SHA256 = \
    "b1823cda92280888d70b00961ab39486036a3086e18637fff21efb4f4b237d30"
HOURS = 143
CELLS = 2500
CASE_NAME = "hefei5km_2022_reference_case_20261011"


def resolve_case(repo_root):
    """Locate the frozen 2022 reference case.

    The case is tracked at `project/cases/<CASE_NAME>` on the integration
    branches, but not every branch/worktree carries it (the p6e feature branch
    predates the `project/` tree).  Search, in order: an explicit override, the
    checkout itself, then the shared local-gate host's driver checkout.
    """
    candidates = []
    override = os.environ.get("CTEAS_P6E_REAL_CASE")
    if override:
        candidates.append(pathlib.Path(override))
    candidates.append(repo_root / "project" / "cases" / CASE_NAME)
    gate_root = pathlib.Path(os.environ.get("CTEAS_GATE_ROOT", "/home/lhy/gate"))
    candidates.append(gate_root / "driver" / "project" / "cases" / CASE_NAME)
    for candidate in candidates:
        if (candidate / "run/met/met.dat").is_file():
            return candidate
    return None


def run(command, work):
    return subprocess.run([str(c) for c in command], cwd=str(work),
                          capture_output=True, text=True)


def load_f32(path):
    values = array.array("f")
    values.frombytes(pathlib.Path(path).read_bytes())
    return values


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True, type=pathlib.Path)
    parser.add_argument("--bridge", required=True, type=pathlib.Path)
    parser.add_argument("--tool", required=True, type=pathlib.Path)
    parser.add_argument("--work", required=True, type=pathlib.Path)
    parser.add_argument("--reference-sha256", default=MET_SHA256)
    args = parser.parse_args()

    case = resolve_case(args.repo_root)
    if case is None:
        print("P6E_FULL_FIELD_REFERENCE=BLOCKED: frozen case "
              f"{CASE_NAME} not found under {args.repo_root}/project/cases or "
              "the local-gate driver checkout")
        return 3
    met = case / "run/met/met.dat"
    surf = case / "met/surface/final/surf.dat"
    upper = case / "met/upperair/final/up_58424.dat"
    geo = case / "geo/makegeo/geo.dat"
    for required in (met, surf, upper, geo):
        if not required.is_file():
            print(f"P6E_FULL_FIELD_REFERENCE=BLOCKED missing {required}")
            return 3
    observed = hashlib.sha256(met.read_bytes()).hexdigest()
    if observed != args.reference_sha256:
        print(f"P6E_FULL_FIELD_REFERENCE=FAIL frozen met.dat sha256 {observed}")
        return 1

    args.work.mkdir(parents=True, exist_ok=True)
    hourly = args.work / "hourly.csv"
    candidate = args.work / "candidate.dat"
    reference_qsw = args.work / "reference-qsw.f32"
    candidate_qsw = args.work / "candidate-qsw.f32"
    verdict = args.work / "full-field-verdict.json"
    comparator = (pathlib.Path(__file__).resolve().parent.parent
                  / "reference" / "compare_calmet_dat21.py")

    steps = [
        [args.bridge, surf, upper, "58424", hourly],
        [args.tool, "emit-realcase", "--reference", met, "--observations",
         hourly, "--wind-file", met, "--geo-file", geo, "--out", candidate],
        [args.tool, "dump-field", "--file", met, "--field", "QSW",
         "--out", reference_qsw],
        [args.tool, "dump-field", "--file", candidate, "--field", "QSW",
         "--out", candidate_qsw],
        ["python3", comparator, "--tool", args.tool, "--reference", met,
         "--reference-sha256", args.reference_sha256, "--candidate",
         candidate, "--out", verdict],
    ]
    for command in steps:
        completed = run(command, args.work)
        if completed.returncode != 0:
            print(completed.stdout[-2000:])
            print(completed.stderr[-2000:])
            print("P6E_FULL_FIELD_REFERENCE=FAIL step "
                  f"{' '.join(str(c) for c in command[:2])}")
            return 1

    reference = load_f32(reference_qsw)
    produced = load_f32(candidate_qsw)
    if len(reference) != HOURS * CELLS or len(produced) != len(reference):
        print("P6E_FULL_FIELD_REFERENCE=FAIL QSW field size")
        return 1
    diff_hours = [h + 1 for h in range(HOURS)
                  if reference[h * CELLS:(h + 1) * CELLS]
                  != produced[h * CELLS:(h + 1) * CELLS]]
    qsw_identical = not diff_hours
    if not qsw_identical:
        print("P6E_FULL_FIELD_REFERENCE=FAIL dQSW != 0 in hours "
              + ",".join(str(h) for h in diff_hours[:20]))
        return 1

    report = json.loads(verdict.read_text())
    fields = report["comparison"]["fields"]
    owned = [f for f in fields if f["denominator"] > 0]
    total = sum(f.get("exceedances", 0) for f in fields)

    def field(label):
        return next((f for f in owned if f["label"].strip() == label), None)

    summary = {
        "status": report["status"],
        "status_detail": report["status_detail"],
        "total_exceedances": total,
        "owned_fields": len(owned),
        "dQSW_zero_hours": HOURS,
        "qsw_max_abs_error": field("QSW")["max_abs_error"] if field("QSW") else None,
        "el_exceedances": field("EL")["exceedances"] if field("EL") else None,
        "wstar_exceedances": field("WSTAR")["exceedances"] if field("WSTAR") else None,
        "wind_regime": "original CALMET.DAT wind (frozen met.dat)",
    }
    print(json.dumps(summary, indent=2))
    ok = qsw_identical and report["status"] == "PASS" and total == 0
    print("P6E_FULL_FIELD_REFERENCE=" + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
