#!/usr/bin/env python3
"""#123 D6-B: pinned GNU Fortran I/O adapter for original CTGPROC.

Original CTGPROC's GNU F77 params.ctg uses unformatted DIRECT with
RECL=1, but BREADH/BREADP perform sequential no-REC READs on a raw
GSHHS byte stream. GNU direct-record reads fail at the first header.
This adjusts ONLY a scratch params.ctg record-access parameter:
DIRECT -> STREAM. All original computational Fortran .for bytes,
control, GSHHS, and GLCC files remain untouched.

Status is always GFORTRAN_STREAM_IO_ADAPTED, never UNMODIFIED_ALL_SOURCES.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

ORIGINAL_CTGPROC_SHA = "719abbd2327269bb0377208b3a7a0c74000b878efc756686023bbb2ef932f281"
ACTUAL = "      parameter(cform='unformatted', caccess='direct', irecl=1)"
REPLACE = "      parameter(cform='unformatted', caccess='stream', irecl=1)"
STATUS = "GFORTRAN_STREAM_IO_ADAPTED_ORIGINAL_ALGORITHMS_UNMODIFIED"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def patch(content: str) -> str:
    active = [
        line for line in content.splitlines()
        if "parameter(" in line.lower() and "caccess=" in line.lower()
        and (line[:1].lower() not in ("c", "*", "!"))
    ]
    if active != [ACTUAL]:
        raise ValueError("D6B_PARAMS_ACTIVE_GFORTRAN_IO_MODE_DRIFT")
    if content.count(ACTUAL) != 1:
        raise ValueError("D6B_PARAMS_EXPECTED_UNIQUE_DIRECT_MODE")
    staged = content.replace(ACTUAL, REPLACE)
    if staged == content or staged.count(REPLACE) != 1:
        raise ValueError("D6B_STREAM_ADAPTER_NOT_APPLIED")
    return staged


def prepare(original_params: Path, original_source: Path,
            target: Path, manifest: Path) -> dict:
    for path in (original_params, original_source):
        if path.is_symlink() or not path.is_file():
            raise ValueError("D6B_ORIGINAL_SOURCE_MISSING_OR_SYMLINK")
    if target.exists() or target.is_symlink() or manifest.exists():
        raise ValueError("D6B_ADAPTER_OUTPUT_MUST_BE_NEW")
    raw_source = original_source.read_bytes()
    if sha(raw_source) != ORIGINAL_CTGPROC_SHA:
        raise ValueError("D6B_ORIGINAL_CTGPROC_SHA_DRIFT")
    raw_params = original_params.read_bytes()
    adapted = patch(raw_params.decode("ascii")).encode("ascii")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(adapted)
    result = {
        "status": STATUS,
        "original_ctgproc_sha256": ORIGINAL_CTGPROC_SHA,
        "original_params_sha256": sha(raw_params),
        "gnu_stream_params_sha256": sha(adapted),
        "changed_include": "params.ctg",
        "changed_parameter_only": "caccess=direct -> caccess=stream",
        "original_ctgproc_fortran_body_changed": False,
        "original_gshhs_binary_changed": False,
        "original_glcc_landuse_changed": False,
        "original_fortran_compiler": "gfortran -std=legacy",
        "physics_parity": "NOT_YET_PROVEN",
        "original_coastext_bln": "NOT_RUN",
        "original_iptype_parity": "NOT_RUN",
        "original_hits_lu_parity": "NOT_RUN",
    }
    manifest.write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original-params", type=Path, required=True)
    p.add_argument("--original-source", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    args = p.parse_args()
    result = prepare(args.original_params, args.original_source,
                     args.out, args.manifest)
    print(json.dumps({"status": result["status"],
                      "original_params_sha256": result["original_params_sha256"],
                      "gnu_stream_params_sha256": result["gnu_stream_params_sha256"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
