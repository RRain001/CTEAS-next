#!/usr/bin/env python3
"""P6F acceptance: the unmodified original CALPUFF 7.2.1 reads what we write.

The P6F roadmap clause is "C++ 完整合法输出 v2.1，原版 P7 读取" - the original
CALPUFF itself must read the file, not only a decoder of ours. This test

  1. rebuilds the original CALPUFF from the *unchanged* tracked vendor sources
     with the repository's documented reference flags and records every source
     and binary hash;
  2. case A: stages the CALMET.DAT that the P6F writer re-serialised from the
     frozen 2022 reference case (byte-identical, SHA-256 pinned) and requires the
     original to run all 143 hours, to produce the same concentration output as
     the tracked original reference and to echo our header values in its listing;
  3. case B: stages a file whose *values* were changed by the documented P6F
     perturbation helper (structure, masks, units and time labels untouched) and
     requires the original to read it, run to the end and produce different,
     finite, physically plausible concentrations - legal-and-readable rather than
     only hash-equal;
  4. case C (only with --p6d-fields): the same for a file whose hourly U/V/W came
     from the real P6D wind-array product, composed with the case's 2-D
     meteorological fields;
  5. a truncated file must not produce a clean successful run.

Nothing here is staged inside project/: every run happens in a temporary
directory, and the frozen inputs are only read.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import shutil
import struct
import subprocess
import sys
import tempfile

# The repository's documented reference build of the original CALPUFF 7.2.1
# (scripts/capture_hefei_2022_reference_case.py PUFF_FFLAGS): unchanged vendor
# sources, fixed-form legacy 72-column window, non-automatic locals.
FORTRAN_FLAGS = ("-std=legacy", "-ffixed-line-length-72", "-fno-automatic",
                 "-fno-align-commons", "-fallow-argument-mismatch", "-O0",
                 "-fdec-format-defaults")
HOURLY_RECORD_BYTES = 10015  # CONC.DAT hourly record: 15 bytes + 50*50 float32
CONC_GRID_BYTES = 10000


def fail(message: str) -> None:
    print("P6F_CALPUFF_READ_FAIL " + message)
    sys.exit(1)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def run(command: list, cwd: pathlib.Path | None = None,
        timeout: int = 900) -> subprocess.CompletedProcess:
    return subprocess.run([str(part) for part in command], cwd=cwd, text=True,
                          capture_output=True, timeout=timeout)


def walk_records(data: bytes) -> list[tuple[int, int, int]]:
    records: list[tuple[int, int, int]] = []
    offset = 0
    while offset + 8 <= len(data):
        (length,) = struct.unpack_from("<i", data, offset)
        if length < 0 or offset + 8 + length > len(data):
            fail(f"damaged record length {length} in a binary output")
        (trailer,) = struct.unpack_from("<i", data, offset + 4 + length)
        if trailer != length:
            fail("record length markers disagree in a binary output")
        records.append((offset, length, offset + 4))
        offset += 8 + length
    if offset != len(data):
        fail("the record walk does not reach the end of a binary output")
    return records


def concentration_stats(path: pathlib.Path) -> dict:
    """Structural float statistics of the original CONC.DAT hourly fields."""
    data = path.read_bytes()
    records = walk_records(data)
    hourly = [payload for _, length, payload in records
              if length == HOURLY_RECORD_BYTES]
    if not hourly:
        fail("the original wrote no 50x50 hourly concentration record")
    digest = hashlib.sha256()
    nonzero = 0
    total = 0
    minimum = None
    maximum = None
    for payload in hourly:
        field = data[payload + (HOURLY_RECORD_BYTES - CONC_GRID_BYTES):
                     payload + HOURLY_RECORD_BYTES]
        digest.update(field)
        values = struct.unpack(f"<{CONC_GRID_BYTES // 4}f", field)
        for value in values:
            if not (value == value) or value in (float("inf"), float("-inf")):
                fail("the original concentration output contains NaN/Inf")
            if value < 0.0:
                fail(f"the original concentration output contains {value} < 0")
            if value != 0.0:
                nonzero += 1
            minimum = value if minimum is None else min(minimum, value)
            maximum = value if maximum is None else max(maximum, value)
            total += value
    count = len(hourly) * (CONC_GRID_BYTES // 4)
    return {"hourly_records": len(hourly), "values": count, "nonzero": nonzero,
            "minimum": minimum, "maximum": maximum, "mean": total / count,
            "payload_sha256": digest.hexdigest(), "records": len(records)}


def build_original(vendor: pathlib.Path, fortran: str, build: pathlib.Path) -> dict:
    modules = vendor / "modules.for"
    calpuff = vendor / "calpuff.for"
    for path in (modules, calpuff):
        if not path.is_file():
            fail(f"missing original vendor source {path}")
    include = build / "include"
    include.mkdir(parents=True, exist_ok=True)
    for item in sorted(vendor.iterdir()):
        if item.is_file():
            link = include / item.name.lower()
            if not link.exists():
                link.symlink_to(item)
    binary = build / "calpuff-original.x"
    result = run([fortran, *FORTRAN_FLAGS, f"-I{include}", modules, calpuff,
                  "-o", binary], cwd=build, timeout=3600)
    if result.returncode != 0 or not binary.is_file():
        print(result.stdout[-4000:])
        print(result.stderr[-4000:])
        fail(f"the original CALPUFF did not build with {fortran}")
    version = run([fortran, "--version"]).stdout.splitlines()[0]
    return {
        "compiler": fortran,
        "compiler_version": version,
        "flags": list(FORTRAN_FLAGS),
        "vendor": str(vendor),
        "source_sha256": {path.name: sha256_file(path)
                          for path in (modules, calpuff)},
        "binary_sha256": sha256_file(binary),
        "binary_path": str(binary),
    }


def stage(root: pathlib.Path, control: pathlib.Path,
          met_bytes: bytes) -> pathlib.Path:
    work = root / "run" / "puff"
    met_dir = root / "deliverables" / "met"
    work.mkdir(parents=True, exist_ok=True)
    met_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(control, work / "puff.inp")
    (met_dir / "met.dat").write_bytes(met_bytes)
    return work


def execute(work: pathlib.Path, binary: pathlib.Path, timeout: int) -> dict:
    met = work.parent.parent / "deliverables" / "met" / "met.dat"
    before = sha256_file(met)
    try:
        result = run([binary], cwd=work, timeout=timeout)
    except subprocess.TimeoutExpired:
        fail(f"the original CALPUFF did not finish within {timeout} s")
    (work / "stdout.log").write_text(result.stdout + result.stderr)
    after = sha256_file(met)
    listing = work / "puff.lst"
    concentration = work / "puff.con"
    return {
        "returncode": result.returncode,
        "stdout": result.stdout + result.stderr,
        "met_sha_before": before,
        "met_sha_after": after,
        "listing": listing,
        "concentration": concentration,
    }


def require_clean_run(run_result: dict, case: str, hours: int) -> dict:
    text = run_result["stdout"]
    if run_result["returncode"] != 0:
        print(text[-3000:])
        fail(f"{case}: the original CALPUFF returned "
             f"{run_result['returncode']}")
    bad = re.findall(r"(?im)^\s*HALTED|\bERROR\b|forrtl:\s*severe|FATAL", text)
    if bad:
        print(text[-3000:])
        fail(f"{case}: the original CALPUFF reported {bad[:5]}")
    rows = re.findall(r"(?m)^\+\s+(\d{9})\s", text)
    if len(rows) != hours:
        fail(f"{case}: the original processed {len(rows)} hours, expected {hours}")
    if rows[0] != "202200100" or rows[-1] != "202200622":
        fail(f"{case}: the original processed {rows[0]}..{rows[-1]}")
    if run_result["met_sha_before"] != run_result["met_sha_after"]:
        fail(f"{case}: the original modified the weather file it read")
    listing = run_result["listing"]
    if not listing.is_file() or not run_result["concentration"].is_file():
        fail(f"{case}: the original produced no listing/concentration output")
    stdout_lines = text.splitlines()
    excerpt = [line.rstrip() for line in stdout_lines[:6]]
    hour_lines = [line.rstrip() for line in stdout_lines if line.startswith("+ ")]
    excerpt += ["  ..."] + hour_lines[-4:]
    return {"hours": len(rows), "first_hour": rows[0], "last_hour": rows[-1],
            "listing_bytes": listing.stat().st_size,
            "listing_sha256": sha256_file(listing),
            "concentration_bytes": run_result["concentration"].stat().st_size,
            "concentration_sha256": sha256_file(run_result["concentration"]),
            "stdout_excerpt": excerpt,
            "stdout_bytes": len(text)}


def listing_evidence(listing: pathlib.Path) -> dict:
    """What the original printed after reading the CALMET.DAT we wrote."""
    text = listing.read_text(errors="replace")
    evidence: dict = {}
    for key in ("metfm", "irlg", "nsecdt", "ibdathr", "iedathr"):
        match = re.search(rf"(?m)^\s*{key}\s*=\s*(\S+)\s*$", text)
        if match is None:
            fail(f"the listing does not echo {key}")
        evidence[key] = match.group(1)
    zone = re.search(r"(?m)^\s*abtz\s*=\s*(\S+)\s*$", text)
    if zone is None or zone.group(1) != "UTC+0000":
        fail("the listing does not echo the UTC+0000 time zone")
    zface = re.search(r"(?m)^\s*zface\s*=(.*)$", text)
    if zface is None or "3000.000" not in zface.group(1):
        fail("the listing does not echo the ZFACE record we wrote")
    evidence["zface_line"] = " ".join(zface.group(1).split())
    last = re.search(r"(?m)^\s*LAST PERIOD PROCESSED ENDS AT:\s*$\s*(.*)$", text)
    if last is None:
        fail("the listing has no last-period echo")
    evidence["last_period"] = " ".join(last.group(1).split())
    if not all(token in evidence["last_period"]
               for token in ("Year: 2022", "Month: 1", "Day: 6", "Hour: 23",
                             "Second: 0")):
        fail("the last-period echo is not the frozen run window: " +
             evidence["last_period"])
    evidence["last_period_anchor"] = evidence["last_period"][
        evidence["last_period"].find("Year:"):][:64]
    return evidence


def normalised_listing(listing: pathlib.Path) -> list[str]:
    """The listing without the run-time stamps (wall clock and host timings)."""
    volatile = ("Clock time:", "Elapsed Clock Time:", "CPU Time:")
    lines = []
    for line in listing.read_text(errors="replace").splitlines():
        if any(token in line for token in volatile) or \
                re.match(r"^\s*Date:\s", line):
            continue
        lines.append(line.rstrip())
    return lines


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tool", required=True)
    parser.add_argument("--perturb", required=True)
    parser.add_argument("--vendor", required=True, type=pathlib.Path)
    parser.add_argument("--fortran", default="gfortran-11")
    parser.add_argument("--control", required=True, type=pathlib.Path)
    parser.add_argument("--frozen-met", required=True, type=pathlib.Path)
    parser.add_argument("--frozen-sha256", required=True)
    parser.add_argument("--reference-con", required=True, type=pathlib.Path)
    parser.add_argument("--reference-lst", required=True, type=pathlib.Path)
    parser.add_argument("--p6d-fields", default=None, type=pathlib.Path)
    parser.add_argument("--p6d-variant", default="wind1",
                        choices=("wind1", "blend", "slope_corrected"))
    parser.add_argument("--out", required=True, type=pathlib.Path)
    parser.add_argument("--report", default=None, type=pathlib.Path)
    parser.add_argument("--max-seconds", type=int, default=1800)
    args = parser.parse_args()

    # Every path argument is resolved once: the driver builds the original in a
    # temporary directory, so relative inputs would resolve against the wrong cwd.
    args.vendor = args.vendor.resolve()
    args.control = args.control.resolve()
    args.frozen_met = args.frozen_met.resolve()
    args.reference_con = args.reference_con.resolve()
    args.reference_lst = args.reference_lst.resolve()
    args.out = args.out.resolve()
    if args.p6d_fields is not None:
        args.p6d_fields = args.p6d_fields.resolve()
    if not args.control.is_file() or not args.frozen_met.is_file():
        fail("the frozen control deck or weather file is missing")
    if not args.reference_con.is_file() or not args.reference_lst.is_file():
        fail("the tracked original reference outputs are missing")
    frozen = args.frozen_met.read_bytes()
    if sha256_bytes(frozen) != args.frozen_sha256:
        fail("the frozen weather file does not match its pinned SHA-256")
    hours = 143
    evidence: dict = {"status": "FAIL", "frozen_sha256": args.frozen_sha256}

    args.out.mkdir(parents=True, exist_ok=True)
    build = args.out / "original-build"
    evidence["original_build"] = build_original(args.vendor, args.fortran, build)
    binary = pathlib.Path(evidence["original_build"]["binary_path"])

    with tempfile.TemporaryDirectory(prefix="p6f-calpuff-") as work_root:
        root = pathlib.Path(work_root)

        # ---- case A: the byte-identical re-serialisation ----
        case_a_dir = root / "A"
        case_a_dir.mkdir()
        written = case_a_dir / "met.dat"
        result = run([args.tool, "roundtrip", "--file", args.frozen_met,
                      "--out", written, "--expect-sha256", args.frozen_sha256])
        if result.returncode != 0 or "P6F_ROUNDTRIP_BYTE_IDENTICAL" not in result.stdout:
            print(result.stdout + result.stderr)
            fail("case A: the writer did not reproduce the frozen file exactly")
        if sha256_file(written) != args.frozen_sha256:
            fail("case A: the re-serialised file has a different digest")
        work = stage(case_a_dir, args.control, written.read_bytes())
        run_a = execute(work, binary, args.max_seconds)
        summary_a = require_clean_run(run_a, "case A", hours)
        evidence["case_a"] = summary_a
        evidence["case_a"]["listing_echo"] = listing_evidence(run_a["listing"])
        evidence["case_a"]["concentration"] = concentration_stats(
            run_a["concentration"])
        if sha256_file(run_a["concentration"]) != sha256_file(args.reference_con):
            fail("case A: the original did not reproduce the tracked reference "
                 "concentration output byte for byte")
        got_listing = normalised_listing(run_a["listing"])
        want_listing = normalised_listing(args.reference_lst)
        if got_listing != want_listing:
            differences = [(index, ours, theirs)
                           for index, (ours, theirs) in enumerate(
                               zip(got_listing, want_listing))
                           if ours != theirs]
            print(f"case A: listing lines ours={len(got_listing)} "
                  f"reference={len(want_listing)} first differences:")
            for index, ours, theirs in differences[:10]:
                print(f"  line {index + 1}: ours={ours[:120]!r} "
                      f"reference={theirs[:120]!r}")
            fail("case A: the original listing differs from the tracked reference "
                 f"beyond the wall-clock lines ({len(differences)} lines)")
        evidence["case_a"]["matches_tracked_reference_outputs"] = True

        # ---- case B: same layout, changed values ----
        case_b_dir = root / "B"
        case_b_dir.mkdir()
        perturbed = case_b_dir / "met.dat"
        perturb_report = case_b_dir / "perturb.json"
        result = run([args.perturb, "--in", args.frozen_met, "--out", perturbed,
                      "--report", perturb_report])
        if result.returncode != 0 or "P6F_PERTURBED" not in result.stdout:
            print(result.stdout + result.stderr)
            fail("case B: the documented perturbation failed")
        changed_sha = sha256_file(perturbed)
        if changed_sha == args.frozen_sha256:
            fail("case B: the perturbed file is still the frozen file")
        result = run([args.tool, "check", "--file", perturbed])
        if result.returncode != 0 or "P6F_CHECK_LAYOUT_VALID" not in result.stdout:
            fail("case B: the perturbed file is not a legal CALMET.DAT 2.1")
        work = stage(case_b_dir, args.control, perturbed.read_bytes())
        run_b = execute(work, binary, args.max_seconds)
        summary_b = require_clean_run(run_b, "case B", hours)
        evidence["case_b"] = summary_b
        evidence["case_b"]["perturbation"] = json.loads(
            perturb_report.read_text())
        evidence["case_b"]["listing_echo"] = listing_evidence(run_b["listing"])
        evidence["case_b"]["concentration"] = concentration_stats(
            run_b["concentration"])
        if evidence["case_b"]["listing_echo"]["last_period_anchor"] != \
                evidence["case_a"]["listing_echo"]["last_period_anchor"]:
            fail("case B: the time labels changed although only values were "
                 "perturbed")
        if sha256_file(run_b["concentration"]) == sha256_file(
                run_a["concentration"]):
            fail("case B: the original produced the same concentrations for "
                 "different wind/temperature values")
        stats_a = evidence["case_a"]["concentration"]
        stats_b = evidence["case_b"]["concentration"]
        if stats_b["maximum"] == stats_a["maximum"] and \
                stats_b["mean"] == stats_a["mean"]:
            fail("case B: the concentration statistics did not change")

        # ---- case C: the real P6D wind arrays, composed with the case met fields ----
        if args.p6d_fields is not None:
            if not (args.p6d_fields / "metadata.json").is_file():
                fail(f"the P6D field directory {args.p6d_fields} has no metadata")
            case_c_dir = root / "C"
            case_c_dir.mkdir()
            composed = case_c_dir / "met.dat"
            result = run([args.tool, "write-from-p6d", "--fields", args.p6d_fields,
                          "--variant", args.p6d_variant, "--w-field", "w_face",
                          "--statics-from", args.frozen_met, "--met-fields-from",
                          args.frozen_met, "--irtype", "1", "--out", composed])
            if result.returncode != 0 or "P6F_WRITE_FROM_P6D_WRITTEN" not in result.stdout:
                print(result.stdout + result.stderr)
                fail("case C: composing the P6D wind arrays failed")
            work = stage(case_c_dir, args.control, composed.read_bytes())
            run_c = execute(work, binary, args.max_seconds)
            summary_c = require_clean_run(run_c, "case C", hours)
            evidence["case_c"] = summary_c
            evidence["case_c"]["composed_sha256"] = sha256_file(composed)
            evidence["case_c"]["p6d_fields"] = str(args.p6d_fields)
            evidence["case_c"]["variant"] = args.p6d_variant
            evidence["case_c"]["provenance"] = (
                f"{args.p6d_variant}_* U/V on the P6D real-case product, whose "
                "own original-source verdicts are recorded in the CLI report "
                "(wind1: original WIND1+SIMILT; blend: original INTER2), plus "
                "w_face_* (SLOPE-compensated, FRADJ PENDING_GAMMA: QA/plumbing "
                "values) and the case's 2-D meteorological fields; this case "
                "proves the original reads a composed reconstruction, not "
                "numerical parity")
            evidence["case_c"]["listing_echo"] = listing_evidence(run_c["listing"])
            evidence["case_c"]["concentration"] = concentration_stats(
                run_c["concentration"])

        # ---- fail-closed: a structurally broken file must not run cleanly ----
        case_d_dir = root / "D"
        case_d_dir.mkdir()
        broken = case_d_dir / "met.dat"
        broken.write_bytes(frozen[:-10])
        work = stage(case_d_dir, args.control, broken.read_bytes())
        run_d = execute(work, binary, args.max_seconds)
        text = run_d["stdout"]
        rejected = (run_d["returncode"] != 0 or "HALTED" in text or
                    "ERROR" in text or not run_d["concentration"].is_file())
        evidence["truncated_input"] = {
            "returncode": run_d["returncode"],
            "rejected": rejected,
            "concentration_written": run_d["concentration"].is_file(),
            "markers": sorted(set(re.findall(
                r"(?im)^\s*(HALTED[^\n]*|.*ERROR[^\n]*)$", text)))[:3],
        }
        if not rejected:
            fail("a truncated CALMET.DAT produced a clean successful run")

    evidence["status"] = "PASS"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(evidence, indent=2) + "\n")
    print(f"P6F_CALPUFF_READS_WRITTEN_CALMET_PASS hours={hours} "
          f"case_a_reference_identical=True "
          f"case_a_con={evidence['case_a']['concentration']['payload_sha256'][:12]} "
          f"case_b_con={evidence['case_b']['concentration']['payload_sha256'][:12]} "
          f"case_c={'ok' if 'case_c' in evidence else 'skipped'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
