#!/usr/bin/env python3
"""Audit CALPUFF 7.2.1 *original* Fortran precision before C++ parity claims.

Read original fixed-format source (columns 1..72), vendor COMMON-block
includes and the exact original build flags; compile a separate tiny Fortran
kind oracle with those flags. Never rewrite vendor source.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

from build_original_calpuff import FLAGS, VENDOR

_SELECTED_UNITS = ("POINTS1", "INJECT", "ADVECT", "COMP", "SETPUF",
                   "PUFRECS", "PFSAMP", "CALCPF")
_REAL_COMMON = {
    "pt1.puf": ("XPT1GRD", "YPT1GRD", "HTSTAK", "QSTAK"),
    "puff.puf": ("XPB", "YPB", "ZPB", "SIGYB", "QU", "QM"),
}
_BANNED = ("-fdefault-real-8", "-fdefault-real-16", "-fdefault-integer-8",
           "-freal-4-real-8", "-freal-4-real-16", "-r8", "-i8")


def fixed_statements(data: bytes) -> list[tuple[int, str]]:
    """Fixed-form executable/declaration lines, not comments or seq IDs."""
    result = []
    for lineno, raw in enumerate(data.decode("latin-1").splitlines(), start=1):
        if not raw or raw[0] in "cC*!dD":
            continue
        body = raw[:72]
        if len(body) < 7 or body[0:6].strip().startswith("!"):
            continue
        statement = body[6:].strip()
        if statement and not statement.startswith("!"):
            result.append((lineno, statement))
    return result


def subroutine_implicit_contract(statements: list[tuple[int,str]]) -> dict:
    """Extract selected routines' visible declaration region and exceptions."""
    units: dict[str, dict] = {}
    active = None
    sub = re.compile(r"^(?:SUBROUTINE|(?:REAL(?:\s*\*\s*\d+)?|DOUBLE\s+PRECISION|INTEGER(?:\s*\*\s*\d+)?)\s+FUNCTION)\s+(\w+)", re.I)
    for lineno, stmt in statements:
        found = sub.match(stmt)
        if found:
            active = found.group(1).upper()
            if active in _SELECTED_UNITS:
                units[active] = {"starts_at": lineno, "implicit": [],
                                 "explicit_real8": [], "explicit_real4": []}
            continue
        if active not in _SELECTED_UNITS:
            continue
        if re.match(r"^END(?:\s+SUBROUTINE)?\s*(?:!.*)?$", stmt, re.I):
            active = None
            continue
        if re.match(r"^IMPLICIT\b", stmt, re.I):
            units[active]["implicit"].append({"line": lineno, "statement": stmt})
        if re.match(r"^(?:DOUBLE\s+PRECISION|REAL\s*\*\s*8\b|REAL\s*\(\s*KIND\s*=\s*8\s*\))", stmt, re.I):
            units[active]["explicit_real8"].append({"line": lineno, "statement": stmt})
        if re.match(r"^REAL\s*\*\s*4\b", stmt, re.I):
            units[active]["explicit_real4"].append({"line": lineno, "statement": stmt})
    missing = sorted(set(_SELECTED_UNITS) - set(units))
    if missing:
        raise AssertionError("Original Fortran routines not found: " + ", ".join(missing))
    for name, details in units.items():
        for implicit in details["implicit"]:
            # Fail closed if an original routine changes to non-default REAL.
            line = implicit["statement"].upper().replace(" ", "")
            if "REAL*8" in line or "DOUBLEPRECISION" in line:
                raise AssertionError(f"{name} has non-default implicit REAL: {implicit}")
    return units


