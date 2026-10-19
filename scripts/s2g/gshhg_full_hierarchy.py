#!/usr/bin/env python3
"""Verify and restore GSHHG v2.3.7 FULL f L1-L4 without changing legacy L1.

Offline by design: requires the exact SHA-pinned official ZIP in the existing
GSHHG cache. No network, no High/Intermediate alternatives and no science.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from zipfile import ZipFile

from scripts.s2g import gshhg_v237_cache as base

LAYERS = tuple(range(1, 5))
MANIFEST = "verified_gshhs_full_l1_l4.json"
EXPECTED_L1_SHA = base.L1_SHA256
MAX_PART = 300 * 1024 * 1024


def members(z: ZipFile) -> dict[tuple[int, str], object]:
    """Refuse missing, duplicated, oversized or unexpected hierarchy members."""
    found = {}
    for level in LAYERS:
        for ext in base.EXTENSIONS:
            suffix = f"GSHHS_shp/f/GSHHS_f_L{level}{ext}"
            hits = [i for i in z.infolist() if i.filename.endswith(suffix)]
            if len(hits) != 1 or not 0 < hits[0].file_size < MAX_PART:
                raise ValueError(f"GSHHG_FULL_L{level}_BAD_MEMBER:{ext}")
            found[(level, ext)] = hits[0]
    return found


def archived_sha(z: ZipFile, member) -> str:
    digest = hashlib.sha256()
    with z.open(member) as inp:
        for buf in iter(lambda: inp.read(1 << 20), b""):
            digest.update(buf)
    return digest.hexdigest()


def unpack(cache: Path) -> dict:
    base.valid_zip(cache / base.NAME)
    # L1 retained from the previously accepted EXACT_AREA_V1 source/cache.
    base.verify(cache)
    with ZipFile(cache / base.NAME) as archive:
        entries = members(archive)
        manifest = {
            "status": "GSHHG_FULL_L1_L4_VERIFIED_BYTES_NOT_SCIENCE",
            "version": "2.3.7",
            "resolution": "f",
            "levels": [1, 2, 3, 4],
            "archive_sha256": base.SHA256,
            "official_source": base.OFFICIAL,
            "source_release": base.RELEASE,
            "science": "NOT_RUN",
            "sidecars": {},
        }
        for level in LAYERS:
            folder = cache / f"GSHHS_f_L{level}"
            folder.mkdir(parents=True, exist_ok=True)
            manifest["sidecars"][str(level)] = {}
            for ext in base.EXTENSIONS:
                dest = folder / f"GSHHS_f_L{level}{ext}"
                expected_sha = archived_sha(archive, entries[(level, ext)])
                if level == 1 and ext == ".shp" and expected_sha != EXPECTED_L1_SHA:
                    raise ValueError("FULL_L1_OFFICIAL_SHA_DRIFT")
                if dest.exists():
                    if dest.is_symlink() or not dest.is_file() or base.sha(dest) != expected_sha:
                        raise ValueError(f"GSHHG_FULL_EXISTING_FILE_DRIFT:L{level}{ext}")
                else:
                    with archive.open(entries[(level, ext)]) as src:
                        with tempfile.NamedTemporaryFile(dir=folder, delete=False) as temp:
                            temporary = Path(temp.name)
                            try:
                                for buf in iter(lambda: src.read(1 << 20), b""):
                                    temp.write(buf)
                                temp.flush()
                                if base.sha(temporary) != expected_sha:
                                    raise ValueError("GSHHG_FULL_UNPACK_SHA_DRIFT")
                                temporary.replace(dest)
                            finally:
                                temporary.unlink(missing_ok=True)
                manifest["sidecars"][str(level)][ext] = {
                    "sha256": expected_sha,
                    "size": entries[(level, ext)].file_size,
                }
    (cache / MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n")
    return verify(cache)


def verify(cache: Path) -> dict:
    base.verify(cache)
    base.valid_zip(cache / base.NAME)
    m = json.loads((cache / MANIFEST).read_text())
    if (m.get("archive_sha256") != base.SHA256 or
        m.get("resolution") != "f" or
        m.get("levels") != [1, 2, 3, 4] or
        m.get("status") != "GSHHG_FULL_L1_L4_VERIFIED_BYTES_NOT_SCIENCE"):
        raise ValueError("GSHHG_FULL_HIERARCHY_MANIFEST_DRIFT")
    with ZipFile(cache / base.NAME) as archive:
        entries = members(archive)
        for level in LAYERS:
            for ext in base.EXTENSIONS:
                part = cache / f"GSHHS_f_L{level}" / f"GSHHS_f_L{level}{ext}"
                expected = archived_sha(archive, entries[(level, ext)])
                record = m["sidecars"][str(level)][ext]
                if (part.is_symlink() or not part.is_file() or
                    part.stat().st_size != entries[(level, ext)].file_size or
                    record["size"] != entries[(level, ext)].file_size or
                    record["sha256"] != expected or base.sha(part) != expected):
                    raise ValueError(f"GSHHG_FULL_L{level}_SIDECAR_TAMPER:{ext}")
    return m


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("unpack", "verify"))
    parser.add_argument("--cache", type=Path, default=Path(".cache/gshhg/2.3.7"))
    args = parser.parse_args()
    try:
        result = unpack(args.cache) if args.mode == "unpack" else verify(args.cache)
        print(json.dumps({"status": result["status"], "archive_sha256": base.SHA256,
                          "resolution": "f", "layers": [1, 2, 3, 4],
                          "original_fortran_parity": "NOT_RUN"}, sort_keys=True))
        return 0
    except (OSError, KeyError, ValueError) as exc:
        print(f"GSHHG_FULL_HIERARCHY_FAIL_CLOSED:{type(exc).__name__}:{str(exc)[:110]}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
