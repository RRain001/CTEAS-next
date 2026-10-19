#!/usr/bin/env python3
"""GNU STREAM raw-input EOF adapter for pinned original CTGPROC BREADH.

Modern GNU STREAM reads signal file exhaustion as END, not ERR. The
original BREADH uses ERR=99 to detect the expected EOF; with STREAM,
this aborts after scanning all polygons. Only eight BREADH READ I/O
specifier tokens are patched in a SHA-pinned temporary compiler copy.
No original computational algorithm or source checkout is modified.
Derivative must NEVER be called fully unmodified vendor source.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

SOURCE_SHA = "719abbd2327269bb0377208b3a7a0c74000b878efc756686023bbb2ef932f281"
STATUS = "D6B_PINNED_ORIGINAL_GFORTRAN_STREAM_AND_EOF_IO_ADAPTED"
OLD = "read(iogshhs,err=99)"
NEW = "read(iogshhs,end=99)"
EXPECTED = 8


def digest(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def patch(source: bytes) -> tuple[bytes, dict]:
    if digest(source) != SOURCE_SHA:
        raise ValueError("D6B_ORIGINAL_SOURCE_SHA_DRIFT")
    text = source.decode("latin-1")
    low = text.lower()
    a, b = low.find("      subroutine breadh("), low.find("      subroutine breadp(")
    if a < 0 or b <= a:
        raise ValueError("D6B_ORIGINAL_BREADH_BREADP_BOUNDARY_DRIFT")
    original = text[a:b]
    found = re.findall(re.escape(OLD), original, flags=re.I)
    if len(found) != EXPECTED:
        raise ValueError("D6B_ORIGINAL_BREADH_EOF_READ_COUNT_DRIFT")
    # Exact replacement in BREADH only, no changes to other subroutines;
    # old and new have identical line lengths for F77 column discipline.
    adapted = re.sub(re.escape(OLD), NEW, original, flags=re.I)
    replacement = text[:a] + adapted + text[b:]
    if len(replacement) != len(text) or text[:a] != replacement[:a] or text[b:] != replacement[b:]:
        raise ValueError("D6B_NON_IO_FORTRAN_CODE_CHANGED")
    changed = replacement.encode("latin-1")
    return changed, {
        "status": STATUS, "original_ctgproc_sha256": SOURCE_SHA,
        "staged_ctgproc_sha256": digest(changed),
        "modified_subroutine_only": "BREADH",
        "modified_token_only": "ERR=99 -> END=99 on 8 GSHHS header READ statements",
        "patched_header_reads": EXPECTED,
        "fortran_body_bytes_changed": True,
        "computational_physics_changes": False,
        "original_source_checkout_modified": False,
        "original_coastext_bln": "NOT_RUN",
        "independent_cpp_parity": "NOT_RUN",
    }


def prepare(original: Path, staged: Path, report: Path) -> dict:
    if (original.is_symlink() or staged.is_symlink() or
            not original.is_file() or not staged.is_file() or report.exists()):
        raise ValueError("D6B_EOF_ADAPTER_BAD_PATHS")
    blob = original.read_bytes()
    if staged.read_bytes() != blob:
        raise ValueError("D6B_STAGED_FORTRAN_NOT_BYTE_IDENTICAL_BEFORE_EOF_ADAPTER")
    derivative, manifest = patch(blob)
    staged.write_bytes(derivative)
    report.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original-source", type=Path, required=True)
    p.add_argument("--staged-source", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    args = p.parse_args()
    result = prepare(args.original_source, args.staged_source, args.manifest)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
