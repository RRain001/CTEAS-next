#!/usr/bin/env python3
"""Capture the locked Hefei 2022 6-day 5 km reference case with the original CTEAS chain.

Locked specification: ``docs/reconstruction_cpp/HEFEI_2022_REFERENCE_CASE.md``.
Locked geometry/landuse inputs: ``calpuff_terrain_and_landuse_data_crop/hefei_5km/``
(both crop files are SHA-256 pinned in ``crop_info.json`` and re-verified here).

This script is a thin, parameterised orchestrator.  It never re-implements a
numerical model: every stage is executed by the frozen original Fortran
binaries in ``bin/linux-x86_64/`` through the repository's own preprocessing /
model driver modules, exactly the way ``project/cases/smoke5d_coldstart_20260701``
was produced (same stage order, same modules, same control templates).

Stages, in order:

    configure_grid_cmn      -> grid/grid.cmn, grid/center_location, grid/research_time
    terrel                  -> geo/terrel/terrel.dat                      (TERREL.x)
    ctgproc                 -> geo/ctgproc/lu.dat                         (CTGPROC.x)
    makegeo                 -> geo/makegeo/geo.dat                        (MAKEGEO.x)
    read62                  -> met/upperair/final/up_*.dat                (READ62.x)
    isd_download            -> met/surface/isd_raw/...                    (NOAA ISD fetch)
    smerge_prepare          -> met/surface/isd2smerge_ready/*.csv         (NOAA clean/fill)
    smerge                  -> met/surface/final/surf.dat                 (SMERGE.x)
    calmet                  -> run/met/met.dat (CALMET.DAT 2.1)           (met.x)
    calpuff                 -> run/puff/puff.con + puff.lst               (puff.x)

The surface chain is the P5 data-prep path already validated in CI for this exact
2022 Hefei domain (``.github/workflows/p4-p5-original-calmet-integration.yml``);
it is the only path that implements the documented station policy of the 5 km
domain (no ISD station inside, so the nearest annual-coverage-qualified station is
relocated virtually to the stack position).  SMERGE itself is the original binary.
The upper-air input is pinned to the single station recorded by the project's 2022
Hefei capture evidence (``CHM00058424``) instead of the module default
``auto_select_all``, which would pull two stations for this domain.

After the last stage the script freezes every produced artifact, every control
deck and every stage traced back to the vendor sources into a machine readable
manifest and (optionally) a Markdown register under ``docs/reconstruction_cpp/``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# --------------------------------------------------------------------------- #
# Locked specification (docs/reconstruction_cpp/HEFEI_2022_REFERENCE_CASE.md)
# --------------------------------------------------------------------------- #

SPEC = {
    "stack_latitude_deg": 31.939774444,
    "stack_longitude_deg": 117.141610855,
    "stack_height_m": 70.8,
    "stack_diameter_m": 1.6,
    "stack_exit_velocity_mps": 17.26,
    "stack_exit_temperature_c": 25.0,
    "hto_bq_per_year": 2.63e13,
    "ht_bq_per_year": 0.0,
    "domain_km": 5.0,
    "resolution_km": 0.1,
    "nz": 9,
    "zface_m": [0.0, 20.0, 40.0, 80.0, 160.0, 320.0, 640.0, 1200.0, 2000.0, 3000.0],
    "begin": "20220101-000000",
    "end": "20220106-230000",
    "timezone": "UTC+0000",
    "pstop_hpa": 500.0,
    "upperair_station_id": "CHM00058424",
    "expected_hour_labels": 144,
    "crop_info": "calpuff_terrain_and_landuse_data_crop/hefei_5km/crop_info.json",
}

# CALMET / CALPUFF options locked by the reference-case document; they are the
# values of the real user deck (project/cases/smoke5d_coldstart_20260701) and are
# the template defaults of engine/templates/{met,puff}.inp, asserted after render.
MET_LOCKED_OPTIONS = {
    "IRTYPE": "1",
    "LCALGRD": "T",
    "IWFCOD": "1",
    "IOBR": "0",
    "ISLOPE": "1",
    "IFRADJ": "1",
    "IKINE": "0",
    "IEXTRP": "-4",
    "TERRAD": "15.",
    "CRITFN": "1.",
    "ALPHA": "0.1",
    "DIVLIM": "5.0E-06",
    "NITER": "50",
    "IMIXH": "1",
    "THRESHL": "0.",
    "IZICRLX": "1",
    "NSECDT": "3600",
    "ISURFT": "-1",
    "IUPT": "-1",
    "IUPWND": "-1",
}
PUFF_LOCKED_OPTIONS = {
    "METFM": "1",
    "NSPEC": "2",
    "NSE": "1",
    "IOUTU": "3",
    "IOVERS": "2",
    "MGAUSS": "1",
    "MSLUG": "0",
    "MTRANS": "1",
    "MTIP": "1",
    "MDISP": "3",
    "MCHEM": "0",
    "MWET": "0",
    "MDRY": "1",
    "MTILT": "0",
    "MBCON": "0",
    "MFOG": "0",
    "MREG": "0",
}

VENDOR_SOURCES = {
    "terrel": "engine/vendor/src/TERREL_v7.0.0_L141010/terrel.for",
    "ctgproc": "engine/vendor/src/CTGPROC_v7.0.0_L150211/ctgproc.for",
    "makegeo": "engine/vendor/src/MAKEGEO_V3.2_L110401/makegeo.for",
    "read62": "engine/vendor/src/READ62_v5.661_L110225/READ62.FOR",
    "smerge": "engine/vendor/src/SMERGE_v5.7.0_L121203/SMERGE.FOR",
    "calmet": "engine/vendor/src/CALMET_v6.5.0_L150223/calmet.for",
    "calmet_calutils": "engine/vendor/src/CALMET_v6.5.0_L150223/calutils.for",
    "calpuff_modules": "engine/vendor/src/CALPUFF_v7.2.1_L150618/modules.for",
    "calpuff": "engine/vendor/src/CALPUFF_v7.2.1_L150618/calpuff.for",
    "grid_cmn": "engine/vendor/src/grid/grid.cmn",
}

TEMPLATE_FILES = {
    "engine/templates/terrel.inp": "geo/terrel/terrel.inp",
    "engine/templates/ctgproc.inp": "geo/ctgproc/ctgproc.inp",
    "engine/templates/makegeo.inp": "geo/makegeo/makegeo.inp",
    "engine/templates/read62.inp": "run/read62/read62.inp",
    "engine/templates/smerge.inp": "run/smerge/smerge.inp",
    "engine/templates/met.inp": "run/met/met.inp",
    "engine/templates/puff.inp": "run/puff/puff.inp",
}

# Artifacts the reference case is graded on; each must exist and be hashed.
REQUIRED_ARTIFACTS = [
    "grid/grid.cmn",
    "grid/center_location",
    "grid/research_time",
    "geo/terrel/terrel.inp",
    "geo/terrel/terrel.dat",
    "geo/ctgproc/ctgproc.inp",
    "geo/ctgproc/lu.dat",
    "geo/makegeo/makegeo.inp",
    "geo/makegeo/geo.dat",
    "run/read62/read62.inp",
    "run/smerge/smerge.inp",
    "met/surface/isd_raw/station_selection_{year}.json",
    "met/surface/final/surf.dat",
    "met/surface/final/stations.csv",
    "met/upperair/final/stations.csv",
    "run/met/met.inp",
    "run/met/met.lst",
    "run/met/met.dat",
    "run/met/met_runtime.log",
    "run/puff/puff.inp",
    "run/puff/puff.lst",
    "run/puff/puff.con",
    "run/puff/puff_runtime.log",
    "deliverables/met/met.dat",
    "deliverables/puff/puff.con",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


BINARY_NAMES = ("terrel", "ctgproc", "makegeo", "read62", "smerge", "met", "puff")

# Recipe verified on lhy-desktop (gfortran-11, Linux x86_64).  The vendor Fortran
# references INCLUDE files whose tracked names are upper case (e.g. PARAMS.TRL)
# while the sources open them lower case, so a lower-case symlink alias tree is
# passed with -I - exactly the workaround the P1/P2/P3 reference capture uses.
COMMON_FFLAGS = ("-std=legacy", "-ffixed-line-length-none", "-fno-automatic",
                 "-fno-align-commons", "-fallow-argument-mismatch", "-O0")
LEGACY72_FFLAGS = ("-std=legacy", "-ffixed-line-length-72", "-fno-automatic",
                   "-fno-align-commons", "-fallow-argument-mismatch", "-O0")
PUFF_FFLAGS = (*LEGACY72_FFLAGS, "-fdec-format-defaults")


def build_binaries(binary_dir: Path, compiler: str = "gfortran-11") -> list[str]:
    """Rebuild the original Fortran chain from the tracked vendor sources."""
    alias_root = Path(tempfile.mkdtemp(prefix="cteas-ref-include-"))
    built = []
    for name, source_rel in VENDOR_SOURCES.items():
        if not source_rel.endswith(".for") and not source_rel.endswith(".FOR"):
            continue
        source = ROOT / source_rel
        vendor_dir = source.parent
        alias = alias_root / vendor_dir.name
        alias.mkdir(exist_ok=True)
        for item in vendor_dir.iterdir():
            if item.is_file():
                link = alias / item.name.lower()
                if not link.exists():
                    link.symlink_to(item)
        flags = {
            "calmet": COMMON_FFLAGS,
            "terrel": COMMON_FFLAGS,
            "calpuff": PUFF_FFLAGS,
        }.get(name, LEGACY72_FFLAGS)
        target = binary_dir / f"{name}.x"
        sources = [str(source)]
        if name == "calpuff":
            sources = [str(ROOT / VENDOR_SOURCES["calpuff_modules"]), str(source)]
        command = [compiler, *flags, f"-I{alias}", *sources, "-o", str(target)]
        subprocess.run(command, check=True, cwd=str(ROOT))
        target.chmod(0o755)
        built.append(name)
    return built


def hefei_emission_bq_per_s(bq_per_year: float, seconds_per_year: float) -> float:
    return bq_per_year / seconds_per_year


def parse_cli_stamp(text: str) -> datetime:
    return datetime.strptime(text, "%Y%m%d-%H%M%S")


def stamp_text(moment: datetime) -> str:
    return moment.strftime("%Y%m%d-%H%M%S")


# --------------------------------------------------------------------------- #
# Case skeleton
# --------------------------------------------------------------------------- #

def build_case_yaml(case_name: str, spec: dict, emission_bq_s: float) -> str:
    lat = spec["stack_latitude_deg"]
    lon = spec["stack_longitude_deg"]
    return f"""schema_version: 1
