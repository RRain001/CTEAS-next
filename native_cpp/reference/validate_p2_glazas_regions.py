#!/usr/bin/env python3
"""Independent, MANUAL-ONLY original CTGPROC GLAZAS regional parity test.

Unlike the frozen Hefei oracle, all grid dimensions/UTM hemispheres are
explicitly profile-bound and compared to newly executed original LFINAL=T/F.
A successful compilation or synthetic smoke test is NEVER scientific PASS.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
import time

from native_cpp.reference.validate_p2_glazas_original import (
    CATS, SRC_SHA, SRC_SIZE, CTEAS_ORIGINAL_COMMIT,
    CTGPROC_ORIGINAL_SOURCE_SHA256, FLOAT_TOL, GateError, require,
    file_sha, safe_original_file, make_glazas_control, _edit_card,
)
from native_cpp.reference.validate_p2_glazas_hits import stage_img


@dataclass(frozen=True)
class Region:
    name: str
    epsg: int
    xrefkm: str
    yrefkm: str
    dgridkm: str
    nx: int
    ny: int
    mesh: int

    @property
    def zone(self) -> int:
        return self.epsg % 100

    @property
    def hem(self) -> str:
        return "N" if self.epsg < 32700 else "S"


# Distinct WGS84 UTM regions and hemispheres WITHIN Eurasian GLCC product.
# Grid centres: inland Tokyo area near 139.7E/35.7N, central Sumatra
# near 101.3E/-1.8S. Both entirely independent of Hefei and of one another.
REGIONS = {
    "japan_utm54n": Region("japan_utm54n", 32654, "378.389",
                           "3945.454", "0.200", 40, 60, 10),
    "sumatra_utm47s": Region("sumatra_utm47s", 32747, "753.626",
                             "9797.884", "0.150", 30, 40, 20),
}
METHOD = "GLCC_HEADERLESS_LAEA_DIRECT_WGS84_UTM_REAL4_GLOBE_LUGRID"


def control_for_region(template: str, case: Region, *, hits: bool) -> str:
    """Change only isolated copy of frozen original's genuine GLAZAS deck."""
    require((32601 <= case.epsg <= 32660) or (32701 <= case.epsg <= 32760),
            "INVALID_REGIONAL_UTM_EPSG")
    require(case.nx > 0 and case.ny > 0 and 1 <= case.mesh <= 50,
            "INVALID_REGIONAL_DIMENSIONS")
    deck = make_glazas_control(template)
    items = (
        ("IUTMZN", str(case.zone)), ("UTMHEM", case.hem),
        ("XREFKM", case.xrefkm), ("YREFKM", case.yrefkm),
        ("DGRIDKM", case.dgridkm), ("NX", str(case.nx)),
        ("NY", str(case.ny)), ("MESHGLAZ", str(case.mesh)),
        ("LFINAL", "F" if hits else "T"),
    )
    for key, value in items:
        deck = _edit_card(deck, key, value)
    require("1 !GLAZAS = glcc.img !" in deck, "ORIGINAL_NOT_GLAZAS")
    require(not re.search(r"(?m)^\s*1\s+!GEN\s*=", deck),
            "ORIGINAL_GEN_NOT_ALLOWED")
    return deck


