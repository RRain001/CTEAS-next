#!/usr/bin/env python3
"""Chained-original DIAGNO IKINE=1 pre-blend kinematic route.

Compiles the *unchanged* original CALMET 6.5.0 ``TOPOF2`` (L31904-L32078,
DIAGNO L5621-L5622) and ``MINIM`` (L9645-L9761, DIAGNO L5628-L5629) verbatim
and replays the original order: W is XMIT-zeroed (L5615-L5616), TOPOF2 builds
the terrain-following vertical velocity, then MINIM relaxes UG/VG at fixed W
using the L5598-L5600 WINDBC boundary snapshot. ``ALPHA`` is the original
empirical topographic coefficient and ``NITER``/``DIVLIM`` the original
namelist MINIM controls.
The frozen real deck has ``IKINE = 0``, so this is a completeness branch and
NOT the real-case path; synthetic fixtures only.
"""
import csv
import hashlib
import math
import sys
from pathlib import Path

# compare_original_fradj imports native_cpp.* by absolute path, which only
# resolves in module form; make the repository root importable.
_ROOT = Path(__file__).resolve().parents[4]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import compare_original_fradj as fradj_module
import compare_original_slope as slope_module
import compare_original_diagno_d9a_fradj as chain_fradj

NX = NY = 50
NZ = 9
N = NX * NY
SOURCE_BLOB = slope_module.SOURCE_BLOB
W_ABS_TOL = 2.0e-4
TOPOF2_ROUTINE_LINES = (31904, 32079)
MINIM_ROUTINE_LINES = (9645, 9762)
WINDBC_LOOP_LINES = (5598, 5600)
WINIT_LINES = (5615, 5616)
TOPOF2_CALL_LINES = (5621, 5622)
MINIM_CALL_LINES = (5628, 5629)

DRIVER_HEAD = """      program d9akinematic
      include 'params.met'
      include 'grid.met'
      include 'd6.met'
      real ug(mxnx,mxny,mxnz),vg(mxnx,mxny,mxnz)
      real w(mxnx,mxny,mxnzp1),div(mxnx,mxny,mxnz)
      real htopo(mxnx,mxny),gamma(mxnx,mxny),temp2d(mxnx,mxny)
      real ub(mxny,2,mxnz),vb(mxnx,2,mxnz),cellzb(mxnzp1)
      real zf1,alpha,tinf,critfn,zero
      integer isurft,niter,ikine
      character*512 fin,fuv,fw
      call get_command_argument(1,fin)
      call get_command_argument(2,fuv)
      call get_command_argument(3,fw)
      nx=50
      ny=50
      nz=9
      dx=100.0
      dy=100.0
      iwr=0
      nzp1=nz+1
      zero=0.
      critfn=1.
      ikine=1
      open(10,file=trim(fin),status='old')
      read(10,*) zf1,isurft,tinf,alpha,niter,critfn
      read(10,*) (dz(k),k=1,nz)
      zface(1)=zf1
      do k=1,nz
        zface(k+1)=zface(k)+dz(k)
      enddo
      do k=1,nzp1
        cellzb(k)=zface(k)
      enddo
      do j=1,ny
        read(10,*) (htopo(i,j),i=1,nx)
      enddo
      do j=1,ny
        read(10,*) (gamma(i,j),i=1,nx)
      enddo
      do j=1,ny
        read(10,*) (temp2d(i,j),i=1,nx)
      enddo
      do k=1,nz
        do j=1,ny
          read(10,*) (ug(i,j,k),i=1,nx)
        enddo
      enddo
      do k=1,nz
        do j=1,ny
          read(10,*) (vg(i,j,k),i=1,nx)
        enddo
      enddo
      close(10)

"""
DRIVER_MID = """

"""
DRIVER_OUT = """
      open(11,file=trim(fuv),status='replace')
      do k=1,nz
        do j=1,ny
          do i=1,nx
            write(11,'(3(I4,1X),2(ES22.13E3,1X))')
     1        i,j,k,ug(i,j,k),vg(i,j,k)
          enddo
        enddo
      enddo
      close(11)
      open(12,file=trim(fw),status='replace')
      do k=1,nzp1
        do j=1,ny
          do i=1,nx
            write(12,'(3(I4,1X),ES22.13E3)') i,j,k,w(i,j,k)
          enddo
        enddo
      enddo
      close(12)
      end
c -- Local test-harness stub for the original array initialiser.
      subroutine xmit(n,val,a)
      real val,a(*)
      do i=1,iabs(n)
        a(i)=val
      enddo
      end
"""

