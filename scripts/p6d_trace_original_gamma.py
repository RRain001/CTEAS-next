#!/usr/bin/env python3
"""Source-pinned original-CALMET 143-hour gridded GAMMA forensic oracle.

Compiles two temporary copies of CALMET 6.5.0 from the same immutable vendor
source, same Fortran compiler, same flags and case inputs. The second source
adds a write-only REAL*4 stream output before DIAGNO's original FRADJ call.
Both binaries MUST produce byte-identical MET.DAT and the frozen reference
MET.DAT SHA-256. The vendor source is never modified.

Purpose: isolate the hourly gridded GAMMA required by P6D FRADJ. This is an
ORIGINAL-REFERENCE INPUT / DIAGNOSTIC ABILITY, not a reconstruction of
CGAMMA/PREPDI or proof of a production-ready self-contained P6D.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import shutil
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "native_cpp/modules/p6_calmet/reference"))
import original_internal_state_dump as original

ORIGINAL_BLOB = "437f43bb7f0e51a1919e56664663e1a046986ed0"
HOOK_LINE = 5642
EXPECTED_BEFORE = "C ---- APPLY THE MELSAR FROUDE NUMBER ADJUSTMENT"
EXPECTED_CALL = "      IF (IFRADJ .EQ. 1) CALL FRADJ(UG,VG,HTOPO,GAMMA,ISURFT,TINF,"

GAMMA_HELPER = """
c --- Temporary source-locked, write-only REAL*4 GAMMA trace.
c --- CALMET 6.5.0 DIAGNO, immediately before source line 5643 FRADJ.
      subroutine dgmrealgamma(gamma,nxi,nyi)
      include 'params.met'
      include 'gen.met'
      integer nxi,nyi,i,j
      real gamma(mxnx,mxny)
      logical opened
      save opened
      data opened/.false./
      if(.not.opened)then
         open(94,file='dgm_gamma.bin',form='unformatted',
     1        access='stream',status='replace')
         opened=.true.
      endif
      write(94) ndathrb,nsecb,nxi,nyi
      write(94) ((gamma(i,j),i=1,nxi),j=1,nyi)
      return
      end
