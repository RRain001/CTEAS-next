#!/usr/bin/env python3
"""Issue #123 D6-B: run unmodified CTGPROC COASTEXT with Wolsong real inputs.

Source files and executable remain in ephemeral runner scratch, not artifacts.
This script prepares exact legal controls and audits the ORIGINAL coast.bln.
No C++ or original IPTYPE parity is claimed here.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import sys

from native_cpp.reference.validate_p2_glazas_original import _edit_card
from scripts.s2g import issue123_gshhg_binary_full as binary
from scripts.s2g.issue123_gfortran_split_io_adapter import STATUS as IO_STATUS
from scripts.s2g.issue123_gfortran_eof_adapter import STATUS as EOF_STATUS

SOURCE_SHA = "719abbd2327269bb0377208b3a7a0c74000b878efc756686023bbb2ef932f281"
GLCC_SHA = "4f2a1977d141e2040da4d36ec6a4826c5c960c84686eaf10f226f388cb3ab90a"
GLCC_BYTES = 156_000_000
# Original COASTEXT FORMAT(I7,',',I1,',"',I1,',',I1,',',I6,'"')
# emits leading spaces *inside the quotes* for the I6 polygon ID.
# COASTRD reads the quoted record list-directed and accepts that padding.
BLN_HEADER = re.compile(r'^\s*(\d+)\s*,\s*([01])\s*,\s*"([0-4])\s*,\s*([0-9]+)\s*,\s*(-?[0-9]+)\s*"\s*
VERTEX = re.compile(r'^\s*([-+]?\d+(?:\.\d+)?)\s*,\s*([-+]?\d+(?:\.\d+)?)\s*$')
GRID = {"epsg": 32652, "xrefkm": "533.215", "yrefkm": "3942.629",
        "nx": 200, "ny": 200, "dgridkm": "0.100", "meshglaz": 10}
MAX_BNL_BYTES = 64 * 1024 * 1024
MAX_VERTICES = 1_000_000
MAX_POLYGONS = 10_000


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for piece in iter(lambda: stream.read(1 << 20), b""):
            h.update(piece)
    return h.hexdigest()


def strict_file(path: Path, expected: str, size: int | None = None) -> None:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"D6B_SOURCE_MISSING_OR_SYMLINK:{path.name}")
    if size is not None and path.stat().st_size != size:
        raise ValueError(f"D6B_BAD_SOURCE_SIZE:{path.name}")
    if sha(path) != expected:
        raise ValueError(f"D6B_SOURCE_SHA_DRIFT:{path.name}")


def build_deck(template: str) -> str:
    if "\x00" in template:
        raise ValueError("D6B_BINARY_CONTROL")
    data_card = re.compile(r'(?m)^[ \t]*1[ \t]+!GLAZAS\s*=[^\r\n]*!END![ \t]*$')
    cards = list(data_card.finditer(template))
    if len(cards) != 1 or re.search(r'(?m)^[ \t]*1[ \t]+!GEN\s*=', template):
        raise ValueError("D6B_NOT_SINGLE_LEGAL_ORIGINAL_GLAZAS")
    m = cards[0]
    deck = template[:m.start()] + "1 !GLAZAS = glcc.img !    !END!" + template[m.end():]
    # Keep a single legal historic GLAZAS input; do NOT substitute GENERIC.
    replacements = (
        ("NDBF", "1"), ("LCFILES", "T"),
        ("GSHHSIN", "gshhs_f.b"), ("COASTBLN", "coast.bln"),
        ("LUDAT", "lu.dat"), ("RUNLST", "ctgproc.lst"),
        ("LFINAL", "F"), ("LPREV", "F"), ("LCOAST", "T"),
        ("LMARSWAP", "T"), ("LMARFILL", "F"), ("LBLNREAD", "F"),
        ("IOCEAN", "55"), ("MESHGLAZ", str(GRID["meshglaz"])),
        ("LQACELL", "F"), ("LSNOW", "F"), ("DUSGSLA", "ESR-S"),
        ("PMAP", "UTM"), ("IUTMZN", "52"), ("UTMHEM", "N"),
        ("DATUM", "WGS-84"),
        ("XREFKM", GRID["xrefkm"]), ("YREFKM", GRID["yrefkm"]),
        ("NX", "200"), ("NY", "200"), ("DGRIDKM", GRID["dgridkm"]),
    )
    for key, value in replacements:
        deck = _edit_card(deck, key, value)
    if (deck.count("1 !GLAZAS = glcc.img !") != 1 or
            "! LCOAST = T " not in deck or
            "! LBLNREAD = F " not in deck):
        raise ValueError("D6B_COASTEXT_NOT_REQUESTED")
    return deck


def prepare(template: Path, source: Path, glcc: Path,
            cache: Path, out: Path) -> dict:
    strict_file(source, SOURCE_SHA)
    strict_file(glcc, GLCC_SHA, GLCC_BYTES)
    manifest = binary.verify(cache)
    if out.is_symlink() or out.exists():
        raise ValueError("D6B_WORKDIR_COLLISION")
    deck = build_deck(template.read_text(encoding="utf-8"))
    out.mkdir(parents=True)
    try:
        # Original expects the following exact short local filenames.
        (out / "gshhs_f.b").symlink_to((cache / "gshhs_f.b").resolve())
        (out / "glcc.img").symlink_to(glcc.resolve())
        (out / "ctgproc.inp").write_text(deck, encoding="utf-8")
        result = {"status": "D6B_READY_TO_RUN_GNU_SPLIT_IO_ADAPTED_ORIGINAL",
                  "grid": GRID, "coast_processing": "ORIGINAL_COASTEXT",
                  "landuse_original_input": "GLAZAS", "control_sha256": sha(out / "ctgproc.inp"),
                  "original_source_sha256": SOURCE_SHA,
                  "original_glcc_sha256": GLCC_SHA,
                  "original_gshhs_full_sha256": manifest["binary_sha256"],
                  "original_coastext_bln": "NOT_RUN", "real_iptype_parity": "NOT_RUN",
                  "original_hits_lu_parity": "NOT_RUN"}
        (out / "input_provenance.json").write_text(json.dumps(result, indent=2) + "\n")
        return result
    except Exception:
        import shutil
        shutil.rmtree(out)
        raise


def parse_bln(path: Path) -> dict:
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size < MAX_BNL_BYTES:
        raise ValueError("D6B_ORIGINAL_BLN_MISSING_OR_OVERSIZE")
    n_polygons = n_vertices = 0
    classes = Counter()
    source_ids = Counter()
    summaries = []
    bounds = [math.inf, math.inf, -math.inf, -math.inf]
    with path.open(encoding="utf-8", errors="strict") as reader:
        while header := reader.readline():
            match = BLN_HEADER.fullmatch(header.rstrip("\n\r"))
            if not match:
                raise ValueError(f"D6B_ORIGINAL_BLN_BAD_HEADER:{n_polygons}")
            count, iside, typ, source, ident = map(int, match.groups())
            if (count < 3 or count > MAX_VERTICES - n_vertices or
                    n_polygons >= MAX_POLYGONS):
                raise ValueError("D6B_ORIGINAL_BLN_POLYGON_BUDGET")
            if iside != (1 if typ % 2 == 0 else 0):
                raise ValueError("D6B_ORIGINAL_BLN_BOUNDARY_FLAG")
            first = last = None
            poly_bounds = [math.inf, math.inf, -math.inf, -math.inf]
            for _ in range(count):
                row = reader.readline()
                p = VERTEX.fullmatch(row.rstrip("\n\r"))
                if p is None:
                    raise ValueError("D6B_ORIGINAL_BLN_TRUNCATED_OR_BAD_VERTEX")
                x, y = map(float, p.groups())
                if not math.isfinite(x) or not math.isfinite(y):
                    raise ValueError("D6B_ORIGINAL_BLN_NONFINITE")
                # Genuine COASTEXT clamps original UTM-km coordinates at
                # xllk/y llk +/- 0.0001; allow +0.01 km for print/roundoff.
                if not (533.205 <= x <= 553.225 and 3942.619 <= y <= 3962.639):
                    raise ValueError("D6B_ORIGINAL_BLN_WRONG_WOLSONG_DOMAIN")
                if first is None:
                    first = (x, y)
                last = (x, y)
                poly_bounds[0] = min(poly_bounds[0], x)
                poly_bounds[1] = min(poly_bounds[1], y)
                poly_bounds[2] = max(poly_bounds[2], x)
                poly_bounds[3] = max(poly_bounds[3], y)
            # Strict closure audit, not a rewritten or repaired BLN.
            if first != last:
                raise ValueError(f"D6B_ORIGINAL_BLN_UNCLOSED_POLYGON:{n_polygons}")
            n_vertices += count
            n_polygons += 1
            classes[str(typ)] += 1
            source_ids[str(source)] += 1
            for k in range(4):
                bounds[k] = (min(bounds[k], poly_bounds[k]) if k < 2
                             else max(bounds[k], poly_bounds[k]))
            if len(summaries) < 40:
                summaries.append({"polygon_index": n_polygons - 1, "type": typ,
                                  "source": source, "polygon_id": ident,
                                  "vertices": count, "iside": iside,
                                  "bbox_km": poly_bounds,
                                  "first_last_same": first == last})
    if n_polygons == 0 or n_vertices == 0:
        raise ValueError("D6B_ORIGINAL_BLN_EMPTY_FOR_COASTAL_WOLSONG")
    return {"original_bln_sha256": sha(path), "original_bln_size_bytes": path.stat().st_size,
            "polygons": n_polygons, "vertices": n_vertices,
            "classes": dict(classes), "sources": dict(source_ids),
            "bbox_km": bounds, "first_40_polygons": summaries}


def audit(out: Path, original_binary: Path) -> dict:
    if (out.is_symlink() or not out.is_dir() or
            not (out / "input_provenance.json").is_file()):
        raise ValueError("D6B_MISSING_INPUT_PROVENANCE")
    provenance = json.loads((out / "input_provenance.json").read_text())
    if (provenance.get("status") != "D6B_READY_TO_RUN_GNU_SPLIT_IO_ADAPTED_ORIGINAL" or
            provenance.get("control_sha256") != sha(out / "ctgproc.inp")):
        raise ValueError("D6B_CONTROL_PROVENANCE_DRIFT")
    adapter_file = out / "split_io_adapter_manifest.json"
    if adapter_file.is_symlink() or not adapter_file.is_file():
        raise ValueError("D6B_MISSING_GNU_SPLIT_IO_ADAPTER_AUDIT")
    adapter = json.loads(adapter_file.read_text())
    if (adapter.get("status") != IO_STATUS or
            adapter.get("original_ctgproc_sha256") != SOURCE_SHA or
            adapter.get("original_params_sha256") !=
                "28dc5877c6a70d74f7a0e136bdd4aa1777dc9cbab15c184e7f483f772cd266c6" or
            adapter.get("glcc_direct_access_preserved") is not True or
            adapter.get("gshhg_stream_only") is not True or
            adapter.get("glcc_access") != "direct-unformatted-recl-1" or
            adapter.get("gshhg_access") != "stream-unformatted-no-recl" or
            adapter.get("modified_original_gshhg_open_only") is not True or
            adapter.get("computational_physics_changes") is not False):
        raise ValueError("D6B_ORIGINAL_GNU_SPLIT_IO_ADAPTER_PROVENANCE_DRIFT")
    eof_file = out / "eof_adapter_manifest.json"
    if eof_file.is_symlink() or not eof_file.is_file():
        raise ValueError("D6B_MISSING_BREADH_EOF_ADAPTER_AUDIT")
    eof_adapter = json.loads(eof_file.read_text())
    if (eof_adapter.get("status") != EOF_STATUS or
            eof_adapter.get("original_ctgproc_sha256") != SOURCE_SHA or
            eof_adapter.get("patched_header_reads") != 8 or
            eof_adapter.get("computational_physics_changes") is not False):
        raise ValueError("D6B_BREADH_EOF_ADAPTER_PROVENANCE_DRIFT")
    result = parse_bln(out / "coast.bln")
    lst = out / "ctgproc.lst"
    if lst.is_symlink() or not lst.is_file() or lst.stat().st_size < 100:
        raise ValueError("D6B_ORIGINAL_CTGPROC_LST_MISSING")
    if original_binary.is_symlink() or not original_binary.is_file():
        raise ValueError("D6B_ORIGINAL_BINARY_MISSING")
    summary = {**provenance, **result,
               "gnu_split_io_adapter": adapter,
               "gnu_breadh_eof_adapter": eof_adapter,
               "status": "D6B_GNU_SPLIT_IO_EOF_ADAPTED_ORIGINAL_COASTEXT_GENERATED_BLN_SCOPED",
               "original_executable_sha256": sha(original_binary),
               "original_ctgproc_lst_sha256": sha(lst),
               "original_coastext_bln": "PASS_ORIGINAL_OUTPUT_PRESENT",
               "real_iptype_parity": "NOT_RUN",
               "original_hits_lu_parity": "NOT_RUN"}
    (out / "original_coastext_report.json").write_text(
        json.dumps(summary, indent=2) + "\n")
    return summary


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("prepare", "audit"))
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--template", type=Path)
    p.add_argument("--original-source", type=Path)
    p.add_argument("--glcc", type=Path)
    p.add_argument("--cache", type=Path)
    p.add_argument("--original-binary", type=Path)
    a = p.parse_args()
    try:
        if a.mode == "prepare":
            if any(v is None for v in (a.template, a.original_source, a.glcc, a.cache)):
                raise ValueError("D6B_MISSING_PREPARE_INPUT")
            result = prepare(a.template, a.original_source, a.glcc, a.cache, a.out)
        else:
            if a.original_binary is None:
                raise ValueError("D6B_MISSING_ORIGINAL_EXECUTABLE")
            result = audit(a.out, a.original_binary)
        print(json.dumps({k: result[k] for k in ("status", "original_coastext_bln")}))
    except (OSError, ValueError, KeyError) as exc:
        print(f"D6B_FAIL_CLOSED:{type(exc).__name__}:{str(exc)[:200]}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
)
VERTEX = re.compile(r'^\s*([-+]?\d+(?:\.\d+)?)\s*,\s*([-+]?\d+(?:\.\d+)?)\s*$')
GRID = {"epsg": 32652, "xrefkm": "533.215", "yrefkm": "3942.629",
        "nx": 200, "ny": 200, "dgridkm": "0.100", "meshglaz": 10}
MAX_BNL_BYTES = 64 * 1024 * 1024
MAX_VERTICES = 1_000_000
MAX_POLYGONS = 10_000


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for piece in iter(lambda: stream.read(1 << 20), b""):
            h.update(piece)
    return h.hexdigest()


def strict_file(path: Path, expected: str, size: int | None = None) -> None:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"D6B_SOURCE_MISSING_OR_SYMLINK:{path.name}")
    if size is not None and path.stat().st_size != size:
        raise ValueError(f"D6B_BAD_SOURCE_SIZE:{path.name}")
    if sha(path) != expected:
        raise ValueError(f"D6B_SOURCE_SHA_DRIFT:{path.name}")


def build_deck(template: str) -> str:
    if "\x00" in template:
        raise ValueError("D6B_BINARY_CONTROL")
    data_card = re.compile(r'(?m)^[ \t]*1[ \t]+!GLAZAS\s*=[^\r\n]*!END![ \t]*$')
    cards = list(data_card.finditer(template))
    if len(cards) != 1 or re.search(r'(?m)^[ \t]*1[ \t]+!GEN\s*=', template):
        raise ValueError("D6B_NOT_SINGLE_LEGAL_ORIGINAL_GLAZAS")
    m = cards[0]
    deck = template[:m.start()] + "1 !GLAZAS = glcc.img !    !END!" + template[m.end():]
    # Keep a single legal historic GLAZAS input; do NOT substitute GENERIC.
    replacements = (
        ("NDBF", "1"), ("LCFILES", "T"),
        ("GSHHSIN", "gshhs_f.b"), ("COASTBLN", "coast.bln"),
        ("LUDAT", "lu.dat"), ("RUNLST", "ctgproc.lst"),
        ("LFINAL", "F"), ("LPREV", "F"), ("LCOAST", "T"),
        ("LMARSWAP", "T"), ("LMARFILL", "F"), ("LBLNREAD", "F"),
        ("IOCEAN", "55"), ("MESHGLAZ", str(GRID["meshglaz"])),
        ("LQACELL", "F"), ("LSNOW", "F"), ("DUSGSLA", "ESR-S"),
        ("PMAP", "UTM"), ("IUTMZN", "52"), ("UTMHEM", "N"),
        ("DATUM", "WGS-84"),
        ("XREFKM", GRID["xrefkm"]), ("YREFKM", GRID["yrefkm"]),
        ("NX", "200"), ("NY", "200"), ("DGRIDKM", GRID["dgridkm"]),
    )
    for key, value in replacements:
        deck = _edit_card(deck, key, value)
    if (deck.count("1 !GLAZAS = glcc.img !") != 1 or
            "! LCOAST = T " not in deck or
            "! LBLNREAD = F " not in deck):
        raise ValueError("D6B_COASTEXT_NOT_REQUESTED")
    return deck


def prepare(template: Path, source: Path, glcc: Path,
            cache: Path, out: Path) -> dict:
    strict_file(source, SOURCE_SHA)
    strict_file(glcc, GLCC_SHA, GLCC_BYTES)
    manifest = binary.verify(cache)
    if out.is_symlink() or out.exists():
        raise ValueError("D6B_WORKDIR_COLLISION")
    deck = build_deck(template.read_text(encoding="utf-8"))
    out.mkdir(parents=True)
    try:
        # Original expects the following exact short local filenames.
        (out / "gshhs_f.b").symlink_to((cache / "gshhs_f.b").resolve())
        (out / "glcc.img").symlink_to(glcc.resolve())
        (out / "ctgproc.inp").write_text(deck, encoding="utf-8")
        result = {"status": "D6B_READY_TO_RUN_GNU_SPLIT_IO_ADAPTED_ORIGINAL",
                  "grid": GRID, "coast_processing": "ORIGINAL_COASTEXT",
                  "landuse_original_input": "GLAZAS", "control_sha256": sha(out / "ctgproc.inp"),
                  "original_source_sha256": SOURCE_SHA,
                  "original_glcc_sha256": GLCC_SHA,
                  "original_gshhs_full_sha256": manifest["binary_sha256"],
                  "original_coastext_bln": "NOT_RUN", "real_iptype_parity": "NOT_RUN",
                  "original_hits_lu_parity": "NOT_RUN"}
        (out / "input_provenance.json").write_text(json.dumps(result, indent=2) + "\n")
        return result
    except Exception:
        import shutil
        shutil.rmtree(out)
        raise


def parse_bln(path: Path) -> dict:
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size < MAX_BNL_BYTES:
        raise ValueError("D6B_ORIGINAL_BLN_MISSING_OR_OVERSIZE")
    n_polygons = n_vertices = 0
    classes = Counter()
    source_ids = Counter()
    summaries = []
    bounds = [math.inf, math.inf, -math.inf, -math.inf]
    with path.open(encoding="utf-8", errors="strict") as reader:
        while header := reader.readline():
            match = BLN_HEADER.fullmatch(header.rstrip("\n\r"))
            if not match:
                raise ValueError(f"D6B_ORIGINAL_BLN_BAD_HEADER:{n_polygons}")
            count, iside, typ, source, ident = map(int, match.groups())
            if (count < 3 or count > MAX_VERTICES - n_vertices or
                    n_polygons >= MAX_POLYGONS):
                raise ValueError("D6B_ORIGINAL_BLN_POLYGON_BUDGET")
            if iside != (1 if typ % 2 == 0 else 0):
                raise ValueError("D6B_ORIGINAL_BLN_BOUNDARY_FLAG")
            first = last = None
            poly_bounds = [math.inf, math.inf, -math.inf, -math.inf]
            for _ in range(count):
                row = reader.readline()
                p = VERTEX.fullmatch(row.rstrip("\n\r"))
                if p is None:
                    raise ValueError("D6B_ORIGINAL_BLN_TRUNCATED_OR_BAD_VERTEX")
                x, y = map(float, p.groups())
                if not math.isfinite(x) or not math.isfinite(y):
                    raise ValueError("D6B_ORIGINAL_BLN_NONFINITE")
                # Genuine COASTEXT clamps original UTM-km coordinates at
                # xllk/y llk +/- 0.0001; allow +0.01 km for print/roundoff.
                if not (533.205 <= x <= 553.225 and 3942.619 <= y <= 3962.639):
                    raise ValueError("D6B_ORIGINAL_BLN_WRONG_WOLSONG_DOMAIN")
                if first is None:
                    first = (x, y)
                last = (x, y)
                poly_bounds[0] = min(poly_bounds[0], x)
                poly_bounds[1] = min(poly_bounds[1], y)
                poly_bounds[2] = max(poly_bounds[2], x)
                poly_bounds[3] = max(poly_bounds[3], y)
            # Strict closure audit, not a rewritten or repaired BLN.
            if first != last:
                raise ValueError(f"D6B_ORIGINAL_BLN_UNCLOSED_POLYGON:{n_polygons}")
            n_vertices += count
            n_polygons += 1
            classes[str(typ)] += 1
            source_ids[str(source)] += 1
            for k in range(4):
                bounds[k] = (min(bounds[k], poly_bounds[k]) if k < 2
                             else max(bounds[k], poly_bounds[k]))
            if len(summaries) < 40:
                summaries.append({"polygon_index": n_polygons - 1, "type": typ,
                                  "source": source, "polygon_id": ident,
                                  "vertices": count, "iside": iside,
                                  "bbox_km": poly_bounds,
                                  "first_last_same": first == last})
    if n_polygons == 0 or n_vertices == 0:
        raise ValueError("D6B_ORIGINAL_BLN_EMPTY_FOR_COASTAL_WOLSONG")
    return {"original_bln_sha256": sha(path), "original_bln_size_bytes": path.stat().st_size,
            "polygons": n_polygons, "vertices": n_vertices,
            "classes": dict(classes), "sources": dict(source_ids),
            "bbox_km": bounds, "first_40_polygons": summaries}


def audit(out: Path, original_binary: Path) -> dict:
    if (out.is_symlink() or not out.is_dir() or
            not (out / "input_provenance.json").is_file()):
        raise ValueError("D6B_MISSING_INPUT_PROVENANCE")
    provenance = json.loads((out / "input_provenance.json").read_text())
    if (provenance.get("status") != "D6B_READY_TO_RUN_GNU_SPLIT_IO_ADAPTED_ORIGINAL" or
            provenance.get("control_sha256") != sha(out / "ctgproc.inp")):
        raise ValueError("D6B_CONTROL_PROVENANCE_DRIFT")
    adapter_file = out / "split_io_adapter_manifest.json"
    if adapter_file.is_symlink() or not adapter_file.is_file():
        raise ValueError("D6B_MISSING_GNU_SPLIT_IO_ADAPTER_AUDIT")
    adapter = json.loads(adapter_file.read_text())
    if (adapter.get("status") != IO_STATUS or
            adapter.get("original_ctgproc_sha256") != SOURCE_SHA or
            adapter.get("original_params_sha256") !=
                "28dc5877c6a70d74f7a0e136bdd4aa1777dc9cbab15c184e7f483f772cd266c6" or
            adapter.get("glcc_direct_access_preserved") is not True or
            adapter.get("gshhg_stream_only") is not True or
            adapter.get("glcc_access") != "direct-unformatted-recl-1" or
            adapter.get("gshhg_access") != "stream-unformatted-no-recl" or
            adapter.get("modified_original_gshhg_open_only") is not True or
            adapter.get("computational_physics_changes") is not False):
        raise ValueError("D6B_ORIGINAL_GNU_SPLIT_IO_ADAPTER_PROVENANCE_DRIFT")
    eof_file = out / "eof_adapter_manifest.json"
    if eof_file.is_symlink() or not eof_file.is_file():
        raise ValueError("D6B_MISSING_BREADH_EOF_ADAPTER_AUDIT")
    eof_adapter = json.loads(eof_file.read_text())
    if (eof_adapter.get("status") != EOF_STATUS or
            eof_adapter.get("original_ctgproc_sha256") != SOURCE_SHA or
            eof_adapter.get("patched_header_reads") != 8 or
            eof_adapter.get("computational_physics_changes") is not False):
        raise ValueError("D6B_BREADH_EOF_ADAPTER_PROVENANCE_DRIFT")
    result = parse_bln(out / "coast.bln")
    lst = out / "ctgproc.lst"
    if lst.is_symlink() or not lst.is_file() or lst.stat().st_size < 100:
        raise ValueError("D6B_ORIGINAL_CTGPROC_LST_MISSING")
    if original_binary.is_symlink() or not original_binary.is_file():
        raise ValueError("D6B_ORIGINAL_BINARY_MISSING")
    summary = {**provenance, **result,
               "gnu_split_io_adapter": adapter,
               "gnu_breadh_eof_adapter": eof_adapter,
               "status": "D6B_GNU_SPLIT_IO_EOF_ADAPTED_ORIGINAL_COASTEXT_GENERATED_BLN_SCOPED",
               "original_executable_sha256": sha(original_binary),
               "original_ctgproc_lst_sha256": sha(lst),
               "original_coastext_bln": "PASS_ORIGINAL_OUTPUT_PRESENT",
               "real_iptype_parity": "NOT_RUN",
               "original_hits_lu_parity": "NOT_RUN"}
    (out / "original_coastext_report.json").write_text(
        json.dumps(summary, indent=2) + "\n")
    return summary


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("prepare", "audit"))
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--template", type=Path)
    p.add_argument("--original-source", type=Path)
    p.add_argument("--glcc", type=Path)
    p.add_argument("--cache", type=Path)
    p.add_argument("--original-binary", type=Path)
    a = p.parse_args()
    try:
        if a.mode == "prepare":
            if any(v is None for v in (a.template, a.original_source, a.glcc, a.cache)):
                raise ValueError("D6B_MISSING_PREPARE_INPUT")
            result = prepare(a.template, a.original_source, a.glcc, a.cache, a.out)
        else:
            if a.original_binary is None:
                raise ValueError("D6B_MISSING_ORIGINAL_EXECUTABLE")
            result = audit(a.out, a.original_binary)
        print(json.dumps({k: result[k] for k in ("status", "original_coastext_bln")}))
    except (OSError, ValueError, KeyError) as exc:
        print(f"D6B_FAIL_CLOSED:{type(exc).__name__}:{str(exc)[:200]}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
