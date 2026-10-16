#!/usr/bin/env python3
"""Stage and optionally run untouched original CALPUFF 7.2.1 reference.

Requires explicit 2022 input files and pinned hashes to run. This is a
reference executor; it does not claim that C++ CALPUFF physics is implemented.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys


def sha256(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def assignment(inp: str, key: str) -> str:
    match = re.findall(r"!\s*" + re.escape(key) + r"\s*=\s*([^!\r\n]+)!", inp,
                       re.IGNORECASE)
    if len(match) != 1:
        raise ValueError(f"P7A expected exactly one active {key}, found {len(match)}")
    return match[0].strip()


def canonical_path(root: Path, cwd: Path, value: str) -> Path:
    value = value.strip().strip("'\"")
    if not value or len(value) > 132 or Path(value).is_absolute():
        raise ValueError(f"P7A invalid relative path {value!r}")
    target = (cwd / value).resolve()
    if not target.is_relative_to(root):
        raise ValueError("P7A reference path escapes the isolated case root")
    return target


def validate_control(text: str) -> dict:
    expected = {
        "METFM": 1, "MWET": 0, "MCHEM": 0, "NX": 50, "NY": 50,
        "NZ": 9, "IOUTU": 3, "METRUN": 0,
        "IBYR": 2022, "IBMO": 1, "IBDY": 1, "IBHR": 0,
        "IEYR": 2022, "IEMO": 1, "IEDY": 6, "IEHR": 23,
        "NPT1": 1,
    }
    for key, value in expected.items():
        if int(assignment(text, key)) != value:
            raise ValueError(f"P7A frozen control mismatch: {key} != {value}")
    if assignment(text, "ABTZ").upper() != "UTC+0000":
        raise ValueError("P7A selected reference requires UTC+0000")
    # Only the selected non-wet 2022 reference can be qualified while
    # CALMET rain is IPCODE=9999 (143/143).
    for key in ("IBSEC", "IESEC"):
        if int(assignment(text, key)) != 0:
            raise ValueError("P7A nonzero seconds in selected case")
    return {"case": "hefei_2022_50x50_100m_143_original_met_intervals",
            "scope": "MWET=0; source/input control is supplied, not synthesized"}


def stage(control: Path, met: Path, output: Path) -> dict:
    control = control.resolve(strict=True)
    met = met.resolve(strict=True)
    output = output.resolve()
    if output in (control, met) or output == control.parent or output == met.parent:
        raise ValueError("P7A output must be distinct from original input")
    if not control.is_file() or not met.is_file() or met.stat().st_size < 1024:
        raise ValueError("P7A missing/empty original input")
    control_sha = sha256(control)
    met_sha = sha256(met)
    text = control.read_text(encoding="latin-1")
    desc = validate_control(text)
    work = output / "case" / "run" / "puff"
    work.mkdir(parents=True, exist_ok=True)
    for name in ("calpuff.inp", "CALPUFF.INP", "puff.inp", "PUFF.INP"):
        path = work / name
        if path.exists() or path.is_symlink():
            raise FileExistsError(f"P7A never overwrite a staged control: {path}")
        shutil.copy2(control, path)
    for raw in (assignment(text, "METDAT"), assignment(text, "METDAT").upper()):
        target = canonical_path(output, work, raw)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() or target.is_symlink():
            raise FileExistsError(f"P7A would overwrite weather: {target}")
        shutil.copy2(met, target)
    # Perform path-safety checks on output destinations without precreating.
    outputs = {}
    for label in ("PUFLST", "CONDAT"):
        dest = canonical_path(output, work, assignment(text, label))
        for p in (dest, canonical_path(output, work, assignment(text, label).upper())):
            if p.exists():
                raise FileExistsError(f"P7A stale reference output: {p}")
        outputs[label] = assignment(text, label)
    manifest = {
        "status": "REFERENCE_STAGED_NOT_EXECUTED",
        "scientific_status": "ORIGINAL_CALPUFF_REFERENCE_NUMERICAL_PARITY_NOT_YET_ESTABLISHED",
        "control_sha256": control_sha,
        "original_met_sha256": met_sha,
        "control_bytes": control.stat().st_size,
        "met_bytes": met.stat().st_size,
        "staged_workdir": str(work),
        "selected_case": desc,
        "declared_output_names": outputs,
    }
    (output / "reference-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def execute(control: Path, met: Path, binary: Path, output: Path,
            control_sha: str, met_sha: str, max_seconds: int) -> dict:
    for name, path, expected in (("control", control, control_sha),
                                 ("MET.DAT", met, met_sha)):
        if not re.fullmatch(r"[0-9a-f]{64}", expected.lower()):
            raise ValueError(f"P7A {name} must have explicit pinned sha256")
        if sha256(path) != expected.lower():
            raise ValueError(f"P7A {name} input SHA256 does not match frozen declaration")
    if not binary.is_file():
        raise FileNotFoundError(f"P7A unmodified original CALPUFF binary missing: {binary}")
    if max_seconds < 1 or max_seconds > 14400:
        raise ValueError("P7A bounded runtime must be 1–14400 seconds")
    binary_hash = sha256(binary)
    manifest = stage(control, met, output)
    work = Path(manifest["staged_workdir"])
    out = output / "calpuff-original-runtime.log"
    try:
        with out.open("w") as log:
            proc = subprocess.run([str(binary.resolve())], cwd=work, stdout=log,
                                  stderr=subprocess.STDOUT, timeout=max_seconds,
                                  check=False)
    except subprocess.TimeoutExpired as exc:
        manifest.update({"status": "REFERENCE_TIMEOUT", "timeout_seconds": max_seconds,
                         "original_binary_sha256": binary_hash})
        (output / "reference-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        raise RuntimeError("P7A original reference run timed out") from exc
    # Source bytes must remain identical after the full original run.
    if sha256(control) != control_sha.lower() or sha256(met) != met_sha.lower():
        raise RuntimeError("P7A original inputs changed unexpectedly during execution")
    names = manifest["declared_output_names"]
    def search_generated(key: str) -> Path | None:
        stem = names[key]
        candidates = [canonical_path(output, work, stem),
                      canonical_path(output, work, stem.upper())]
        for candidate in candidates:
            if candidate.is_file() and candidate.stat().st_size:
                return candidate
        return None
    listing = search_generated("PUFLST")
    concentration = search_generated("CONDAT")
    logs = out.read_text(errors="replace")
    if listing:
        logs += "\n" + listing.read_text(errors="replace")
    bad = re.findall(r"(?im)^\s*ERROR IN SUBR\.|\bFATAL\b|\bABORT\b|segmentation fault|forrtl:\s*severe",
                     logs)
    passed = proc.returncode == 0 and listing is not None and concentration is not None and not bad
    manifest.update({
        "status": "ORIGINAL_REFERENCE_EXECUTION_PASS" if passed else "ORIGINAL_REFERENCE_EXECUTION_FAIL",
        "original_binary_sha256": binary_hash,
        "original_return_code": proc.returncode,
        "critical_log_markers": bad[:15],
        "listing_sha256": sha256(listing) if listing else None,
        "concentration_sha256": sha256(concentration) if concentration else None,
        "concentration_bytes": concentration.stat().st_size if concentration else 0,
        "scientific_status": "ORIGINAL_EXECUTION_ONLY_NO_CPP_CONCENTRATION_PARITY",
    })
    (output / "reference-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    if not passed:
        raise RuntimeError("P7A original CALPUFF failed; see manifest, list and runtime logs")
    return manifest


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--control", type=Path, required=True)
    p.add_argument("--met", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--original-binary", type=Path)
    p.add_argument("--expected-control-sha256")
    p.add_argument("--expected-met-sha256")
    p.add_argument("--max-seconds", type=int, default=3600)
    p.add_argument("--execute", action="store_true")
    args = p.parse_args()
    if args.execute:
        if not args.original_binary or not args.expected_control_sha256 or not args.expected_met_sha256:
            p.error("--execute requires original binary and both frozen SHA256 values")
        result = execute(args.control, args.met, args.original_binary, args.output,
                         args.expected_control_sha256, args.expected_met_sha256,
                         args.max_seconds)
    else:
        result = stage(args.control, args.met, args.output)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