def parse_lu(path: Path, case: Region, *, hits: bool):
    """Parse genuine original LFINAL=T/F OR independently built D3 LU.DAT."""
    lines = path.read_text(encoding="utf-8", errors="strict").splitlines()
    cells = case.nx * case.ny
    require(len(lines) == 11 + cells, "REGIONAL_LU_ROW_COUNT")
    require(lines[0].split()[:2] == ["LU.DAT", "2.1"], "REGIONAL_LU_VERSION")
    require(lines[4].strip() == ("HITS" if hits else "FRACTION"),
            "REGIONAL_LU_WRONG_MODE")
    require(lines[5].strip() == "UTM" and lines[6].strip() ==
            f"{case.zone}{case.hem}" and lines[7].startswith("WGS-84"),
            "REGIONAL_LU_CRS")
    h = lines[8].split()
    require(len(h) >= 7, "REGIONAL_LU_MALFORMED_GRID")
    require([int(x) for x in h[:2]] == [case.nx, case.ny],
            "REGIONAL_LU_GRID_DIMS")
    require(abs(float(h[2])-float(case.xrefkm)) <= 1e-6 and
            abs(float(h[3])-float(case.yrefkm)) <= 1e-6 and
            abs(float(h[4])-float(case.dgridkm)) <= 1e-6 and
            abs(float(h[5])-float(case.dgridkm)) <= 1e-6 and
            int(h[6]) == len(CATS), "REGIONAL_LU_GRID_METRICS")
    require(lines[9].split() in (["KM"], ["KM", "M"]),
            "REGIONAL_LU_UNITS")
    require(tuple(map(int, lines[10].split())) == CATS,
            "REGIONAL_LU_CLASS_ORDER")
    parsed = []
    for cell, line in enumerate(lines[11:]):
        fields = line.split()
        require(len(fields) == len(CATS)+3 and fields[-1] == ".",
                "REGIONAL_LU_BAD_CELL_WIDTH")
        require(int(fields[0]) == cell % case.nx + 1 and
                int(fields[1]) == cell // case.nx + 1,
                "REGIONAL_LU_GRID_ORDER")
        values = []
        for token in fields[2:-1]:
            if hits:
                require(re.fullmatch(r"[0-9]+", token) is not None,
                        "REGIONAL_LU_NONINTEGER_HITS")
                values.append(int(token))
            else:
                v = float(token)
                require(math.isfinite(v) and 0 <= v <= 1,
                        "REGIONAL_LU_INVALID_FRACTION")
                values.append(v)
        parsed.append(values)
    return parsed


def parse_native_hits(path: Path, case: Region, manifest: dict):
    require(manifest.get("producer") == "cteas_p2_glcc_raw" and
            manifest.get("source_sha256") == SRC_SHA and
            manifest.get("method") == METHOD and
            manifest.get("utm_epsg") == case.epsg and
            manifest.get("nx") == case.nx and
            manifest.get("ny") == case.ny and
            manifest.get("mesh") == case.mesh and
            manifest.get("xrefkm") == case.xrefkm and
            manifest.get("yrefkm") == case.yrefkm and
            abs(manifest.get("dgridkm", -1)-float(case.dgridkm)) <= 1e-9 and
            manifest.get("hits_csv_sha256") == file_sha(path),
            "REGIONAL_UNTRUSTED_NATIVE_HITS_MANIFEST")
    rows, samples = [], []
    with path.open(newline="", encoding="utf-8") as f:
        rd = csv.reader(f)
        require(next(rd, None) == ["i", "j", "samples"] +
                [f"cat{k}" for k in CATS], "REGIONAL_HITS_CSV_HEADER")
        for index, fields in enumerate(rd):
            require(index < case.nx*case.ny and len(fields) == len(CATS)+3
                    and all(re.fullmatch(r"[0-9]+", x) for x in fields),
                    "REGIONAL_HITS_CSV_ROW")
            require(int(fields[0]) == index % case.nx + 1 and
                    int(fields[1]) == index // case.nx + 1,
                    "REGIONAL_HITS_CSV_ORDER")
            n = int(fields[2])
            values = list(map(int, fields[3:]))
            require(n > 0 and sum(values) == n,
                    "REGIONAL_HITS_CSV_PER_CELL_CONSERVATION")
            samples.append(n)
            rows.append(values)
    require(len(rows) == case.nx*case.ny and
            sum(samples) == manifest["included"],
            "REGIONAL_HITS_CSV_TOTALS")
    return rows, samples


