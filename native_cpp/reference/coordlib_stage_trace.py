"""Scratch-only COORDLIB stage trace for #53 GLAZAS, never a science oracle.

Reads the unchanged, pinned original CTEAS vendor COORDLIB.FOR at runtime.
Only adds tagged REAL*8 hexadecimal diagnostics in its LAZA2UTM path.
The generated derivative and its fort.99 raw trace remain runner-local;
unmodified CTGPROC LFINAL=F/T and byte-equality checks remain authoritative.
"""
from __future__ import annotations

import math
from pathlib import Path
import struct

from native_cpp.reference.validate_p2_glazas_original import (
    GateError, file_sha, require,
)
from native_cpp.reference.diagnose_glazas_mesh_coordinates import f32

BEGIN = "      IF(IRNKIN.NE.IRNKIO.AND.INSYS.NE.0.AND.IOSYS.NE.0)THEN"
END = "C --- DOES ONLY A DATUM SHIFT"
P11_MARK = "         IF(IFLG.NE.0)RETURN\nC\nC --- STEP 2 DATUM TRANSFORMATION"
DAT_MARK = "         XYZIO(3) = DBLE(ZLEVIO)\nC\nC --- GETS THE TO UTM ZONE"
P09_MARK = "         UTMOUT = DBLE(IOZONE)"
KM_MARK = ("         XYZIO(2) = CRDIO(2)*DBLE(XMULTO)\n"
           "      ENDIF\nC\nC --- NOW DOES A 'TO' (OUTPUT) PROJECTION CHECK")
STAGES = ("P11", "DAT", "P09", "KM")


def _trace_write(tag: str, x: str, y: str) -> str:
    # Fixed-form Fortran (72 columns) and exact, portable IEEE-754 bit words.
    return (
        "         if(IPROJ.eq.'LAZA2UTM    ') then\n"
        "           write(99,'(a,1x,4(z16.16,1x))') '"+tag+"',\n"
        "     &       transfer(XYZIN(1),0_8),\n"
        "     &       transfer(XYZIN(2),0_8),\n"
        "     &       transfer("+x+",0_8),\n"
        "     &       transfer("+y+",0_8)\n"
        "         endif\n"
    )


def instrument_coordlib(source: str) -> str:
    """Change only the bounded original COORDS LAZA2UTM stage observation."""
    require(source.count(BEGIN)==1, "COORD_STAGE_BRANCH_DRIFT")
    begin=source.index(BEGIN)
    end=source.index(END,begin+len(BEGIN))
    branch=source[begin:end]
    for marker in (P11_MARK,DAT_MARK,P09_MARK):
        require(branch.count(marker)==1, "COORD_STAGE_MARKER_DRIFT")
    require(source.count(KM_MARK)==1, "COORD_STAGE_KM_MARKER_DRIFT")
    branch=branch.replace(P11_MARK,
        _trace_write("P11","CRDIO(1)","CRDIO(2)")+P11_MARK,1)
    branch=branch.replace(DAT_MARK,
        _trace_write("DAT","CRDIN(1)","CRDIN(2)")+DAT_MARK,1)
    branch=branch.replace(P09_MARK,
        _trace_write("P09","CRDIO(1)","CRDIO(2)")+P09_MARK,1)
    result=source[:begin]+branch+source[end:]
    result=result.replace(KM_MARK,
        KM_MARK.replace("C\nC --- NOW DOES", 
            _trace_write("KM","XYZIO(1)","XYZIO(2)")+"C\nC --- NOW DOES"),1)
    require(result.count("write(99,")==4,
            "COORD_STAGE_INSTRUMENTATION_COUNT")
    return result


def create_staged_include(original: Path, destination: Path) -> str:
    require(original.is_file() and not original.is_symlink(),
            "COORD_STAGE_PINNED_VENDOR_INCLUDE_REQUIRED")
    require(destination.parent.is_dir() and not destination.exists(),
            "COORD_STAGE_DESTINATION_NOT_ISOLATED")
    original_bytes=original.read_bytes()
    require(original_bytes and b"SUBROUTINE COORDS" in original_bytes,
            "COORD_STAGE_UNEXPECTED_VENDOR")
    patched=instrument_coordlib(original_bytes.decode("latin1"))
    destination.write_bytes(patched.encode("latin1"))
    return file_sha(destination)


