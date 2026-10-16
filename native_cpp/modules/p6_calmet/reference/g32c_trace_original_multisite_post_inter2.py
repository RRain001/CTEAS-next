#!/usr/bin/env python3
"""G32C: independent original CALMET post-INTER2 grid U/V vs G23 native.

Port only the frozen *single-site* p6d_trace_original_inter2_first_layer_143h
write-only hook at original DIAGNO line 6072, AFTER both original INTER2 calls.
The source code, physical inputs and P6E comparator remain untouched. Before
any interpretation, instrumented original MET.DAT must be byte-identical to
the genuinely unmodified original G31 output. Diagnosis is not acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
from pathlib import Path

import original_internal_state_dump as source
from g32b_trace_original_multisite_slope_first_divergence import (
    COUNT, NX, NY, NZ, compare, native_csv,
)

HELPER = r"""
c --- G32C: write-only source full-grid after two original INTER2 calls
      subroutine dgm_p6g_post_inter2
      include 'params.met'
      include 'gen.met'
      include 'grid.met'
      include 'd1.met'
      integer i,j,k
      logical opened
      save opened
      data opened/.false./
      if(.not.opened)then
         open(94,file='g32c_post_inter2.bin',
     1        form='unformatted',access='stream',status='replace')
         opened=.true.
      endif
      write(94) 16,ndathrb,nsecb,nx,ny,nz
      write(94) (((u(i,j,k),i=1,nx),j=1,ny),k=1,nz)
      write(94) (((v(i,j,k),i=1,nx),j=1,ny),k=1,nz)
      return
      end
c --- G32D: independent write-only all 4 source station US/VS profiles
c --- after STHEOR/DIAGI, before native/original INTER2 comparison.
      subroutine dgm_p6g_inter2_sites
      include 'params.met'
      include 'gen.met'
      include 'grid.met'
      include 'd1.met'
      integer k,l
      logical opened
      save opened
      data opened/.false./
      if(.not.opened)then
         open(93,file='g32d_inter2_sites.bin',
     1        form='unformatted',access='stream',status='replace')
         opened=.true.
      endif
      write(93) 17,ndathrb,nsecb,4,nz,0
      write(93) ((us(k,l),l=1,4),k=1,nz)
      write(93) ((vs(k,l),l=1,4),k=1,nz)
      return
      end
