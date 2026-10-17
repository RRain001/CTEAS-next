#!/usr/bin/env python3
"""CTEAS local gate — authoritative verification without GitHub Actions.

GitHub-hosted workflow runs are no longer used for these tracks (Actions is
disabled repository-wide).  This script replays the same commands the workflow
files specify, on lhy-desktop, from a pinned git ref, and writes a
machine-readable evidence file.  The workflow files stay in the repository as
the *specification* of each gate; each track records its ``source_workflow``,
and when a workflow changes the matching step list here must change with it.

Design rules:
  * fail-closed: a non-zero step makes the gate FAIL.
  * a step whose declared input is absent is reported BLOCKED — never silently
    skipped, never counted as a pass.
  * metrics are parsed from real command output only; no fabricated passes.
  * evidence is written for PASS, FAIL and BLOCKED alike.

Usage (on lhy-desktop, inside a checkout of this repository):
    python3 scripts/local_gate.py --track p6e
    python3 scripts/local_gate.py --track p7 --ref origin/main
    python3 scripts/local_gate.py --list
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import uuid

GATE_ROOT = pathlib.Path(os.environ.get("CTEAS_GATE_ROOT", "/home/lhy/gate"))
CXX = os.environ.get("CTEAS_GATE_CXX", "g++-12")
FC = os.environ.get("CTEAS_GATE_FC", "gfortran-11")
VENDOR_CALMET = "engine/vendor/src/CALMET_v6.5.0_L150223"
CASE_2022 = "project/cases/hefei5km_2022_reference_case_20261011"
MET_DAT = CASE_2022 + "/run/met/met.dat"
PUFF_INP = CASE_2022 + "/run/puff/puff.inp"
MET_SHA = "b1823cda92280888d70b00961ab39486036a3086e18637fff21efb4f4b237d30"
PUFF_SHA = "cf5cca70cb75b1aac92f86fdc100500e901a8b904d056c73b2330175793532bc"
CROP_TERRAIN = "calpuff_terrain_and_landuse_data_crop/hefei_5km/china_srtm/srtm_60_06_hefei_5km.tif"
CROP_LANDUSE = "calpuff_terrain_and_landuse_data_crop/hefei_5km/eurasia_asia_landuse/eausgs2_0la_hefei_5km.generic.txt"

# Each track mirrors one workflow file (kept in the repo as the spec).
TRACKS: dict[str, dict] = {
    "p6d": {
        "branch": "origin/codex/p6d9a-wind1-inter2-diagno-bridge-20261011",
        "source_workflow": ".github/workflows/p6d9a-original-chained-diagno-parity.yml",
        "steps": [
            {"cmd": ["cmake", "-S", "native_cpp/modules/p6_calmet", "-B", "{build}", "-DCMAKE_BUILD_TYPE=Debug"]},
            {"cmd": ["cmake", "--build", "{build}", "--parallel", "24"]},
            {"cmd": ["ctest", "--test-dir", "{build}", "--output-on-failure"]},
            {"cmd": ["python3", "native_cpp/modules/p6_calmet/reference/compare_original_diagno_d9a_chained.py",
                     "--vendor", VENDOR_CALMET, "--cpp", "{build}/cteas_p6_d9a_source_trace",
                     "--out", "{out}/p6d-chained"],
             "requires": [VENDOR_CALMET]},
            {"cmd": ["python3", "native_cpp/modules/p6_calmet/reference/compare_original_similt_profile.py",
                     "--vendor", VENDOR_CALMET, "--cpp", "{build}/cteas_p6_similt_profile",
                     "--out", "{out}/p6d-verdict-similt"],
             "requires": [VENDOR_CALMET]},
            # Real-case producer + its two original-source verdicts (requested by
            # the P6D track in PR #23; comparators compile the unchanged original
            # routines with gfortran and are fail-closed).
            {"cmd": ["{build}/cteas_p6_realcase_wind_field", "--case", CASE_2022,
                     "--out", "{out}/p6d-realcase", "--fixtures", "{out}/p6d-realcase-fixtures"],
             "requires": [CASE_2022]},
            {"cmd": ["python3", "native_cpp/modules/p6_calmet/reference/compare_original_d9a_realcase_step_one.py",
                     "--vendor", VENDOR_CALMET, "--fields", "{out}/p6d-realcase",
                     "--fixtures", "{out}/p6d-realcase-fixtures", "--out", "{out}/p6d-verdict-step-one"],
             "requires": [VENDOR_CALMET, CASE_2022]},
            {"cmd": ["python3", "native_cpp/modules/p6_calmet/reference/compare_original_d9a_realcase_blend.py",
                     "--vendor", VENDOR_CALMET, "--fields", "{out}/p6d-realcase",
                     "--fixtures", "{out}/p6d-realcase-fixtures", "--out", "{out}/p6d-verdict-blend"],
             "requires": [VENDOR_CALMET, CASE_2022]},
        ],
    },
    "p6e": {
        "branch": "origin/codex/cteas-p6e-surface-boundary-layer-20261011",
        "source_workflow": ".github/workflows/p6e-solar-source-parity.yml",
        "steps": [
            {"cmd": ["cmake", "-S", "native_cpp/modules/p6_calmet/p6e", "-B", "{build}",
                     "-DCMAKE_BUILD_TYPE=Debug", "-DCMAKE_CXX_COMPILER={cxx}"]},
            {"cmd": ["cmake", "--build", "{build}", "--parallel", "24"]},
            {"cmd": ["ctest", "--test-dir", "{build}", "--output-on-failure"]},
        ],
    },
    "p6f": {
        # CALMET.DAT 2.1 C++ writer. No workflow spec exists (Actions is disabled);
        # the track mirrors the P6E module shape plus the writer's own CTest set,
        # which must include the byte-identity round-trip against the frozen
        # 2022 reference met.dat.
        "branch": "origin/codex/p6f-calmet-dat21-writer-20261011",
        "source_workflow": "n/a (local gate track; see docs/reconstruction_cpp/P6_A_TO_G_SEQUENTIAL_EXECUTION_LEDGER.md P6F)",
        "steps": [
            {"cmd": ["cmake", "-S", "native_cpp/modules/p6_calmet/p6f", "-B", "{build}",
                     "-DCMAKE_BUILD_TYPE=Debug", "-DCMAKE_CXX_COMPILER={cxx}"]},
            {"cmd": ["cmake", "--build", "{build}", "--parallel", "24"]},
            # The original-CALPUFF read test is excluded here and run as its own
            # step below, where its Fortran toolchain and frozen inputs are
            # declared: a missing toolchain must be reported BLOCKED, never
            # silently skipped by ctest.
            {"cmd": ["ctest", "--test-dir", "{build}", "--output-on-failure",
                     "-E", "p6f_calmet_dat21_original_calpuff"]},
            # Roadmap clause "原版 P7 读取": rebuild the unmodified original
            # CALPUFF 7.2.1 from the tracked vendor sources and let it read the
            # file the writer produced (byte-identical case, changed-value case
            # and a structurally broken case). --no-tests=error keeps a silent
            # skip impossible.
            {"cmd": ["ctest", "--test-dir", "{build}", "--output-on-failure",
                     "--no-tests=error", "-R",
                     "p6f_calmet_dat21_original_calpuff"],
             "requires": ["engine/vendor/src/CALPUFF_v7.2.1_L150618/modules.for",
                          "engine/vendor/src/CALPUFF_v7.2.1_L150618/calpuff.for",
                          "project/cases/hefei5km_2022_reference_case_20261011/run/puff/puff.inp",
                          MET_DAT,
                          "project/cases/hefei5km_2022_reference_case_20261011/deliverables/puff/puff.con",
                          "project/cases/hefei5km_2022_reference_case_20261011/deliverables/puff/puff.lst",
                          "/usr/bin/gfortran-11"]},
        ],
    },
    "p7": {
        "branch": "origin/codex/cteas-p7-calpuff-20261011",
        "source_workflow": ".github/workflows/p7-calpuff-scoped-ci.yml",
        "steps": [
            {"cmd": ["cmake", "-S", "native_cpp/modules/p7_calpuff", "-B", "{build}",
                     "-DCMAKE_BUILD_TYPE=Debug", "-DCMAKE_CXX_COMPILER={cxx}"]},
            {"cmd": ["cmake", "--build", "{build}", "--parallel", "24"]},
            {"cmd": ["ctest", "--test-dir", "{build}", "--output-on-failure"]},
            {"cmd": ["python3", "native_cpp/modules/p7_calpuff/tests/sigma_fortran_parity_tests.py",
                     "--probe", "{build}/cteas_p7d_sigma_probe", "--repo-root", ".", "--require"]},
            {"cmd": ["{build}/cteas_p7d_sigma_probe", "--audit",
                     "project/cases/smoke5d_coldstart_20260701/run/puff/puff.inp"],
             "requires": ["project/cases/smoke5d_coldstart_20260701/run/puff/puff.inp"]},
            {"cmd": ["{build}/cteas_p7_calmet21_tests", "--met", MET_DAT],
             "requires": [MET_DAT]},
            {"cmd": ["{build}/cteas_p7f_drydep_probe", "--real-cell", MET_DAT, PUFF_INP, "25", "25",
                     "0"],
             "requires": [MET_DAT, PUFF_INP]},
            {"cmd": ["python3", "native_cpp/modules/p7_calpuff/tests/p7e_parity_tests.py",
                     "--probe", "{build}/cteas_p7e_probe", "--repo-root", ".",
                     "--require", "--require-case"]},
            {"cmd": ["python3", "native_cpp/modules/p7_calpuff/reference/p7k_source_anchor.py",
                     "--check", "native_cpp/modules/p7_calpuff/reference/p7k_source_anchor.json"]},
            {"cmd": ["python3", "native_cpp/modules/p7_calpuff/reference/p7m_source_anchor.py",
                     "--check", "native_cpp/modules/p7_calpuff/reference/p7m_source_anchor.json"]},
            {"cmd": ["python3", "native_cpp/modules/p7_calpuff/tests/p7m_parity_tests.py",
                     "--probe", "{build}/cteas_p7m_probe", "--repo-root", ".", "--require"]},
            {"cmd": ["{build}/cteas_p7m_probe", "--real-grid", MET_DAT, PUFF_INP, "0", "2.63e13",
                     "513.3846439571", "3533.7689269678", "70.8"],
             "requires": [MET_DAT, PUFF_INP]},
            {"cmd": ["python3", "native_cpp/modules/p7_calpuff/reference/p7n_source_anchor.py",
                     "--check", "native_cpp/modules/p7_calpuff/reference/p7n_source_anchor.json"]},
            {"cmd": ["python3", "native_cpp/modules/p7_calpuff/tests/p7n_parity_tests.py",
                     "--probe", "{build}/cteas_p7n_probe", "--repo-root", ".", "--require"]},
            {"cmd": ["{build}/cteas_p7n_probe", "--deck-rise", MET_DAT, PUFF_INP, "0",
                     "513.3846439571", "3533.7689269678", "70.8", "1.6", "17.26", "298.15"],
             "requires": [MET_DAT, PUFF_INP]},
            {"cmd": ["python3", "native_cpp/modules/p7_calpuff/reference/p7o_source_anchor.py",
                     "--check", "native_cpp/modules/p7_calpuff/reference/p7o_source_anchor.json"]},
            {"cmd": ["python3", "native_cpp/modules/p7_calpuff/tests/p7o_parity_tests.py",
                     "--probe", "{build}/cteas_p7o_probe", "--repo-root", ".", "--require"]},
            {"cmd": ["{build}/cteas_p7o_probe", "--deck-release", MET_DAT, PUFF_INP, "0",
                     "513.3846439571", "3533.7689269678", "70.8", "1.6", "17.26", "298.15",
                     "8.34e5"],
             "requires": [MET_DAT, PUFF_INP]},
            {"cmd": ["python3", "native_cpp/modules/p7_calpuff/reference/p7p_source_anchor.py",
                     "--check", "native_cpp/modules/p7_calpuff/reference/p7p_source_anchor.json"]},
            {"cmd": ["python3", "native_cpp/modules/p7_calpuff/tests/p7p_parity_tests.py",
                     "--probe", "{build}/cteas_p7p_probe", "--repo-root", ".", "--require"]},
            {"cmd": ["{build}/cteas_p7p_probe", "--deck-step", MET_DAT, PUFF_INP, "0",
                     "513.3846439571", "3533.7689269678", "70.8"],
             "requires": [MET_DAT, PUFF_INP]},
            {"cmd": ["python3", "native_cpp/modules/p7_calpuff/reference/p7q_source_anchor.py",
                     "--check", "native_cpp/modules/p7_calpuff/reference/p7q_source_anchor.json"]},
            {"cmd": ["python3", "native_cpp/modules/p7_calpuff/tests/p7q_parity_tests.py",
                     "--probe", "{build}/cteas_p7q_probe", "--repo-root", ".", "--require"]},
            {"cmd": ["{build}/cteas_p7q_probe", "--deck-sigma", MET_DAT, PUFF_INP, "0",
                     "513.3846439571", "3533.7689269678", "70.8", "1.0", "1.0", "100.0"],
             "requires": [MET_DAT, PUFF_INP]},
            {"cmd": ["python3", "native_cpp/modules/p7_calpuff/reference/p7r_source_anchor.py",
                     "--check", "native_cpp/modules/p7_calpuff/reference/p7r_source_anchor.json"]},
            {"cmd": ["python3", "native_cpp/modules/p7_calpuff/tests/p7r_parity_tests.py",
                     "--probe", "{build}/cteas_p7r_probe", "--repo-root", ".", "--require"]},
            {"cmd": ["{build}/cteas_p7r_probe", "--deck-terrain", MET_DAT, PUFF_INP, "0",
                     "513.3846439571", "3533.7689269678", "70.8", "89.152", "0.9", "1.396",
                     "0.02"],
             "requires": [MET_DAT, PUFF_INP]},
            {"cmd": ["python3", "native_cpp/modules/p7_calpuff/reference/p7s_source_anchor.py",
                     "--check", "native_cpp/modules/p7_calpuff/reference/p7s_source_anchor.json"]},
            {"cmd": ["python3", "native_cpp/modules/p7_calpuff/tests/p7s_parity_tests.py",
                     "--probe", "{build}/cteas_p7s_probe", "--repo-root", ".", "--require"]},
            {"cmd": ["{build}/cteas_p7s_probe", "--deck-relief", MET_DAT, PUFF_INP, "0",
                     "513.3846439571", "3533.7689269678", "70.8", "89.152", "0.9", "1.396",
                     "0.02"],
             "requires": [MET_DAT, PUFF_INP]},
            {"cmd": ["python3", "native_cpp/modules/p7_calpuff/reference/p7t_source_anchor.py",
                     "--check", "native_cpp/modules/p7_calpuff/reference/p7t_source_anchor.json"]},
            {"cmd": ["python3", "native_cpp/modules/p7_calpuff/tests/p7t_parity_tests.py",
                     "--probe", "{build}/cteas_p7t_probe", "--repo-root", ".", "--require"]},
            {"cmd": ["{build}/cteas_p7t_probe", "--deck-valley", MET_DAT, PUFF_INP, "0",
                     "513.3846439571", "3533.7689269678", "70.8"],
             "requires": [MET_DAT, PUFF_INP]},
            {"cmd": ["python3", "native_cpp/modules/p7_calpuff/reference/p7u_source_anchor.py",
                     "--check", "native_cpp/modules/p7_calpuff/reference/p7u_source_anchor.json"]},
            {"cmd": ["python3", "native_cpp/modules/p7_calpuff/reference/p7v_source_anchor.py",
                     "--check", "native_cpp/modules/p7_calpuff/reference/p7v_source_anchor.json"]},
            {"cmd": ["python3", "native_cpp/modules/p7_calpuff/tests/p7v_parity_tests.py",
                     "--probe", "{build}/cteas_p7v_probe", "--repo-root", ".", "--require"]},
            {"cmd": ["{build}/cteas_p7v_probe", "--deck-advection", MET_DAT, PUFF_INP, "0",
                     "513.3846439571", "3533.7689269678", "70.8", "89.152"],
             "requires": [MET_DAT, PUFF_INP]},
            {"cmd": ["python3", "native_cpp/modules/p7_calpuff/reference/p7w_source_anchor.py",
                     "--check", "native_cpp/modules/p7_calpuff/reference/p7w_source_anchor.json"]},
            {"cmd": ["python3", "native_cpp/modules/p7_calpuff/tests/p7w_parity_tests.py",
                     "--probe", "{build}/cteas_p7w_probe", "--repo-root", ".", "--require"]},
            {"cmd": ["python3", "native_cpp/modules/p7_calpuff/reference/p7x_source_anchor.py",
                     "--check", "native_cpp/modules/p7_calpuff/reference/p7x_source_anchor.json"]},
            {"cmd": ["{build}/cteas_p7x_tests"]},
            {"cmd": ["python3", "native_cpp/modules/p7_calpuff/tests/p7g_structure_tests.py",
                     "--probe", "{build}/cteas_p7e_probe", "--repo-root", "."]},
            {"cmd": ["{build}/cteas_p7w_probe", "--dgm-steps",
                     "native_cpp/modules/p7_calpuff/reference/dgm_p7_advection_2022/dgm_puffstep_hour202200100.bin",
                     MET_DAT, PUFF_INP, "513.3846439571", "3533.7689269678", "70.8", "1.6",
                     "17.26", "298.15"],
             "requires": [MET_DAT, PUFF_INP]},
            {"cmd": ["python3", "native_cpp/modules/p7_calpuff/tests/p7i_parity_tests.py",
                     "--probe", "{build}/cteas_p7i_tests", "--repo-root", ".", "--require"]},
            {"cmd": ["python3", "native_cpp/modules/p7_calpuff/tests/p7h_parity_tests.py",
                     "--probe", "{build}/cteas_p7e_probe", "--repo-root", ".", "--require"]},
            {"cmd": ["{build}/cteas_p7e_probe", "--real-grid", MET_DAT, PUFF_INP, "0", "2.63e13",
                     "513.3846439571", "3533.7689269678", "70.8"],
             "requires": [MET_DAT, PUFF_INP]},
            {"cmd": ["{build}/cteas_p7e_probe", "--receptors", PUFF_INP],
             "requires": [PUFF_INP]},
            {"cmd": ["{build}/cteas_p7e_probe", "--structure", CASE_2022 + "/run/puff/puff.con"],
             "requires": [CASE_2022 + "/run/puff/puff.con"]},
            {"cmd": ["python3", "native_cpp/modules/p7_calpuff/tests/drydep_parity_tests.py",
                     "--probe", "{build}/cteas_p7f_drydep_probe", "--repo-root", ".",
                     "--require", "--require-case"]},
            {"cmd": ["{build}/cteas_p7f_drydep_probe", "--audit", PUFF_INP],
             "requires": [PUFF_INP]},
            {"cmd": ["python3", "native_cpp/modules/p7_calpuff/tests/case_ledger_real_2023_tests.py",
                     "--binary", "{build}/cteas_p7_2022_case_ledger",
                     "--report", "{out}/p7-2022-ledger-refusal.json", "--require"],
             "requires": ["project/cases/smoke5d_coldstart_20260701/run/met/met.dat",
                          "project/cases/smoke5d_coldstart_20260701/run/puff/puff.inp"]},
            # ---- real 2022 frozen reference-case gates ----
            {"cmd": ["python3", "-c",
                     "import hashlib,pathlib,sys;"
                     "p=pathlib.Path('" + MET_DAT + "');"
                     "got=hashlib.sha256(p.read_bytes()).hexdigest();"
                     "print('P7_FROZEN_MET_SHA256_MATCH' if got=='" + MET_SHA + "' else 'P7_FROZEN_MET_SHA256_MISMATCH ' + got);"
                     "sys.exit(0 if got=='" + MET_SHA + "' else 1)"],
             "requires": [MET_DAT]},
            {"cmd": ["python3", "native_cpp/modules/p7_calpuff/reference/original_decode_calmet_hourly.py",
                     "--report", "{out}/p7-met21.json", MET_DAT],
             "requires": [MET_DAT]},
            {"cmd": ["{build}/cteas_p7_2022_case_ledger",
                     "--met", MET_DAT, "--control", PUFF_INP,
                     "--expect-met-sha256", MET_SHA, "--expect-control-sha256", PUFF_SHA,
                     "--report", "{out}/p7-2022-ledger.json"],
             "requires": [MET_DAT, PUFF_INP]},
            {"cmd": ["python3", "native_cpp/modules/p7_calpuff/reference/run_original_calpuff_reference.py",
                     "--control", PUFF_INP, "--met", MET_DAT, "--out", "{build}/p7-original-calpuff"],
             "requires": [PUFF_INP]},
        ],
    },
    "shared": {
        "branch": "origin/main",
        "source_workflow": ".github/workflows/cpp-input-contracts.yml",
        "steps": [
            {"cmd": ["cmake", "-S", "native_cpp", "-B", "{build}", "-DCMAKE_BUILD_TYPE=Debug",
                     "-DCMAKE_CXX_COMPILER={cxx}"]},
            {"cmd": ["cmake", "--build", "{build}", "--parallel", "24"]},
            {"cmd": ["ctest", "--test-dir", "{build}", "--output-on-failure"]},
            {"cmd": ["{build}/cteas_geo_inspect", "terrain", CROP_TERRAIN], "requires": [CROP_TERRAIN]},
            {"cmd": ["{build}/cteas_geo_inspect", "landuse", CROP_LANDUSE], "requires": [CROP_LANDUSE]},
        ],
        "expect_stdout": {"cteas_geo_inspect terrain": "width=90 height=77",
                          "cteas_geo_inspect landuse": "categories=38 points=57600"},
    },
}

CTEST_RE = re.compile(r"(\d+)% tests passed, (\d+) tests failed out of (\d+)")


def sh(cmd: list[str], cwd: pathlib.Path, env: dict[str, str]) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=str(cwd), env=env, capture_output=True, text=True, timeout=7200)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def main() -> int:
    ap = argparse.ArgumentParser(description="CTEAS local gate (no GitHub Actions)")
    ap.add_argument("--track", choices=sorted(TRACKS))
    ap.add_argument("--list", action="store_true", help="list tracks and their source workflows")
    ap.add_argument("--ref", default=None, help="git ref to gate (default: the track's branch)")
    ap.add_argument("--repo", default=".", help="driver checkout used for git operations")
    ap.add_argument("--report", default=None, help="evidence JSON path")
    ap.add_argument("--keep", action="store_true", help="keep the gate worktree in place")
    args = ap.parse_args()

    if args.list or not args.track:
        for name, t in sorted(TRACKS.items()):
            print(f"{name:<8} {t['branch']:<60} spec: {t['source_workflow']}")
        return 0

    track = TRACKS[args.track]
    ref = args.ref or track["branch"]
    repo = pathlib.Path(args.repo).resolve()
    wt = GATE_ROOT / "worktrees" / args.track
    out = GATE_ROOT / "evidence" / args.track
    build = wt / "build" / args.track
    out.mkdir(parents=True, exist_ok=True)
    wt.parent.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env.update({"CXX": CXX, "FC": FC, "GIT_TERMINAL_PROMPT": "0"})
    env["PATH"] = "/home/lhy/bin-fortran:" + env.get("PATH", "")

    started = time.time()
    evidence: dict = {
        "track": args.track, "ref": ref, "source_workflow": track["source_workflow"],
        "host": os.uname().nodename, "cxx": CXX, "fc": FC,
        "driver_sha": None, "gated_sha": None, "steps": [], "status": "FAIL",
        "failed_steps": [], "blocked_steps": [], "notes": [],
    }

    rc, driver_sha = sh(["git", "-C", str(repo), "rev-parse", "HEAD"], repo, env)
    evidence["driver_sha"] = driver_sha.strip() if rc == 0 else None

    # Retry: a concurrent fetch (e.g. an agent's own `git fetch` in the same
    # driver checkout) updates the same remote-tracking refs and can make this
    # fail with a ref-lock error.  Never report BLOCKED for that.
    for attempt in range(1, 4):
        rc, log = sh(["git", "-C", str(repo), "fetch", "--prune", "--quiet", "origin",
                      "+refs/heads/*:refs/remotes/origin/*"], repo, env)
        if rc == 0:
            break
        print(f"fetch attempt {attempt} failed (rc={rc}); retrying")
        time.sleep(2 * attempt)
    if rc != 0:
        print(f"BLOCKED: git fetch failed (rc={rc}): {log.strip()[:300]}")
        _write(args, evidence, started)
        return 2

    rc, sha = sh(["git", "-C", str(repo), "rev-parse", ref], repo, env)
    if rc != 0:
        print(f"BLOCKED: ref {ref} not found")
        _write(args, evidence, started)
        return 2
    evidence["gated_sha"] = gated_sha = sha.strip()
    # Per-run output directory: a re-run of the same ref must not collide with a
    # previous run's staged inputs (steps are required to fail closed on overwrite).
    # Per-run paths keyed by a random token, not by the gated sha: two concurrent
    # runs of the SAME ref (an agent gating its own tip plus the parent verifying
    # it) previously shared one worktree, and either run's cleanup removed the
    # other's checkout mid-build ("fatal error: opening dependency file").
    run_id = f"{os.getpid()}-{uuid.uuid4().hex[:8]}"
    out = GATE_ROOT / "evidence" / args.track / f"{gated_sha[:12]}-{run_id}"
    out.mkdir(parents=True, exist_ok=True)
    wt = GATE_ROOT / "worktrees" / f"{args.track}-{run_id}"
    build = wt / "build" / args.track

    if wt.exists():
        sh(["git", "-C", str(repo), "worktree", "remove", "--force", str(wt)], repo, env)
    rc, log = sh(["git", "-C", str(repo), "worktree", "add", "--detach", "--force", str(wt), gated_sha], repo, env)
    if rc != 0:
        print(f"BLOCKED: worktree add failed: {log.strip()[:300]}")
        _write(args, evidence, started)
        return 2

    fmt = {"build": str(build), "out": str(out), "cxx": CXX, "repo": str(wt)}
    for step in track["steps"]:
        cmd = [c.format(**fmt) for c in step["cmd"]]
        missing = [p for p in step.get("requires", []) if not (wt / p).exists()]
        if missing:
            entry = {"cmd": cmd, "status": "BLOCKED", "missing": missing}
            evidence["steps"].append(entry)
            evidence["blocked_steps"].append(f"{' '.join(cmd[:3])} (missing: {', '.join(missing)})")
            print(f"[BLOCK] {' '.join(cmd[:3])} … missing {', '.join(missing)}")
            continue
        t0 = time.time()
        rc, log = sh(cmd, wt, env)
        entry = {"cmd": cmd, "rc": rc, "seconds": round(time.time() - t0, 2),
                 "tail": "\n".join(log.strip().splitlines()[-12:]), "status": "ok" if rc == 0 else "FAIL"}
        m = CTEST_RE.search(log)
        if m:
            entry["ctest"] = {"pct": int(m.group(1)), "failed": int(m.group(2)), "total": int(m.group(3))}
            if m.group(2) != "0":
                entry["status"] = "FAIL"
        if entry["status"] == "FAIL":
            evidence["failed_steps"].append(" ".join(cmd[:3]))
            evidence["steps"].append(entry)
            print(f"[FAIL] {' '.join(cmd[:3])} … rc={rc}")
            break
        evidence["steps"].append(entry)
        print(f"[ok  ] {' '.join(cmd[:3])} … rc=0 ({entry['seconds']}s)")

    for marker, expected in track.get("expect_stdout", {}).items():
        step = next((s for s in evidence["steps"] if s.get("tail") and marker in " ".join(s["cmd"])), None)
        if step is None or expected not in step["tail"]:
            evidence["notes"].append(f"EXPECTED_STDOUT_MISSING: {marker!r} -> {expected!r}")
            evidence["failed_steps"].append(f"stdout contract: {marker}")

    if evidence["failed_steps"]:
        evidence["status"] = "FAIL"
    elif evidence["blocked_steps"]:
        evidence["status"] = "BLOCKED"
    else:
        evidence["status"] = "PASS"
    _write(args, evidence, started)

    if not args.keep and wt.exists():
        sh(["git", "-C", str(repo), "worktree", "remove", "--force", str(wt)], repo, env)

    print(f"LOCAL_GATE_{args.track.upper()}={evidence['status']} sha={gated_sha[:9]} "
          f"ok={len([s for s in evidence['steps'] if s.get('status') == 'ok'])} "
          f"blocked={len(evidence['blocked_steps'])} failed={len(evidence['failed_steps'])} "
          f"seconds={evidence['seconds']} report={evidence.get('report_path')}")
    return 0 if evidence["status"] == "PASS" else (1 if evidence["status"] == "FAIL" else 3)


def _write(args, evidence: dict, started: float) -> None:
    evidence["seconds"] = round(time.time() - started, 2)
    path = pathlib.Path(args.report) if args.report else (
        GATE_ROOT / "evidence" / f"{args.track}-{(evidence.get('gated_sha') or 'unknown')[:12]}.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(evidence, indent=2) + "\n")
    evidence["report_path"] = str(path)


if __name__ == "__main__":
    sys.exit(main())
