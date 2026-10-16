#!/usr/bin/env python3
"""G33A: first original-calmet-vs-C++ divergence in two hourly SURFVAR passes.

Run unmodified SHA-pinned CALMET 6.5.0 on real G19 2SS+2US first hour,
then compile a COPY with two DIAGNO write-only TEMP2D snapshots, exactly
after each authentic SURFVAR call (first after WIND1, second after FRADJ).
Output MET.DAT must remain byte-identical to the untouched original.
Compare independently computed C++ G17B4 per-cell temperature at each
checkpoint. This is diagnostic only, never original science acceptance.
"""
from __future__ import annotations
import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import re
import shutil
import struct
from pathlib import Path

import original_internal_state_dump as original

NX = NY = 12
CELLS = NX*NY
RECORD_BYTES = 24 + 4*CELLS

HELPER = r"""
c --- G33A: TEST-ONLY write-only source CALMET SURFVAR TEMP2D snapshots
      subroutine dgm_g33a_surfvar(kpt,temp2d)
      include 'params.met'
      include 'gen.met'
      include 'grid.met'
      integer kpt,i,j
      real temp2d(mxnx,mxny)
      logical opened
      save opened
      data opened/.false./
      if(.not.opened)then
         open(92,file='g33a_surfvar_two_pass.bin',
     1        form='unformatted',access='stream',status='replace')
         opened=.true.
      endif
      write(92) kpt,ndathrb,nsecb,nx,ny,0
      write(92) ((temp2d(i,j),i=1,nx),j=1,ny)
      return
      end
"""

def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def patch_vendor(original_path:Path,out:Path):
    if sha(original_path)!=original.ORIGINAL_CALMET_SHA256:
        raise RuntimeError("G33A original vendor source provenance SHA drift")
    lines=original_path.read_text().splitlines(keepends=True)
    match=re.compile(r"\bCALL\s+SURFVAR\s*\(",re.IGNORECASE)
    anchors=[]
    for start0 in range(5580,5700):
        if not match.search(lines[start0]):continue
        opened=0
        last=None
        for idx in range(start0,min(len(lines),start0+12)):
            # CALMET original is fixed-form Fortran, comment cards excluded.
            if lines[idx][:1].lower() in ("c","*","!"):
                raise RuntimeError("G33A SURFVAR call continuation crosses comment")
            opened+=lines[idx].count("(")-lines[idx].count(")")
            if opened==0 and "(" in "".join(lines[start0:idx+1]):
                last=idx
                break
        if last is None:raise RuntimeError("G33A original SURFVAR call not closed")
        anchors.append((start0,last))
    if len(anchors)!=2 or not (5590<=anchors[0][0]+1<=5620) or not (5650<=anchors[1][0]+1<=5690):
        raise RuntimeError(
            "G33A source original SURFVAR 2-call ordering/locations unexpected: "+
            repr([(a+1,b+1) for a,b in anchors]))
    # Anchors must not overlap; deterministic source-order injection.
    if anchors[0][1]>=anchors[1][0]:
        raise RuntimeError("G33A SURFVAR call scopes overlap")
    add={end:f"      call dgm_g33a_surfvar({index},temp2d)\n"
         for index,(_start,end) in enumerate(anchors,1)}
    out.write_text("".join(line+add.get(idx,"")
                           for idx,line in enumerate(lines))+HELPER)
    return [{"ordinal":idx+1,"original_start_line":start+1,
             "original_last_line":end+1,
             "source_call":"".join(lines[start:end+1]).strip()}
            for idx,(start,end) in enumerate(anchors)]

def native_grid(path:Path):
    cells={}
    epochs=set()
    with path.open(newline="") as f:
        reader=csv.DictReader(f)
        required={"hour_end_utc_seconds","i","j",
                  "pre_fradj_temp_k","post_fradj_temp_k"}
        if set(reader.fieldnames or []) !=required:
            raise ValueError("G33A native two-pass grid layout changed")
        for row in reader:
            i,j=int(row["i"]),int(row["j"])
            if not(1<=i<=NX and 1<=j<=NY) or (i,j) in cells:
                raise ValueError("G33A bad native source grid cell")
            values=[float(row[x]) for x in
                    ("pre_fradj_temp_k","post_fradj_temp_k")]
            if not all(math.isfinite(x) for x in values):
                raise ValueError("G33A nonfinite native temperature")
            cells[i,j]=[struct.unpack("<f",struct.pack("<f",x))[0] for x in values]
            epochs.add(int(row["hour_end_utc_seconds"]))
    if len(cells)!=CELLS or len(epochs)!=1:
        raise ValueError("G33A native two-pass grid or hour incomplete")
    return cells,epochs.pop()

def original_grid(path:Path,expected_packed:int):
    raw=path.read_bytes()
    if len(raw)!=2*RECORD_BYTES:
        raise ValueError("G33A original SURFVAR requires exactly 2 write-only snapshots")
    grids=[]
    for phase in (0,1):
        begin=phase*RECORD_BYTES
        kpt,packed,seconds,nx,ny,reserved=struct.unpack_from(
            "<6i",raw,begin)
        if (kpt,packed,seconds,nx,ny,reserved)!=(
                phase+1,expected_packed,0,NX,NY,0):
            raise ValueError("G33A original surface snapshots not same first hour")
        grids.append(struct.unpack_from("<"+str(CELLS)+"f",raw,begin+24))
    return grids

