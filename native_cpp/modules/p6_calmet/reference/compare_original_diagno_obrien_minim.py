#!/usr/bin/env python3
"""Parity for the selected original CALMET 6.5.0 DIAGNO IOBR=1 tail.

The unmodified original sources are compiled together: the literal DIAGNO
L6119-L6148 SMOOTH/DIVCEL/W block, the literal L6153-L6159 O'Brien (1970)
vertical-velocity error adjustment and the literal L6180
``IF (IOBR .EQ. 1) CALL MINIM(U,V,W,UB,VB,DIV,NITER,DIVLIM)`` calling the
unchanged ``minim`` subroutine.  The skipped L6160-L6179 interval is verified
to contain printing only.  Original CELLZB(K)=ZFACE(K) is reproduced from DZ
exactly as calmet.for L5151/L5157 does.
This is a SYNTHETIC source-only audit and no real-case 2022 equivalence is
implied; upstream topology/heat/Froude/slope stages remain unimplemented.
"""
import hashlib
from pathlib import Path

import compare_original_diagno_final_segment as diag

SOURCE_BLOB = diag.SOURCE_BLOB
OBRIEN_LINES = (6153, 6159)
MINIM_CALL_LINE = 6180
MINIM_ROUTINE_LINES = (9645, 9762)
PRINT_ONLY_FIRST, PRINT_ONLY_LAST = 6160, 6179
PRINT_ONLY_ALLOWED = {
    "IF (IPR2 .LE. 0) GO TO 360",
    "WRITE(IWR,2400)",
    "WRITE(IWR,2402)",
    "CALL WINDPR(U,V,W)",
    "WRITE(IWR,2401) DIVMAX",
    "CALL DIVPR(DIV)",
    "360 CONTINUE",
}

def _source_lines(vendor):
    raw = (vendor / "calmet.for").read_bytes()
    sha = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    if sha != SOURCE_BLOB:
        raise RuntimeError("original CALMET source drift " + sha)
    return raw.decode().splitlines(keepends=True)

def _driver(block, obrien, minim_call):
    """diag.DRIVER_HEAD extended with CELLZB/NITER/DIVLIM/IOBR controls."""
    marker = "c --- LITERAL ORIGINAL DIAGNO SOURCE"
    head = diag.DRIVER_HEAD
    if marker not in head:
        raise RuntimeError("DIAGNO driver head marker drift")
    declared = head.replace(
        "      integer nsmth(mxnz),side\n",
        "      include 'd6.met'\n"
        "      integer nsmth(mxnz),side\n"
        "      real cellzb(mxnzp1)\n"
        "      integer iobr,niter\n"
        "      real divlim,zface1\n", 1)
    if declared == head:
        raise RuntimeError("DIAGNO driver declaration anchor drift")
    if declared.count("      close(10)\n") != 1:
        raise RuntimeError("DIAGNO driver unit 10 anchor drift")
    declared = declared.replace(
        "      close(10)\n",
        "      read(10,*) zface1,iobr,niter,divlim\n"
        "      close(10)\n", 1)
    # Original CELLZB(i)=ZFACE(i) (calmet.for L5151/L5157); the driver owns
    # ZFACE(1) so the O'Brien height ratio is exercised off the ground.
    setup = ("      nzp1=nz+1\n"
             "      iwr=0\n"
             "      zface(1)=zface1\n"
             "      do k=1,nz\n"
             "        zface(k+1)=zface(k)+dz(k)\n"
             "      enddo\n"
             "      do k=1,nzp1\n"
             "        cellzb(k)=zface(k)\n"
             "      enddo\n")
    position = declared.index(marker)
    return (declared[:position] + setup + declared[position:] +
            block + obrien + minim_call + diag.DRIVER_TAIL)