def _fragment(lines, span):
    return "".join(lines[span[0] - 1:span[1]])

def original_source(vendor, out):
    """Literal TOPOF2 + pre-blend MINIM route and the unchanged subroutines."""
    source = vendor / "calmet.for"
    topof2_path = out / "topof2_original.for"
    topof2_meta = fradj_module.extract(source, "topof2", "unpack", topof2_path)
    topof2_meta["name"] = "topof2"
    topof2_meta["note"] = "extraction also carries the self-contained UNIDOT function"
    minim_path = out / "minim_d9a_original.for"
    minim_meta = fradj_module.extract(source, "minim", "missfc", minim_path)
    minim_meta["name"] = "minim"
    lines = source.read_text().splitlines(keepends=True)
    fragments = {
        "windbc_loop": _fragment(lines, WINDBC_LOOP_LINES),
        "w_init": _fragment(lines, WINIT_LINES),
        "topof2_call": _fragment(lines, TOPOF2_CALL_LINES),
        "minim_call": _fragment(lines, MINIM_CALL_LINES),
    }
    expected = {
        "windbc_loop": "CALL WINDBC(UG,VG,UB,VB,K)",
        "w_init": "CALL XMIT(-N,ZERO,W)",
        "topof2_call": "CALL TOPOF2(UG,VG,W,HTOPO,",
        "minim_call": "CALL MINIM(UG,VG,W,UB,VB,DIV,",
    }
    for key, needle in expected.items():
        if needle not in fragments[key]:
            raise RuntimeError(f"DIAGNO {key} fragment anchor drift")
    driver = out / "original_d9a_kinematic.for"
    driver.write_text(DRIVER_HEAD +
                      fragments["windbc_loop"] + DRIVER_MID +
                      fragments["w_init"] + DRIVER_MID +
                      fragments["topof2_call"] + DRIVER_MID +
                      fragments["minim_call"] + DRIVER_MID +
                      DRIVER_OUT)
    meta = {
        "subroutines": [topof2_meta, minim_meta],
        "topof2_subroutine_lines": list(TOPOF2_ROUTINE_LINES),
        "literal_blocks": {
            key: {"lines": list(span),
                  "sha256": hashlib.sha256(fragments[key].encode()).hexdigest()}
            for key, span in (("windbc_loop", WINDBC_LOOP_LINES),
                              ("w_init", WINIT_LINES),
                              ("topof2_call", TOPOF2_CALL_LINES),
                              ("minim_call", MINIM_CALL_LINES))
        },
        "driver_sha256": hashlib.sha256(driver.read_bytes()).hexdigest(),
        "alpha_consumers": "DIAGNO L5621-L5622 TOPOF2 only",
        "surfvar_temp2d_lines": [5609, 5610],
    }
    return topof2_path, minim_path, driver, meta

def compile_reference(vendor, out, base_flags):
    import compare_original_diagno_final_segment as diag
    topof2, minim, driver, meta = original_source(vendor, out)
    # DIVCEL is called by MINIM; WINDBC is needed by the literal L5598-L5600
    # boundary snapshot and by MINIM's own refresh. Both come from the literal
    # DIAGNO segment extraction, unchanged.
    routines, _, _ = diag.original_source(vendor, out)
    helpers = [path for path, ref in routines
               if ref["name"] in ("divcel", "windbc")]
    if len(helpers) != 2:
        raise RuntimeError("kinematic route DIVCEL/WINDBC extraction missing")
    binary = out / "original_d9a_kinematic"
    fradj_module.run(list(base_flags) + [topof2, minim] + helpers +
                     [driver, "-o", binary], timeout=120)
    return binary, meta