def compare(original_temp,native_temp,phase):
    unequal=0;differences=[];first=None
    for j in range(1,NY+1):
        for i in range(1,NX+1):
            p=(j-1)*NX+i-1
            ref=original_temp[p];native=native_temp[i,j][phase]
            if not math.isfinite(ref):
                raise ValueError("G33A original emitted nonfinite TEMP2D")
            diff=abs(ref-native);differences.append(diff)
            if struct.pack("<f",ref)!=struct.pack("<f",native):
                unequal+=1
                if first is None:
                    first={"i":i,"j":j,"original_k":ref,"native_k":native,
                           "absolute_error_k":diff}
    return {"checkpoint":"post_FIRST_SURFVAR_before_FRADJ"
            if phase==0 else "post_SECOND_SURFVAR_after_FRADJ",
            "compared_cells":CELLS,"bit_mismatches":unequal,
            "max_abs_k":max(differences),
            "rms_k":math.sqrt(sum(x*x for x in differences)/CELLS),
            "first_bit_difference":first}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source-run-dir",required=True,type=Path)
    p.add_argument("--untouched-met",required=True,type=Path)
    p.add_argument("--frozen-verdict",required=True,type=Path)
    p.add_argument("--native-two-pass",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    p.add_argument("--compiler",default="gfortran")
    a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    report={"status":"BLOCKED","scientific_status":"FAIL_NUMERIC",
            "scope":"G33A full original 2SS/2US SURFVAR first/second pass diagnostic only"}
    try:
        verd=json.loads(a.frozen_verdict.read_text())
        if (verd.get("status")!="FAIL_NUMERIC"
                or verd.get("fields_per_hour")!=45
                or verd.get("intervals")!=1):
            raise ValueError("G33A requires same failing genuine 45-field vendor science")
        if sha(a.source_run_dir/"met.dat")!=sha(a.untouched_met):
            raise ValueError("G33A original G31 source run/untouched MET.DAT mismatch")
        native,end=native_grid(a.native_two_pass)
        clock=dt.datetime.fromtimestamp(end-3600,dt.timezone.utc)
        if clock!=dt.datetime(2024,1,1,2,tzinfo=dt.timezone.utc):
            raise ValueError("G33A original model clock not G19 frozen first hour")
        stamp=clock.year*100000+clock.timetuple().tm_yday*100+clock.hour
        vendor=Path(__file__).resolve().parents[4]/"engine/vendor/src/CALMET_v6.5.0_L150223"
        if sha(vendor/"calutils.for")!=original.ORIGINAL_CALUTILS_SHA256:
            raise ValueError("G33A original vendor calutils changed")
        instrumented=a.out/"calmet-surfvar-writeonly.for"
        sites=patch_vendor(vendor/"calmet.for",instrumented)
        alias=original._alias_tree(vendor,a.out/"include-alias")
        binary=a.out/"calmet-writeonly-surfvar.x"
        original._build(a.compiler,instrumented,alias,binary)
        staged=a.out/"instrumented-original"
        if staged.exists():shutil.rmtree(staged)
        shutil.copytree(a.source_run_dir,staged)
        run=original._run(binary,staged)
        if run["met_dat_sha256"]!=sha(a.untouched_met):
            raise ValueError("G33A instrumentation changed frozen untouched CALMET MET.DAT")
        dump=staged/"g33a_surfvar_two_pass.bin"
        if not dump.is_file():
            raise ValueError("G33A original source SURFVAR snapshots not written")
        original_temps=original_grid(dump,stamp)
        results=[compare(original_temps[k],native,k) for k in (0,1)]
        report.update({
            "status":"PASS_G33A_ORIGINAL_SURFVAR_STAGE_DIAGNOSIS_ONLY",
            "scientific_status":"FAIL_NUMERIC",
            "frozen_total_exceedances":verd["total_exceedances"],
            "original_vendor_sha256":sha(vendor/"calmet.for"),
            "untouched_original_met_sha256":sha(a.untouched_met),
            "original_instrumented_met_sha256":run["met_dat_sha256"],
            "original_surfvar_dump_sha256":sha(dump),
            "native_two_pass_sha256":sha(a.native_two_pass),
            "source_call_anchors":sites,
            "hour_start_utc":clock.isoformat(),
            "results":results,
            "first_original_vs_native_bit_difference_checkpoint":
                next((x["checkpoint"] for x in results if x["bit_mismatches"]),None),
            "next_if_both_exact":"inspect original HEATFX/SOLAR and ELUSTR inputs or ordering",
            "next_if_first_differs":"inspect source SURFVAR/AVETMP controls, selected raw temperature, wind input and REAL4 weighting",
            "next_if_only_second_differs":"inspect original second SURFVAR FRADJ wind and source AVETMP state reuse",
            "single_station_precedent":
                "single-site P6D original_internal_state_dump.py pinned write-only snapshots; source controls and time frozen",
        })
    except Exception as exc:
        report["blocker"]=str(exc)
        raise
    finally:
        (a.out/"g33a-two-pass-diagnosis.json").write_text(json.dumps(report,indent=2)+"\n")
        print(json.dumps(report,indent=2))

if __name__=="__main__":
    main()
