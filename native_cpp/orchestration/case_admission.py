"""#42 shared read-only B-0 case/grid/time admission. No source download or model execution.

Reuses site_plan geography and UTC validators and the existing station_grid
numeric parser, with a strict *lexical* gate before either can discard original
key spellings or duplicate records. All three SHA256 hashes refer to raw bytes.
Not a producer-science acceptance or B-1 scratch orchestrator.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
from pathlib import Path
import re
from typing import Any

import yaml
from native_cpp.orchestration.site_plan import _geography, _time
from native_cpp.orchestration.plan import ContractError, mapping

ACTIVE = re.compile(r"^\s*!\s*([A-Z0-9_]+)\s*=\s*(.*?)\s*!\s*$")
ORIGIN = re.compile(r"-?\d+\.\d{3}\Z")
INTEGER = re.compile(r"\d+\Z")
DECIMAL = re.compile(r"(?:\d+(?:\.\d+)?|\.\d+)\Z")
STAMP = re.compile(r"\d{8}-\d{6}\Z")
FIELDS = ("IMAP", "DATUM", "IUTMZN", "LSOHEM", "XREFKM", "YREFKM",
          "NX", "NY", "DGRIDKM", "NZ")
ROOT = Path(__file__).resolve().parents[2]


def _read(path: Path, *, max_bytes: int) -> bytes:
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= max_bytes:
        raise ContractError("B0 missing, symlinked, empty or oversized input")
    return path.read_bytes()


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _lexical_grid(raw: bytes) -> dict[str, str]:
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise ContractError("B0 grid must be UTF-8") from exc
    seen: dict[str, str] = {}
    zfaces = 0
    for line in lines:
        # The legacy numeric parser also recognizes '*' (inactive template)
        # cards. Reject shadowed *physical* authority rather than letting a
        # star-card silently override a validated active ! key.
        shadow = re.fullmatch(r"\\s*\\*\\s*([A-Z0-9_]+)\\s*=.*\\*\\s*", line)
        if shadow and shadow.group(1) in (*FIELDS, "ZFACE"):
            raise ContractError("B0 inactive grid record shadows numerical authority")
        match = ACTIVE.fullmatch(line)
        if not match:
            continue
        key, value = match.group(1), match.group(2).strip()
        if key == "ZFACE":
            zfaces += 1
        else:
            if key in seen:
                raise ContractError("B0 duplicated grid key: " + key)
            seen[key] = value
    for key in FIELDS:
        if key not in seen or not seen[key]:
            raise ContractError("B0 grid required field absent: " + key)
    if seen["IMAP"] != "UTM" or seen["DATUM"] != "WGS-84":
        raise ContractError("B0 only supports WGS-84 UTM")
    if seen["LSOHEM"] not in ("N", "S"):
        raise ContractError("B0 invalid hemisphere")
    for key in ("XREFKM", "YREFKM"):
        if not ORIGIN.fullmatch(seen[key]):
            raise ContractError("B0 " + key + " must be exactly three decimal km digits")
    for key in ("IUTMZN", "NX", "NY", "NZ"):
        if not INTEGER.fullmatch(seen[key]):
            raise ContractError("B0 " + key + " must be a positive integer literal")
    if not 1 <= int(seen["IUTMZN"]) <= 60 or any(int(seen[k]) <= 0 for k in ("NX", "NY", "NZ")):
        raise ContractError("B0 UTM zone or grid dimensions outside supported range")
    if not DECIMAL.fullmatch(seen["DGRIDKM"]) or float(seen["DGRIDKM"]) <= 0:
        raise ContractError("B0 DGRIDKM must be a positive numeric literal")
    if zfaces != int(seen["NZ"]) + 1:
        raise ContractError("B0 ZFACE count not consistent with NZ")
    if int(seen["NX"]) * int(seen["NY"]) > 10_000_000:
        raise ContractError("B0 grid exceeds 10-million-cell admission limit")
    return seen


def _lexical_time(raw: bytes) -> tuple[str, str]:
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise ContractError("B0 research_time must be UTF-8") from exc
    fields: dict[str, str] = {}
    for line in lines:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.fullmatch(r"\s*(BEGIN|END)\s*:\s*(\S+)\s*", line)
        if not match or match.group(1) in fields:
            raise ContractError("B0 research_time duplicate or unexpected record")
        key, value = match.groups()
        if not STAMP.fullmatch(value):
            raise ContractError("B0 malformed research_time timestamp")
        fields[key] = value
    if set(fields) != {"BEGIN", "END"}:
        raise ContractError("B0 research_time requires one BEGIN and one END")
    begin, end = _time(fields["BEGIN"]), _time(fields["END"])
    if end < begin:
        raise ContractError("B0 research_time END earlier than BEGIN")
    return fields["BEGIN"], fields["END"]


class _UniqueSafeLoader(yaml.SafeLoader):
    """Reject duplicate YAML keys before site_plan consumes the case."""


def _unique_mapping(loader: _UniqueSafeLoader, node: yaml.MappingNode) -> dict:
    loader.flatten_mapping(node)
    result = {}
    for key_node, val_node in node.value:
        key = loader.construct_object(key_node, deep=True)
        if not isinstance(key, (str, int, float, bool)) or key in result:
            raise ContractError("B0 case.yaml duplicate or unsupported mapping key")
        result[key] = loader.construct_object(val_node, deep=True)
    return result


_UniqueSafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _unique_mapping)


@dataclass(frozen=True)
class CaseAdmission:
    case_name: str
    case_path: Path
    grid_path: Path
    time_path: Path
    case_sha256: str
    grid_sha256: str
    time_sha256: str
    utm_zone: int
    hemisphere: str
    xrefkm_text: str
    yrefkm_text: str
    nx: int
    ny: int
    dgridkm: float
    research_begin: str
    research_end: str


def admit_case(case_path: Path) -> CaseAdmission:
    """Read a physically staged new-site case; do not create or alter files."""
    if case_path.name != "case.yaml":
        raise ContractError("B0 expected case.yaml")
    root = case_path.parent
    if any(p.is_symlink() for p in (root, root / "grid")):
        raise ContractError("B0 staged directories must not be symlinks")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", root.name):
        raise ContractError("B0 invalid independent case name")
    if root.resolve().is_relative_to(ROOT) or root.name.startswith("hefei5km_2022_reference"):
        raise ContractError("B0 case must be independent and outside repo/frozen Hefei")
    grid_path, time_path = root / "grid/grid.cmn", root / "grid/research_time"
    case_raw = _read(case_path, max_bytes=131072)
    grid_raw = _read(grid_path, max_bytes=262144)
    time_raw = _read(time_path, max_bytes=65536)
    lexical = _lexical_grid(grid_raw)
    begin, end = _lexical_time(time_raw)
    try:
        case = mapping(yaml.load(case_raw, Loader=_UniqueSafeLoader), "B0 case")
    except ContractError:
        raise
    except (yaml.YAMLError, UnicodeError, ValueError) as exc:
        raise ContractError("B0 invalid case YAML") from exc
    if case.get("case_name") != root.name:
        raise ContractError("B0 case name differs from independent staging directory")
    if case.get("settings", {}).get("timezone") != "UTC+0000":
        raise ContractError("B0 requires UTC+0000 case timezone")
    # Existing site_plan validates case-grid horizontal agreement, center, NZ,
    # and both WGS84/UTM values. This is not a second projected-grid parser.
    grid, _ = _geography(case, case_path)
    timestamps = mapping(mapping(case.get("preprocess"), "preprocess").get("research_time"),
                         "preprocess.research_time")
    if timestamps.get("begin") != begin or timestamps.get("end") != end:
        raise ContractError("B0 research_time disagrees with case.yaml")
    if (grid.iutmzn != int(lexical["IUTMZN"]) or grid.lsohem != lexical["LSOHEM"]
            or grid.nx != int(lexical["NX"]) or grid.ny != int(lexical["NY"])
            or grid.nz != int(lexical["NZ"])
            or any(abs(actual - float(lexical[key])) > 1e-12
                   for actual, key in ((grid.xrefkm, "XREFKM"),
                                       (grid.yrefkm, "YREFKM"),
                                       (grid.dgridkm, "DGRIDKM")))):
        raise ContractError("B0 original grid literals inconsistent with parsed grid")
    return CaseAdmission(
        root.name, case_path, grid_path, time_path,
        _sha(case_raw), _sha(grid_raw), _sha(time_raw),
        grid.iutmzn, grid.lsohem,
        lexical["XREFKM"], lexical["YREFKM"],
        grid.nx, grid.ny, grid.dgridkm, begin, end)


def verify_immutable(admission: CaseAdmission) -> None:
    """Call after a producer runs: any changed byte invalidates the handoff."""
    for path, expected, cap in (
        (admission.case_path, admission.case_sha256, 131072),
        (admission.grid_path, admission.grid_sha256, 262144),
        (admission.time_path, admission.time_sha256, 65536),
    ):
        if _sha(_read(path, max_bytes=cap)) != expected:
            raise ContractError("B0 staged case/grid/time bytes changed after admission")