def _d64(hex_string: str) -> float:
    require(len(hex_string)==16 and all(c in "0123456789ABCDEFabcdef"
                                       for c in hex_string),
            "COORD_STAGE_BAD_HEX_WORD")
    value=struct.unpack(">d",bytes.fromhex(hex_string))[0]
    require(math.isfinite(value),"COORD_STAGE_NOT_FINITE")
    return value


def _xy_key(x: float,y: float) -> bytes:
    return struct.pack("<ff",f32(x),f32(y))


def read_staged_records(path: Path) -> dict:
    require(path.is_file() and not path.is_symlink(),
            "COORD_STAGE_TRACE_MISSING")
    result={}
    nlines=0
    with path.open(encoding="ascii",errors="strict") as fp:
        for line in fp:
            nlines+=1
            require(nlines<=3000000,"COORD_STAGE_TRACE_TOO_LARGE")
            parts=line.split()
            require(len(parts)==5 and parts[0] in STAGES,
                    "COORD_STAGE_BAD_TRACE_ROW")
            vals=[_d64(x) for x in parts[1:]]
            key=_xy_key(vals[0],vals[1])
            item=result.setdefault(key,{"input":vals[:2]})
            require(parts[0] not in item,
                    "COORD_STAGE_DUPLICATE_SOURCE_STAGE")
            item[parts[0]]=vals[2:]
    require(nlines>0,"COORD_STAGE_TRACE_EMPTY")
    return {"rows":result,"raw_stage_records":nlines}


def summarize_staged_records(indexed_original: dict,staged: dict) -> dict:
    """Check stage coverage via exact REAL*4 LAEA keys; never infer parity."""
    rows=staged["rows"]
    missing=0
    matches=0
    max_datum_deg=0.0
    max_scale_resid_m=0.0
    max_real4_resid_m=0.0
    preview=[]
    for key,orig in sorted(indexed_original.items()):
        coordkey=_xy_key(orig["laea_x"],orig["laea_y"])
        stage=rows.get(coordkey)
        if stage is None or not all(s in stage for s in STAGES):
            missing+=1
            continue
        matches+=1
        p11=stage["P11"];datum=stage["DAT"];p09=stage["P09"]
        km=stage["KM"]
        delta=math.hypot(datum[0]-p11[0],datum[1]-p11[1])
        max_datum_deg=max(max_datum_deg,delta)
        xkm=p09[0]*float(f32(.001))
        ykm=p09[1]*float(f32(.001))
        max_scale_resid_m=max(max_scale_resid_m,
                              1000*max(abs(xkm-km[0]),abs(ykm-km[1])))
        max_real4_resid_m=max(max_real4_resid_m,
            1000*max(abs(f32(km[0])-f32(orig["x"])),
                     abs(f32(km[1])-f32(orig["y"]))))
        if len(preview)<12:
            preview.append({
                "source_i":key[0],"source_j":key[1],
                "mesh_i":key[2],"mesh_j":key[3],
                "PJ11_geographic_deg":p11,
                "DAT2DAT_geographic_deg":datum,
                "PJ09_utm_m":p09,
                "COORDS_km_real8":km,
            })
    require(matches>0 and missing==0,
            "COORD_STAGE_INDEXED_ORIGINAL_COVERAGE_INCOMPLETE")
    require(max_real4_resid_m==0.0,
            "COORD_STAGE_GLOBE_REAL4_DOES_NOT_MATCH_UNMODIFIED_QA")
    require(max_scale_resid_m==0.0,
            "COORD_STAGE_XMULTO_REAL8_STAGE_DRIFT")
    return {
        "status":"DIAGNOSTIC_ONLY_NOT_SCIENTIFIC_ORACLE",
        "method":"original_gctp_stage_real8_hex_with_real4_source_join",
        "raw_stage_records":staged["raw_stage_records"],
        "original_indexed_stage_matches":matches,
        "original_indexed_stage_missing":missing,
        "max_PJ11_to_DAT2DAT_delta_deg":max_datum_deg,
        "max_XMULTO_real8_stage_residual_m":max_scale_resid_m,
        "max_GLOBE_real4_stage_residual_m":max_real4_resid_m,
        "first_12_stage_examples":preview,
    }
