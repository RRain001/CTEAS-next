#!/usr/bin/env python3
"""P7M CTSG kernel: vendor source anchor and Fortran parity.

Builds the UNMODIFIED vendor units extracted by
reference/p7m_source_anchor.py together with reference/p7m_oracle_driver.f and
compares them against the ported kernel through the case matrices the probe
`cteas_p7m_probe` prints. Both sides see the same deterministic SIGTY/SIGTZ
stubs, so the comparison isolates the ported units (MUNU, IREG, BI, BJI, BJIL,
SIGMA, CTREC, PUFFC, LOWER, CTSG).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import pathlib
import re
import subprocess
import sys
import tempfile

REPO_FALLBACK = pathlib.Path(__file__).resolve().parents[4]
MODULE = "native_cpp/modules/p7_calpuff"
ANCHOR = f"{MODULE}/reference/p7m_source_anchor.json"
P7K_ANCHOR = f"{MODULE}/reference/p7k_source_anchor.json"
TOLERANCE_RELATIVE = 1.0e-5
TOLERANCE_ABSOLUTE = 1.0e-30

QUOTES = {
    "munu": ("nu=ATAN2(ybi,xbi)", "mu=ALOG((xbi/cosnu+ybi/sinnu)/rp1)",
             "snusq=(-capb+SQRT(capb*capb-four*ac))/twoa", "if(absx .LT. small) then"),
    "bi": ("exarg1=afac*argm**2", "if(exarg1 .LT. expmax) term1=EXP(-exarg1)",
           "b=two*(term1+term2)"),
    "bjil": ("dum=half/szsq", "arg1p=ak*(b1+b2+b3)", "arg2m=ak*(b1-b2+b3)",
             "bj=term1+term2"),
    "bji": ("dum=half/szesq", "akd4=ak*(dp+szosq*ej)",
            "if(exarg3 .LT. expmax) term3=EXP(-exarg3)*(ERF(d0+akd3)-ERF(akd3))"),
    "ireg": ("ireg=2", "elseif(x .GT. x23) then"),
    "sigma": ("if(s1 .EQ. s2) then", "a(1)=tstart+frac*tstep", "index=1",
              "tsec=AMAX1(zero,vty+(t-a(index)))", "call sigty(zero,dkm,tsec,sigma,dum1,dum2)"),
    "ctrec": ("xrc=xr-xc(ih)", "call ROTATE(xrf,yrf,-rotang,xre,yre)",
              "iregl=IREG(xrb,xob,-xob)", "t12rl=(xrb-xob)/(u*cbeta)"),
    "puffc": ("if(imode .EQ. 0) zpole=0.0", "dely=yrf-ypf",
              "co=q*(ERFDIF((t2mtr*dum),(t1mtr*dum)))/(tstep*four*pi*u*sy*sz)",
              "test=(fz-fzo)/fz"),
    "lower": ("side=SIGN(one,SIN(rnu+alfw))", "sz=SIGMA(2,zpuff,u,tup,sz1,tstart,sz2,tstep,szr,frac)",
              "if(szo .GE. 1.6*zlid) imix=1", "ak=one/(rt2*sz*szo*szp)", "fz=half*twofz"),
    "ctsg": ("if(tstart .EQ. tin) then", "twokz=(sz2**2-sz1**2)/tstep", "call CTPAR",
             "zrec=zrec-zgrid(ih)", "call PUFFC(0,zero,zero,cflat)", "conc=cu+cl"),
}

FIELD_ORDER = ("tstart tstep u q zlid frac sz1 sz2 sy1 sy2 szr syr szmn symn hd ubyn h zgrid xc yc "
               "rotflo rotang alfw beta cbeta d baxi r x12f x23f xob xp yp zpuff xpf ypf t12p "
               "timgp szimpg syimpg xr yr zrec isc ih ip").split()


def fail(message: str) -> None:
    print(f"P7M_SOURCE_PARITY=FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_script(path: pathlib.Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_quotes(text: str, quotes: tuple[str, ...], what: str) -> int:
    normalised = re.sub(r"\s+", "", text).lower()
    for quote in quotes:
        if re.sub(r"\s+", "", quote).lower() not in normalised:
            fail(f"{what}: quoted vendor statement is missing: {quote}")
    return len(quotes)


def compiler_major(compiler: str) -> int | None:
    run = subprocess.run([compiler, "-dumpversion"], capture_output=True, text=True)
    if run.returncode != 0:
        return None
    text = run.stdout.strip()
    return int(text) if text.isdigit() else None


def find_gfortran(explicit: str | None) -> str | None:
    candidates = [explicit] if explicit else ["gfortran-13", "gfortran-12", "gfortran-11", "gfortran"]
    for candidate in candidates:
        if candidate and subprocess.run(["which", candidate], capture_output=True).returncode == 0:
            return candidate
    return None


def state(**overrides) -> list[float]:
    base = dict(tstart=0.0, tstep=60.0, u=3.0, q=1.0e6, zlid=200.0, frac=1.0, sz1=2.0, sz2=20.0,
                sy1=5.0, sy2=60.0, szr=20.0, syr=60.0, szmn=1.0, symn=1.0, hd=50.0, ubyn=1.0,
                h=100.0, zgrid=0.0, xc=0.0, yc=0.0, rotflo=0.0, rotang=0.0, alfw=0.0, beta=0.0,
                cbeta=1.0, d=30.0, baxi=0.0005, r=0.5, x12f=-1000.0, x23f=1000.0, xob=0.0,
                xp=-100.0, yp=0.0, zpuff=50.0, xpf=100.0, ypf=0.0, t12p=-100.0, timgp=20.0,
                szimpg=2.0, syimpg=5.0, xr=300.0, yr=30.0, zrec=0.0, isc=4, ih=1, ip=1)
    base.update(overrides)
    return [float(base[name]) for name in FIELD_ORDER]


def munu_matrix() -> list[tuple]:
    rows = []
    for muflag in (0, 1):
        for x, y in ((-2.0, 0.0), (-0.5, 0.3), (0.0, 0.0), (0.5, 0.0), (1.5, -1.5), (0.2, 0.9),
                     (2.0, 2.0), (0.0, -1.0)):
            for ratio in (0.5, 1.0, 2.0):
                # The vendor MUNU is undefined (NaN) for an on-axis point inside
                # the ellipse of a non-circular hill; those combinations are
                # excluded from the parity matrix (the contract test documents
                # that the port reproduces the NaN).
                if abs(y) < 1.0e-6 and 1.0e-9 < abs(x) < math.sqrt(max(ratio * ratio - 1.0, 0.0)):
                    continue
                rows.append((muflag, x, y, ratio))
    return rows


def bi_matrix() -> list[tuple]:
    rows = []
    for afac in (0.001, 0.01, 0.1, 1.0):
        for argm in (-30.0, -5.0, 0.0):
            for argp in (5.0, 30.0, 100.0):
                rows.append((afac, argm, argp))
    return rows


def bji_matrix() -> list[tuple]:
    rows = []
    for szesq, szosq, szpsq in ((4.0, 1.0, 3.0), (25.0, 4.0, 9.0), (100.0, 0.0, 1.0)):
        for ak in (0.01, 0.2):
            for ej, eoimh, eoiph, d0, dm, dp in ((5.0, -1.0, 9.0, 0.5, 10.0, 30.0),
                                                 (40.0, 35.0, 45.0, -0.25, -5.0, 60.0)):
                rows.append((ak, dm, dp, d0, eoimh, eoiph, ej, szesq, szosq, szpsq))
    return rows


def bjil_matrix() -> list[tuple]:
    rows = []
    for szsq, szosq, szpsq in ((4.0, 1.0, 3.0), (25.0, 4.0, 9.0), (100.0, 0.0, 1.0)):
        for ak in (0.01, 0.5):
            for b1 in (10.0, 100.0):
                for ej, eoi in ((0.0, 5.0), (5.0, 20.0)):
                    rows.append((ak, b1, ej, eoi, szsq, szosq, szpsq))
    return rows


def sigma_matrix() -> list[tuple]:
    rows = []
    for itype in (1, 2):
        for zpuff in (10.0, 50.0):
            for ws in (2.0, 5.0):
                for t in (30.0, 120.0, 300.0):
                    for s1, tstart, s2, tstep, sr, frac in ((2.0, 0.0, 20.0, 60.0, 20.0, 1.0),
                                                            (5.0, 10.0, 60.0, 120.0, 30.0, 0.5),
                                                            (7.0, 0.0, 7.0, 60.0, 7.0, 1.0),
                                                            (1.0, 0.0, 40.0, 90.0, 15.0, 0.25)):
                        rows.append((itype, zpuff, ws, t, s1, tstart, s2, tstep, sr, frac))
    return rows


def ireg_matrix() -> list[tuple]:
    return [(-5.0, 0.0, 10.0), (0.0, 0.0, 10.0), (5.0, 0.0, 10.0), (15.0, 0.0, 10.0),
            (0.0, 0.0, 0.0), (-1.0, 0.0, 0.0), (1.0, 0.0, 0.0), (-300.0, 0.0, 0.0),
            (300.0, 0.0, 0.0), (-1000.0, -1000.0, 1000.0), (2000.0, -1000.0, 1000.0),
            (0.5, -0.5, 0.5)]


def state_matrix() -> list[list[float]]:
    """States that exercise the lower-segment, pole, flat and zero branches."""
    return [
        # (a) receptor below Hd, downwind of the hill centre: LOWER
        state(),
        # (b) receptor below Hd, upwind: PUFFC(2) with the stagnation offset
        state(xr=-300.0, yr=-40.0, d=40.0),
        # (c) receptor above Hd and upwind of the boundary: PUFFC(1) + LOWER
        state(zrec=60.0, x12f=400.0, x23f=1200.0),
        # (d) receptor above Hd and downwind: this one is REFUSED by the port
        #     (UPPER is not reconstructed) and is only used by the matrices that
        #     never reach the CTSG dispatch.
        state(zrec=60.0, xr=300.0),
        # (e) lid below Hd: CTSG leaves both branches at zero
        state(zlid=40.0, zrec=60.0, x12f=400.0),
        # (f) no hill at all (hd = 0) with a receptor on the base plane
        state(hd=0.0, zrec=0.0, x12f=1.0e9, x23f=1.0e9),
        # (g) sigma-z not growing: the BI branch of LOWER
        state(sz2=2.0, szr=2.0, szimpg=2.0, zpuff=2.0),
        # (h) puff mixed in the vertical: the RT2PI quirk branch
        state(szimpg=400.0, sz2=400.0, szr=400.0, sy2=600.0, syr=600.0),
        # (i) rotated hill frames
        state(rotflo=0.4, rotang=-0.3, beta=0.2, cbeta=0.980067, alfw=0.1),
        # (j) receptor on the axis, ellipse reset in CTREC
        state(xr=120.0, yr=0.0, d=0.0),
        # (k) low puff with a growing sigma-z: a well-scaled LOWER value
        state(zpuff=10.0, sz1=1.0, sz2=10.0, szr=10.0, szimpg=5.0, sy2=40.0, syr=40.0),
        # (l) no hill, receptor above the base plane and upwind: PUFFC(1) flat
        state(hd=0.0, zrec=5.0, x12f=1.0e9, x23f=1.0e9),
    ]


def ctsg_cases() -> list[tuple]:
    """(state, ipin, ihin, tin) rows; isame must hold so CTPAR is not needed."""
    rows = []
    for fields in state_matrix():
        # State (d) would need UPPER, which this port refuses by design.
        if fields[FIELD_ORDER.index("zrec")] > fields[FIELD_ORDER.index("hd")] and \
                fields[FIELD_ORDER.index("xr")] > fields[FIELD_ORDER.index("x12f")]:
            continue
        rows.append((fields, 1, 1, 0.0))
    return rows


def parse_rows(text: str) -> dict[int, list[float]]:
    rows: dict[int, list[float]] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("P7M_") or line.startswith("{"):
            continue
        fields = line.split()
        if len(fields) < 2:
            continue
        try:
            rows[int(fields[0])] = [float(value) for value in fields[1:]]
        except ValueError:
            continue
    return rows


def compare(what: str, oracle_rows: dict[int, list[float]], probe_rows: dict[int, list[float]],
            integer_columns: tuple[int, ...] = ()) -> tuple[int, float]:
    if sorted(oracle_rows) != sorted(probe_rows):
        fail(f"{what}: case sets differ (oracle {len(oracle_rows)}, probe {len(probe_rows)})")
    worst = 0.0
    worst_absolute = 0.0
    worst_case = 0
    for key in sorted(oracle_rows):
        want_row = oracle_rows[key]
        got_row = probe_rows[key]
        if len(want_row) != len(got_row):
            fail(f"{what} case {key}: column count {len(want_row)} vs {len(got_row)}")
        for column, (want, got) in enumerate(zip(want_row, got_row)):
            if column in integer_columns:
                if int(want) != int(got):
                    fail(f"{what} case {key} column {column}: oracle={want!r} probe={got!r}")
                continue
            if not math.isfinite(want) or not math.isfinite(got):
                fail(f"{what} case {key} column {column}: non-finite {want!r} / {got!r}")
            if abs(want - got) > max(TOLERANCE_RELATIVE * abs(want), TOLERANCE_ABSOLUTE):
                fail(f"{what} case {key} column {column}: oracle={want!r} probe={got!r}")
            worst_absolute = max(worst_absolute, abs(want - got))
            relative = abs(want - got) / max(abs(want), 1.0e-30)
            if relative > worst:
                worst = relative
                worst_case = key
    print(f"P7M_{what.upper()}_ORACLE_PARITY=PASS CASES={len(oracle_rows)} "
          f"COLUMNS={len(next(iter(oracle_rows.values())))} MISMATCHES=0 "
          f"TOLERANCE_REL={TOLERANCE_RELATIVE:.0e} MAX_REL={worst:.3e} "
          f"MAX_ABS={worst_absolute:.3e} WORST_CASE={worst_case}")
    return len(oracle_rows), worst


def run_pair(probe: pathlib.Path, oracle: pathlib.Path, mode: int, probe_flag: str,
             payload: str, cwd: pathlib.Path) -> tuple[dict, dict]:
    probe_run = subprocess.run([str(probe), probe_flag], input=payload, capture_output=True,
                               text=True)
    if probe_run.returncode != 0:
        fail(f"{probe_flag}: probe failed: {probe_run.stderr.strip()[-400:]}")
    oracle_run = subprocess.run([str(oracle)], input=f"{mode}\n{payload}", capture_output=True,
                                text=True, cwd=cwd)
    if oracle_run.returncode != 0:
        fail(f"oracle mode {mode} failed: {oracle_run.stderr.strip()[-400:]}")
    return parse_rows(oracle_run.stdout), parse_rows(probe_run.stdout)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", type=pathlib.Path, required=True, help="built cteas_p7m_probe")
    parser.add_argument("--repo-root", type=pathlib.Path, default=REPO_FALLBACK)
    parser.add_argument("--gfortran", help="explicit gfortran executable")
    parser.add_argument("--require", action="store_true",
                        help="fail instead of skipping when no Fortran compiler is available")
    args = parser.parse_args()
    if not args.probe.is_file():
        fail(f"probe binary missing: {args.probe}")
    repo = args.repo_root.resolve()
    ext = load_script(repo / MODULE / "reference/p7m_source_anchor.py", "p7m_anchor")
    vendor = repo / ext.VENDOR_SUBDIR
    manifest, spans = ext.extract(vendor)
    pinned = json.loads((repo / ANCHOR).read_text())
    if pinned != manifest:
        fail(f"vendor source drift: extracted spans/hashes differ from {ANCHOR}")
    p7k = json.loads((repo / P7K_ANCHOR).read_text())
    for name in ext.P7K_SHARED:
        mine, theirs = manifest["units"][name], p7k["units"][name]
        if (mine["first_line"], mine["last_line"], mine["sha256"]) != (
                theirs["first_line"], theirs["last_line"], theirs["sha256"]):
            fail(f"unit {name} disagrees with the P7K pin")
    print(f"P7M_SOURCE_ANCHOR=PASS VENDOR_SHA256={manifest['vendor_source_sha256']} "
          f"UNITS={','.join(sorted(manifest['units']))}")
    print(f"P7M_P7K_CROSSCHECK=PASS UNITS={len(ext.P7K_SHARED)}")
    quirk = manifest["const_initialisation"]
    if quirk["vendor_rt2pi_initialised"] or quirk["ctinit_sets_rt2pi"]:
        fail("the vendor /CONST/ RT2PI quirk no longer holds")
    print(f"P7M_CONST_RT2PI_QUIRK=PASS RT2PI_INITIALISED=false "
          f"CTINIT_LINES={quirk['ctinit_span']['first_line']}-{quirk['ctinit_span']['last_line']} "
          f"RT2PI_WRITERS={','.join(quirk['rt2pi_writers'])}")
    closure = manifest["call_closure"]
    if closure["flopuff"] != ["path", "path0", "upper"] or closure["upper"] != ["ctsg"]:
        fail(f"CTSG call closure changed: flopuff<-{closure['flopuff']} "
             f"upper<-{closure['upper']}")
    print("P7M_CALL_CLOSURE=PASS FLOPUFF_CALLERS=path,path0,upper UPPER_CALLERS=ctsg "
          "CTPAR_CALLERS=ctsg PATH_CALLERS=ctpar")
    # CTSG does NOT consume VCBAR in the vendor source: VCBAR's only caller is
    # DRY (the Gaussian-puff dry-removal branch), so "VCBAR -> CTSG" is not a
    # vendor call edge.
    references = manifest["function_reference_callers"]
    if references["vcbar"] != ["dry"]:
        fail(f"VCBAR function references changed: {references['vcbar']}")
    for unit in ("ctsg", "lower", "puffc", "ctrec", "sigma"):
        if "vcbar" in manifest["units"][unit]["calls"]:
            fail(f"{unit} unexpectedly calls VCBAR")
    print("P7M_VCBAR_CLOSURE=PASS VCBAR_FUNCTION_REFERENCE_CALLERS=dry "
          "CTSG_CONSUMES_VCBAR=false")
    quotes = 0
    for name, quoted in QUOTES.items():
        quotes += check_quotes(spans[name], quoted, name.upper())
    print(f"P7M_QUOTED_SOURCE_STATEMENTS=PASS COUNT={quotes}")

    compiler = find_gfortran(args.gfortran)
    if compiler is not None:
        major = compiler_major(compiler)
        if major is None or major < 10:
            if args.require:
                fail(f"gfortran {compiler} is older than 10 and cannot build the vendor oracle")
            print(f"P7M_FORTRAN_ORACLE=SKIPPED_TOO_OLD_COMPILER {compiler}")
            compiler = None
    if compiler is None:
        if args.require:
            fail("no Fortran compiler available but --require was given")
        print("P7M_FORTRAN_ORACLE=SKIPPED_WITHOUT_FORTRAN")
        return 0

    with tempfile.TemporaryDirectory(prefix="p7m-oracle-") as temporary:
        stage = pathlib.Path(temporary) / "stage"
        ext.stage(vendor, stage, manifest, spans)
        sources = sorted(str(path) for path in stage.glob("vendor_*.f"))
        binary = stage / "p7m_oracle"
        build = subprocess.run(
            [compiler, "-O0", "-std=legacy", "-ffixed-line-length-72", "-fallow-argument-mismatch",
             "-fno-automatic", f"-I{stage}", "-o", str(binary), *sources,
             str(stage / "p7m_oracle_driver.f")],
            capture_output=True, text=True)
        if build.returncode != 0:
            fail(f"vendor oracle compilation failed: {build.stderr.strip()[-800:]}")
        version = subprocess.run([compiler, "--version"], capture_output=True, text=True)

        # /CONST/ readback from the compiled unmodified-source oracle.
        const_run = subprocess.run([str(binary)], input="11\n", capture_output=True, text=True,
                                   cwd=stage)
        if const_run.returncode != 0:
            fail(f"oracle /CONST/ readback failed: {const_run.stderr.strip()[-200:]}")
        constants = {}
        for line in const_run.stdout.splitlines():
            fields = line.split()
            if len(fields) == 2:
                constants[fields[0]] = float(fields[1])
        probe_const = subprocess.run([str(args.probe), "--const"], capture_output=True, text=True)
        for line in probe_const.stdout.splitlines():
            fields = line.split()
            if len(fields) == 2:
                name = fields[0]
                if name not in constants:
                    fail(f"{name} missing from the oracle /CONST/ readback")
                if abs(float(fields[1]) - constants[name]) > 1.0e-12:
                    fail(f"{name}: oracle={constants[name]!r} probe={fields[1]!r}")
        print(f"P7M_CONST_READBACK=PASS RT2PI={constants['P7M_CONST_RT2PI']:.1f} "
              f"SMALL={constants['P7M_CONST_SMALL']:.3e} EXPMAX={constants['P7M_CONST_EXPMAX']:.1f} "
              f"EPSREFL={constants['P7M_CONST_EPSREFL']:.2e} "
              f"MXREFL={int(constants['P7M_CONST_MXREFL'])}")

        total = 0
        # MUNU
        rows = munu_matrix()
        payload = "\n".join(f"{index + 1} {muflag} {x!r} {y!r} {ratio!r}"
                            for index, (muflag, x, y, ratio) in enumerate(rows)) + "\n"
        oracle_rows, probe_rows = run_pair(args.probe, binary, 1, "--munu-matrix", payload, stage)
        cases, _ = compare("munu", oracle_rows, probe_rows)
        total += cases
        # BI
        rows = bi_matrix()
        payload = "\n".join(f"{index + 1} {afac!r} {argm!r} {argp!r}"
                            for index, (afac, argm, argp) in enumerate(rows)) + "\n"
        oracle_rows, probe_rows = run_pair(args.probe, binary, 2, "--bi-matrix", payload, stage)
        cases, _ = compare("bi", oracle_rows, probe_rows)
        total += cases
        # BJI
        rows = bji_matrix()
        payload = "\n".join(f"{index + 1} " + " ".join(repr(value) for value in row)
                            for index, row in enumerate(rows)) + "\n"
        oracle_rows, probe_rows = run_pair(args.probe, binary, 3, "--bji-matrix", payload, stage)
        cases, _ = compare("bji", oracle_rows, probe_rows)
        total += cases
        # BJIL
        rows = bjil_matrix()
        payload = "\n".join(f"{index + 1} " + " ".join(repr(value) for value in row)
                            for index, row in enumerate(rows)) + "\n"
        oracle_rows, probe_rows = run_pair(args.probe, binary, 4, "--bjil-matrix", payload, stage)
        cases, _ = compare("bjil", oracle_rows, probe_rows)
        total += cases
        # SIGMA
        rows = sigma_matrix()
        payload = "\n".join(f"{index + 1} " + " ".join(repr(value) for value in row)
                            for index, row in enumerate(rows)) + "\n"
        oracle_rows, probe_rows = run_pair(args.probe, binary, 5, "--sigma-matrix", payload, stage)
        cases, _ = compare("sigma", oracle_rows, probe_rows)
        total += cases
        # IREG
        rows = ireg_matrix()
        payload = "\n".join(f"{index + 1} {x!r} {x12!r} {x23!r}"
                            for index, (x, x12, x23) in enumerate(rows)) + "\n"
        oracle_rows, probe_rows = run_pair(args.probe, binary, 6, "--ireg-matrix", payload, stage)
        cases, _ = compare("ireg", oracle_rows, probe_rows, integer_columns=(0,))
        total += cases
        # CTREC
        states = state_matrix()
        payload = "\n".join(f"{index + 1} " + " ".join(repr(value) for value in fields)
                            for index, fields in enumerate(states)) + "\n"
        oracle_rows, probe_rows = run_pair(args.probe, binary, 7, "--ctrec-matrix", payload, stage)
        cases, _ = compare("ctrec", oracle_rows, probe_rows, integer_columns=(8, 9))
        total += cases
        # PUFFC
        rows = [(index + 1, fields, imode, pole, dpole)
                for index, fields in enumerate(states)
                for imode, pole, dpole in ((0, 0.0, 0.0), (1, 25.0, 0.0), (2, 25.0, 15.0))]
        payload = "\n".join(f"{case} " + " ".join(repr(value) for value in fields) +
                            f"\n{imode} {pole!r} {dpole!r}"
                            for case, fields, imode, pole, dpole in rows) + "\n"
        oracle_rows, probe_rows = run_pair(args.probe, binary, 8, "--puffc-matrix", payload, stage)
        cases, _ = compare("puffc", oracle_rows, probe_rows)
        total += cases
        # LOWER
        payload = "\n".join(f"{index + 1} " + " ".join(repr(value) for value in fields)
                            for index, fields in enumerate(states)) + "\n"
        oracle_rows, probe_rows = run_pair(args.probe, binary, 9, "--lower-matrix", payload, stage)
        cases, _ = compare("lower", oracle_rows, probe_rows)
        total += cases
        # CTSG (lower-segment / pole / flat branches only)
        rows = ctsg_cases()
        payload = "\n".join(f"{index + 1} " + " ".join(repr(value) for value in fields) +
                            f"\n{ipin} {ihin} {tin!r}"
                            for index, (fields, ipin, ihin, tin) in enumerate(rows)) + "\n"
        oracle_rows, probe_rows = run_pair(args.probe, binary, 10, "--ctsg-matrix", payload, stage)
        cases, _ = compare("ctsg", oracle_rows, probe_rows)
        total += cases
        print(f"P7M_ORACLE_PARITY_TOTAL_CASES={total}")
        print(f"P7M_FORTRAN_COMPILER={version.stdout.splitlines()[0].strip()}")
    print("P7M_CTSG_KERNEL_PARITY_IS_NOT_A_CONCENTRATION_COMPARISON=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