def validate_common_includes(vendor: Path) -> dict:
    manifests = {}
    for name, fields in _REAL_COMMON.items():
        path = vendor / name
        text = path.read_bytes().decode("latin-1")
        statements = fixed_statements(path.read_bytes())
        body = " ".join(s for _, s in statements).upper()
        if "COMMON/" not in body and "COMMON /" not in body:
            raise AssertionError(f"Missing COMMON block in {name}")
        # COMMON variables inherit default Fortran REAL unless explicitly
        # typed in their enclosing program unit, which is audited separately.
        for variable in fields:
            if not re.search(r"\b" + variable + r"\s*\(", body):
                raise AssertionError(f"{variable} missing from original {name}")
        manifests[name] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                           "default_real_fields": list(fields),
                           "original_comment_real": "- real" in text.lower()}
    return manifests


def kind_probe(compiler: str) -> dict:
    # This is compiled with precisely the flags used by the original build;
    # it is NOT a general Fortran language assertion.
    program = """
program p7kind
  implicit none
  real :: a
  real*4 :: b
  double precision :: c
  real*8 :: d
  integer :: i
  print '(A,I0)', 'P7_FORTRAN_DEFAULT_REAL_BYTES=', storage_size(a)/8
  print '(A,I0)', 'P7_FORTRAN_EXPLICIT_REAL4_BYTES=', storage_size(b)/8
  print '(A,I0)', 'P7_FORTRAN_DOUBLE_PRECISION_BYTES=', storage_size(c)/8
  print '(A,I0)', 'P7_FORTRAN_EXPLICIT_REAL8_BYTES=', storage_size(d)/8
  print '(A,I0)', 'P7_FORTRAN_DEFAULT_INTEGER_BYTES=', storage_size(i)/8
end program
"""
    with tempfile.TemporaryDirectory(prefix="p7-fortran-kinds-") as temp:
        base = Path(temp)
        src = base / "probe.f90"
        exe = base / "probe.x"
        src.write_text(program)
        subprocess.run([compiler, *FLAGS, str(src), "-o", str(exe)],
                       check=True, capture_output=True, text=True)
        output = subprocess.run([str(exe)], check=True, capture_output=True, text=True).stdout
    got = {}
    for line in output.splitlines():
        if "=" in line:
            key, value = line.strip().split("=", 1)
            got[key] = int(value)
    expected = {
        "P7_FORTRAN_DEFAULT_REAL_BYTES": 4,
        "P7_FORTRAN_EXPLICIT_REAL4_BYTES": 4,
        "P7_FORTRAN_DOUBLE_PRECISION_BYTES": 8,
        "P7_FORTRAN_EXPLICIT_REAL8_BYTES": 8,
        "P7_FORTRAN_DEFAULT_INTEGER_BYTES": 4,
    }
    if got != expected:
        raise AssertionError(f"Original Fortran compiler kinds changed: expected={expected} actual={got}")
    return got


