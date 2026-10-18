#!/usr/bin/env python3
"""#54 D2/D3: dynamic-grid original TERREL DAT/SAV vs native CSV parity gate.

A numeric match is PROVISIONAL until independent real source, control,
original executable and logs are audited. Never redistribute raw assets.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
import re
import struct
from pathlib import Path

DAT_TOLERANCE_M=0.0500001
RAW_TOLERANCE_M=0.00001
MAX_CELLS=10_000_000

class ComparisonError(ValueError):
    pass

def sha(path:Path)->str:
    if path.is_symlink() or not path.is_file() or path.stat().st_size==0:
        raise ComparisonError("missing/empty/symlinked evidence file")
    h=hashlib.sha256()
    with path.open("rb") as f:
        for buf in iter(lambda:f.read(1<<20),b""):
            h.update(buf)
    return h.hexdigest()

def json_obj(path:Path)->dict:
    sha(path)
    try:
        value=json.loads(path.read_text(encoding="utf-8"))
    except (ValueError,UnicodeError) as e:
        raise ComparisonError("invalid evidence JSON") from e
    if not isinstance(value,dict):
        raise ComparisonError("evidence must be a JSON mapping")
    return value

def fortran_sav(path:Path,nx:int,ny:int):
    # Only the already-audited gfortran TERREL record format: 4-byte little
    # endian sequential-unformatted markers. Do not guess other encodings.
    raw=path.read_bytes()
    pos,records=0,[]
    while pos<len(raw):
        if pos+8>len(raw):
            raise ComparisonError("truncated SAV record")
        (length,)=struct.unpack_from("<i",raw,pos)
        if length<0 or length>200_000_000 or pos+8+length>len(raw):
            raise ComparisonError("invalid SAV record size")
        (end,)=struct.unpack_from("<i",raw,pos+4+length)
        if end!=length:
            raise ComparisonError("SAV closing marker differs")
        records.append(raw[pos+4:pos+4+length]);pos+=length+8
    count=nx*ny
    if len(records)<4 or len(records[0])!=28 or any(len(v)!=count*4 for v in records[1:4]):
        raise ComparisonError("unsupported SAV record schema/shape")
    header=struct.unpack("<7i",records[0])
    if header[4:6]!=(nx,ny):
        raise ComparisonError("SAV grid dimensions differ")
    sums=struct.unpack(f"<{count}f",records[1])
    hits=struct.unpack(f"<{count}i",records[2])
    if any(h<0 for h in hits) or not all(math.isfinite(s) for s in sums):
        raise ComparisonError("SAV invalid hit histogram or sums")
    return sums,hits

def fortran_dat(path:Path,grid:dict):
    lines=path.read_text(encoding="utf-8").splitlines()
    nx,ny=grid["nx"],grid["ny"]
    if len(lines)<11 or lines[0].split()[:2]!=["TERREL.DAT","2.0"]:
        raise ComparisonError("TERREL.DAT version/header mismatch")
    if (lines[4].strip()!="UTM" or
        lines[5].strip()!=f'{grid["zone"]}{grid["hemisphere"]}' or
        not lines[6].startswith("WGS-84") or
        lines[8].split()!=["KM","M"] or lines[9].split()!=["W_E","N_S"]):
        raise ComparisonError("TERREL.DAT projection/datum/units mismatch")
    meta=lines[7].split()
    if len(meta)!=6:
        raise ComparisonError("TERREL.DAT grid-header column mismatch")
    try:
        sx,sy=int(meta[0]),int(meta[1])
        x,y,dx,dy=map(float,meta[2:])
    except ValueError as e:
        raise ComparisonError("TERREL.DAT malformed grid header") from e
    if ((sx,sy)!=(nx,ny) or
        abs(x-float(grid["xrefkm"]))>1e-6 or abs(y-float(grid["yrefkm"]))>1e-6 or
        abs(dx-grid["dgridkm"])>1e-9 or abs(dy-grid["dgridkm"])>1e-9):
        raise ComparisonError("TERREL.DAT differs from authoritative grid")
    # Original F8.1 records: max 10 values per line, restarting each j.
    perrow=(nx+9)//10;payload=lines[10:]
    if len(payload)!=perrow*ny:
        raise ComparisonError("TERREL.DAT row-count/layout mismatch")
    vals=[]
    for rowno in range(ny):
        row=[]
        for block in range(perrow):
            line=payload[rowno*perrow+block]
            nfields=min(10,nx-len(row))
            if len(line)!=8*nfields:
                raise ComparisonError("TERREL.DAT F8.1 width mismatch")
            for col in range(nfields):
                token=line[8*col:8*(col+1)]
                if not re.fullmatch(r"\s*-?\d+\.\d",token):
                    raise ComparisonError("TERREL.DAT malformed F8.1 value")
                row.append(float(token))
        vals+=row
    # DAT north->south; native and SAV south->north
    return [vals[(ny-1-j)*nx+i] for j in range(ny) for i in range(nx)]

def native_csv(path:Path,nx:int,ny:int):
    hits,heights=[],[]
    with path.open(newline="",encoding="utf-8") as f:
        reader=csv.DictReader(f)
        if reader.fieldnames!=["i","j","hits","elevation_m"]:
            raise ComparisonError("native terrain CSV header invalid")
        for n,row in enumerate(reader):
            if n>=nx*ny:raise ComparisonError("native CSV has extra model cells")
            try:
                i,j,h=int(row["i"]),int(row["j"]),int(row["hits"])
                z=float(row["elevation_m"])
            except (ValueError,TypeError) as e:
                raise ComparisonError("native terrain CSV contains malformed number") from e
            if (i,j)!=(n%nx+1,n//nx+1) or h<0 or not math.isfinite(z):
                raise ComparisonError("native terrain index/hit/height invalid")
            hits.append(h);heights.append(z)
    if len(hits)!=nx*ny:
        raise ComparisonError("native terrain CSV incomplete")
    return hits,heights


def validate_original_terrel_control(path:Path, selected_tif:Path, grid:dict)->dict:
    """Fail closed unless the original TERREL input deck names the same TIFF bytes
    and the exact zone, origin, dimensions and spacing as native P1.
    This cannot by itself prove the original executable was actually launched.
    """
    try:
        deck=path.read_text(encoding="utf-8")
    except (UnicodeError,OSError) as e:
        raise ComparisonError("original TERREL control unreadable") from e

    def key(name:str)->str:
        found=re.findall(r"!\s*"+re.escape(name)+r"\s*=\s*([^!]*?)\s*!",deck,re.IGNORECASE)
        if len(found)!=1:
            raise ComparisonError("TERREL control absent/duplicated "+name)
        return found[0].strip()

    if key("PMAP").upper()!="UTM" or key("DATUM").upper()!="WGS-84":
        raise ComparisonError("TERREL control projection/datum mismatch")
    if key("UTMHEM").upper()!=grid["hemisphere"]:
        raise ComparisonError("TERREL control hemisphere mismatch")
    for name,expected in (("IUTMZN",grid["zone"]),
                          ("NX",grid["nx"]),("NY",grid["ny"]),("NTDF",1)):
        value=key(name)
        if not re.fullmatch(r"\d+",value) or int(value)!=expected:
            raise ComparisonError("TERREL control mismatched "+name)
    for name,expected in (("XREFKM",float(grid["xrefkm"])),
                          ("YREFKM",float(grid["yrefkm"])),
                          ("DGRIDKM",grid["dgridkm"])):
        try:
            value=float(key(name))
        except ValueError as e:
            raise ComparisonError("TERREL control invalid "+name) from e
        if not math.isfinite(value) or abs(value-expected)>1e-8:
            raise ComparisonError("TERREL control mismatched "+name)

    # The selected original's GEOTIFF card is numbered in Subgroup 0b.
    # Exactly one non-ambiguous TIFF is supported for the existing unified
    # source manifest. Multiple original inputs must be re-audited separately.
    sources=re.findall(r"^\s*(\d+)\s*!GEOTIFF\s*=\s*([^!]+?)\s*!",
                       deck,re.MULTILINE|re.IGNORECASE)
    if len(sources)!=1 or sources[0][0]!="1":
        raise ComparisonError("TERREL control requires one numbered GEOTIFF")
    raw=sources[0][1].strip()
    if not raw:
        raise ComparisonError("TERREL control GEOTIFF path empty")
    original_tif=Path(raw)
    if not original_tif.is_absolute():
        original_tif=path.parent/original_tif
    # No silent missing path or symlink indirection; actual bytes must be same.
    source_sha=sha(original_tif)
    if source_sha!=sha(selected_tif):
        raise ComparisonError("TERREL original GEOTIFF bytes differ from native selected TIFF")
    return {"original_control_geotiff_sha256":source_sha,
            "original_control_geotiff_count":1,
            "original_control_geometry":"MATCH_NATIVE_P1"}

def compare(*,native_manifest:Path,original_attestation:Path,native_terrain:Path,
            original_dat_path:Path,original_sav_path:Path,original_control:Path,
            original_executable:Path,selected_tif:Path,report:Path)->dict:
    native=json_obj(native_manifest)
    attest=json_obj(original_attestation)
    grid=native.get("grid")
    if (not isinstance(grid,dict) or native.get("producer_issue")!=54 or
        native.get("status")!="PRODUCED_UNVERIFIED" or
        native.get("route") not in ("P1_A_90M_LOCAL","P1_B_30M_DOWNLOAD")):
        raise ComparisonError("native P1 manifest not admitted")
    nx,ny=grid.get("nx"),grid.get("ny")
    if (type(nx) is not int or type(ny) is not int or nx<1 or ny<1 or nx*ny>MAX_CELLS):
        raise ComparisonError("native grid dimensions invalid")
    if (type(grid.get("zone")) is not int or not 1<=grid["zone"]<=60 or
        grid.get("hemisphere") not in ("N","S") or
        not all(isinstance(grid.get(k),str) and
                re.fullmatch(r"-?\d+\.\d{3}",grid[k]) for k in ("xrefkm","yrefkm"))):
        raise ComparisonError("native WGS84 UTM/3-decimal origin invalid")
    spacing=grid.get("dgridkm")
    if type(spacing) not in (int,float) or not math.isfinite(spacing) or spacing<=0:
        raise ComparisonError("invalid DGRIDKM")
    # Always rehash the actual bytes, never just trust a source manifest.
    actual={
      "selected_tif_sha256":sha(selected_tif),
      "original_terrel_dat_sha256":sha(original_dat_path),
      "original_terrel_sav_sha256":sha(original_sav_path),
      "original_control_sha256":sha(original_control),
      "original_executable_sha256":sha(original_executable),
    }
    if actual["selected_tif_sha256"]!=native.get("selected_tif_sha256"):
        raise ComparisonError("real selected TIFF hash differs from native source")
    if sha(native_terrain)!=native.get("terrain_csv_sha256"):
        raise ComparisonError("native CSV changed after calculation")
    if any(attest.get(k)!=v for k,v in actual.items()):
        raise ComparisonError("original attestation does not match actual bytes")
    if attest.get("grid_sha256")!=native.get("grid_sha256") or attest.get("route")!=native["route"]:
        raise ComparisonError("original/native grid or route identities differ")
    # Verify the actual original TERREL control references the same selected
    # source bytes and authoritative grid, rather than merely trusting JSON.
    control_binding=validate_original_terrel_control(original_control,selected_tif,grid)
    # This still does not independently prove that original TERREL executed.
    data=fortran_dat(original_dat_path,grid)
    sums,oldhits=fortran_sav(original_sav_path,nx,ny)
    newhits,newz=native_csv(native_terrain,nx,ny)
    means=[s/h if h else -999.0 for s,h in zip(sums,oldhits)]
    badcounts,badmask,baddat,badmean=[],[],[],[]
    maxdat=maxraw=0.0
    for k,(old,new,dat,mean,z) in enumerate(zip(oldhits,newhits,data,means,newz)):
        i,j=k%nx+1,k//nx+1
        if old!=new:badcounts.append([i,j,old,new])
        if (old==0)!=(new==0):badmask.append([i,j,old,new])
        errdat,errraw=abs(dat-z),abs(mean-z)
        maxdat=max(maxdat,errdat);maxraw=max(maxraw,errraw)
        if errdat>DAT_TOLERANCE_M:baddat.append([i,j,dat,z,errdat])
        if errraw>RAW_TOLERANCE_M:badmean.append([i,j,mean,z,errraw])
    passed=not (badcounts or badmask or baddat or badmean)
    result={
      "schema_version":"p1-generic-fortran-native-parity-v1",
      "producer_issue":54,"route":native["route"],"grid":grid,
      "numeric_parity":"NUMERIC_PASS_PROVISIONAL" if passed else "NUMERIC_FAIL",
      "science_acceptance":"NOT_ACCEPTED_INDEPENDENT_ORIGINAL_RUN_AUDIT_REQUIRED",
      "original_run_attestation":"CLAIM_REQUIRES_CONTROL_AND_LOG_AUDIT",
      "cells":nx*ny,"dat_f8_1_tolerance_m":DAT_TOLERANCE_M,
      "sav_real4_mean_tolerance_m":RAW_TOLERANCE_M,
      "native_csv_sha256":sha(native_terrain),
      "original_attestation_sha256":sha(original_attestation),
      "selected_tif_sha256":actual["selected_tif_sha256"],
      "original_terrel_dat_sha256":actual["original_terrel_dat_sha256"],
      "original_terrel_sav_sha256":actual["original_terrel_sav_sha256"],
      "original_control_sha256":actual["original_control_sha256"],
      "original_control_source_binding":control_binding,
      "original_executable_sha256":actual["original_executable_sha256"],
      "original_hits_total":sum(oldhits),"native_hits_total":sum(newhits),
      "hit_count_mismatches":len(badcounts),"hit_count_first20":badcounts[:20],
      "missing_mask_mismatches":len(badmask),"missing_mask_first20":badmask[:20],
      "dat_bad_cells":len(baddat),"dat_first20":baddat[:20],
      "raw_mean_bad_cells":len(badmean),"raw_mean_first20":badmean[:20],
      "max_dat_error_m":maxdat,"max_raw_mean_error_m":maxraw
    }
    if report.exists() or report.is_symlink():
        raise ComparisonError("report exists; no overwriting evidence")
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return result

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("native_manifest","original_attestation","native_terrain",
                "original_dat_path","original_sav_path","original_control",
                "original_executable","selected_tif","report"):
        p.add_argument("--"+key.replace("_","-"),required=True,type=Path)
    try:
        result=compare(**vars(p.parse_args(argv)))
        print(json.dumps({"numeric_parity":result["numeric_parity"],
                          "science_acceptance":result["science_acceptance"],
                          "route":result["route"]}))
        return 0 if result["numeric_parity"]=="NUMERIC_PASS_PROVISIONAL" else 1
    except (OSError,UnicodeError,ValueError,struct.error) as exc:
        print(json.dumps({"numeric_parity":"BLOCKED_INPUT_OR_FORMAT",
                          "science_acceptance":"NOT_ACCEPTED",
                          "reason_type":type(exc).__name__}))
        return 2

if __name__=="__main__":
    raise SystemExit(main())
