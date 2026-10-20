"""#46 D1-C: same immutable B-0 case P1 native terrain + retained P2 LU -> P3.

Real native binaries only; scientific statuses remain PRODUCED_UNVERIFIED until
independent authentic DEM/GLC/GLCC and original MAKEGEO comparison (#46 D2/D3).
P2-B is retired; no alt physics, no terrain filler, no Docker.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

from .case_admission import admit_case, verify_immutable
from .plan import ContractError

ROOT = Path(__file__).resolve().parents[2]
APPROVED_TEMPLATE = ROOT / "project/cases/hefei5km_2022_reference_case_20261011/geo/makegeo/makegeo.inp"
OPTIONS = ("IUTMZN", "UTMHEM", "XREFKM", "YREFKM", "NX", "NY", "DGRIDKM")
P2_STATUS = {"A": "P2A_GENERIC_CASE_PRODUCED_UNVERIFIED",
             "C": "P2C_GENERIC_CASE_PRODUCED_UNVERIFIED"}
P2_METHODS = {
    "A": ("GLCC_HEADERLESS_LAEA_DIRECT_UTM50N_REAL4_GLOBE_LUGRID",
          "GLCC_HEADERLESS_LAEA_DIRECT_WGS84_UTM_REAL4_GLOBE_LUGRID"),
    "C": ("P2_C_GLC30M_SOURCE_SUBPOINT_GLAZAS_LUGRID_R4_HITS_V1",),
}


def sha(path: Path) -> str:
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size < 2_000_000_000:
        raise ContractError("P3 required file missing, empty, too large or symlinked: " + str(path))
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1 << 20), b""):
            h.update(part)
    return h.hexdigest()


def _run(parts: list[str], cwd: Path, kind: str) -> None:
    try:
        p = subprocess.run(parts, cwd=cwd, capture_output=True, text=True, timeout=1200)
    except subprocess.TimeoutExpired as exc:
        raise ContractError("P3 " + kind + " native timeout") from exc
    if p.returncode:
        raise ContractError("P3 " + kind + " returned " + str(p.returncode) + ": " +
                            p.stderr[-1000:])


def make_control(template: str, case) -> str:
    """Replace *only* B-0 geographic controls in selected original template."""
    options = {
        "IUTMZN": str(case.utm_zone),
        "UTMHEM": case.hemisphere,
        "XREFKM": case.xrefkm_text,
        "YREFKM": case.yrefkm_text,
        "NX": str(case.nx),
        "NY": str(case.ny),
        "DGRIDKM": f"{case.dgridkm:.3f}",
    }
    for key in OPTIONS:
        pattern = rf"(!\s*{key}\s*=\s*)([^!]*)(!)"
        template, count = re.subn(
            pattern, lambda m: m.group(1) + options[key] + " " + m.group(3),
            template)
        if count != 1:
            raise ContractError("P3 template missing/duplicate geographic key: " + key)
    return template


def produce(*, case_yaml: Path, p1_tif: Path, p1_tif_sha256: str,
            p1_bin: Path, dat_bin: Path, p3_bin: Path,
            p2_kind: str, template_path: Path = APPROVED_TEMPLATE) -> dict:
    case = admit_case(case_yaml)
    root = case.case_path.parent
    if case.nx > 500 or case.ny > 500 or case.nx*case.ny > 250_000:
        raise ContractError("P3 current MAKEGEO 500x500 resource boundary")
    if p2_kind not in P2_STATUS:
        raise ContractError("P3 only admits P2-A historic GLCC or P2-C 30m point method")
    if not re.fullmatch("[0-9a-f]{64}", p1_tif_sha256) or sha(p1_tif) != p1_tif_sha256:
        raise ContractError("P3 native P1 source GeoTIFF SHA mismatch")
    native_shas = {"p1_bin_sha256": sha(p1_bin),
                   "dat_bin_sha256": sha(dat_bin),
                   "p3_bin_sha256": sha(p3_bin)}
    if template_path.resolve() != APPROVED_TEMPLATE.resolve():
        raise ContractError("P3 only selected original Hefei 38-to-14 option template supported")
    template_sha = sha(template_path)
    template = template_path.read_text(encoding="utf-8")

    p2_dir = root / ("geo/ctgproc/p2a_case/lu" if p2_kind == "A"
                     else "geo/ctgproc/p2c_case")
    p2_lu = p2_dir / "lu.dat"
    p2_proof_path = root / "evidence/p2.json"
    p2_lu_sha = sha(p2_lu)
    p2_proof = json.loads(p2_proof_path.read_text(encoding="utf-8"))
    expected_epsg = case.utm_zone + (32600 if case.hemisphere == "N" else 32700)
    if (p2_proof.get("status") != P2_STATUS[p2_kind] or
            p2_proof.get("method") not in P2_METHODS[p2_kind] or
            p2_proof.get("case_name") != case.case_name or
            p2_proof.get("case_yaml_sha256") != case.case_sha256 or
            p2_proof.get("grid_cmn_sha256") != case.grid_sha256 or
            p2_proof.get("research_time_sha256") != case.time_sha256 or
            p2_proof.get("utm_epsg") != expected_epsg or
            p2_proof.get("nx") != case.nx or
            p2_proof.get("ny") != case.ny or
            p2_proof.get("lu_dat_sha256") != p2_lu_sha or
            p2_proof.get("original_science") != "NOT_RUN"):
        raise ContractError("P3 native P2 provenance/case/source grid mismatch")
    if p2_kind == "A":
        if (p2_proof.get("xrefkm") != case.xrefkm_text or
                p2_proof.get("yrefkm") != case.yrefkm_text or
                abs(p2_proof.get("dgridkm", -1) - case.dgridkm) > 1e-9):
            raise ContractError("P3 P2-A grid geometry mismatched")
    # For P2-C its native manifest has the actual origin/spacing,
    # independently verified by the P2-C producer before attestation. P3's
    # strict LU header reader rejects any mismatch before physics execution.
    out = root / "geo/makegeo/p3_case"
    evidence = root / "evidence/p3.json"
    for dest in (out, evidence):
        if dest.exists() or dest.is_symlink():
            raise ContractError("P3 new output/attestation already exists: " + str(dest))
    for folder in (root/"geo", root/"geo/makegeo", root/"evidence"):
        if folder.is_symlink():
            raise ContractError("P3 output parent symlink forbidden")
    verify_immutable(case)
    out.mkdir(parents=True)
    geo_ctrl = out/"makegeo.inp"
    geo_ctrl.write_text(make_control(template, case), encoding="utf-8")
    p1_csv = out/"terrain.csv"
    terrel = out/"terrel.dat"
    csv = out/"p3.csv"
    geo = out/"geo.dat"
    _run([str(p1_bin.resolve()), str(p1_tif.resolve()),
          case.xrefkm_text, case.yrefkm_text, str(case.nx), str(case.ny),
          f"{case.dgridkm:.3f}", str(case.utm_zone), case.hemisphere,
          str(p1_csv)], root, "P1 SRTM native")
    verify_immutable(case)
    _run([str(dat_bin.resolve()), "--grid", "terrain", str(p1_csv),
          str(terrel), str(case.utm_zone), case.hemisphere,
          case.xrefkm_text, case.yrefkm_text, str(case.nx), str(case.ny),
          f"{case.dgridkm:.3f}"], root, "P1 to TERREL")
    _run([str(p3_bin.resolve()), str(geo_ctrl), str(p2_lu),
          str(terrel), str(csv), str(geo)], root, "MAKEGEO supported branch")
    verify_immutable(case)
    hashes = {name: sha(path) for name,path in (
        ("p1_csv_sha256",p1_csv),("terrel_dat_sha256",terrel),
        ("p3_csv_sha256",csv),("geo_dat_sha256",geo),
        ("makegeo_controls_sha256",geo_ctrl))}
    proof = {
        "schema": "cteas.p3.native_b0_handoff.v1",
        "case_name": case.case_name,
        "case_yaml_sha256": case.case_sha256,
        "grid_cmn_sha256": case.grid_sha256,
        "research_time_sha256": case.time_sha256,
        "p1_tif_sha256": p1_tif_sha256,
        "p2_kind": p2_kind, "p2_method": p2_proof["method"],
        "p2_attestation_sha256": sha(p2_proof_path),
        "p2_lu_dat_sha256": p2_lu_sha,
        "makegeo_template_sha256": template_sha,
        "utm_epsg": expected_epsg, "nx": case.nx, "ny": case.ny,
        "xrefkm": case.xrefkm_text, "yrefkm": case.yrefkm_text,
        "dgridkm": case.dgridkm,
        "research_begin_utc": case.research_begin,
        "research_end_utc": case.research_end,
        **native_shas, **hashes,
        "status": "P3_NATIVE_SAME_CASE_PRODUCED_UNVERIFIED",
        "p1_original_science": "NOT_RUN",
        "p2_original_newsite_science": "NOT_RUN",
        "p3_original_makegeo_science": "NOT_RUN",
        "p6_p7": "OUT_OF_SCOPE",
    }
    evidence.parent.mkdir(parents=True, exist_ok=True)
    verify_immutable(case)
    with evidence.open("x", encoding="utf-8") as stream:
        json.dump(proof, stream, sort_keys=True, indent=2)
        stream.write("\n")
    verify_immutable(case)
    return proof


def main() -> int:
    parser = argparse.ArgumentParser(description="Issue46 B-0 authentic producer interface; science NOT_RUN")
    parser.add_argument("--case-yaml", type=Path, required=True)
    parser.add_argument("--p1-tif", type=Path, required=True)
    parser.add_argument("--p1-tif-sha256", required=True)
    parser.add_argument("--p1-bin", type=Path, required=True)
    parser.add_argument("--dat-bin", type=Path, required=True)
    parser.add_argument("--p3-bin", type=Path, required=True)
    parser.add_argument("--p2-kind", choices=("A", "C"), required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(produce(case_yaml=args.case_yaml, p1_tif=args.p1_tif,
                                 p1_tif_sha256=args.p1_tif_sha256,
                                 p1_bin=args.p1_bin, dat_bin=args.dat_bin,
                                 p3_bin=args.p3_bin, p2_kind=args.p2_kind),
                         sort_keys=True))
        return 0
    except (ContractError, OSError, ValueError, KeyError, TypeError,
            UnicodeError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "P3_B0_HANDOFF_BLOCKED", "reason": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
