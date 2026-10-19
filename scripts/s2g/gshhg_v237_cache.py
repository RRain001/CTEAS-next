#!/usr/bin/env python3
"""Restore source-pinned GSHHG v2.3.7 Full L1 from a project release or upstream.

Only the explicit fetch mode uses the network; modelling must use verified local data.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
from urllib.request import urlopen
from zipfile import ZipFile, BadZipFile

NAME = "gshhg-shp-2.3.7.zip"
SHA256 = "8dbbe7e071e77e9e75f2d639239099ebca8d5c16d6a07df8169729d49f15cf41"
L1_SHA256 = "121435427911ea80624802e0f352d777eaf6ba6966ca5f07e687650e95329fd9"
RELEASE = "https://github.com/RRain001/CTEAS-next/releases/download/gshhg-data-v2.3.7/" + NAME
OFFICIAL = "https://github.com/GenericMappingTools/gshhg-gmt/releases/download/2.3.7/" + NAME
EXTENSIONS = (".shp", ".shx", ".dbf", ".prj")
MAX_ARCHIVE = 250 * 1024 * 1024
MAX_MEMBER = 300 * 1024 * 1024

def sha(path: Path) -> str:
    d = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1 << 20):
            d.update(chunk)
    return d.hexdigest()

def valid_zip(path: Path) -> None:
    if not path.is_file() or not (0 < path.stat().st_size <= MAX_ARCHIVE):
        raise ValueError("GSHHG_ARCHIVE_MISSING_OR_OVERSIZE")
    if sha(path) != SHA256:
        raise ValueError("GSHHG_ARCHIVE_SHA256_MISMATCH")

def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=dest.parent, suffix=".partial", delete=False) as out:
        temp=Path(out.name)
        try:
            with urlopen(url,timeout=180) as stream:
                total=0
                while chunk:=stream.read(1<<20):
                    total+=len(chunk)
                    if total>MAX_ARCHIVE:
                        raise ValueError("GSHHG_ARCHIVE_OVERSIZE")
                    out.write(chunk)
            out.flush()
            valid_zip(temp)
            temp.replace(dest)
        finally:
            if temp.exists():
                temp.unlink()

def unpack(cache: Path) -> dict:
    valid_zip(cache/NAME)
    coast=cache/"GSHHS_f_L1"
    coast.mkdir(parents=True,exist_ok=True)
    with ZipFile(cache/NAME) as z:
        entries={}
        for ext in EXTENSIONS:
            suffix="GSHHS_shp/f/GSHHS_f_L1"+ext
            candidates=[m for m in z.infolist() if m.filename.endswith(suffix)]
            if len(candidates)!=1 or not (0<candidates[0].file_size<MAX_MEMBER):
                raise ValueError("GSHHG_L1_MISSING_OR_BAD_MEMBER:"+ext)
            entries[ext]=candidates[0]
        for ext,info in entries.items():
            dest=coast/("GSHHS_f_L1"+ext)
            with z.open(info) as source, tempfile.NamedTemporaryFile(dir=coast,delete=False) as sink:
                temp=Path(sink.name)
                try:
                    shutil.copyfileobj(source,sink)
                    sink.flush()
                    temp.replace(dest)
                finally:
                    if temp.exists():
                        temp.unlink()
    if sha(coast/"GSHHS_f_L1.shp")!=L1_SHA256:
        raise ValueError("GSHHG_SHAPEFILE_SHA256_MISMATCH")
    manifest={
      "status":"VERIFIED_FULL_GSHHS_L1_ORIGINAL_BYTES",
      "version":"2.3.7",
      "source_zip_sha256":SHA256,
      "gshhs_l1_shp_sha256":L1_SHA256,
      "sidecars":{ext:{"sha256":sha(coast/("GSHHS_f_L1"+ext)),
                          "size":(coast/("GSHHS_f_L1"+ext)).stat().st_size} for ext in EXTENSIONS},
      "official_source":OFFICIAL,
      "project_release":RELEASE,
      "license":"GSHHG LGPL-3.0-or-later; see LICENSE.TXT bundled with upstream ZIP",
      "science_acceptance":"NOT_RUN",
    }
    (cache/"verified_gshhs_full_l1.json").write_text(json.dumps(manifest,indent=2)+"\n")
    return manifest

def verify(cache: Path) -> dict:
    valid_zip(cache/NAME)
    manifest=json.loads((cache/"verified_gshhs_full_l1.json").read_text())
    if manifest.get("source_zip_sha256")!=SHA256 or manifest.get("gshhs_l1_shp_sha256")!=L1_SHA256:
        raise ValueError("GSHHG_CACHE_PIN_DRIFT")
    coast=cache/"GSHHS_f_L1"
    for ext in EXTENSIONS:
        p=coast/("GSHHS_f_L1"+ext)
        expect=manifest["sidecars"][ext]
        if not p.is_file() or p.stat().st_size!=expect["size"] or sha(p)!=expect["sha256"]:
            raise ValueError("GSHHG_SIDECAR_TAMPER:"+ext)
    return manifest

def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode",choices=("fetch","verify"))
    parser.add_argument("--cache",type=Path,default=Path(".cache/gshhg/2.3.7"))
    parser.add_argument("--source",choices=("project-release","official"),default="project-release")
    args=parser.parse_args()
    try:
        cache=args.cache.resolve()
        if args.mode=="fetch":
            archive=cache/NAME
            if archive.exists():valid_zip(archive)
            else:download(RELEASE if args.source=="project-release" else OFFICIAL,archive)
            unpack(cache)
        manifest=verify(cache)
        print(json.dumps({"status":manifest["status"],
            "shapefile":str(cache/"GSHHS_f_L1/GSHHS_f_L1.shp"),
            "sha256":manifest["source_zip_sha256"],
            "science_acceptance":"NOT_RUN"},sort_keys=True))
        return 0
    except (OSError, KeyError, ValueError, BadZipFile) as exc:
        print("GSHHG_CACHE_FAIL_CLOSED:"+type(exc).__name__+":"+str(exc)[:100],file=sys.stderr)
        return 1
if __name__=="__main__":
    raise SystemExit(main())
