#!/usr/bin/env python3
"""Chained-original FRADJ stage for the P6D9A DIAGNO chain.

Compiles the *unchanged* original CALMET 6.5.0 ``FRADJ`` (calmet.for
L7289-L7451, DIAGNO L5643-L5644, ``IF (IFRADJ .EQ. 1)``) verbatim and applies
it to a step-one UG/VG fixture with caller-provided terrain, terrain envelope
HMAX, lapse rate GAMMA and 2-D surface temperature, exactly as DIAGNO does
before the L5748 WINDBC snapshot and the L6055/L6059 INTER2 calls.
``compare_original_fradj.compare`` is reused for the numeric verdict.
This is a SYNTHETIC terrain/heat fixture; no real 2022 fields are claimed.
"""
import math
import sys
from pathlib import Path

# compare_original_fradj imports native_cpp.* by absolute path, which only
# resolves in module form; make the repository root importable so this module
# also works when the chained parity script is executed as a plain file.
_ROOT = Path(__file__).resolve().parents[4]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import compare_original_fradj as fradj

NX = NY = 50
NZ = 9
N = NX * NY
# Original namelist controls used for the replayed IFRADJ=1 route.
ISURFT = -1
TINF_K = 285.0
CRITFN = 1.0
# Synthetic terrain envelope margin above HTOPO (m); HMAX is supplied by the
# caller in the original call sequence, so the fixture owns its definition.
ENVELOPE_MARGIN_M = 400.0

DRIVER = """      program d9afradj
      include 'params.met'
      include 'grid.met'
      include 'd6.met'
      real topo(mxnx,mxny),highest(mxnx,mxny)
      real gam(mxnx,mxny),sfct(mxnx,mxny)
      real u(mxnx,mxny,mxnz),v(mxnx,mxny,mxnz)
      real critfn,tinf,zf1
      integer isurft
      character*256 fin,fout
      call get_command_argument(1,fin)
      call get_command_argument(2,fout)
      nx=50
      ny=50
      nz=9
      dx=100.0
      dy=100.0
      iwr=0
      open(10,file=trim(fin),status='old')
      read(10,*) zf1,isurft,tinf,critfn
      read(10,*) (dz(k),k=1,nz)
      zface(1)=zf1
      do k=1,nz
        zface(k+1)=zface(k)+dz(k)
      enddo
      do j=1,ny
        read(10,*) (topo(i,j),i=1,nx)
      enddo
      do j=1,ny
        read(10,*) (highest(i,j),i=1,nx)
      enddo
      do j=1,ny
        read(10,*) (gam(i,j),i=1,nx)
      enddo
      do j=1,ny
        read(10,*) (sfct(i,j),i=1,nx)
      enddo
      do k=1,nz
        do j=1,ny
          read(10,*) (u(i,j,k),i=1,nx)
        enddo
      enddo
      do k=1,nz
        do j=1,ny
          read(10,*) (v(i,j,k),i=1,nx)
        enddo
      enddo
      close(10)
c --- LITERAL ORIGINAL CALMET 6.5.0 FRADJ CALL BEGINS (DIAGNO L5643-L5644):
      call fradj(u,v,topo,gam,isurft,tinf,sfct,critfn,zface,highest)
c --- LITERAL ORIGINAL CALMET 6.5.0 FRADJ CALL ENDS.
      open(11,file=trim(fout),status='replace')
      do k=1,nz
        do j=1,ny
          do i=1,nx
            write(11,'(3(I4,1X),2(ES22.13E3,1X))')
     1        i,j,k,u(i,j,k),v(i,j,k)
          enddo
        enddo
      enddo
      close(11)
      end
"""

def original_source(vendor, out):
    """Literal FRADJ subroutine plus the chained stage driver."""
    path = out / "fradj_d9a_original.for"
    meta = fradj.extract(vendor / "calmet.for", "fradj", "gride", path)
    meta["name"] = "fradj"
    meta["diagno_call_lines"] = [5643, 5644]
    driver = out / "original_d9a_fradj.for"
    driver.write_text(DRIVER)
    return path, driver, meta

def compile_reference(vendor, out, base_flags):
    subroutine, driver, meta = original_source(vendor, out)
    binary = out / "original_d9a_fradj"
    fradj.run(list(base_flags) + [subroutine, driver, "-o", binary], timeout=120)
    return binary, meta

def fields(scene):
    """Deterministic synthetic terrain/heat envelope for one D9A scene."""
    name = scene["name"]
    if name == "upper_bias":
        terrain = [104. + 70. * math.sin(i * .13) + 30. * math.cos(j * .17)
                   for j in range(NY) for i in range(NX)]
    elif name == "unbiased":
        terrain = [100. + 160. * math.exp(-((i - 21) ** 2 + (j - 24) ** 2) / 90.)
                   for j in range(NY) for i in range(NX)]
    else:
        terrain = [100. + 160. * math.exp(-((i - 11) ** 2 + (j - 9) ** 2) / 90.)
                   for j in range(NY) for i in range(NX)]
    highest = [value + ENVELOPE_MARGIN_M for value in terrain]
    lapse = [0.006] * N
    temperature = [285. + 2. * math.sin(i * .13)
                   for j in range(NY) for i in range(NX)]
    return terrain, highest, lapse, temperature

def write_case(path, zface1_m, dz_m, terrain, highest, lapse, temperature, u, v):
    shapes = ((terrain, N), (highest, N), (lapse, N), (temperature, N),
              (u, N * NZ), (v, N * NZ))
    if any(len(field) != size for field, size in shapes):
        raise ValueError("FRADJ chained input shape")
    with path.open("w") as handle:
        handle.write(f"{zface1_m:.9f} {ISURFT} {TINF_K:.9f} {CRITFN:.9f}\n")
        handle.write(" ".join(f"{value:.9f}" for value in dz_m) + "\n")
        for field in (terrain, highest, lapse, temperature, u, v):
            for offset in range(0, len(field), NX):
                handle.write(" ".join(f"{value:.8f}"
                                      for value in field[offset:offset + NX]) + "\n")

def write_bridge_fields(handle, enabled, terrain, highest, lapse, temperature):
    """Append the IFRADJ control record and 50x50 planes to a d9a fixture.

    The planes are always written so the fixture record shape is fixed; the
    C++ bridge ignores them unless the IFRADJ flag is set.
    """
    handle.write(f"{1 if enabled else 0} {ISURFT} {TINF_K} {CRITFN}\n")
    for field in (terrain, highest, lapse, temperature):
        for offset in range(0, len(field), NX):
            handle.write(" ".join(f"{value:.8f}"
                                  for value in field[offset:offset + NX]) + "\n")

def read_output(path):
    rows = [line.split() for line in path.read_text().splitlines()]
    if len(rows) != N * NZ:
        raise RuntimeError("chained FRADJ output shape")
    u = []
    v = []
    for n, row in enumerate(rows):
        expected = (n % NX + 1, (n // NX) % NY + 1, n // N + 1)
        if len(row) != 5 or tuple(map(int, row[:3])) != expected:
            raise RuntimeError("chained FRADJ output ordering")
        u.append(float(row[3]))
        v.append(float(row[4]))
    return u, v

compare = fradj.compare