def write_case(path, zface1_m, dz_m, terrain, lapse, temperature, alpha,
               niter, divlim_per_s, u, v):
    shapes = ((terrain, N), (lapse, N), (temperature, N),
              (u, N * NZ), (v, N * NZ))
    if any(len(field) != size for field, size in shapes):
        raise ValueError("kinematic route input shape")
    with path.open("w") as handle:
        handle.write(f"{zface1_m!r} {chain_fradj.ISURFT} "
                     f"{chain_fradj.TINF_K!r} {alpha!r} {niter} "
                     f"{divlim_per_s!r}\n")
        handle.write(" ".join(repr(float(value)) for value in dz_m) + "\n")
        # repr() is the shortest round-trip form, so the unchanged Fortran
        # reader reconstructs exactly the float32 the C++ bridge holds. A
        # truncated fixture would seed the MINIM iteration differently and
        # that difference grows through the Gauss-Seidel sweeps.
        for field in (terrain, lapse, temperature, u, v):
            for offset in range(0, len(field), NX):
                handle.write(" ".join(repr(float(value))
                                      for value in field[offset:offset + NX]) + "\n")

def write_bridge_fields(handle, enabled, alpha, niter, divlim_per_s):
    """Append the IKINE selector and its MINIM controls to a fixture stream.

    TOPOF2 consumes the shared HTOPO/GAMMA/TEMP2D planes already carried by
    the terrain record, so only the selector and its namelist controls are
    written here.
    """
    handle.write(f"{1 if enabled else 0} {alpha:.9f} {niter} "
                 f"{divlim_per_s:.9f}\n")

def read_uv(path):
    rows = [line.split() for line in path.read_text().splitlines()]
    if len(rows) != N * NZ:
        raise RuntimeError("kinematic route U/V output shape")
    for n, row in enumerate(rows):
        expected = (n % NX + 1, (n // NX) % NY + 1, n // N + 1)
        if len(row) != 5 or tuple(map(int, row[:3])) != expected:
            raise RuntimeError("kinematic route U/V output ordering")
    return rows

def compare_uv(ref, cpp):
    """Reuse the SLOPE verdict: both sides write i,j,k,u_mps,v_mps."""
    return slope_module.compare(ref, cpp)

def compare_w(ref, cpp):
    """Numeric verdict for the original TOPOF2 terrain-following W faces."""
    original = [line.split() for line in ref.read_text().splitlines()]
    with cpp.open(newline="") as handle:
        modern = list(csv.DictReader(handle))
    if len(original) != N * (NZ + 1) or len(modern) != N * (NZ + 1):
        raise RuntimeError("kinematic route W face count mismatch")
    mismatch = []
    nonzero = 0
    largest = 0.
    for n, (row, entry) in enumerate(zip(original, modern)):
        idx = (n % NX + 1, (n // NX) % NY + 1, n // N + 1)
        if len(row) != 4 or tuple(map(int, row[:3])) != idx or \
           (int(entry["i"]), int(entry["j"]), int(entry["face"])) != idx:
            raise RuntimeError("kinematic route W face ordering mismatch")
        reference, candidate = float(row[3]), float(entry["w_mps"])
        if not (math.isfinite(reference) and math.isfinite(candidate)):
            raise RuntimeError("nonfinite TOPOF2 W face")
        if abs(reference) > 1.0e-6:
            nonzero += 1
        error = abs(reference - candidate)
        largest = max(largest, error)
        if error > W_ABS_TOL and len(mismatch) < 10:
            mismatch.append({"idx": idx, "fortran": reference,
                             "cpp": candidate, "error": error})
    return {"status": "PASS" if not mismatch else "FAIL",
            "compared_faces": N * (NZ + 1),
            "nonzero_original_faces": nonzero,
            "max_abs_error_mps": largest,
            "abs_tolerance_mps": W_ABS_TOL,
            "first_mismatches": mismatch}