"""


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def pinned(path: Path) -> str:
    raw = path.read_bytes()
    oid = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
    if oid != ORIGINAL_BLOB:
        raise RuntimeError(f"original CALMET Git blob drift: {oid}")
    if sha256(path) != original.ORIGINAL_CALMET_SHA256:
        raise RuntimeError("original CALMET SHA256 drift")
    return oid


def instrument(vendor: Path, dest: Path) -> dict:
    source = vendor / "calmet.for"
    blob = pinned(source)
    lines = source.read_text().splitlines(keepends=True)
    if (lines[HOOK_LINE - 2].strip() != EXPECTED_BEFORE or
        lines[HOOK_LINE].rstrip("\r\n") != EXPECTED_CALL):
        raise RuntimeError("DIAGNO GAMMA hook moved relative to FRADJ source")
    # After source line 5642 and before the unchanged original FRADJ call.
    injected = ("c --- original-source GAMMA trace before FRADJ\n"
                "      if (ifradj.eq.1) call dgmrealgamma(gamma,nx,ny)\n")
    dest.write_text("".join(lines[:HOOK_LINE]) + injected +
                    "".join(lines[HOOK_LINE:]) + GAMMA_HELPER)
    return {
        "original_git_blob": blob,
        "original_sha256": sha256(source),
        "instrumented_sha256": sha256(dest),
        "hook_before_original_line": HOOK_LINE + 1,
        "call_is_write_only": True,
        "original_source_altered_in_vendor": False,
    }


def decode(path: Path, out: Path, hours: int) -> dict:
    raw = path.read_bytes()
    offset = 0
    seen = set()
    records = []
    gamma_dir = out / "gamma"
    gamma_dir.mkdir(parents=True, exist_ok=True)
    while offset < len(raw):
        if offset + 16 > len(raw):
            raise RuntimeError("truncated Fortran GAMMA record header")
        packed, seconds, nx, ny = struct.unpack_from("<4i", raw, offset)
        offset += 16
        if (nx, ny) != (50, 50) or seconds != 0:
            raise RuntimeError(f"unexpected GAMMA grid/time {(packed, seconds, nx, ny)}")
        count = nx * ny
        size = count * 4
        if offset + size > len(raw):
            raise RuntimeError("truncated Fortran GAMMA REAL*4 values")
        payload = raw[offset:offset + size]
        vals = struct.unpack_from(f"<{count}f", raw, offset)
        offset += size
        if any(not math.isfinite(x) for x in vals):
            raise RuntimeError("original CALMET GAMMA has nonfinite cells")
        date = dt.datetime.strptime(f"{packed:09d}", "%Y%j%H") + dt.timedelta(hours=1)
        label = date.strftime("%Y-%m-%d_%H")
        if label in seen:
            raise RuntimeError(f"duplicate original GAMMA hour {label}")
        seen.add(label)
        dest = gamma_dir / f"gamma_{label}.f32"
        dest.write_bytes(payload)  # zero-transform original Fortran REAL*4 bytes
        records.append({
            "hour": label,
            "original_start_time": packed,
            "nx": nx, "ny": ny, "dtype": "float32_le",
            "min_kpm": min(vals), "max_kpm": max(vals),
            "mean_kpm": math.fsum(vals) / len(vals),
            "sha256": hashlib.sha256(payload).hexdigest(),
        })
    if len(records) != hours:
        raise RuntimeError(f"expected {hours} original GAMMA hours, got {len(records)}")
    if sorted(seen) != sorted(x["hour"] for x in records):
        raise RuntimeError("GAMMA hour labels inconsistent")
    for first, second in zip(records, records[1:]):
        a = dt.datetime.strptime(first["hour"], "%Y-%m-%d_%H")
        b = dt.datetime.strptime(second["hour"], "%Y-%m-%d_%H")
        if b - a != dt.timedelta(hours=1):
            raise RuntimeError(f"gap in original hourly GAMMA: {a} -> {b}")
    return {
        "records": records,
        "hours": len(records),
        "float32_values": len(records) * 2500,
        "binary_sha256": sha256(path),
        "layout": "original Fortran gamma(i,j), i-fastest, no padding",
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--vendor", required=True, type=Path)
    p.add_argument("--case", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--compiler", default="gfortran-11")
    p.add_argument("--hours", type=int, default=143)
    args = p.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    vendor = args.vendor.resolve()
    case = args.case.resolve()
    (out / "bin").mkdir(exist_ok=True)
    source_a = vendor / "calmet.for"
    hook = out / "calmet_gamma_instrumented.for"
    provenance = instrument(vendor, hook)
    alias = original._alias_tree(vendor, out / "includes")
    untouched = out / "bin" / "calmet-untouched"
    traced = out / "bin" / "calmet-gamma-writeonly"
    recipe_a = original._build(args.compiler, source_a, alias, untouched)
    recipe_b = original._build(args.compiler, hook, alias, traced)
    staging = out / "case"
    if staging.exists():
        shutil.rmtree(staging)
    staged = original._stage_case(case, staging)
    run_dir = staging / "run" / "met"
    gamma_file = run_dir / "dgm_gamma.bin"
    if gamma_file.exists():
        gamma_file.unlink()
    baseline = original._run(untouched, run_dir)
    if gamma_file.exists():
        raise RuntimeError("unmodified CALMET unexpectedly created GAMMA instrumentation")
    observed = original._run(traced, run_dir)
    if not gamma_file.is_file():
        raise RuntimeError("write-only GAMMA hook produced no hourly REAL*4 dump")
    intact = baseline["met_dat_sha256"] == observed["met_dat_sha256"]
    frozen = observed["met_dat_sha256"] == original.TARGET_MET_DAT_SHA256
    report = {
        "status": "PASS_ORIGINAL_GAMMA_SOURCE_REAL4" if intact and frozen else "FAIL",
        "input_case": str(case),
        "pin": provenance,
        "case_inputs": staged,
        "toolchain": {"compiler": args.compiler,
                      "flags": list(original.COMMON_FFLAGS),
                      "original": recipe_a, "instrumented": recipe_b},
        "original_output": baseline,
        "instrumented_output": observed,
        "met_dat_byte_identical": intact,
        "met_dat_matches_frozen_reference": frozen,
        "reference_sha256": original.TARGET_MET_DAT_SHA256,
        "scope": ("143h original DIAGNO pre-FRADJ GAMMA reference forcing; "
                  "NOT C++ CGAMMA/PREPDI reconstruction nor P6D final parity"),
    }
    if intact and frozen:
        report["gamma"] = decode(gamma_file, out, args.hours)
    (out / "gamma_source_manifest.json").write_text(
        json.dumps(report, indent=2) + "\n")
    print(json.dumps({
        "status": report["status"],
        "met_dat_byte_identical": intact,
        "met_dat_matches_frozen_reference": frozen,
        "original_gamma_hours": report.get("gamma", {}).get("hours"),
        "total_gamma_values": report.get("gamma", {}).get("float32_values"),
        "manifest": str(out / "gamma_source_manifest.json"),
    }, indent=2))
    if not (intact and frozen):
        raise SystemExit("original GAMMA oracle failed unchanged-MET.DAT proof")


if __name__ == "__main__":
    main()
