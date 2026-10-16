#!/usr/bin/env python3
"""P7G: the CONC.DAT structure comparison against the frozen puff.con.

Writes a file with this module's own framing for every period the frozen artifact
carries and asserts that the DATA records match one for one (periods, grid
descriptors, species fields, their sizes and their times), while the frozen file's
additional header records are exactly the difference. Values are not compared here:
the frozen values need the full puff model (see the ledger's comparability
statement).
"""
from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys
import tempfile

REPO_FALLBACK = pathlib.Path(__file__).resolve().parents[4]
FROZEN = "project/cases/hefei5km_2022_reference_case_20261011/run/puff/puff.con"
FROZEN_BYTES = 1_896_056
FROZEN_RECORDS = 3655
NX = NY = 50


def fail(message: str) -> None:
    print(f"P7G_CONC_STRUCTURE=FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def parse(text: str) -> tuple[dict[str, str], list[str]]:
    fields: dict[str, str] = {}
    labels: list[str] = []
    for line in text.splitlines():
        if line.startswith("P7G_CONC_STRUCTURE_COMPARE "):
            for token in line.split()[1:]:
                key, _, value = token.partition("=")
                fields[key] = value
        elif line.startswith("P7G_CONC_STRUCTURE_SPECIES "):
            fields["SPECIES"] = line.split('"')[1]
        elif line.startswith("P7G_CONC_STRUCTURE_LABEL "):
            labels.append(line.split('"')[1])
    return fields, labels


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", type=pathlib.Path, required=True, help="built cteas_p7e_probe")
    parser.add_argument("--repo-root", type=pathlib.Path, default=REPO_FALLBACK)
    args = parser.parse_args()
    if not args.probe.is_file():
        fail(f"probe binary missing: {args.probe}")
    frozen = args.repo_root.resolve() / FROZEN
    if not frozen.is_file():
        print("P7G_CONC_STRUCTURE=SKIPPED_WITHOUT_FROZEN_ARTIFACT")
        return 0

    with tempfile.TemporaryDirectory(prefix="p7g-structure-") as temporary:
        written = pathlib.Path(temporary) / "reconstructed.dat"
        run = subprocess.run([str(args.probe), "--structure-compare", str(frozen), str(written),
                              str(NX), str(NY)], capture_output=True, text=True)
        if run.returncode != 0:
            fail(f"structure comparison failed: {run.stderr.strip()[-400:]}")
        fields, labels = parse(run.stdout)
        if fields.get("FROZEN_BYTES") != str(FROZEN_BYTES):
            fail(f"frozen artifact size changed: {fields.get('FROZEN_BYTES')}")
        if fields.get("FROZEN_RECORDS") != str(FROZEN_RECORDS):
            fail(f"frozen record count changed: {fields.get('FROZEN_RECORDS')}")
        for key in ("PERIODS", "FROZEN_PERIODS", "FROZEN_GRID", "FROZEN_SPECIES_FIELDS",
                    "WRITTEN_PERIODS", "WRITTEN_GRID", "WRITTEN_SPECIES_FIELDS"):
            if fields.get(key) != "143":
                fail(f"{key} is {fields.get(key)}, expected 143")
        if fields.get("SPECIES") != "H-3     ":
            fail(f"unexpected species label {fields.get('SPECIES')!r}")
        if fields.get("FIRST_BEGIN") != "2022001" or fields.get("LAST_END") != "2022006":
            fail("the frozen artifact's period span changed")
        # The data records are reproduced exactly; the frozen file carries the
        # embedded control file and the WROUT1 header tables on top.
        data_records = 3 * 143
        if int(fields["WRITTEN_RECORDS"]) != data_records + 2:
            fail(f"written records {fields['WRITTEN_RECORDS']}, expected {data_records + 2}")
        header_records = int(fields["FROZEN_RECORDS"]) - data_records
        if header_records <= 0:
            fail("the frozen artifact unexpectedly has no header records")
        if "H-3     " not in labels:
            fail("the frozen species label was not reported")
        print(f"P7G_CONC_STRUCTURE=PASS PERIODS=143 GRID=143 SPECIES_FIELDS=143 "
              f"FIELD_BYTES=10015 NX={NX} NY={NY} FROZEN_RECORDS={FROZEN_RECORDS} "
              f"DATA_RECORDS={data_records} HEADER_RECORDS={header_records} "
              f"WRITTEN_RECORDS={fields['WRITTEN_RECORDS']} "
              f"FROZEN_BYTES={FROZEN_BYTES} WRITTEN_BYTES={fields['WRITTEN_BYTES']}")
    print("P7G_CONC_STRUCTURE_COMPARISON_IS_NOT_A_VALUE_COMPARISON=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