def compare(case: Region, oh, of, nh, nf, ns):
    """Zero-tolerance integers; predeclared 0.0005 display-fraction tolerance."""
    first = []
    count_deltas = 0
    max_int = 0
    int_errors = 0
    frac_errors = 0
    max_frac = 0.0
    original_consistency = 0
    orig_total = native_total = 0
    for index, (orig_hits, orig_frac, nat_hits, nat_frac, samples) in enumerate(
            zip(oh, of, nh, nf, ns)):
        osum, nsum = sum(orig_hits), sum(nat_hits)
        require(osum > 0 and nsum == samples and samples > 0,
                "REGIONAL_EMPTY_OR_NONCONSERVING_CELL")
        orig_total += osum
        native_total += nsum
        count_deltas += osum != nsum
        for k, (oi, ni, off, nff) in enumerate(
                zip(orig_hits, nat_hits, orig_frac, nat_frac)):
            idiff = abs(oi-ni)
            fdiff = abs(off-nff)
            max_int = max(max_int, idiff)
            max_frac = max(max_frac, fdiff)
            int_errors += idiff != 0
            frac_errors += fdiff > FLOAT_TOL
            original_consistency += abs(off - oi/osum) > FLOAT_TOL+1e-8
            if (idiff != 0 or fdiff > FLOAT_TOL) and len(first) < 25:
                first.append(dict(i=index%case.nx+1, j=index//case.nx+1,
                                  category=CATS[k], original_hits=oi,
                                  native_hits=ni, original_fraction=off,
                                  native_fraction=nff))
    good = (int_errors == 0 and frac_errors == 0 and
            count_deltas == 0 and original_consistency == 0)
    return dict(gate="REAL_ORIGINAL_GLAZAS_REGIONAL_INTEGER_AND_FRACTION",
                region=case.name, epsg=case.epsg,
                grid=f"{case.nx}x{case.ny}",
                mesh=case.mesh, compared_values=case.nx*case.ny*len(CATS),
                integer_exceedances=int_errors, max_integer_difference=max_int,
                fraction_exceedances=frac_errors, max_fraction_difference=max_frac,
                original_internal_fraction_mismatch=original_consistency,
                different_cell_hit_totals=count_deltas,
                original_submesh_hits=orig_total, native_submesh_hits=native_total,
                first_differences=first,
                overall=("PASS_SCOPED_ORIGINAL_GLAZAS_REGIONAL" if good
                         else "FAIL_REGIONAL_ORIGINAL_GLAZAS_SCIENCE"))


def original_run(case: Region, template: str, *, hits: bool,
                 binary: Path, image: Path, output: Path, timeout: int):
    output.mkdir(parents=True, exist_ok=False)
    (output/"ctgproc.inp").write_text(
        control_for_region(template, case, hits=hits), encoding="utf-8")
    stage_img(image, output)
    run = subprocess.run([str(binary.resolve()), "ctgproc.inp"],
                         cwd=output, text=True, errors="replace",
                         capture_output=True, timeout=timeout, check=False)
    (output/"stdout.log").write_text(run.stdout, encoding="utf-8")
    (output/"stderr.log").write_text(run.stderr, encoding="utf-8")
    require(run.returncode == 0, f"ORIGINAL_{case.name}_{'HITS' if hits else 'FRACTION'}_EXIT_{run.returncode}")
    require((output/"lu.dat").is_file() and
            (output/"ctgproc.lst").is_file(),
            "REGIONAL_ORIGINAL_OUTPUT_MISSING")
    return parse_lu(output/"lu.dat", case, hits=hits)