case_name: {case_name}
paths:
  grid_dir: project/current/grid
  met_surface_dir: project/current/met/surface
  met_upperair_dir: project/current/met/upperair
  geo_ctgproc_dir: project/current/geo/ctgproc
  geo_terrel_dir: project/current/geo/terrel
  geo_makegeo_dir: project/current/geo/makegeo
  run_met_dir: project/current/run/met
  run_puff_dir: project/current/run/puff
  run_read62_dir: project/current/run/read62
  run_smerge_dir: project/current/run/smerge
settings:
  timezone: {spec['timezone']}
  pstop_hpa_default: {int(spec['pstop_hpa'])}
preprocess:
  grid:
    center:
      longitude: {lon!r}
      latitude: {lat!r}
    domain:
      length_km: {spec['domain_km']:g}
      width_km: {spec['domain_km']:g}
    resolution_km: {spec['resolution_km']:g}
    nz: {spec['nz']}
  research_time:
    begin: {spec['begin']}
    end: {spec['end']}
  upperair:
    pstop_hpa: {int(spec['pstop_hpa'])}
    auto_select_all: false
    station_id: {spec['upperair_station_id']}
  surface:
    auto_select_all: true
met:
  station_selection:
    isurft_mode: spatial
    iupt_mode: spatial
    iupwnd_mode: spatial
  options:
    lcfiles: true
    irtype: 1
    lcalgrd: true
    lsave: true
    lprint: false
    noobs: 0
    npsta: 0
    icloud: 0
    iforms: 2
    iformp: 2
    iformc: 2
    iwfcod: 1
    ifradj: 1
    ikine: 0
    iobr: 0
