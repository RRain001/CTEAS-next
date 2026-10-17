#!/usr/bin/env python3
"""Literal-source probe for the PREPDI ``IEXTRP <= 0`` first-level exclusion.

Extracts the *unchanged* original PREPDI statement sequence that fills the
station profiles from the buffered sounding values, wraps it in a driver that
feeds one synthetic sounding, and asserts the documented behaviour:

    I1 = 2 for IEXTRP <= 0   -> US(1)/VS(1) stay unset (original EDIT)
    I1 = 1 otherwise         -> US(1) is filled from the lowest layer

Anchors: calmet.for L14099 `IF (IEXTRP .LE. 0) I1=2` and the fill loop that
follows it (SURF/UA same-name rule at L14090-L14098).
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

SOURCE_BLOB = "437f43bb7f0e51a1919e56664663e1a046986ed0"
EXCLUSION_LINE = 14099      # `IF (IEXTRP .LE. 0) I1=2`
FILL_FIRST = 14099          # literal block starts at the exclusion test
FILL_LAST = 14107           # `   55 CONTINUE` ends the level fill loop
NZ = 9

DRIVER_HEAD = """      program prepdi_iextrp_probe
      include 'params.met'
      real us(mxnz,2),vs(mxnz,2),work3(64)
      real edit
      integer i1,iextrp,i,j,k,nz
      character*256 arg
      edit=999999.
      call get_command_argument(1,arg)
      read(arg,*) iextrp
      j=1
      nz=9
      do k=1,32
        work3(k)=100.+float(k)
      enddo
      do k=1,9
        us(k,j)=edit
        vs(k,j)=edit
      enddo
      i1=1
"""

DRIVER_TAIL = """      open(11,file='probe_'//trim(arg)//'.out',status='replace')
      do k=1,9
        write(11,'(I3,1X,2(ES20.10E3,1X))') k,us(k,1),vs(k,1)
      enddo
      close(11)
      end
"""

def sha1_blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--vendor", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    source = args.vendor / "calmet.for"
    raw = source.read_bytes()
    if sha1_blob(raw) != SOURCE_BLOB:
        raise RuntimeError("original CALMET source changed")
    lines = raw.decode().splitlines(keepends=True)
    if "      IF (IEXTRP .LE. 0) I1=2\n" not in lines[EXCLUSION_LINE - 1]:
        raise RuntimeError("PREPDI IEXTRP exclusion anchor drift")
    if "   55 CONTINUE\n" not in lines[FILL_LAST - 1]:
        raise RuntimeError("PREPDI fill loop end anchor drift")
    fragment = "".join(lines[FILL_FIRST - 1:FILL_LAST])
    driver = args.out / "prepdi_iextrp_probe.for"
    driver.write_text(DRIVER_HEAD + fragment + DRIVER_TAIL)
    binary = args.out / "prepdi_iextrp_probe"
    subprocess.run(["gfortran", "-std=legacy", "-O0", "-fno-automatic",
                    "-ffixed-line-length-none", "-fallow-argument-mismatch",
                    "-I" + str(args.vendor), str(driver), "-o", str(binary)],
                   check=True, capture_output=True, text=True)
    results = {}
    for label, iextrp in (("iextrp_minus4", -4), ("iextrp_plus4", 4)):
        case = args.out / label
        subprocess.run([str(binary), f"{iextrp}"], check=True,
                       capture_output=True, text=True)
        rows = [line.split() for line in
                Path(f"probe_{iextrp}.out").read_text().splitlines()]
        level1 = [float(rows[0][1]), float(rows[0][2])]
        level2 = [float(rows[1][1]), float(rows[1][2])]
        results[label] = {
            "iextrp": iextrp,
            "level1_us": level1[0], "level1_vs": level1[1],
            "level2_us": level2[0], "level2_vs": level2[1],
            "level1_unset": level1[0] == 999999.0 and level1[1] == 999999.0,
            "level2_filled": level2[0] != 999999.0 and level2[1] != 999999.0,
        }
    expected = (results["iextrp_minus4"]["level1_unset"] and
                results["iextrp_minus4"]["level2_filled"] and
                not results["iextrp_plus4"]["level1_unset"] and
                results["iextrp_plus4"]["level2_filled"])
    report = {
        "status": ("PASS_PREPDI_IEXTRP_LEVEL1_EXCLUSION" if expected else "FAIL"),
        "source": {"vendor_blob_sha1": SOURCE_BLOB,
                   "literal_lines": [FILL_FIRST, FILL_LAST],
                   "literal_sha256": hashlib.sha256(fragment.encode()).hexdigest(),
                   "exclusion_line": EXCLUSION_LINE,
                   "exclusion_sha256": hashlib.sha256(
                       lines[EXCLUSION_LINE - 1].encode()).hexdigest()},
        "deck_value": "IEXTRP = -4 (met.inp L528)",
        "cases": results,
    }
    (args.out / "prepdi-iextrp-probe.json").write_text(
        json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if not expected:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