"""


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def patch_original(original: Path, destination: Path):
    if sha(original) != source.ORIGINAL_CALMET_SHA256:
        raise ValueError("G32C original vendor calmet.for SHA changed")
    lines = original.read_text().splitlines(keepends=True)
    # EXACT single-station source anchors: untouched original CALMET 6.5.0,
    # two INTER2 calls and the post-INTER2 conditional, prior to WINDBC.
    if (lines[6054].strip() != "CALL INTER2(US,NWIND,UTMXST,UTMYST,"
            or lines[6058].strip() != "CALL INTER2(VS,NWIND,UTMXST,UTMYST,"
            or lines[6071].strip() != "ENDIF"
            or "Lake breeze region" not in lines[6075]):
        raise RuntimeError("G32C single-site original post-INTER2 anchors drifted")
    lines.insert(6072, "      call dgm_p6g_post_inter2\n"
                       "      call dgm_p6g_inter2_sites\n")
    destination.write_text("".join(lines) + HELPER)


def read_dump(path: Path, native_end: int):
    raw = path.read_bytes()
    if len(raw) != 24 + 2*COUNT*4:
        raise ValueError("G32C original post-INTER2 full-grid bytes invalid")
    marker, packed, second, nx, ny, nz = struct.unpack_from("<6i", raw, 0)
    if (marker, nx, ny, nz, second) != (16, NX, NY, NZ, 0):
        raise ValueError("G32C original post-INTER2 physical/clock header invalid")
    from datetime import datetime, timezone
    start = datetime.fromtimestamp(native_end-3600, timezone.utc)
    wanted = start.year*100000 + start.timetuple().tm_yday*100 + start.hour
    if packed != wanted or start.minute or start.second:
        raise ValueError("G32C original post-INTER2 model hour differs from native")
    values = struct.unpack_from("<" + str(2*COUNT) + "f", raw, 24)
    return (values[:COUNT], values[COUNT:]), packed


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source-run-dir", required=True, type=Path)
    p.add_argument("--untouched-met", required=True, type=Path)
    p.add_argument("--frozen-verdict", required=True, type=Path)
    p.add_argument("--native-inter2", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--compiler", default="gfortran")
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    report = {"status": "BLOCKED", "scientific_status": "FAIL_NUMERIC",
              "scope": "G32C independent original post-INTER2, all 9 levels; diagnostic-only"}
    try:
        vendor = Path(__file__).resolve().parents[4] / "engine/vendor/src/CALMET_v6.5.0_L150223"
        if sha(vendor/"calutils.for") != source.ORIGINAL_CALUTILS_SHA256:
            raise ValueError("G32C original calutils changed")
        frozen = json.loads(args.frozen_verdict.read_text())
        if (frozen.get("status") != "FAIL_NUMERIC"
                or frozen.get("fields_per_hour") != 45
                or frozen.get("intervals") != 1):
            raise ValueError("G32C requires genuine failed full-original science verdict")
        if sha(args.source_run_dir/"met.dat") != sha(args.untouched_met):
            raise ValueError("G32C source run differs from original science MET.DAT")
        native, native_end = native_csv(args.native_inter2)
        copy = args.out/"original-post-inter2-write-only.for"
        patch_original(vendor/"calmet.for", copy)
        alias = source._alias_tree(vendor, args.out/"include-alias")
        binary = args.out/"original-post-inter2.x"
        command = source._build(args.compiler, copy, alias, binary)
        run = args.out/"instrumented-run"
        if run.exists():
            shutil.rmtree(run)
        shutil.copytree(args.source_run_dir, run)
        actual = source._run(binary, run)
        if actual["met_dat_sha256"] != sha(args.untouched_met):
            raise ValueError("G32C write-only after-INTER2 instrumentation changed original MET.DAT")
        dump = run/"g32c_post_inter2.bin"
        if not dump.is_file():
            raise ValueError("G32C original post-INTER2 Fortran output absent")
        original, packed = read_dump(dump, native_end)
        stage = compare("original_CALMET_post_both_INTER2_vs_native_G23", original, native)
        report.update({
            "status": "PASS_G32C_WRITE_ONLY_POST_INTER2_DIAGNOSIS",
            "original_vendor_sha256": sha(vendor/"calmet.for"),
            "untouched_original_met_sha256": sha(args.untouched_met),
            "instrumented_met_sha256": actual["met_dat_sha256"],
            "original_post_inter2_dump_sha256": sha(dump),
            "original_hour_packed": packed,
            "original_vs_native_post_inter2": stage,
            "compiler_command": command,
            "scientific_status": "FAIL_NUMERIC",
            "next_stage_if_bit_equal": "second WINDBC -> SMOOTH/DIVCEL/W (kpt10)",
            "next_stage_if_different": "G23 DIAGI/STHEOR/INTER2 station columns and controls",
            "single_site_precedent": "scripts/p6d_trace_original_inter2_first_layer_143h.py",
        })
    except Exception as exc:
        report["blocker"] = str(exc)
        raise
    finally:
        evidence = args.out/"g32c-diagnosis.json"
        evidence.write_text(json.dumps(report, indent=2) + "\n")
        compact = {key: ({"bit_mismatches": val["bit_mismatches"],
                          "above_diagnostic_1e_minus_3_mps":
                              val["above_diagnostic_1e_minus_3_mps"],
                          "first_bit_difference": val["first_bit_difference"],
                          "level1": val["by_level"][0]}
                         if key == "original_vs_native_post_inter2" else val)
                   for key, val in report.items()}
        print(json.dumps(compact, indent=2))


if __name__ == "__main__":
    main()