puff:
  options:
    lcfiles: true
    source_mode: case_yaml
    nspec: 2
    nse: 1
    mchem: 0
    idry: 0
    iwet: 0
    ndecay: 0
  point_sources:
  - name: HTO_STACK
    longitude: {lon!r}
    latitude: {lat!r}
    stack_height_m: {spec['stack_height_m']:g}
    base_elev_m: 0.0
    stack_diameter_m: {spec['stack_diameter_m']:g}
    exit_velocity_mps: {spec['stack_exit_velocity_mps']:g}
    exit_temp_k: {spec['stack_exit_temperature_c'] + 273.15:g}
    building_downwash_flag: 0.0
    zpltfm_m: 0.0
    fmfac: 1.0
    emissions: [{emission_bq_s!r}, 0.0]
"""


def create_case(case_dir: Path, case_name: str, spec: dict, emission_bq_s: float) -> None:
    for relative in (
        "grid",
        "geo/terrel",
        "geo/ctgproc",
        "geo/makegeo",
        "met/surface",
        "met/upperair",
        "run/read62",
        "run/smerge",
        "run/met",
        "run/puff",
        "deliverables",
        "logs",
    ):
        (case_dir / relative).mkdir(parents=True, exist_ok=True)
    for source_rel, target_rel in TEMPLATE_FILES.items():
        source = ROOT / source_rel
        if not source.is_file():
            raise FileNotFoundError(f"control template missing: {source}")
        shutil.copyfile(source, case_dir / target_rel)
    (case_dir / "case.yaml").write_text(
        build_case_yaml(case_name, spec, emission_bq_s), encoding="utf-8"
    )


# --------------------------------------------------------------------------- #
# Stage runner
# --------------------------------------------------------------------------- #

class StageRunner:
    def __init__(self, case_dir: Path, python_bin: str, env: dict) -> None:
        self.case_dir = case_dir
        self.python = python_bin
        self.env = env
        self.logs = case_dir / "logs"
        self.logs.mkdir(parents=True, exist_ok=True)
        self.records: list[dict] = []

    def run(self, index: int, label: str, module: str, args: list[str]) -> None:
        command = [self.python, "-m", module, *args]
        log_path = self.logs / f"{index:02d}_{label}.log"
        print(f"\n=== [{index:02d}] {label}: {' '.join(command)} ===", flush=True)
        begun = time.monotonic()
        with log_path.open("w", encoding="utf-8") as handle:
            handle.write(f"# command: {' '.join(command)}\n")
            handle.write(f"# cwd: {ROOT}\n\n")
            handle.flush()
            proc = subprocess.run(
                command,
                cwd=str(ROOT),
                stdout=handle,
                stderr=subprocess.STDOUT,
                text=True,
                env=self.env,
            )
        elapsed = time.monotonic() - begun
        self.records.append(
            {
                "stage": label,
                "module": module,
                "argv": args,
                "command": " ".join(command),
                "cwd": str(ROOT),
                "returncode": proc.returncode,
                "elapsed_s": round(elapsed, 3),
                "log": str(log_path.relative_to(self.case_dir)),
                "log_sha256": sha256(log_path),
            }
        )
        print(f"--- [{label}] rc={proc.returncode} in {elapsed:.1f}s -> {log_path.name}", flush=True)
        if proc.returncode != 0:
            tail = log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-40:]
            raise RuntimeError(
                f"stage {label} failed with rc={proc.returncode}\n" + "\n".join(tail)
            )


# --------------------------------------------------------------------------- #
# Verification helpers
# --------------------------------------------------------------------------- #

def parse_control_option(text: str, key: str) -> str | None:
    match = re.search(rf"!\s*{re.escape(key)}\s*=\s*([^!]*?)\s*!", text)
    return match.group(1).strip() if match else None


def verify_control_options(path: Path, expected: dict, label: str) -> dict:
    text = path.read_text(encoding="utf-8", errors="ignore")
    found, mismatches = {}, {}
    for key, want in expected.items():
        got = parse_control_option(text, key)
        found[key] = got
        if got is None or got.split(",")[0].strip() != want:
            mismatches[key] = {"expected": want, "found": got}
    if mismatches:
        raise RuntimeError(f"{label} control option mismatch: {json.dumps(mismatches, indent=2)}")
    return found


def verify_calmet_hourly_coverage(log_path: Path, spec: dict) -> dict:
    """Count CALMET's own per-step log lines; the END hour is not logged."""
    text = log_path.read_text(encoding="utf-8", errors="replace")
    pattern = re.compile(
        r"^\+Processing Year, Day, Hour, Sec from:\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)",
        re.MULTILINE,
    )
    hits = pattern.findall(text)
    if not hits:
        raise RuntimeError(f"no CALMET processing lines found in {log_path}")

    def julian_label(hit: tuple[str, str, str, str]) -> datetime:
        return datetime(int(hit[0]), 1, 1, int(hit[2])) + timedelta(days=int(hit[1]) - 1)

    begin = parse_cli_stamp(spec["begin"])
    end = parse_cli_stamp(spec["end"])
    expected_labels = int((end - begin).total_seconds() // 3600) + 1
    first = julian_label(hits[0])
    last = julian_label(hits[-1])
    if first != begin:
        raise RuntimeError(f"CALMET first step {first} != locked begin {begin}")
    if last != end - timedelta(hours=1):
        raise RuntimeError(f"CALMET last logged step {last} is not end-1h of {end}")
    if len(hits) != expected_labels - 1:
        raise RuntimeError(
            f"CALMET logged {len(hits)} steps, expected {expected_labels - 1} "
            f"for {expected_labels} hourly labels"
        )
    return {
        "hourly_labels": expected_labels,
        "calmet_logged_steps": len(hits),
        "first_step_utc": first.isoformat(),
        "last_logged_step_utc": last.isoformat(),
    }


def verify_error_keywords(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    patterns = [
        r"^\s*ERROR IN SUBR\.",
        r"\bFATAL\b",
        r"\bABORT\b",
        r"segmentation fault",
        r"forrtl:\s*severe",
        r"cannot open",
    ]
    found = [p for p in patterns if re.search(p, text, flags=re.IGNORECASE | re.MULTILINE)]
    if found:
        raise RuntimeError(f"{path.name} contains error keywords: {found}")
    return found


def verify_calmet_dat_header(met_dat: Path, spec: dict, nx: int, ny: int, nz: int) -> dict:
    """Verify the CALMET.DAT 2.1 dataset identity and its embedded control image."""
    head = met_dat.read_bytes()[:1 << 20]
    if b"CALMET.DAT" not in head:
        raise RuntimeError("met.dat does not carry the CALMET.DAT marker")
    if b"2.1" not in head:
        raise RuntimeError("met.dat is not the CALMET.DAT 2.1 dataset version")
    text = head.decode("latin-1")
    expected = {
        "NX": str(nx),
        "NY": str(ny),
        "NZ": str(nz),
        "IBYR": str(parse_cli_stamp(spec["begin"]).year),
        "IBDY": str(parse_cli_stamp(spec["begin"]).day),
        "IEYR": str(parse_cli_stamp(spec["end"]).year),
        "IEDY": str(parse_cli_stamp(spec["end"]).day),
    }
    found, mismatches = {}, {}
    for key, want in expected.items():
        got = parse_control_option(text, key)
        found[key] = got
        if got is None or got.split(",")[0].strip() != want:
            mismatches[key] = {"expected": want, "found": got}
    if mismatches:
        raise RuntimeError(
            f"embedded CALMET.INP image in met.dat disagrees with the locked run: "
            f"{json.dumps(mismatches, indent=2)}"
        )
    return {
        "bytes": met_dat.stat().st_size,
        "dataset_marker": "CALMET.DAT",
        "dataset_version": "2.1",
        "embedded_control": found,
        "sha256": sha256(met_dat),
    }


def verify_puff_con(puff_con: Path) -> dict:
    head = puff_con.read_bytes()[:2048]
    text = head.decode("latin-1")
    match = re.search(r"CONC\.DAT\s+(\d+\.\d+)", text)
    if not match:
        raise RuntimeError("puff.con is not a recognised CALPUFF concentration dataset")
    return {"bytes": puff_con.stat().st_size, "dataset_version": match.group(1)}


# --------------------------------------------------------------------------- #
# Freeze manifest
# --------------------------------------------------------------------------- #

def hash_tree(root: Path, relative_root: Path) -> list[dict]:
    items = []
    for path in sorted(relative_root.rglob("*")):
        if not path.is_file():
            continue
        if "logs" in path.relative_to(relative_root).parts:
            continue
        items.append(
            {
                "path": str(path.relative_to(relative_root)),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    return items


def render_capture_markdown(manifest: dict) -> str:
    spec = manifest["spec"]
    lines = [
        "# Hefei 2022 6-day 5 km reference case: capture register",
        "",
        f"Generated: {manifest['generated_utc']}",
        f"Status: **REFERENCE_CAPTURED** (machine generated by "
        f"`scripts/capture_hefei_2022_reference_case.py`)",
        "",
        "This register freezes the artifacts of the locked reference case described in",
        "`docs/reconstruction_cpp/HEFEI_2022_REFERENCE_CASE.md`. It is the real-data",
        "acceptance baseline for P6 (CALMET reconstruction) and P7 (CALPUFF reconstruction):",
        "every number below was produced on `lhy-desktop` by the frozen original Fortran",
        "binaries, not by the C++ reconstruction.",
        "",
        "## Locked geometry and period as executed",
        "",
        "| Property | Value |",
        "|---|---|",
        f"| Case directory | `project/cases/{manifest['case_name']}` |",
        f"| Centre (stack) | {spec['stack_latitude_deg']}N, {spec['stack_longitude_deg']}E |",
        f"| Grid | {manifest['grid']['nx']} x {manifest['grid']['ny']} cells, "
        f"{spec['resolution_km']:g} km, NZ={spec['nz']} |",
        f"| Grid origin XORIGKM/YORIGKM (km) | {manifest['grid']['xref_km']}, {manifest['grid']['yref_km']} |",
        f"| ZFACE (m) | {', '.join(str(int(z)) for z in spec['zface_m'])} |",
        f"| Period (UTC) | {spec['begin']} -> {spec['end']} |",
        f"| Hourly labels produced | {manifest['verification']['calmet']['hourly_labels']} |",
        f"| Capture host | {manifest['host']['platform']}, {manifest['host']['processor_count']} CPUs, "
        f"python {manifest['host']['python']} |",
        f"| Total stage time (s) | {manifest['stage_total_s']} |",
        "",
        "## Stage commands (original Fortran binaries)",
        "",
        "| # | Stage | Command | rc | seconds |",
        "|---|---|---|---|---|",
    ]
    for record in manifest["stages"]:
        lines.append(
            f"| {record['stage']} | {record['module']} | `{record['command']}` | "
            f"{record['returncode']} | {record['elapsed_s']} |"
        )
    lines += [
        "",
        "## Frozen artifacts (SHA-256)",
        "",
        "| Artifact | Bytes | SHA-256 |",
        "|---|---|---|",
    ]
    for item in manifest["artifacts"]:
        lines.append(f"| `{item['path']}` | {item['bytes']} | `{item['sha256']}` |")
    lines += [
        "",
        "## Control decks (SHA-256 of the rendered decks that were executed)",
        "",
        "| Deck | SHA-256 |",
        "|---|---|",
    ]
    for name, digest in manifest["control_decks"].items():
        lines.append(f"| `{name}` | `{digest}` |")
    lines += [
        "",
        "## Original toolchain identity",
        "",
        "Binaries (built from the frozen vendor sources by `scripts/build_native_linux_x86_64.sh`):",
        "",
        "| Binary | SHA-256 |",
        "|---|---|",
    ]
    for name, digest in manifest["binaries"].items():
        lines.append(f"| `{name}.x` | `{digest}` |")
    lines += [
        "",
        "Vendor sources:",
        "",
        "| Source | SHA-256 |",
        "|---|---|",
    ]
    for name, digest in manifest["vendor_sources"].items():
        lines.append(f"| `{name}` | `{digest}` |")
    lines += [
        "",
        "Input data identity:",
        "",
        "| Input | Bytes | SHA-256 |",
        "|---|---|---|",
    ]
    for name, item in manifest["inputs"].items():
        lines.append(f"| `{name}` | {item['bytes']} | `{item['sha256']}` |")
    lines += [
        "",
        "## Selected meteorological stations",
        "",
        "```json",
        json.dumps(manifest.get("selected_stations", {}), indent=2),
        "```",
        "",
        "## Verification performed by the capture script",
        "",
        "```json",
        json.dumps(manifest["verification"], indent=2),
        "```",
        "",
        "## Known deviations from the locked specification",
        "",
    ]
    for note in manifest["deviations"]:
        lines.append(f"- {note}")
    lines += [
        "",
        "## Downstream consumption",
        "",
        "`MET_SHA256` pins the file named by `P7_FROZEN_2022_MET_DAT` (the CALMET.DAT 2.1",
        "binary); `PUFF_SHA256` pins the file named by `PUFF_INP` (the rendered CALPUFF deck).",
        "",
        "- `P7_FROZEN_2022_MET_DAT` = `" + manifest["actions_variables"]["P7_FROZEN_2022_MET_DAT"] + "`",
        "- `PUFF_INP` = `" + manifest["actions_variables"]["PUFF_INP"] + "`",
        "- `MET_SHA256` = `" + manifest["actions_variables"]["MET_SHA256"] + "`",
        "- `PUFF_SHA256` = `" + manifest["actions_variables"]["PUFF_SHA256"] + "`",
        "",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--case-name", default="hefei5km_2022_reference_case_20261011")
    parser.add_argument("--year", type=int, default=2022)
    parser.add_argument("--begin", default=SPEC["begin"], help="YYYYMMDD-HHMMSS (UTC)")
    parser.add_argument("--end", default=SPEC["end"], help="YYYYMMDD-HHMMSS (UTC)")
    parser.add_argument("--domain-km", type=float, default=SPEC["domain_km"])
    parser.add_argument("--resolution-km", type=float, default=SPEC["resolution_km"])
    parser.add_argument("--nz", type=int, default=SPEC["nz"])
    parser.add_argument("--crop-info", default=SPEC["crop_info"])
    parser.add_argument("--pstop", type=float, default=SPEC["pstop_hpa"])
    parser.add_argument(
        "--upperair-station-id",
        default=SPEC["upperair_station_id"],
        help="IGRA station pinned for the case (matches the project's 2022 Hefei capture evidence)",
    )
    parser.add_argument(
        "--build-missing-binaries",
        action="store_true",
        help="Rebuild any missing bin/linux-x86_64/*.x from the tracked vendor sources",
    )
    parser.add_argument("--seconds-per-year", type=float, default=365.0 * 24.0 * 3600.0)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--binaries-dir", default=str(Path("bin") / "linux-x86_64"))
    parser.add_argument("--manifest", default=None, help="Manifest path (default <case>/run_manifest.json)")
    parser.add_argument("--doc-out", default=None, help="Optional Markdown register path")
    parser.add_argument("--reuse-case", action="store_true", help="Do not fail if the case already exists")
    args = parser.parse_args()

    spec = dict(SPEC)
    spec["begin"] = args.begin
    spec["end"] = args.end
    spec["domain_km"] = args.domain_km
    spec["resolution_km"] = args.resolution_km
    spec["nz"] = args.nz
    spec["pstop_hpa"] = args.pstop
    spec["upperair_station_id"] = args.upperair_station_id
    spec["crop_info"] = args.crop_info

    crop_path = (ROOT / args.crop_info).resolve()
    crop = json.loads(crop_path.read_text(encoding="utf-8"))
    if crop["utm_crs"] != "EPSG:32650" or float(crop["study_side_km"]) != spec["domain_km"]:
        raise RuntimeError(f"unexpected crop for the locked case: {crop_path}")

    station_lat = spec["stack_latitude_deg"]
    station_lon = spec["stack_longitude_deg"]
    if abs(float(crop["center"]["lat"]) - station_lat) > 1e-9 or abs(
        float(crop["center"]["lon"]) - station_lon
    ) > 1e-9:
        raise RuntimeError("crop centre does not match the locked stack position")

    emission_bq_s = hefei_emission_bq_per_s(spec["hto_bq_per_year"], args.seconds_per_year)

    case_dir = ROOT / "project" / "cases" / args.case_name
    if case_dir.exists() and not args.reuse_case:
        raise SystemExit(f"case directory already exists: {case_dir} (use --reuse-case to reuse)")
    create_case(case_dir, args.case_name, spec, emission_bq_s)

    from engine.core.case_manager import set_current_case

    set_current_case(args.case_name)

    env = dict(os.environ)
    env.setdefault("PYTHONPATH", str(ROOT))
    runner = StageRunner(case_dir, args.python, env)

    binary_dir = (ROOT / args.binaries_dir).resolve()
    binary_dir.mkdir(parents=True, exist_ok=True)
    missing_binaries = [name for name in BINARY_NAMES if not (binary_dir / f"{name}.x").is_file()]
    if missing_binaries and args.build_missing_binaries:
        print(f"[toolchain] rebuilding from tracked vendor sources: {missing_binaries}", flush=True)
        print(f"[toolchain] built: {build_binaries(binary_dir)}", flush=True)
        missing_binaries = [name for name in BINARY_NAMES if not (binary_dir / f"{name}.x").is_file()]
    if missing_binaries:
        raise SystemExit(
            f"original binaries missing in {binary_dir}: {missing_binaries}; "
            "rerun with --build-missing-binaries to rebuild them from the tracked vendor sources"
        )

    crop_terrain_dir = (ROOT / crop["terrain"][0]["output"]).resolve().parent
    crop_landuse = (ROOT / crop["landuse"]["generic"]["output"]).resolve()

    runner.run(1, "configure_grid_cmn", "engine.preprocess.grid.configure_grid_cmn", [])
    runner.run(
        2,
        "terrel",
        "engine.preprocess.terrel.auto_select_srtm_to_terrel",
        [
            "--grid", str(case_dir / "grid" / "grid.cmn"),
            "--terrel", str(case_dir / "geo" / "terrel" / "terrel.inp"),
            "--srtm-dir", str(crop_terrain_dir),
        ],
    )
    runner.run(
        3,
        "ctgproc",
        "engine.preprocess.ctgproc.auto_select_landuse_to_ctgproc",
        [
            "--grid", str(case_dir / "grid" / "grid.cmn"),
            "--ctgproc", str(case_dir / "geo" / "ctgproc" / "ctgproc.inp"),
            "--landuse-file", str(crop_landuse),
            "--lulc-type", "GEN",
        ],
    )
    runner.run(
        4,
        "makegeo",
        "engine.preprocess.makegeo.auto_config_makegeo",
        [
            "--grid", str(case_dir / "grid" / "grid.cmn"),
            "--makegeo", str(case_dir / "geo" / "makegeo" / "makegeo.inp"),
            "--ludat", str(case_dir / "geo" / "ctgproc" / "lu.dat"),
            "--terrdat", str(case_dir / "geo" / "terrel" / "terrel.dat"),
        ],
    )
    runner.run(
        5,
        "read62",
        "engine.preprocess.read62_upperair_data.run_upperair_pipeline",
        ["--python", args.python, "--pstop", repr(spec["pstop_hpa"])],
    )
    runner.run(
        6,
        "isd_download",
        "native_cpp.modules.p5_smerge.data_prep.download_isd_by_grid",
        [
            "--year", str(args.year),
            "--stack-lat", repr(spec["stack_latitude_deg"]),
            "--stack-lon", repr(spec["stack_longitude_deg"]),
            "--timeout", "30",
            "--retries", "2",
        ],
    )
    runner.run(
        7,
        "smerge_prepare",
        "native_cpp.modules.p5_smerge.data_prep.prepare_inputs",
        [
            "--expected-year", str(args.year),
            "--skip-download",
            "--write-legacy-control",
            "--execute",
        ],
    )
    runner.run(
        8,
        "smerge",
        "native_cpp.modules.p5_smerge.data_prep.run_smerge_and_monitor",
        [],
    )
    runner.run(9, "calmet", "engine.run_met.run_met", ["--case", args.case_name])
    runner.run(10, "calpuff", "engine.run_puff.run_puff", ["--case", args.case_name])

    # ---------------- verification -----------------------------------------
    grid_text = (case_dir / "grid" / "grid.cmn").read_text(encoding="utf-8")
    nx = int(float(parse_control_option(grid_text, "NX")))
    ny = int(float(parse_control_option(grid_text, "NY")))
    nz = int(float(parse_control_option(grid_text, "NZ")))
    if (nx, ny, nz) != (50, 50, spec["nz"]):
        raise RuntimeError(f"grid.cmn is not the locked grid: NX={nx} NY={ny} NZ={nz}")

    missing = [
        rel.format(year=args.year)
        for rel in REQUIRED_ARTIFACTS
        if not (case_dir / rel.format(year=args.year)).is_file()
    ]
    if missing:
        raise RuntimeError(f"required artifacts missing: {missing}")

    verification = {
        "met_control_options": verify_control_options(
            case_dir / "run" / "met" / "met.inp", MET_LOCKED_OPTIONS, "CALMET"
        ),
        "puff_control_options": verify_control_options(
            case_dir / "run" / "puff" / "puff.inp", PUFF_LOCKED_OPTIONS, "CALPUFF"
        ),
        "calmet": verify_calmet_hourly_coverage(case_dir / "run" / "met" / "met_runtime.log", spec),
        "calmet_errors": verify_error_keywords(case_dir / "run" / "met" / "met.lst"),
        "calmet_dat": verify_calmet_dat_header(case_dir / "run" / "met" / "met.dat", spec, nx, ny, nz),
        "calpuff_errors": verify_error_keywords(case_dir / "run" / "puff" / "puff.lst"),
        "puff_con": verify_puff_con(case_dir / "run" / "puff" / "puff.con"),
    }
    if int(verification["calmet"]["hourly_labels"]) != spec["expected_hour_labels"]:
        raise RuntimeError(
            f"hourly label count {verification['calmet']['hourly_labels']} != "
            f"{spec['expected_hour_labels']}"
        )

    # ---------------- freeze -------------------------------------------------
    artifacts = hash_tree(case_dir, case_dir)
    control_decks = {
        rel: sha256(case_dir / rel)
        for rel in (
            "geo/terrel/terrel.inp",
            "geo/ctgproc/ctgproc.inp",
            "geo/makegeo/makegeo.inp",
            "run/read62/read62.inp",
            "run/smerge/smerge.inp",
            "run/met/met.inp",
            "run/puff/puff.inp",
        )
    }
    binaries = {
        name: sha256(binary_dir / f"{name}.x")
        for name in ("terrel", "ctgproc", "makegeo", "read62", "smerge", "met", "puff")
    }
    selected_stations = {}
    upperair_used = case_dir / "met" / "upperair" / str(args.year) / "upperair_station_used_list.txt"
    if upperair_used.is_file():
        selected_stations["upperair_station_used_list"] = upperair_used.read_text(
            encoding="utf-8", errors="replace"
        ).strip().splitlines()
    selection_json = case_dir / "met" / "surface" / "isd_raw" / f"station_selection_{args.year}.json"
    if selection_json.is_file():
        payload = json.loads(selection_json.read_text(encoding="utf-8"))
        selected_stations["surface_selection"] = {
            key: payload[key] for key in ("mode", "station_selection_case") if key in payload
        }
        selected_stations["surface_stations"] = [
            {
                "sid": station.get("sid"),
                "ifstn": station.get("ifstn"),
                "name": station.get("name"),
                "lat": station.get("lat"),
                "lon": station.get("lon"),
                "relocated": station.get("relocated"),
                "wind_treatment": station.get("wind_treatment"),
            }
            for station in payload.get("stations", [])
        ]
    vendor_sources = {}
    for name, rel in VENDOR_SOURCES.items():
        path = ROOT / rel
        if not path.is_file():
            raise RuntimeError(f"vendor source missing: {rel}")
        vendor_sources[name] = sha256(path)
    inputs = {}
    for name, rel in (
        ("crop_info", args.crop_info),
        ("terrain_geotiff", str(crop["terrain"][0]["output"])),
        ("landuse_generic", str(crop["landuse"]["generic"]["output"])),
    ):
        path = (ROOT / rel).resolve()
        inputs[name] = {"path": rel, "bytes": path.stat().st_size, "sha256": sha256(path)}

    met_dat_rel = f"project/cases/{args.case_name}/run/met/met.dat"
    puff_inp_rel = f"project/cases/{args.case_name}/run/puff/puff.inp"
    stage_total_s = round(sum(r["elapsed_s"] for r in runner.records), 3)
    manifest = {
        "case_name": args.case_name,
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "host": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor_count": os.cpu_count(),
            "python": sys.version.split()[0],
            "capture_command": " ".join(sys.argv),
        },
        "stage_total_s": stage_total_s,
        "spec": spec,
        "emission_bq_per_s": emission_bq_s,
        "seconds_per_year": args.seconds_per_year,
        "grid": {
            "nx": nx,
            "ny": ny,
            "nz": nz,
            "xref_km": parse_control_option(grid_text, "XREFKM"),
            "yref_km": parse_control_option(grid_text, "YREFKM"),
            "dgridkm": parse_control_option(grid_text, "DGRIDKM"),
            "iutmzn": parse_control_option(grid_text, "IUTMZN"),
            "datum": parse_control_option(grid_text, "DATUM"),
        },
        "stages": runner.records,
        "control_decks": control_decks,
        "binaries": binaries,
        "toolchain": {
            "build_recipe": {
                "compiler": "gfortran-11",
                "common_flags": list(COMMON_FFLAGS),
                "legacy72_flags": list(LEGACY72_FFLAGS),
                "calpuff_flags": list(PUFF_FFLAGS),
                "include_handling": "lower-case symlink alias tree per vendor directory passed with -I",
            },
            "built_missing_binaries": bool(args.build_missing_binaries),
            "note": (
                "byte identity of the .x files depends on compiler version and build paths; "
                "the vendor source hashes below are the frozen provenance"
            ),
        },
        "selected_stations": selected_stations,
        "vendor_sources": vendor_sources,
        "inputs": inputs,
        "verification": verification,
        "artifacts": artifacts,
        "actions_variables": {
            "P7_FROZEN_2022_MET_DAT": met_dat_rel,
            "PUFF_INP": puff_inp_rel,
            "MET_SHA256": verification["calmet_dat"]["sha256"],
            "PUFF_SHA256": control_decks["run/puff/puff.inp"],
        },
        "deviations": [],
    }

    # ---- documented deviations from the locked specification ----------------
    exact_x0 = float(crop["center"]["utm_e"]) - spec["domain_km"] / 2.0
    exact_y0 = float(crop["center"]["utm_n"]) - spec["domain_km"] / 2.0
    written_x0 = float(parse_control_option(grid_text, "XREFKM"))
    written_y0 = float(parse_control_option(grid_text, "YREFKM"))
    puff_text = (case_dir / "run" / "puff" / "puff.inp").read_text(encoding="utf-8", errors="ignore")
    source_match = re.search(r"!\s*X\s*=\s*([-+0-9.Ee]+)\s*,\s*([-+0-9.Ee]+)", puff_text)
    written_source = (float(source_match.group(1)), float(source_match.group(2))) if source_match else (None, None)
    manifest["deviations"] = [
        (
            "Grid origin precision: the locked absolute geometry is "
            f"XORIGKM={exact_x0!r} km, YORIGKM={exact_y0!r} km (crop centre minus half domain). "
            f"The canonical control renderers write 3 decimals, so every deck used "
            f"XORIGKM={written_x0} km, YORIGKM={written_y0} km; the SW corner therefore "
            f"differs by {abs(written_x0 - exact_x0) * 1000.0:.4f} m in x and "
            f"{abs(written_y0 - exact_y0) * 1000.0:.4f} m in y from the exact spec. "
            "Terrain, landuse, CALMET and CALPUFF all read this same rounded origin, so the "
            "captured chain is internally consistent; the residual offset is documented, not resolved."
        ),
        (
            "Point-source coordinates are written to 3 decimals by the CALPUFF renderer: "
            f"deck ({written_source[0]}, {written_source[1]}) km versus the exact crop centre "
            f"({float(crop['center']['utm_e'])!r}, {float(crop['center']['utm_n'])!r}) km, i.e. "
            f"{abs(written_source[0] - float(crop['center']['utm_e'])) * 1000.0:.4f} m / "
            f"{abs(written_source[1] - float(crop['center']['utm_n'])) * 1000.0:.4f} m."
        ),
        (
            f"Annual HTO release {spec['hto_bq_per_year']:g} Bq/year is injected with CALPUFF "
            f"IPTU=8 (Bq/s) at {emission_bq_s!r} Bq/s, assuming "
            f"{args.seconds_per_year:g} s/year. The locked document leaves the "
            "'release window/hourly rate' as TBD, so the year length is an explicit choice, "
            "not a verified legacy control."
        ),
        (
            "Stack base elevation is 0.0 m (ground datum) because the locked document lists "
            "'datum and original height representation' as TBD. The terrain elevation at the "
            "stack cell is available in geo/makegeo/geo.dat for a later datum decision."
        ),
        (
            "NM3D=0 with IUPWND=-1: with no MM4/MM5/3D.DAT input and NOOBS=0 the initial guess "
            "field is built from the single upper-air sounding; this combination was not "
            "independently verified against the vendor documentation, only exercised end to end."
        ),
        (
            "IKINE=0 / IFRADJ=1 / ISLOPE=1 / IEXTRP=-4 are the values of the real user deck and "
            "of engine/templates/met.inp; the locked document records them as deck values, not as "
            "values derived from a primary CTEAS specification."
        ),
    ]

    manifest_path = Path(args.manifest) if args.manifest else case_dir / "run_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    if args.doc_out:
        doc_path = (ROOT / args.doc_out).resolve()
        doc_path.parent.mkdir(parents=True, exist_ok=True)
        doc_path.write_text(render_capture_markdown(manifest), encoding="utf-8")
        print(f"[doc] {doc_path}")

    print("\nREFERENCE_CAPTURE_COMPLETE")
    print(json.dumps({
        "case": args.case_name,
        "met_dat": manifest["actions_variables"]["P7_FROZEN_2022_MET_DAT"],
        "met_dat_sha256": manifest["actions_variables"]["MET_SHA256"],
        "puff_inp": manifest["actions_variables"]["PUFF_INP"],
        "puff_inp_sha256": manifest["actions_variables"]["PUFF_SHA256"],
        "puff_con_sha256": sha256(case_dir / "run" / "puff" / "puff.con"),
        "hourly_labels": verification["calmet"]["hourly_labels"],
        "artifacts": len(artifacts),
        "manifest": str(manifest_path),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
