#!/usr/bin/env python3
"""Authenticate the original GSHHS Full binary input for CTGPROC (#123 D5).

Official GSHHG v2.3.7 BINARY release (not the accepted shapefile ZIP).
Only source provenance: does not run COASTEXT, IPTYPE or CTGPROC.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
from urllib.request import urlopen
from zipfile import ZipFile, BadZipFile

ARCHIVE = "gshhg-bin-2.3.7.zip"
OFFICIAL = ("https://github.com/GenericMappingTools/gshhg-gmt/releases/"
            "download/2.3.7/" + ARCHIVE)
ZIP_SHA256 = "28600e8f7a08645aab43079326df6504212ec5ccb2b4bcf3b5f4f12ed60e82bc"
BINARY = "gshhs_f.b"
MANIFEST = "verified_original_gshhs_f_binary.json"
STATUS = "AUTHENTIC_GSHHS_FULL_BINARY_BYTES_VERIFIED_NOT_SCIENCE"
MAX_ARCHIVE_BYTES = 160 * 1024 * 1024
MAX_MEMBER_BYTES = 512 * 1024 * 1024


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def choose_full_member(archive: ZipFile):
    matches = [m for m in archive.infolist()
               if Path(m.filename).name == BINARY and not m.is_dir()]
    if len(matches) != 1:
        raise ValueError("GSHHS_FULL_BINARY_MEMBER_MISSING_OR_DUPLICATED")
    result = matches[0]
    if not 44 <= result.file_size <= MAX_MEMBER_BYTES:
        raise ValueError("GSHHS_FULL_BINARY_MEMBER_BAD_SIZE")
    return result


def inspect_header(first44: bytes) -> dict:
    """GSHHG 2.x: eleven big-endian int32 header words; original BREADH."""
    if len(first44) != 44:
        raise ValueError("GSHHS_BINARY_HEADER_TRUNCATED")
    polygon_id, npoints, signed_flag = struct.unpack(">11i", first44)[:3]
    flag = signed_flag & 0xFFFFFFFF
    level = flag & 0xFF
    version = (flag >> 8) & 0xFF
    if polygon_id < 0 or npoints < 3 or level not in (1, 2, 3, 4) or version < 10:
        raise ValueError("GSHHS_BINARY_HEADER_INCOMPATIBLE_WITH_BREADH_V2")
    return {"first_polygon_id": polygon_id, "first_polygon_points": npoints,
            "first_polygon_level": level, "packed_header_version": version,
            "header_bytes": 44}


def checked_zip(path: Path) -> None:
    if (path.is_symlink() or not path.is_file() or
            not 0 < path.stat().st_size <= MAX_ARCHIVE_BYTES or
            sha256(path) != ZIP_SHA256):
        raise ValueError("GSHHS_ORIGINAL_BINARY_ARCHIVE_SHA_OR_SIZE_DRIFT")


def fetch_archive(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        checked_zip(path)
        return
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temp = Path(stream.name)
        try:
            total = 0
            with urlopen(OFFICIAL, timeout=180) as response:
                while chunk := response.read(1 << 20):
                    total += len(chunk)
                    if total > MAX_ARCHIVE_BYTES:
                        raise ValueError("GSHHS_ORIGINAL_BINARY_ARCHIVE_OVERSIZE")
                    stream.write(chunk)
            stream.flush()
            checked_zip(temp)
            temp.replace(path)
        finally:
            temp.unlink(missing_ok=True)


def verify(cache: Path) -> dict:
    checked_zip(cache / ARCHIVE)
    target = cache / BINARY
    manifest_file = cache / MANIFEST
    if (target.is_symlink() or not target.is_file() or
            not manifest_file.is_file() or manifest_file.is_symlink()):
        raise ValueError("GSHHS_ORIGINAL_BINARY_CACHE_OR_MANIFEST_MISSING")
    record = json.loads(manifest_file.read_text())
    with ZipFile(cache / ARCHIVE) as z:
        member = choose_full_member(z)
        with z.open(member) as source:
            header = inspect_header(source.read(44))
        if (record.get("status") != STATUS or
                record.get("resolution") != "Full f" or
                record.get("archive_sha256") != ZIP_SHA256 or
                record.get("binary_member") != member.filename or
                record.get("binary_size") != member.file_size or
                record.get("first_header") != header or
                target.stat().st_size != member.file_size or
                sha256(target) != record.get("binary_sha256")):
            raise ValueError("GSHHS_ORIGINAL_BINARY_MANIFEST_OR_DATA_DRIFT")
        digest = hashlib.sha256()
        with z.open(member) as source:
            for block in iter(lambda: source.read(1 << 20), b""):
                digest.update(block)
        if digest.hexdigest() != record["binary_sha256"]:
            raise ValueError("GSHHS_ORIGINAL_BINARY_EXTRACTED_BYTES_DRIFT")
    return record


def unpack(cache: Path) -> dict:
    checked_zip(cache / ARCHIVE)
    cache.mkdir(parents=True, exist_ok=True)
    dest = cache / BINARY
    if dest.is_symlink():
        raise ValueError("GSHHS_ORIGINAL_BINARY_SYMLINK_REJECTED")
    with ZipFile(cache / ARCHIVE) as z:
        member = choose_full_member(z)
        with z.open(member) as src:
            header = inspect_header(src.read(44))
        digest = hashlib.sha256()
        if dest.exists():
            with z.open(member) as source:
                for chunk in iter(lambda: source.read(1 << 20), b""):
                    digest.update(chunk)
            if dest.stat().st_size != member.file_size or sha256(dest) != digest.hexdigest():
                raise ValueError("GSHHS_ORIGINAL_BINARY_EXISTING_BYTES_DRIFT")
        else:
            with z.open(member) as source, tempfile.NamedTemporaryFile(
                    dir=cache, delete=False) as sink:
                temp = Path(sink.name)
                try:
                    total = 0
                    while chunk := source.read(1 << 20):
                        total += len(chunk)
                        digest.update(chunk)
                        sink.write(chunk)
                    sink.flush()
                    if total != member.file_size:
                        raise ValueError("GSHHS_ORIGINAL_BINARY_MEMBER_SIZE_DRIFT")
                    temp.replace(dest)
                finally:
                    temp.unlink(missing_ok=True)
    record = {
        "status": STATUS, "version": "2.3.7", "resolution": "Full f",
        "official_release": OFFICIAL, "archive_sha256": ZIP_SHA256,
        "binary_member": member.filename, "binary_filename": BINARY,
        "binary_size": member.file_size, "binary_sha256": digest.hexdigest(),
        "first_header": header, "original_coastext_bln": "NOT_RUN",
        "original_iptype_parity": "NOT_RUN",
        "original_38class_hits_lu_parity": "NOT_RUN",
    }
    (cache / MANIFEST).write_text(json.dumps(record, indent=2) + "\n")
    return verify(cache)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("fetch", "unpack", "verify"))
    parser.add_argument("--cache", type=Path, default=Path(".cache/gshhg/bin-2.3.7"))
    args = parser.parse_args()
    try:
        if args.mode == "fetch":
            fetch_archive(args.cache / ARCHIVE)
        record = (unpack(args.cache) if args.mode != "verify" else verify(args.cache))
        print(json.dumps({"status": record["status"],
                          "binary_sha256": record["binary_sha256"],
                          "first_header": record["first_header"],
                          "original_coastext_bln": "NOT_RUN"}, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, BadZipFile) as exc:
        print(f"GSHHS_ORIGINAL_BINARY_FAIL_CLOSED:{type(exc).__name__}:{str(exc)[:160]}",
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