def original_source(vendor, out):
    """Literal original O'Brien/MINIM tail plus the reused SMOOTH/DIVCEL/W block."""
    lines = _source_lines(vendor)
    routines, block, _ = diag.original_source(vendor, out)
    first, last = OBRIEN_LINES
    if lines[first - 1] != "      IF (IOBR .EQ. 1) THEN\n":
        raise RuntimeError("DIAGNO IOBR guard anchor drift")
    if lines[6156] != ("        W(I,J,K+1)=W(I,J,K+1)-CELLZB(K+1)/CELLZB(NZP1)"
                       "*W(I,J,NZP1)\n"):
        raise RuntimeError("DIAGNO O'Brien adjustment anchor drift")
    if lines[last - 1] != "      ENDIF\n":
        raise RuntimeError("DIAGNO IOBR guard end anchor drift")
    for number in range(PRINT_ONLY_FIRST, PRINT_ONLY_LAST + 1):
        text = lines[number - 1].strip()
        if not text or lines[number - 1][0] in "cC*":
            continue
        if text not in PRINT_ONLY_ALLOWED:
            raise RuntimeError(f"DIAGNO L{number} is not print-only: {text!r}")
    minim_sig = ("      IF (IOBR .EQ. 1) CALL MINIM(U,V,W,UB,VB,DIV,NITER,"
                 "DIVLIM)\n")
    if lines[MINIM_CALL_LINE - 1] != minim_sig:
        raise RuntimeError("DIAGNO MINIM call anchor drift")
    routine_first, routine_after = MINIM_ROUTINE_LINES
    if not lines[routine_first - 1].lower().startswith("      subroutine minim("):
        raise RuntimeError("MINIM subroutine anchor drift")
    if not lines[routine_after - 1].lower().startswith("      subroutine missfc("):
        raise RuntimeError("MINIM subroutine end anchor drift")
    minim_path = out / "minim_original.for"
    minim_path.write_text("".join(lines[routine_first - 1:routine_after - 1]))
    obrien = "".join(lines[first - 1:last])
    minim_call = lines[MINIM_CALL_LINE - 1]
    driver = out / "original_diagno_obrien_minim.for"
    driver.write_text(_driver(block, obrien, minim_call))
    meta = {
        "obrien_lines": [first, last],
        "obrien_sha256": hashlib.sha256(obrien.encode()).hexdigest(),
        "minim_call_line": MINIM_CALL_LINE,
        "minim_call_sha256": hashlib.sha256(minim_call.encode()).hexdigest(),
        "skipped_print_only_lines": [PRINT_ONLY_FIRST, PRINT_ONLY_LAST],
        "cellzb_source_lines": [5151, 5157],
        "minim_subroutine": {
            "first_line": routine_first,
            "last_line": routine_after - 1,
            "sha256": hashlib.sha256(minim_path.read_bytes()).hexdigest(),
        },
    }
    return routines + [(minim_path, meta["minim_subroutine"])], meta

def compile_reference(vendor, out, base_flags):
    routines, meta = original_source(vendor, out)
    binary = out / "original_diagno_obrien_minim"
    diag.run(list(base_flags) + [str(path) for path, _ in routines] +
             [str(out / "original_diagno_obrien_minim.for"), "-o", str(binary)])
    return binary, meta

def write_case(path, passes, fields, zface1_m, iobr, niter, divlim_per_s):
    """diag.write_case format plus the IOBR/CELLZB/MINIM control record."""
    diag.write_case(path, passes, fields)
    with path.open("a") as handle:
        handle.write(f"{zface1_m:.9f} {iobr} {niter} {divlim_per_s:.9f}\n")

def top_face_nonzero(path):
    """Count non-zero W(NZP1) cells in an original segment trace."""
    rows = [line.split() for line in path.read_text().splitlines()]
    if len(rows) != diag.N * diag.NZ:
        raise ValueError("original IOBR tail trace shape")
    return sum(1 for row in rows if int(row[2]) == diag.NZ and float(row[7]) != 0.)

compare = diag.compare
