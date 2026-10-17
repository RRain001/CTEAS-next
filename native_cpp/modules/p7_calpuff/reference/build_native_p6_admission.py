#!/usr/bin/env python3
"""Create a scoped native-P6 -> P7 admission record after real P6 execution.

Integrity/provenance evidence, NOT a signed attestation. Only a trusted,
source-pinned runner can establish authenticity of the compiled producer.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

CASE = "hefei5km_2022_reference_case_20261011"
SCHEMA = "CTEAS_NATIVE_P6_TO_P7_V1"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as src:
        for block in iter(lambda: src.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def required_file(path: Path) -> None:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"missing / symlink native P6 artifact: {path}")


def build(met: Path, manifest: Path, driver: Path, source_sha: str, out: Path) -> str:
    for path in (met, manifest, driver):
        required_file(path)
    if met.name != "native_causal_independent_header_calmet.dat":
        raise ValueError("not the P6F independent-header native MET output")
    if manifest.name != "native_cpp_hourly_manifest.json" or met.parent.resolve() != manifest.parent.resolve():
        raise ValueError("P6 MET and manifest must share an original producer directory")
    if driver.name != "cteas_p6_native_hourly_driver":
        raise ValueError("not an approved P6 native driver")
    if not re.fullmatch(r"[0-9a-f]{40}", source_sha):
        raise ValueError("invalid source commit")
    current_head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True
    ).strip()
    if source_sha != current_head:
        raise ValueError("source SHA does not match checked-out trusted runner")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("P6 manifest not an object")
    required = {
        "status": "PASS_CPP_PROCESS_COORDINATOR_EXECUTION",
        "hours_completed": 143,
        "native_wind": True,
        "native_previous_hour_comp_state": True,
        "p6e_reference_is_geo_deck_metadata_only": True,
        "p6f_header_from_native_hour_manifest": True,
        "original_met_role": "NOT_REQUIRED_NOT_OPENED_BY_NATIVE_EXECUTION",
    }
    for key, value in required.items():
        if type(data.get(key)) is not type(value) or data.get(key) != value:
            raise ValueError(f"P6 producer manifest state mismatch: {key}")
    met_hash = sha256(met)
    if data.get("independent_p6f_header_sha256") != met_hash:
        raise ValueError("P6F MET digest mismatches actual output")
    native = met.with_name("native_causal_calmet.dat")
    required_file(native)
    if data.get("native_calmet_dat_sha256") != sha256(native):
        raise ValueError("P6 baseline digest mismatches producer manifest")
    if out.exists() or out.is_symlink():
        raise ValueError("admission output already exists")
    payload = {
        "case_id": CASE,
        "source_sha": source_sha,
        "hours": "143",
        "xrefkm": "510.885",
        "yrefkm": "3531.269",
        "met_sha256": met_hash,
        "manifest_sha256": sha256(manifest),
        "p6_driver_sha256": sha256(driver),
        "manifest_independent_sha256": data["independent_p6f_header_sha256"],
    }
    # Deterministic exact field order; strict native reader rejects extras.
    ordered = (
        "case_id", "source_sha", "hours", "xrefkm", "yrefkm",
        "met_sha256", "manifest_sha256", "p6_driver_sha256",
        "manifest_independent_sha256",
    )
    output = SCHEMA + "\n" + "".join(f"{k}={payload[k]}\n" for k in ordered)
    out.write_text(output, encoding="ascii")
    return output


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--met", required=True, type=Path)
    p.add_argument("--manifest", required=True, type=Path)
    p.add_argument("--p6-driver", required=True, type=Path)
    p.add_argument("--source-sha", required=True)
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    build(a.met, a.manifest, a.p6_driver, a.source_sha, a.out)
    print("P7_P6_ADMISSION_INTEGRITY_RECORD_CREATED=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
