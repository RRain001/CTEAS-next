"""S2-2C/2D read-only manifest integrity gate for scoped native handoffs.

This is deliberately NOT an executor or a scientific acceptance oracle.
The producer strings below are self-attested metadata; a later verified run
manifest must bind them to executable hashes, commands and real science checks.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path, PurePosixPath

from .plan import CASE_ID, ContractError

PROFILE = "HEFEI_2022_UTM50N_100M_1SS_1US_143H_NO_RAIN"
# These are the only file roles admitted by this integrity-only gate.
# Paths are relative to a separately staged, immutable case working root.
EXPECTED = {
    "p6": {
        "p3_geo": ("geo/makegeo/geo.dat", "P3_NATIVE"),
        "p4_upper": ("met/upperair/final/up_58424.dat", "P4_NATIVE"),
        "p4_station_metadata": ("met/upperair/final/stations.csv", "P4_PREP_METADATA"),
        "p5_surface": ("met/surface/final/surf.dat", "P5_NATIVE"),
        "p5_station_metadata": ("met/surface/final/stations.csv", "P5_PREP_METADATA"),
        "met_control": ("run/met/met.inp", "FROZEN_DECK"),
    },
    "p7": {
        "p6_met": ("run/met/native_met.dat", "P6_NATIVE"),
        "p7_control": ("run/puff/puff.inp", "FROZEN_DECK"),
    },
}
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
GIT_SHA = re.compile(r"[0-9a-f]{40}\Z")


def _relative_path(value: object) -> str:
    if not isinstance(value, str) or "\\" in value or "\x00" in value:
        raise ContractError("artifact path is not a safe POSIX string")
    path = PurePosixPath(value)
    if (path.is_absolute() or value != path.as_posix()
            or "." in path.parts or ".." in path.parts):
        raise ContractError("artifact path is non-canonical or escapes the staging root")
    return value


def _regular_file_no_symlinks(root: Path, relative: str) -> Path:
    if root.is_symlink() or not root.is_dir():
        raise ContractError("staging root is missing, non-directory or symlink")
    target = root
    for part in PurePosixPath(relative).parts:
        target = target / part
        if target.is_symlink():
            raise ContractError("symlink in handoff path: " + relative)
    if not target.is_file():
        raise ContractError("required handoff file absent: " + relative)
    return target


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def preflight(root: Path, manifest_path: Path, consumer: str) -> dict[str, object]:
    """Verify a narrowly scoped file handoff, without invoking any solver."""
    if consumer not in EXPECTED:
        raise ContractError("unrecognized consumer")
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ContractError("manifest missing or symlink")
    raw = manifest_path.read_bytes()
    if len(raw) > 65536:
        raise ContractError("manifest exceeds bounded size")
    try:
        document = json.loads(raw)
    except (UnicodeError, ValueError) as exc:
        raise ContractError("invalid JSON manifest") from exc
    if not isinstance(document, dict) or set(document) != {
            "schema_version", "case_name", "science_profile", "source_head", "artifacts"}:
        raise ContractError("manifest schema keys mismatch")
    if type(document["schema_version"]) is not int or document["schema_version"] != 1:
        raise ContractError("unsupported manifest schema version")
    if document["case_name"] != CASE_ID or document["science_profile"] != PROFILE:
        raise ContractError("not the frozen no-rain Hefei 2022 scope")
    head = document["source_head"]
    if not isinstance(head, str) or GIT_SHA.fullmatch(head) is None:
        raise ContractError("source commit is not an exact Git SHA")
    artifacts = document["artifacts"]
    if not isinstance(artifacts, dict) or set(artifacts) != set(EXPECTED[consumer]):
        raise ContractError("missing/extra artifact role")
    details = {}
    for role, (required_path, required_producer) in EXPECTED[consumer].items():
        record = artifacts[role]
        if not isinstance(record, dict) or set(record) != {
                "path", "sha256", "bytes", "producer"}:
            raise ContractError(role + ": invalid record keys")
        path = _relative_path(record["path"])
        if path != required_path or record["producer"] != required_producer:
            raise ContractError(role + ": wrong path or producer assertion")
        size, expected_sha = record["bytes"], record["sha256"]
        if type(size) is not int or size < 1:
            raise ContractError(role + ": invalid byte length")
        if not isinstance(expected_sha, str) or SHA256.fullmatch(expected_sha) is None:
            raise ContractError(role + ": invalid SHA256")
        file_path = _regular_file_no_symlinks(root, path)
        actual_size = file_path.stat().st_size
        if actual_size != size or _sha256(file_path) != expected_sha:
            raise ContractError(role + ": bytes/hash mismatch")
        details[role] = {"path": path, "bytes": actual_size, "sha256": expected_sha}
    return {
        "status": "INPUT_INTEGRITY_VERIFIED_ONLY",
        "consumer": consumer,
        "source_head_asserted_not_independently_authenticated": head,
        "case_name": CASE_ID,
        "model_executed": False,
        "scientific_acceptance": "NOT_EVALUATED",
        "ready_to_execute": False,
        "legacy_fallback": False,
        "verified_artifacts": details,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only S2 native artifact integrity gate")
    parser.add_argument("--consumer", required=True, choices=sorted(EXPECTED))
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = preflight(args.root, args.manifest, args.consumer)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (ContractError, OSError, UnicodeError, TypeError) as exc:
        print(json.dumps({"status": "BLOCKED_HANDOFF", "ready_to_execute": False,
                          "model_executed": False, "legacy_fallback": False,
                          "error": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
