#!/usr/bin/env python3
"""Six comparisons from frozen four-arm CALMET x CALPUFF 143h evidence.

Two modes intentionally have different evidence strength:
* files: read four independent H-3 Fortran-sequential outputs, compare all
  six pairs directly and enforce bit-exact A/B and C/D.
* summaries: verify four archived, independently measured AB/AC/CD/BD
  comparisons, their shared artifact SHA/provenance and hourly results,
  then derive AD and BC mathematically (NOT re-read puff.con).

No solver, meteorology, reference concentration or vendor source is run here.
Different MET pairs are quantified, never forced to bitwise equality.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

from compare_p7_hourly_concentrations import compare, fail, read_fields

PAIRS = ("AB", "AC", "AD", "BC", "BD", "CD")
CROSS_MET = ("AC", "AD", "BC", "BD")
# All four cross-MET differences have the SAME orientation: original MET minus
# reconstructed MET, because A==B and C==D, elementwise as IEEE REAL4.
METRICS = (
    "hours", "nx", "ny", "values", "matching_real4", "bitwise_identical",
    "first_difference", "max_difference_location",
    "max_absolute_difference_bq_m3",
    "max_symmetric_relative_difference",
    "mean_absolute_difference_bq_m3", "rmse_bq_m3",
    "sum_concentration_a", "sum_concentration_b", "hourly",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def compact(value: dict, *, derivation: str, basis: str) -> dict:
    require(all(k in value for k in METRICS), f"missing fields in {basis}")
    result = {k: value[k] for k in METRICS}
    result["provenance"] = derivation
    result["basis"] = basis
    return result


def check_dimensions(value: dict, nx: int, ny: int, hours: int, name: str) -> None:
    require((value.get("nx"), value.get("ny"), value.get("hours"), value.get("values"))
            == (nx, ny, hours, nx * ny * hours),
            f"{name} hourly/dimension/REAL4 field count mismatch")
    hourly = value.get("hourly")
    require(isinstance(hourly, list) and len(hourly) == hours,
            f"{name} missing complete hourly analysis")
    for hour, item in enumerate(hourly, 1):
        require(item.get("hour_1based") == hour and item.get("values") == nx * ny
                and isinstance(item.get("matching_real4"), int)
                and 0 <= item["matching_real4"] <= nx * ny,
                f"{name} invalid/nonconsecutive hour {hour}")
        require(item.get("bit_exact") is (item["matching_real4"] == nx * ny),
                f"{name} contradictory hour {hour} bit-exact label")
    require(sum(x["matching_real4"] for x in hourly) == value["matching_real4"],
            f"{name} hourly matching count contradicts aggregate")
    require(isinstance(value.get("matching_real4"), int)
            and 0 <= value["matching_real4"] <= value["values"]
            and value.get("bitwise_identical") is
            (value["matching_real4"] == value["values"]),
            f"{name} contradictory total bitwise status")
    for metric in ("max_absolute_difference_bq_m3", "mean_absolute_difference_bq_m3",
                   "rmse_bq_m3", "max_symmetric_relative_difference",
                   "sum_concentration_a", "sum_concentration_b"):
        z = value.get(metric)
        require(isinstance(z, (float, int)) and math.isfinite(z) and z >= 0,
                f"{name} invalid numerical metric {metric}")
    if value["bitwise_identical"]:
        require(value["first_difference"] is None
                and value["max_absolute_difference_bq_m3"] == 0
                and value["rmse_bq_m3"] == 0, f"{name} false exactness evidence")


def check_identity(value: dict, pair: str) -> None:
    require(value["bitwise_identical"] is True
            and value["matching_real4"] == value["values"]
            and value["first_difference"] is None,
            f"{pair} must pass strict same-MET REAL4 bit identity")


def verify_cross_equal(reference: dict, compared: dict, pair: str) -> None:
    # Exact equality of all measured aggregate AND hourly metrics is a strong
    # closure check, independent of simply checking the maximum error.
    for name in METRICS:
        require(reference[name] == compared[name],
                f"{pair} differs from AC in {name}, despite AB/CD bit identity")


def from_files(files: dict[str, Path], nx: int, ny: int, hours: int) -> dict:
    require(set(files) == set("ABCD"), "four original A/B/C/D files required")
    fields = {arm: read_fields(path, nx, ny, hours) for arm, path in files.items()}
    raw = {pair: compare(fields[pair[0]], fields[pair[1]], nx, ny) for pair in PAIRS}
    for p, value in raw.items():
        check_dimensions(value, nx, ny, hours, p)
    check_identity(raw["AB"], "AB")
    check_identity(raw["CD"], "CD")
    for p in CROSS_MET:
        verify_cross_equal(raw["AC"], raw[p], p)
    return {
        "mode": "direct_four_files", "input_files": {
            arm: {k: v for k, v in f.items() if k != "fields"}
            for arm, f in fields.items()
        },
        "pairs": {p: compact(raw[p], derivation="DIRECT_RECORDED_REAL4",
                              basis=f"{p[0]}-vs-{p[1]} authentic hourly fields")
                  for p in PAIRS},
    }


def load_json(path: Path) -> dict:
    require(path.is_file() and path.stat().st_size > 0,
            f"missing/empty archive evidence {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"invalid archive JSON: {path}")
    return value


def require_sha(report: dict, side: str, expected: str, pair: str) -> None:
    item = report.get(side)
    require(isinstance(item, dict) and item.get("sha256") == expected
            and isinstance(expected, str) and len(expected) == 64,
            f"{pair} {side} input file SHA not bound to authoritative archive")


def from_summaries(summaries: dict[str, Path], provenance: Path,
                   nx: int, ny: int, hours: int) -> dict:
    require(set(summaries) == {"AB", "AC", "BD", "CD"},
            "four independently measured AB/AC/BD/CD reports required")
    raw = {pair: load_json(path) for pair, path in summaries.items()}
    prov = load_json(provenance)
    require(prov.get("scope") == "P7_C2_VENDOR_A_C_WITH_NONZERO_INTERNAL_SOURCE",
            "wrong archived case/science provenance")
    require(prov.get("nx") == nx and prov.get("ny") == ny
            and prov.get("hours") == hours, "archive case dimensions differ")
    require(prov.get("p6_pr63_sha")
            == "7a13cc6a2f2d7b4c99e18b8866043a0319733454",
            "PR63 frozen physical authority changed")
    sha_a = prov["A"]["puff_con_sha256"]
    sha_c = prov["C"]["puff_con_sha256"]
    require_sha(raw["AB"], "a", sha_a, "AB")
    require_sha(raw["CD"], "a", sha_c, "CD")
    require_sha(raw["BD"], "a", raw["AB"]["b"]["sha256"], "BD")
    require_sha(raw["BD"], "b", raw["CD"]["b"]["sha256"], "BD")
    for p, value in raw.items():
        check_dimensions(value, nx, ny, hours, p)
    check_identity(raw["AB"], "AB")
    check_identity(raw["CD"], "CD")
    for p in ("BD",):
        verify_cross_equal(raw["AC"], raw[p], p)
    pairs = {}
    for pair in PAIRS:
        if pair in raw:
            pairs[pair] = compact(raw[pair], derivation="MEASURED_ARCHIVED_COMPARATOR",
                                  basis=str(summaries[pair]))
        else:
            pairs[pair] = compact(raw["AC"], derivation="ALGEBRAIC_DERIVATION_NOT_REMEASURED",
                                  basis="AB and CD bit-exact, AC and BD independently measured")
    return {
        "mode": "archived_summary_closure", "source_provenance": str(provenance),
        "archived_reports": {p: str(x) for p, x in summaries.items()},
        "pairs": pairs,
    }


def build_report(case: str, evidence: dict, nx: int, ny: int, hours: int) -> dict:
    pairs = evidence["pairs"]
    require(list(pairs) == list(PAIRS), "pair matrix must have all six comparisons")
    for p in PAIRS:
        check_dimensions(pairs[p], nx, ny, hours, p)
    for p in ("AB", "CD"):
        check_identity(pairs[p], p)
    for p in CROSS_MET:
        verify_cross_equal(pairs["AC"], pairs[p], p)
    require(pairs["AC"]["matching_real4"] < pairs["AC"]["values"],
            "frozen case has no observed MET-propagated concentration sensitivity")
    return {
        "case": case, "hours": hours, "nx": nx, "ny": ny,
        "status": "PASS_SCOPE_RESTRICTED", "scientific_claims": {
            "same_met_AB_CD": "REAL4_BIT_IDENTICAL",
            "different_met_AC_BD": "MEASURED_NOT_EXPECTED_BIT_IDENTICAL",
            "cross_AD_BC": ("DIRECT" if evidence["mode"] == "direct_four_files"
                            else "DERIVED_NOT_DIRECTLY_MEASURED"),
            "interaction_(D-C)-(B-A)": "ZERO_EACH_HOUR_AND_CELL_BY_REAL4_IDENTITY",
            "annual_simulation": "NOT_PERFORMED",
        },
        "integrated_receptor_concentration": (
            "sum over hourly H-3 receptor concentration, NOT total emitted mass "
            "or dose; physical time/area integrals require corresponding weights"
        ),
        "evidence": {k: v for k, v in evidence.items() if k != "pairs"},
        "pair_matrix": pairs,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--case", choices=("C1", "C2"), required=True)
    p.add_argument("--mode", choices=("files", "summaries"), required=True)
    p.add_argument("--nx", type=int, required=True)
    p.add_argument("--ny", type=int, required=True)
    p.add_argument("--hours", type=int, default=143)
    p.add_argument("--report", type=Path, required=True)
    for arm in "abcd":
        p.add_argument(f"--{arm}", type=Path)
    for pair in ("ab", "ac", "bd", "cd"):
        p.add_argument(f"--{pair}-report", type=Path)
    p.add_argument("--provenance", type=Path)
    a = p.parse_args()
    try:
        require(a.nx > 0 and a.ny > 0 and a.hours > 0, "invalid grid or duration")
        if a.mode == "files":
            require(all(getattr(a, arm) is not None for arm in "abcd"),
                    "files mode requires all four independent output files")
            evidence = from_files(
                {arm.upper(): getattr(a, arm) for arm in "abcd"},
                a.nx, a.ny, a.hours)
        else:
            require(a.provenance is not None and
                    all(getattr(a, f"{pair}_report") is not None
                        for pair in ("ab", "ac", "bd", "cd")),
                    "summary mode requires four reports and source provenance")
            evidence = from_summaries(
                {pair.upper(): getattr(a, f"{pair}_report")
                 for pair in ("ab", "ac", "bd", "cd")},
                a.provenance, a.nx, a.ny, a.hours)
        result = build_report(a.case, evidence, a.nx, a.ny, a.hours)
        a.report.parent.mkdir(parents=True, exist_ok=True)
        a.report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        for p_name, item in result["pair_matrix"].items():
            print(f"P7_SIX_PAIR {a.case} {p_name} "
                  f"REAL4={item['matching_real4']}/{item['values']} "
                  f"MAX_ABS={item['max_absolute_difference_bq_m3']:.12g} "
                  f"PROVENANCE={item['provenance']}")
        print(f"P7_SIX_PAIR_CASE=PASS CASE={a.case} HOURS={a.hours} "
              f"MODE={evidence['mode']} ALL_SIX=CONSISTENT INTERACTION=ZERO")
        return 0
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print("P7_SIX_PAIR_BLOCKED: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
