#!/usr/bin/env python3
"""Chained-original DIAGNO upstream terrain stages for the P6D9A chain.

Compiles the *unchanged* original CALMET 6.5.0 ``FRADJ`` (L7289-L7451,
DIAGNO L5643-L5644) and ``SLOPE`` (L30372-L30604, DIAGNO L5722-L5723 plus the
L5727-L5732 additive loop) verbatim and applies them, in the original order,
to a step-one UG/VG fixture with caller-provided terrain, terrain envelope,
valley bottoms, birdwise distances, lapse rate, 2-D surface temperature and
gridded sensible heat flux. This is exactly the ``IWFCOD=1``/``IFRADJ=1``/
``ISLOPE=1`` upstream combination of the real case deck. Synthetic fixtures
only; no real 2022 fields are claimed.
"""
import hashlib
import csv
import math
import sys
from pathlib import Path

# compare_original_fradj/compare_original_slope live in this directory, but
# compare_original_fradj imports native_cpp.* by absolute path, which only
# resolves in module form; make the repository root importable.
_ROOT = Path(__file__).resolve().parents[4]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import compare_original_slope as slope_module
import compare_original_fradj as fradj_module
import compare_original_diagno_d9a_fradj as chain_fradj

NX = NY = 50
NZ = 9
N = NX * NY
SOURCE_BLOB = slope_module.SOURCE_BLOB
ABS_TOL = slope_module.ABS_TOL
FRADJ_CALL_LINES = (5643, 5644)
SLOPE_CALL_LINES = (5722, 5723)
SLOPE_ADD_LINES = (5727, 5732)
# Original DIAGI call that builds the HMAX/HMIN/DISTHMAX/DISTHMIN envelope
# from the GEO terrain; I3DCTW=IWFCOD, so IWFCOD=1 (the real deck) runs it.
TERSET_CALL_LINES = (5228, 5228)
TERSET_ROUTINE_LINES = (31805, 31903)
# Real deck water range for the GEO landuse categories (CALMET water class).
WATER_FIRST = 50
WATER_LAST = 55

DRIVER_HEAD = """      program d9aupstream
      include 'params.met'
      include 'grid.met'
      include 'metgrd.met'
      include 'geo.met'
      include 'd6.met'
      real ug(mxnx,mxny,mxnz),vg(mxnx,mxny,mxnz)
      real uslope(mxnx,mxny,mxnz),vslope(mxnx,mxny,mxnz)
      real htopo(mxnx,mxny),gamma(mxnx,mxny),temp2d(mxnx,mxny)
      real hmax(mxnx,mxny),cellzb(mxnzp1)
      real critfn,tinf,zf1,terrad
      integer isurft,iters,i3dctw
      integer ifradj,islope
      character*512 fin,fout
      call get_command_argument(1,fin)
      call get_command_argument(2,fout)
      nx=50
      ny=50
      nz=9
      dx=100.0
      dy=100.0
      iwr=0
      nzp1=nz+1
      ifradj=1
      islope=1
      open(10,file=trim(fin),status='old')
      read(10,*) zf1,isurft,tinf,critfn,iwat1,iwat2,terrad,iters
      i3dctw=iters
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
      do j=1,ny
        read(10,*) (hmax(i,j),i=1,nx)
      enddo
      do j=1,ny
        read(10,*) (hmin(i,j),i=1,nx)
      enddo
      do j=1,ny
        read(10,*) (disthmax(i,j),i=1,nx)
      enddo
      do j=1,ny
        read(10,*) (disthmin(i,j),i=1,nx)
      enddo
      do j=1,ny
        read(10,*) (qh(i,j),i=1,nx)
      enddo
      do j=1,ny
        read(10,*) (ilandu(i,j),i=1,nx)
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
c --- LITERAL ORIGINAL DIAGI TERSET ENVELOPE CALL L5228 BEGINS:
"""

DRIVER_MID0 = """c --- LITERAL ORIGINAL DIAGNO FRADJ CALL L5643-L5644 BEGINS:
"""

DRIVER_MID = """c --- LITERAL ORIGINAL DIAGNO SLOPE CALL L5722-L5723 BEGINS:
"""

DRIVER_MID2 = """c --- LITERAL ORIGINAL DIAGNO SLOPE ADDITIVE LOOP L5727-L5732 BEGINS:
"""

DRIVER_TAIL = """c --- LITERAL ORIGINAL DIAGNO UPSTREAM STAGES END.
      open(11,file=trim(fout),status='replace')
      do k=1,nz
        do j=1,ny
          do i=1,nx
            write(11,'(3(I4,1X),2(ES22.13E3,1X))')
     1        i,j,k,ug(i,j,k),vg(i,j,k)
          enddo
        enddo
      enddo
      close(11)
      end
c -- Local test-harness stubs for the plot/initialisation helpers the
c -- original SLOPE source references; no physical source is altered.
      subroutine xmit(n,val,a)
      real val,a(*)
      do i=1,iabs(n)
        a(i)=val
      enddo
      end
      subroutine wndlpt(a)
      real a(*)
      return
      end
"""