def execute_case(case: Region, args, template: str, original_sha: str):
    out = args.out_dir/case.name
    out.mkdir(exist_ok=False)
    d1, d3 = out/"native-d1", out/"native-d3"
    cmd = [str(args.native_d1.resolve()), str(args.source_img.resolve()),
           str(d1), str(case.epsg), case.xrefkm, case.yrefkm,
           case.dgridkm, str(case.nx), str(case.ny), str(case.mesh),
           "--production-direct"]
    subprocess.run(cmd, check=True, timeout=args.timeout_sec)
    m1 = json.loads((d1/"p2_manifest.json").read_text())
    require(m1.get("method") == METHOD and
            m1.get("source_sha256") == SRC_SHA and
            m1.get("official_GLAZAS_parity") == "NOT_RUN",
            "REGIONAL_D1_METHOD_OR_SOURCE_UNTRUSTED")
    fractions = d1/"p2_glcc_usgs92_direct_laea.csv"
    require(m1.get("fractions_csv_sha256") == file_sha(fractions),
            "REGIONAL_D1_FRACTIONS_SHA")
    nh, ns = parse_native_hits(d1/"p2_glcc_usgs92_hits.csv", case, m1)
    subprocess.run([str(args.native_d3.resolve()),
                    str(d1/"p2_manifest.json"), str(fractions), str(d3)],
                   check=True, timeout=args.timeout_sec)
    m3 = json.loads((d3/"p2_d3_manifest.json").read_text())
    native_lu = d3/"lu.dat"
    require(m3.get("producer") == "cteas_p2_glcc_lu_dat" and
            m3.get("input_d1_method") == METHOD and
            m3.get("input_d1_csv_sha256") == m1["fractions_csv_sha256"] and
            m3.get("source_sha256") == SRC_SHA and
            m3.get("lu_dat_sha256") == file_sha(native_lu) and
            m3.get("total_samples") == sum(ns) and
            m3.get("original_GLAZAS_parity") == "NOT_RUN",
            "REGIONAL_D1_D3_PROVENANCE_UNTRUSTED")
    nf = parse_lu(native_lu, case, hits=False)
    of = original_run(case, template, hits=False, binary=args.original_ctgproc,
                      image=args.source_img, output=out/"original-fraction",
                      timeout=args.timeout_sec)
    oh = original_run(case, template, hits=True, binary=args.original_ctgproc,
                      image=args.source_img, output=out/"original-hits",
                      timeout=args.timeout_sec)
    require(file_sha(args.source_img) == SRC_SHA, "REGIONAL_SOURCE_CHANGED")
    evidence = compare(case, oh, of, nh, nf, ns)
    evidence.update(original_source_git_commit=CTEAS_ORIGINAL_COMMIT,
                    original_source_sha256=CTGPROC_ORIGINAL_SOURCE_SHA256,
                    original_binary_sha256=original_sha,
                    official_glcc_img_sha256=SRC_SHA,
                    native_d1_method=METHOD, native_d1_manifest_sha256=file_sha(d1/"p2_manifest.json"),
                    native_d3_manifest_sha256=file_sha(d3/"p2_d3_manifest.json"),
                    original_fraction_lu_sha256=file_sha(out/"original-fraction"/"lu.dat"),
                    original_hits_lu_sha256=file_sha(out/"original-hits"/"lu.dat"),
                    native_fraction_lu_sha256=file_sha(native_lu),
                    native_integer_hits_sha256=file_sha(d1/"p2_glcc_usgs92_hits.csv"),
                    control_fraction_sha256=file_sha(out/"original-fraction"/"ctgproc.inp"),
                    control_hits_sha256=file_sha(out/"original-hits"/"ctgproc.inp"),
                    original_science_proof="NEW_UNMODIFIED_CTGRPOC_LFINAL_T_F",
                    p3="NOT_RUN", glc30_crosswalk="P2_MAPPING_REVIEW_REQUIRED")
    return evidence


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for field in ("source-img", "original-ctgproc", "original-source-file",
                  "control-template", "native-d1", "native-d3", "out-dir"):
        p.add_argument("--"+field, type=Path, required=True)
    p.add_argument("--original-bin-sha256", required=True)
    p.add_argument("--timeout-sec", type=int, default=300)
    args = p.parse_args(argv)
    require(20 <= args.timeout_sec <= 600, "REGIONAL_TIMEOUT_OUT_OF_BOUNDS")
    require(not args.out_dir.exists(), "REGIONAL_OUTPUT_ALREADY_EXISTS")
    safe_original_file(args.source_img, expected=SRC_SHA, exact_size=SRC_SIZE)
    safe_original_file(args.original_source_file,
                       expected=CTGPROC_ORIGINAL_SOURCE_SHA256)
    safe_original_file(args.original_ctgproc,
                       expected=args.original_bin_sha256)
    for path in (args.native_d1, args.native_d3):
        require(path.is_file() and not path.is_symlink(),
                "REGIONAL_NATIVE_BINARY_MISSING")
    require(args.control_template.is_file() and
            not args.control_template.is_symlink(),
            "REGIONAL_ORIGINAL_TEMPLATE_MISSING")
    template = args.control_template.read_text(encoding="utf-8")
    args.out_dir.mkdir(parents=True)
    results = []
    for case in REGIONS.values():
        started = time.monotonic()
        try:
            record = execute_case(case, args, template, args.original_bin_sha256)
        except Exception as exc:
            record = dict(region=case.name, epsg=case.epsg,
                          overall="FAIL_REGIONAL_EXECUTION_OR_ORACLE",
                          failure_reason=f"{type(exc).__name__}: {exc}")
        record["runtime_seconds"] = round(time.monotonic()-started, 3)
        results.append(record)
        print(json.dumps(record, ensure_ascii=False), flush=True)
    passed = all(x["overall"] == "PASS_SCOPED_ORIGINAL_GLAZAS_REGIONAL"
                 for x in results)
    report = dict(overall=("PASS_SCOPED_ALL_TESTED_REGIONS" if passed else
                           "FAIL_ORIGINAL_MULTI_REGION_GLAZAS"),
                  current_main_original_science="HEFEI_PREVIOUSLY_PASS_SCOPED_NOT_THIS_GATE",
                  provenance="ACTUAL_156MB_AND_FROZEN_ORIGINAL_BINARY",
                  regions=results)
    (args.out_dir/"result.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False)+"\n",
        encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
