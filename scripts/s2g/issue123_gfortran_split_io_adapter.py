#!/usr/bin/env python3
"""#123 D6-B3: audited, scratch-only split I/O for original CTGPROC.

The original shared params.ctg caccess=DIRECT, RECL=1 is required by the
GLCC GLAZAS Read(IOINP,REC=...) random access. Only GSHHG BREADH/BREADP
needs sequential unformatted STREAM. Patch exactly the COASTEXT GSHHS
OPEN on the already EOF-adapted scratch Fortran file; retain the original
params.ctg DIRECT settings byte-for-byte. Never call the derivative an
unmodified original Fortran source or imply mathematical parity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ORIGINAL_SOURCE_SHA = "719abbd2327269bb0377208b3a7a0c74000b878efc756686023bbb2ef932f281"
ORIGINAL_PARAMS_SHA = "28dc5877c6a70d74f7a0e136bdd4aa1777dc9cbab15c184e7f483f772cd266c6"
AFTER_EOF_SHA = "f7044e89f32cf0ebf00f29b4c95786ea5f52beefdcdcabdfbf56b6976281cb2d"
STATUS = "D6B_GSHHG_ONLY_STREAM_GLCC_DIRECT_PRESERVED"
OLD_OPEN = ("      open(unit=iogshhs,file=gshhsin,access=caccess,form=cform,\n"
            "     &  status='OLD',recl=irecl,iostat=ierr)")
NEW_OPEN = ("      open(unit=iogshhs,file=gshhsin,access='stream',form=cform,\n"
            "     &  status='OLD',iostat=ierr)")
DIRECT_PARAM = "      parameter(cform='unformatted', caccess='direct', irecl=1)"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check_params(original: bytes, staged: bytes) -> None:
    if digest(original) != ORIGINAL_PARAMS_SHA or staged != original:
        raise ValueError("D6B3_ORIGINAL_GLCC_DIRECT_PARAMS_SHA_OR_COPY_DRIFT")
    t = original.decode("latin-1")
    active = [line for line in t.splitlines()
              if "parameter(" in line.lower() and "caccess=" in line.lower()
              and line[:1].lower() not in ("c", "*", "!")]
    if active != [DIRECT_PARAM]:
        raise ValueError("D6B3_SHARED_IO_MUST_REMAIN_DIRECT")


def patch(original: bytes, staged_after_eof: bytes) -> tuple[bytes, dict]:
    if digest(original) != ORIGINAL_SOURCE_SHA:
        raise ValueError("D6B3_ORIGINAL_CTGPROC_SHA_DRIFT")
    if digest(staged_after_eof) != AFTER_EOF_SHA:
        raise ValueError("D6B3_PRIOR_EOF_ADAPTER_SHA_DRIFT")
    s = staged_after_eof.decode("latin-1")
    a = s.lower().find("      subroutine coastext")
    b = s.lower().find("      subroutine breadh", a)
    if a < 0 or b <= a:
        raise ValueError("D6B3_COASTEXT_BOUNDARY_DRIFT")
    if s.count(OLD_OPEN) != 1 or s[a:b].count(OLD_OPEN) != 1:
        raise ValueError("D6B3_GSHHG_OPEN_COUNT_DRIFT")
    if "read(ioinp,rec=kcnt)kbuf" not in s.lower():
        raise ValueError("D6B3_ORIGINAL_GLCC_RANDOM_READ_DRIFT")
    changed = s.replace(OLD_OPEN, NEW_OPEN).encode("latin-1")
    if changed == staged_after_eof or changed.count(NEW_OPEN.encode("latin-1")) != 1:
        raise ValueError("D6B3_GSHHG_ONLY_PATCH_NOT_APPLIED")
    return changed, {
        "status": STATUS,
        "original_ctgproc_sha256": ORIGINAL_SOURCE_SHA,
        "original_params_sha256": ORIGINAL_PARAMS_SHA,
        "before_gshhg_only_open_sha256": AFTER_EOF_SHA,
        "staged_ctgproc_sha256": digest(changed),
        "modified_original_subroutine_only": "COASTEXT",
        "modified_original_gshhg_open_only": True,
        "gshhg_access": "stream-unformatted-no-recl",
        "glcc_access": "direct-unformatted-recl-1",
        "glcc_direct_access_preserved": True,
        "gshhg_stream_only": True,
        "original_ctgproc_body_modified_for_io": True,
        "computational_physics_changes": False,
        "original_source_checkout_modified": False,
        "source_inputs_modified": False,
        "original_coastext_bln": "NOT_RUN",
        "original_iptype_parity": "NOT_RUN",
        "original_hits_lu_parity": "NOT_RUN",
    }


def prepare(original_source: Path, original_params: Path,
            staged_source: Path, staged_params: Path, manifest: Path) -> dict:
    for name, p in (("original_source", original_source),
                    ("original_params", original_params),
                    ("staged_source", staged_source),
                    ("staged_params", staged_params)):
        if p.is_symlink() or not p.is_file():
            raise ValueError(f"D6B3_REQUIRED_FILE_MISSING_OR_SYMLINK:{name}")
    if manifest.exists() or manifest.is_symlink():
        raise ValueError("D6B3_MANIFEST_MUST_BE_NEW")
    check_params(original_params.read_bytes(), staged_params.read_bytes())
    adapted, record = patch(original_source.read_bytes(), staged_source.read_bytes())
    staged_source.write_bytes(adapted)
    manifest.write_text(json.dumps(record, sort_keys=True, indent=2) + "\n")
    return record


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--original-source", type=Path, required=True)
    ap.add_argument("--original-params", type=Path, required=True)
    ap.add_argument("--staged-source", type=Path, required=True)
    ap.add_argument("--staged-params", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    ns = ap.parse_args()
    result = prepare(ns.original_source, ns.original_params,
                     ns.staged_source, ns.staged_params, ns.manifest)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