def _fragment(lines, span):
    return "".join(lines[span[0] - 1:span[1]])

def original_source(vendor, out):
    """Literal FRADJ+SLOPE chain, plus the reused original FRADJ subroutine."""
    fradj_path, _, fradj_meta = chain_fradj.original_source(vendor, out)
    slope_path = out / "slope_d9a_original.for"
    slope_sha = slope_module.original_slope(vendor / "calmet.for", slope_path)
    terset_path = out / "terset_d9a_original.for"
    terset_meta = fradj_module.extract(vendor / "calmet.for", "terset", "topof2",
                                       terset_path)
    terset_meta["name"] = "terset"
    terset_meta["diagno_call_lines"] = list(TERSET_CALL_LINES)
    lines = (vendor / "calmet.for").read_text().splitlines(keepends=True)
    fragments = {
        "terset_call": _fragment(lines, TERSET_CALL_LINES),
        "fradj_call": _fragment(lines, FRADJ_CALL_LINES),
        "slope_call": _fragment(lines, SLOPE_CALL_LINES),
        "slope_add": _fragment(lines, SLOPE_ADD_LINES),
    }
    expected = {
        "terset_call": "call terset(htopo,hmax,terrad)",
        "fradj_call": "CALL FRADJ(UG,VG,HTOPO,GAMMA,ISURFT,TINF,",
        "slope_call": "CALL SLOPE(USLOPE,VSLOPE,HTOPO,ISURFT,TINF,TEMP2D,",
        "slope_add": "UG(I,J,K)=UG(I,J,K)+USLOPE(I,J,K)",
    }
    for key, needle in expected.items():
        if needle not in fragments[key]:
            raise RuntimeError(f"DIAGNO {key} fragment anchor drift")
    if "      DO 300 K=1,NZ\n" not in fragments["slope_add"] or \
       "  300 CONTINUE\n" not in fragments["slope_add"]:
        raise RuntimeError("DIAGNO slope additive loop drift")
    driver = out / "original_d9a_upstream.for"
    driver.write_text(DRIVER_HEAD + fragments["terset_call"] + DRIVER_MID0 +
                      fragments["fradj_call"] + DRIVER_MID +
                      fragments["slope_call"] + DRIVER_MID2 +
                      fragments["slope_add"] + DRIVER_TAIL)
    meta = dict(fradj_meta)
    meta.update({
        "slope_subroutine": {"first_line": 30372, "last_line": 30604,
                             "sha256": slope_sha},
        "terset_subroutine": terset_meta,
        "literal_blocks": {
            key: {"lines": list(span),
                  "sha256": hashlib.sha256(fragments[key].encode()).hexdigest()}
            for key, span in (("terset_call", TERSET_CALL_LINES),
                              ("fradj_call", FRADJ_CALL_LINES),
                              ("slope_call", SLOPE_CALL_LINES),
                              ("slope_add", SLOPE_ADD_LINES))
        },
        "driver_sha256": hashlib.sha256(driver.read_bytes()).hexdigest(),
        "water_class_range": [WATER_FIRST, WATER_LAST],
    })
    return fradj_path, slope_path, terset_path, driver, meta

def compile_reference(vendor, out, base_flags):
    fradj_path, slope_path, terset_path, driver, meta = original_source(vendor,
                                                                        out)
    binary = out / "original_d9a_upstream"
    slope_module.run(list(base_flags) + [terset_path, fradj_path, slope_path,
                                         driver, "-o", binary])
    return binary, meta

def fields(scene, landuse):
    """SLOPE planes consistent with the shared FRADJ terrain fixture."""
    terrain, highest, _, _ = chain_fradj.fields(scene)
    minimum = [value - 650. for value in terrain]
    distance_max = [900. + i * 12. for j in range(NY) for i in range(NX)]
    distance_min = [1100. + j * 10. for j in range(NY) for i in range(NX)]
    # Both flux signs so the daytime/upslope and nighttime/downhill branches
    # of the original Mahrt parameterisation are exercised.
    heat = [160. * math.exp(-((i - 25) ** 2 + (j - 25) ** 2) / 400.) - 90.
            for j in range(NY) for i in range(NX)]
    if len(landuse) != N:
        raise ValueError("SLOPE landuse shape")
    return terrain, highest, minimum, distance_max, distance_min, heat

