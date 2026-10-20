"""S2-B #169 P2-C adapter: admitted B-0 case -> existing native 10x10 point producer.

No raster downloads, reprojection, physical changes, P2-B area algorithm, or
claims of Fortran parity. A supplied source SHA is source *integrity* only,
not proof the TIFF belongs to the licensed 2022 data product.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import hashlib
import json
import subprocess

from .case_admission import admit_case, verify_immutable
from .plan import ContractError

POLICY_SHA = "a5fa157f57feb1aa160dd96d920a22d267fea78c5828c6040fa95e86536544ed"
METHOD = "P2_C_GLC30M_SOURCE_SUBPOINT_GLAZAS_LUGRID_R4_HITS_V1"


def digest(path: Path) -> str:
    if path.is_symlink() or not path.is_file() or path.stat().st_size < 1:
        raise ContractError(f"P2-C missing, empty, or symlinked file: {path}")
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            sha.update(block)
    return sha.hexdigest()


def produce(*, case_yaml: Path, tif: Path, tif_sha256: str, policy: Path,
            mode: str, native_bin: Path, bln: Path | None = None,
            bln_sha256: str | None = None) -> dict:
    case = admit_case(case_yaml)
    root = case.case_path.parent
    if mode not in ("inland", "coastal"):
        raise ContractError("P2-C requires explicit inland/coastal source method")
    if len(tif_sha256) != 64 or any(c not in "0123456789abcdef" for c in tif_sha256):
        raise ContractError("P2-C expected TIFF SHA must be lowercase 64-hex")
    if digest(tif) != tif_sha256:
        raise ContractError("P2-C authentic data bytes do not match supplied SHA")
    if digest(policy) != POLICY_SHA:
        raise ContractError("P2-C user-approved 34+210 policy has changed")
    if not native_bin.is_file() or native_bin.is_symlink():
        raise ContractError("P2-C native producer executable missing or symlinked")
    if mode == "coastal":
        if bln is None or bln_sha256 is None or len(bln_sha256) != 64 or any(
                c not in "0123456789abcdef" for c in bln_sha256):
            raise ContractError("P2-C coastal source requires original BLN + actual SHA")
        if digest(bln) != bln_sha256:
            raise ContractError("P2-C coastal BLN bytes differ from supplied SHA")
    elif bln is not None or bln_sha256 is not None:
        raise ContractError("P2-C inland forbids any coastline BLN")

    out = root / "geo/ctgproc/p2c_case"
    evidence = root / "evidence/p2.json"
    for path in (out, evidence):
        if path.exists() or path.is_symlink():
            raise ContractError("P2-C fresh output/attestation path already used: " + str(path))
    for folder in (root / "geo", root / "geo/ctgproc", root / "evidence"):
        if folder.is_symlink():
            raise ContractError("P2-C output parent cannot be symlink")
    command = [
        str(native_bin.resolve()), "--case-grid", mode, str(tif.resolve()),
        tif_sha256, str(policy.resolve()),
        str(case.utm_zone + (32600 if case.hemisphere == "N" else 32700)),
        case.xrefkm_text, case.yrefkm_text, str(case.nx), str(case.ny),
        format(case.dgridkm, ".12g"), str(bln.resolve()) if bln else "-",
        bln_sha256 if bln_sha256 else "-", str(out),
    ]
    verify_immutable(case)
    out.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(command, cwd=root, text=True, capture_output=True, timeout=1200)
    if result.returncode:
        raise ContractError("P2-C native producer returned " + str(result.returncode)
                            + ": " + result.stderr[-1000:])
    verify_immutable(case)
    native_manifest_path = out / "p2c_glc30m_manifest.json"
    native = json.loads(native_manifest_path.read_text(encoding="utf-8"))
    if (native.get("method") != METHOD or
            native.get("mapping_policy_sha256") != POLICY_SHA or
            native.get("data_sha256") != tif_sha256 or
            native.get("utm_epsg") != case.utm_zone +
                    (32600 if case.hemisphere == "N" else 32700) or
            native.get("nx") != case.nx or native.get("ny") != case.ny or
            native.get("xrefkm") != case.xrefkm_text or
            native.get("yrefkm") != case.yrefkm_text or
            native.get("site") != mode or
            native.get("lcoast") != (mode == "coastal") or
            native.get("fraction_fields") != case.nx * case.ny * 38 or
            native.get("full_l1_original_bln_sha256") != (
                bln_sha256 if bln_sha256 else "NOT_APPLICABLE_LCOAST_FALSE")):
        raise ContractError("P2-C native manifest disagrees with admitted case/source")
    if abs(float(native.get("dgridkm", -1)) - case.dgridkm) > 1e-9:
        raise ContractError("P2-C native spacing differs from admitted grid")
    for filename, name in (("lu.dat", "lu_dat_sha256"), ("hits.csv", "hits_csv_sha256")):
        if digest(out / filename) != native.get(name):
            raise ContractError("P2-C actual output sha differs from native manifest")
    attestation = {
        "schema": "cteas.s2b.p2c.case.produced_unverified.v1",
        "case_name": case.case_name,
        "case_yaml_sha256": case.case_sha256,
        "grid_cmn_sha256": case.grid_sha256,
        "research_time_sha256": case.time_sha256,
        "source_tiff_sha256": tif_sha256,
        "source_bln_sha256": bln_sha256 if bln_sha256 else "NOT_APPLICABLE",
        "mapping_policy_sha256": POLICY_SHA,
        "native_binary_sha256": digest(native_bin),
        "native_manifest_sha256": digest(native_manifest_path),
        "lu_dat_sha256": digest(out / "lu.dat"),
        "hits_csv_sha256": digest(out / "hits.csv"),
        "method": METHOD,
        "mode": mode,
        "utm_epsg": native["utm_epsg"],
        "nx": case.nx, "ny": case.ny,
        "research_begin_utc": case.research_begin,
        "research_end_utc": case.research_end,
        "status": "P2C_GENERIC_CASE_PRODUCED_UNVERIFIED",
        "original_science": "NOT_RUN",
        "p3_makegeo": "OUT_OF_SCOPE_ISSUE46",
    }
    evidence.parent.mkdir(parents=True, exist_ok=True)
    verify_immutable(case)
    with evidence.open("x", encoding="utf-8") as stream:
        json.dump(attestation, stream, indent=2, sort_keys=True)
        stream.write("\n")
    verify_immutable(case)
    return attestation


def main() -> int:
    parser = argparse.ArgumentParser(description="S2-B immutable-case P2-C producer (no Fortran science claim)")
    parser.add_argument("--case-yaml", type=Path, required=True)
    parser.add_argument("--tif", type=Path, required=True)
    parser.add_argument("--tif-sha256", required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--mode", choices=["inland", "coastal"], required=True)
    parser.add_argument("--bln", type=Path)
    parser.add_argument("--bln-sha256")
    parser.add_argument("--native-cpp-bin", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = produce(case_yaml=args.case_yaml, tif=args.tif,
                         tif_sha256=args.tif_sha256, policy=args.policy,
                         mode=args.mode, native_bin=args.native_cpp_bin,
                         bln=args.bln, bln_sha256=args.bln_sha256)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (ContractError, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"status": "P2C_GENERIC_BLOCKED", "reason": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