def original_vs_cpp_receptor_precision(vendor_source: bytes) -> dict:
    """Require source-verified REAL4 evaluation order for PFSAMP/CALCPF.

    The public C++ SamplingIntegrals stores double values, which are NOT
    permission to carry double intermediates through original PFSAMP XI2.
    This is a static precision/provenance contract, not numeric parity.
    """
    code = "\\n".join(stmt.upper().replace(" ", "")
                     for _, stmt in fixed_statements(vendor_source))
    expected_fortran = {
        "pfsamp_xi1": "XI1=(RTPIBY2/SQRTA)*XXEXP*(ERFDIF(",
        "pfsamp_xi2": "XI2=-B*XI1/A+(XXEXP/A)*(",
        "calcpf_dinv": "DINV=ASDF(LDBHR,SAMDM,SYREC)/(6.2831853*SYREC**2)",
        "calcpf_t2": "T2=XI2*DINV",
        "calcpf_t1": "T1=XI1*DINV-T2",
    }
    for label, expression in expected_fortran.items():
        if expression not in code:
            raise AssertionError(f"Vendor receptor precision expression changed: {label}")
    module = Path(__file__).resolve().parents[1]
    header = (module / "include/cteas/puff/receptors.hpp").read_text()
    sampler = (module / "src/receptors.cpp").read_text()
    for token in ("double i1", "double i2"):
        if token not in header:
            raise AssertionError("PFSAMP C++ public integral storage changed: " + token)
    cpp_guards = {
        "original_real4_type": "using R = float;",
        "xi1_narrow_at_internal_use": "const R xi1 = static_cast<R>(integrals.i1);",
        "xi2_single_precision_expression": "const R xi2 = (-b * xi1 / a) +",
        "sigma_squared_first": "const R sigma_squared = sigma * sigma;",
        "pi_times_sigma_squared": "const R denominator = static_cast<R>(kTwoPi) * sigma_squared;",
    }
    for label, token in cpp_guards.items():
        if token not in sampler:
            raise AssertionError(f"C++ receptor REAL4 source contract drift: {label}")
    return {
        "original": expected_fortran,
        "cpp": cpp_guards,
        "fortran_intermediates": "default REAL*4; 1.4142136 and 6.2831853 are REAL4 literals",
        "cpp_boundary": "SamplingIntegrals.i1/i2 double storage; narrow to float before XI2 arithmetic",
        "fortran_xi2": "REAL4 (-B*XI1/A)+(XXEXP/A)*(EXP(...) - EXP(...))",
        "fortran_calcpf": "SYREC**2 is REAL4 before multiplication by REAL4 6.2831853",
        "numeric_bitwise_equivalence": "NOT_CLAIMED_BY_STATIC_AUDIT; require native-vendor physical-step CI",
    }


def audit(vendor: Path, compiler: str, report: Path) -> dict:
    arguments = " ".join(FLAGS).lower()
    if any(bad in arguments.split() for bad in _BANNED):
        raise AssertionError("Original CALPUFF build applies blanket precision promotion")
    original = vendor / "calpuff.for"
    raw = original.read_bytes()
    units = subroutine_implicit_contract(fixed_statements(raw))
    common = validate_common_includes(vendor)
    kinds = kind_probe(compiler)
    receptor_precision = original_vs_cpp_receptor_precision(raw)
    manifest = {
        "status": "PASS",
        "scope": "P7_SOURCE_AND_COMPILER_PRECISION_CONTRACT_ONLY",
        "vendor_source_sha256": hashlib.sha256(raw).hexdigest(),
        "source_lines": len(raw.splitlines()),
        "original_build_flags": list(FLAGS),
        "fortran_compiler": compiler,
        "kind_probe": kinds,
        "selected_original_routines": units,
        "common_blocks": common,
        "receptor_precision": receptor_precision,
        "precision_rule": "unqualified REAL=REAL4; explicit DOUBLE PRECISION/REAL*8=REAL8; INTEGER=INT4",
        "cpp_interface_double_is_not_vendor_arithmetic": True,
        "vendor_physics_parity": "NOT_TESTED",
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--vendor", type=Path, default=VENDOR)
    p.add_argument("--compiler", required=True)
    p.add_argument("--report", type=Path, required=True)
    args = p.parse_args()
    manifest = audit(args.vendor, args.compiler, args.report)
    print("P7_VENDOR_PRECISION=PASS DEFAULT_REAL_BYTES=4 EXPLICIT_DOUBLE_BYTES=8 "
          "DEFAULT_INTEGER_BYTES=4")
    print("P7_VENDOR_PRECISION_ROUTINES=" + ",".join(sorted(manifest["selected_original_routines"])))
    print("P7_VENDOR_PFSAMP_CALCPF_REAL4_SOURCE=PASS"
          " FORTRAN_DEFAULT_REAL=4_BYTES CXX_LOCAL_FLOAT=4_BYTES"
          " PUBLIC_STORAGE_DOUBLE_DOES_NOT_PROMOTE_XI2=ENFORCED"
          " CALCPF_SYREC_SQUARE_FIRST=ENFORCED"
          " NUMERIC_PARITY=SEPARATE_REAL_CASE_GATE")


if __name__ == "__main__":
    main()