def write_case(path, zface1_m, dz_m, terrain, highest, lapse, temperature,
               minimum, distance_max, distance_min, heat, landuse, u, v,
               terrad_km, terset_enabled):
    shapes = ((terrain, N), (highest, N), (lapse, N), (temperature, N),
              (minimum, N), (distance_max, N), (distance_min, N), (heat, N),
              (landuse, N), (u, N * NZ), (v, N * NZ))
    if any(len(field) != size for field, size in shapes):
        raise ValueError("chained upstream stage input shape")
    with path.open("w") as handle:
        handle.write(f"{zface1_m:.9f} {chain_fradj.ISURFT} "
                     f"{chain_fradj.TINF_K:.9f} {chain_fradj.CRITFN:.9f} "
                     f"{WATER_FIRST} {WATER_LAST} {terrad_km:.9f} "
                     f"{1 if terset_enabled else 0}\n")
        handle.write(" ".join(f"{value:.9f}" for value in dz_m) + "\n")
        # Same plane order as the driver reads: HTOPO, GAMMA, TEMP2D, HMAX,
        # HMIN, DISTHMAX, DISTHMIN, QH, ILANDU.
        for field in (terrain, lapse, temperature, highest, minimum,
                      distance_max, distance_min, heat):
            for offset in range(0, N, NX):
                handle.write(" ".join(f"{value:.8f}"
                                      for value in field[offset:offset + NX]) + "\n")
        for offset in range(0, N, NX):
            handle.write(" ".join(str(value)
                                  for value in landuse[offset:offset + NX]) + "\n")
        for field in (u, v):
            for offset in range(0, len(field), NX):
                handle.write(" ".join(f"{value:.8f}"
                                      for value in field[offset:offset + NX]) + "\n")

def write_bridge_fields(handle, enabled, planes, landuse):
    """Append the ISLOPE selector, its planes and the GEO landuse to a fixture.

    Always written so the fixture record shape is fixed; the C++ bridge
    ignores the planes unless ISLOPE is enabled.
    """
    terrain, highest, minimum, distance_max, distance_min, heat = planes
    del terrain, highest
    handle.write(f"{1 if enabled else 0} {WATER_FIRST} {WATER_LAST}\n")
    for field in (minimum, distance_max, distance_min, heat):
        for offset in range(0, N, NX):
            handle.write(" ".join(f"{value:.8f}"
                                  for value in field[offset:offset + NX]) + "\n")
    if len(landuse) != N:
        raise ValueError("SLOPE bridge landuse shape")
    for offset in range(0, N, NX):
        handle.write(" ".join(str(value)
                              for value in landuse[offset:offset + NX]) + "\n")

def read_output(path):
    rows = [line.split() for line in path.read_text().splitlines()]
    if len(rows) != N * NZ:
        raise RuntimeError("chained upstream stage output shape")
    u = []
    v = []
    for n, row in enumerate(rows):
        expected = (n % NX + 1, (n // NX) % NY + 1, n // N + 1)
        if len(row) != 5 or tuple(map(int, row[:3])) != expected:
            raise RuntimeError("chained upstream stage output ordering")
        u.append(float(row[3]))
        v.append(float(row[4]))
    return u, v

def compare(ref, cpp, before_u, before_v):
    """Numeric verdict for the composed FRADJ+SLOPE step-one field."""
    original = [line.split() for line in ref.read_text().splitlines()]
    with cpp.open(newline="") as handle:
        modern = list(csv.DictReader(handle))
    if len(original) != N * NZ or len(modern) != N * NZ:
        raise RuntimeError("FRADJ+SLOPE output record count mismatch")
    mismatch = []
    changed = 0
    maxerr = {"u_mps": 0., "v_mps": 0.}
    for n, (row, entry) in enumerate(zip(original, modern)):
        idx = (n % NX + 1, (n // NX) % NY + 1, n // N + 1)
        if len(row) != 5 or tuple(map(int, row[:3])) != idx or \
           (int(entry["i"]), int(entry["j"]), int(entry["k"])) != idx:
            raise RuntimeError("FRADJ+SLOPE output ordering mismatch")
        if abs(float(row[3]) - before_u[n]) > 1e-6 or \
           abs(float(row[4]) - before_v[n]) > 1e-6:
            changed += 1
        for field, column in (("u_mps", 3), ("v_mps", 4)):
            reference, candidate = float(row[column]), float(entry[field])
            if not (math.isfinite(reference) and math.isfinite(candidate)):
                raise RuntimeError("nonfinite FRADJ+SLOPE output")
            error = abs(reference - candidate)
            maxerr[field] = max(maxerr[field], error)
            if error > ABS_TOL and len(mismatch) < 10:
                mismatch.append({"idx": idx, "field": field,
                                 "fortran": reference, "cpp": candidate,
                                 "error": error})
    return {"status": "PASS" if not mismatch else "FAIL",
            "compared_components": 2 * N * NZ,
            "original_changed_step_one_components": changed,
            "max_abs_errors": maxerr,
            "abs_tolerance_mps": ABS_TOL,
            "first_mismatches": mismatch}
