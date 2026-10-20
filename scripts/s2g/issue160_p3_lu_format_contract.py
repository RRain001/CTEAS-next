#!/usr/bin/env python3
"""Issue #160 C5: independent LU.DAT v2.1 fixed-width P3-input FORMAT reader.

This deliberately does NOT run MAKEGEO, derive 38->14 surface parameters,
or produce GEO.DAT; all such physics/parity work belongs solely to #46.
Only 20km Hefei / Wolsong 200x200 input contracts are admitted by CLI.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys

USGS38=(11,12,13,14,15,16,17,21,22,23,24,31,32,33,41,42,43,51,52,
        53,54,55,61,62,71,72,73,74,75,76,77,81,82,83,84,85,91,92)
SITE={"inland":{"epsg":32650,"x0":"503.385","y0":"3523.769","nx":200,"ny":200},
      "wolsong":{"epsg":32652,"x0":"533.215","y0":"3942.629","nx":200,"ny":200}}
METHOD="P2_C_GLC30M_SOURCE_SUBPOINT_GLAZAS_LUGRID_R4_HITS_V1"

def require(v,why):
    if not v:raise ValueError("P2C_P3_FORMAT_"+why)

def digest(file:Path):
    h=hashlib.sha256()
    with file.open("rb") as r:
        for block in iter(lambda:r.read(1<<20),b""):
            h.update(block)
    return h.hexdigest()

def read_v21_f63(path:Path,*,epsg:int,x0:str,y0:str,nx:int,ny:int):
    require(path.is_file() and not path.is_symlink(),"SOURCE_NOT_REGULAR")
    expected_zone=str(epsg%100)+("N" if epsg<=32660 else "S")
    require(nx>0 and ny>0 and nx*ny<=40000 and epsg in (32650,32652),
            "GRID_SCOPE")
    stats={"fraction_fields":0,"nonempty_cells":0,"missing_cells":0,
           "f52_positive_cells":0,"f55_positive_cells":0,
           "mixed_water_cells":0,"max_printed_sum_error":0.}
    with path.open(encoding="utf-8") as fd:
        header=[fd.readline().rstrip("\r\n") for _ in range(11)]
        require(len(header)==11 and
                header[0].split()[:2]==["LU.DAT","2.1"],
                "VERSION_2_1_REQUIRED")
        require(header[1].strip()=="2","WRITHEAD_TWO_COMMENTS")
        require(header[2].strip()!="" and header[3].strip()!="",
                "COMMENT_RECORDS_MISSING")
        require(header[4].strip()=="FRACTION" and header[5].strip()=="UTM" and
                header[6].strip()==expected_zone and
                header[7].strip().startswith("WGS-84"),
                "UTM_HEMISPHERE_DATUM_AND_FRACTION")
        shape=header[8].split()
        require(len(shape)==7 and [int(v) for v in shape[:2]]==[nx,ny] and
                f"{float(shape[2]):.3f}"==x0 and
                f"{float(shape[3]):.3f}"==y0 and
                f"{float(shape[4]):.3f}"==f"{float(shape[5]):.3f}"=="0.100" and
                int(shape[6])==38,
                "GRID_ORIGIN_1M_SPACING_100M_AND_38_CLASSES")
        require(header[9].split()==["KM"],"METRIC_UNIT_HEADER")
        require(tuple(map(int,header[10].split()))==USGS38,
                "USGS38_INPUT_CATEGORY_ORDER")
        for n in range(nx*ny):
            line=fd.readline().rstrip("\r\n")
            require(len(line)>=238,"F6_3_ROW_TRUNCATED")
            try:
                i,j=int(line[:5]),int(line[5:10])
            except ValueError as exc:
                raise ValueError("P2C_P3_FORMAT_BAD_CELL_INDICES") from exc
            require(i==n%nx+1 and j==n//nx+1,
                    "SOUTH_UP_ROW_COLUMN_ORDER")
            fields=[line[10+6*k:16+6*k] for k in range(38)]
            require(all(re.fullmatch(r"\s*(?:0|1)?\.\d{3}\s*",v) for v in fields),
                    "FORTRAN_F6_3_FIXED_FIELD_ENCODING")
            fractions=[float(v) for v in fields]
            require(all(math.isfinite(v) and 0<=v<=1 for v in fractions),
                    "FRACTION_INVALID_VALUE")
            marker=line[238:].strip()
            require(marker in (".","Missing"),"INVALID_MISSING_SUFFIX")
            total=sum(fractions)
            if marker=="Missing":
                require(all(v==0 for v in fractions),
                        "MISSING_CELL_HAS_NONZERO_FRACTION")
                stats["missing_cells"]+=1
            else:
                # 38 independently rounded F6.3 fields. Allow at most
                # 38*0.0005 error from pre-printed unity; no physical
                # renormalization is attempted in the format validator.
                require(abs(total-1.)<=.019001,
                        "NONMISSING_CELL_SUM_OUTSIDE_F6_3_BOUND")
                stats["nonempty_cells"]+=1
                stats["max_printed_sum_error"]=max(
                    stats["max_printed_sum_error"],abs(total-1.))
            water52=fractions[USGS38.index(52)]>0.
            water55=fractions[USGS38.index(55)]>0.
            stats["f52_positive_cells"]+=water52
            stats["f55_positive_cells"]+=water55
            stats["mixed_water_cells"]+=water52 and water55
            stats["fraction_fields"]+=38
        require(fd.readline()=="","EXTRA_ROWS_BEYOND_GRID")
    require(stats["fraction_fields"]==nx*ny*38 and
            stats["nonempty_cells"]+stats["missing_cells"]==nx*ny,
            "TOTAL_GRID_ACCOUNTING")
    return stats

def consume(site:str,lu:Path,manifest:Path,out:Path):
    require(site in SITE,"UNSUPPORTED_SITE")
    expected=SITE[site]
    require(manifest.is_file() and not manifest.is_symlink(),
            "PROVENANCE_MISSING")
    m=json.loads(manifest.read_text())
    require(m.get("producer")=="cteas_p2c_glc30m_sampling" and
            m.get("method")==METHOD and m.get("site")==site and
            m.get("utm_epsg")==expected["epsg"] and
            m.get("nx")==expected["nx"] and m.get("ny")==expected["ny"] and
            m.get("mesh")==10 and m.get("classes")==38 and
            m.get("xrefkm")==expected["x0"] and m.get("yrefkm")==expected["y0"] and
            m.get("lu_dat_sha256")==digest(lu),
            "PRODUCER_SOURCE_AND_GRID_MANIFEST")
    s=read_v21_f63(lu,**expected)
    require(s["nonempty_cells"]==m["nonempty_cells"] and
            s["missing_cells"]==m["missing_cells"] and
            s["fraction_fields"]==m["fraction_fields"],
            "PRODUCER_AND_INDEPENDENT_READER_ACCOUNTING")
    if site=="inland":
        require(s["f55_positive_cells"]==0,"INLAND_MARINE55_FORBIDDEN")
    require(not out.exists(),"EVIDENCE_WOULD_OVERWRITE")
    r={"status":"P2C_P3_LU_DAT_V2_1_FORMAT_ONLY_COMPATIBLE",
       "scope":site.upper()+"_20KM_200X200",
       "producer_method":METHOD,
       "input_sha256":digest(lu),"producer_manifest_sha256":digest(manifest),
       "independent_consumer":"PYTHON_FIXED_WIDTH_USGS38_HEADER_ORDER_F63_MISSING",
       "verified_utm_epsg":expected["epsg"],
       "xrefkm":expected["x0"],"yrefkm":expected["y0"],
       "nx":expected["nx"],"ny":expected["ny"],"classes":38,
       "statistics":s,
       "p3_38to14_parameter_calculation":"OUT_OF_SCOPE_ISSUE46",
       "p3_original_makegeo_numeric_parity":"NOT_RUN",
       "p3_actual_current_native_50x50_reader":"NOT_USED"}
    out.write_text(json.dumps(r,indent=2)+"\n")
    return r

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--site",choices=SITE,required=True)
    p.add_argument("--lu",type=Path,required=True)
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    try:
        r=consume(a.site,a.lu,a.manifest,a.out)
        print(json.dumps({k:r[k] for k in ("status","scope","verified_utm_epsg","statistics")}))
        return 0
    except (ValueError,KeyError,OSError,IndexError) as exc:
        print(f"P2C_P3_FORMAT_FAIL_CLOSED:{exc}",file=sys.stderr)
        return 2
if __name__=="__main__":
    raise SystemExit(main())
