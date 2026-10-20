"""S2-B P2-A: immutable B-0 case -> existing original GLCC direct-LAEA + D3 LU.

Preserves the historical 24-to-38 map and 20x20 original-style sample grid.
Software staging/byte provenance only; genuine independent original GLAZAS
parity on a new region remains NOT_RUN. No P2-B area algorithm or Docker.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from .case_admission import admit_case, verify_immutable
from .plan import ContractError

GLCC_SHA256 = "4f2a1977d141e2040da4d36ec6a4826c5c960c84686eaf10f226f388cb3ab90a"
GLCC_SIZE_BYTES = 156_000_000
MESH = 20
METHOD_UTM50 = "GLCC_HEADERLESS_LAEA_DIRECT_UTM50N_REAL4_GLOBE_LUGRID"
METHOD_MULTI = "GLCC_HEADERLESS_LAEA_DIRECT_WGS84_UTM_REAL4_GLOBE_LUGRID"
RAW_NAME = "p2_glcc_usgs92_direct_laea.csv"
HITS_NAME = "p2_glcc_usgs92_hits.csv"


def digest(path: Path) -> str:
    if path.is_symlink() or not path.is_file() or path.stat().st_size <= 0:
        raise ContractError("P2-A source, producer or output missing/empty/symlink: " + str(path))
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _admit_output(root: Path) -> tuple[Path, Path]:
    out = root / "geo/ctgproc/p2a_case"
    evidence = root / "evidence/p2.json"
    for path in (out, evidence):
        if path.exists() or path.is_symlink():
            raise ContractError("P2-A fresh output/attestation path already used: " + str(path))
    for path in (root / "geo", root / "geo/ctgproc", root / "evidence"):
        if path.is_symlink():
            raise ContractError("P2-A output parent cannot be symlink")
    return out, evidence


def _run(command: list[str], root: Path, label: str) -> None:
    result = subprocess.run(command, cwd=root, text=True, capture_output=True, timeout=1200)
    if result.returncode:
        raise ContractError("P2-A " + label + " producer exit " + str(result.returncode)
                            + ": " + result.stderr[-1000:])


def produce(*, case_yaml: Path, glcc_img: Path,
            raw_bin: Path, lu_bin: Path) -> dict[str, object]:
    case = admit_case(case_yaml)
    root = case.case_path.parent
    # These bounds reflect the existing native P2-A + D3 writer. The S5 scale
    # effort must handle larger domains separately, not by weakening the gate.
    if case.nx > 20_000 or case.ny > 20_000 or case.nx * case.ny > 250_000:
        raise ContractError("P2-A current native 250000-cell grid budget exceeded")
    if not (0.001 <= case.dgridkm <= 100.
            and abs(case.dgridkm * 1000 - round(case.dgridkm * 1000)) < 1e-7):
        raise ContractError("P2-A spacing must represent whole metres in native D3")

    if glcc_img.stat().st_size != GLCC_SIZE_BYTES or digest(glcc_img) != GLCC_SHA256:
        raise ContractError("P2-A only official 156MB Eurasia GLCC original SHA admitted")
    raw_sha = digest(raw_bin)
    lu_sha = digest(lu_bin)
    out, evidence = _admit_output(root)
    epsg = case.utm_zone + (32600 if case.hemisphere == "N" else 32700)
    method = METHOD_UTM50 if epsg == 32650 else METHOD_MULTI
    raw_out, lu_out = out / "raw", out / "lu"
    raw_command = [
        str(raw_bin.resolve()), str(glcc_img.resolve()), str(raw_out), str(epsg),
        case.xrefkm_text, case.yrefkm_text,
        format(case.dgridkm, ".12g"), str(case.nx), str(case.ny), str(MESH),
        "--production-direct",
    ]
    verify_immutable(case)
    out.mkdir(parents=True)
    _run(raw_command, root, "original GLCC direct-LAEA")
    verify_immutable(case)
    raw_manifest_path = raw_out / "p2_manifest.json"
    raw_manifest = json.loads(raw_manifest_path.read_text(encoding="utf-8"))
    if (raw_manifest.get("producer") != "cteas_p2_glcc_raw" or
            raw_manifest.get("source_product") != "USGS_GLCC_EURASIA_1992_1993_ORIGINAL_1KM" or
            raw_manifest.get("source_sha256") != GLCC_SHA256 or
            raw_manifest.get("source_size_bytes") != GLCC_SIZE_BYTES or
            raw_manifest.get("method") != method or
            raw_manifest.get("utm_epsg") != epsg or
            raw_manifest.get("nx") != case.nx or
            raw_manifest.get("ny") != case.ny or
            raw_manifest.get("xrefkm") != case.xrefkm_text or
            raw_manifest.get("yrefkm") != case.yrefkm_text or
            raw_manifest.get("mesh") != MESH or
            raw_manifest.get("fractions_filename") != RAW_NAME or
            raw_manifest.get("evidence_status") != "PRODUCED_UNVERIFIED" or
            raw_manifest.get("official_GLAZAS_parity") != "NOT_RUN" or
            raw_manifest.get("lu_dat") != "NOT_RUN" or
            raw_manifest.get("p3_geo_dat") != "NOT_RUN"):
        raise ContractError("P2-A direct source manifest disagrees with B-0 authority")
    if abs(float(raw_manifest.get("dgridkm", -1)) - case.dgridkm) > 1e-9:
        raise ContractError("P2-A source manifest spacing differs from case")
    fractions = raw_out / RAW_NAME
    if (raw_manifest.get("fractions_csv_sha256") != digest(fractions)
            or raw_manifest.get("hits_csv_sha256") != digest(raw_out / HITS_NAME)):
        raise ContractError("P2-A original source fractions/HITS SHA mismatch")

    _run([str(lu_bin.resolve()), str(raw_manifest_path), str(fractions), str(lu_out)],
         root, "GLCC D3 LU.DAT")
    verify_immutable(case)
    d3_path = lu_out / "p2_d3_manifest.json"
    d3 = json.loads(d3_path.read_text(encoding="utf-8"))
    if (d3.get("producer") != "cteas_p2_glcc_lu_dat" or
            d3.get("source_kind") != "P2_A_GLCC_HISTORICAL_24_TO_USGS92_38" or
            d3.get("source_sha256") != GLCC_SHA256 or
            d3.get("input_d1_csv_sha256") != digest(fractions) or
            d3.get("input_d1_method") != method or
            d3.get("rows") != case.nx * case.ny or
            d3.get("classes") != 38 or
            d3.get("total_samples") != raw_manifest.get("included") or
            d3.get("evidence_status") != "PRODUCED_UNVERIFIED" or
            d3.get("original_GLAZAS_parity") != "NOT_RUN" or
            d3.get("p3_geo_dat") != "NOT_RUN"):
        raise ContractError("P2-A D3 LU manifest disagrees with admitted raw method/grid")
    lu_path = lu_out / "lu.dat"
    if d3.get("lu_dat_sha256") != digest(lu_path):
        raise ContractError("P2-A LU output SHA mismatch")
    attestation: dict[str, object] = {
        "schema": "cteas.s2b.p2a.case.produced_unverified.v1",
        "case_name": case.case_name,
        "case_yaml_sha256": case.case_sha256,
        "grid_cmn_sha256": case.grid_sha256,
        "research_time_sha256": case.time_sha256,
        "source_product": raw_manifest["source_product"],
        "source_img_sha256": GLCC_SHA256,
        "raw_executable_sha256": raw_sha,
        "lu_executable_sha256": lu_sha,
        "raw_manifest_sha256": digest(raw_manifest_path),
        "d3_manifest_sha256": digest(d3_path),
        "fractions_sha256": digest(fractions),
        "hits_sha256": digest(raw_out / HITS_NAME),
        "lu_dat_sha256": digest(lu_path),
        "method": method,
        "utm_epsg": epsg,
        "mesh": MESH,
        "nx": case.nx,
        "ny": case.ny,
        "xrefkm": case.xrefkm_text,
        "yrefkm": case.yrefkm_text,
        "dgridkm": case.dgridkm,
        "research_begin_utc": case.research_begin,
        "research_end_utc": case.research_end,
        "status": "P2A_GENERIC_CASE_PRODUCED_UNVERIFIED",
        "original_science": "NOT_RUN",
        "p3_makegeo": "OUT_OF_SCOPE_ISSUE46",
    }
    verify_immutable(case)
    evidence.parent.mkdir(parents=True, exist_ok=True)
    with evidence.open("x", encoding="utf-8") as stream:
        json.dump(attestation, stream, indent=2, sort_keys=True)
        stream.write("\n")
    verify_immutable(case)
    return attestation


def main() -> int:
    parser = argparse.ArgumentParser(description="S2-B P2-A source-authenticated case producer")
    parser.add_argument("--case-yaml", required=True, type=Path)
    parser.add_argument("--glcc-img", required=True, type=Path)
    parser.add_argument("--raw-bin", required=True, type=Path)
    parser.add_argument("--lu-bin", required=True, type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(produce(case_yaml=args.case_yaml, glcc_img=args.glcc_img,
                                 raw_bin=args.raw_bin, lu_bin=args.lu_bin), sort_keys=True))
        return 0
    except (ContractError, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"status": "P2A_GENERIC_BLOCKED", "reason": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
