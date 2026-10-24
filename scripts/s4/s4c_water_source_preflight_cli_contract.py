#!/usr/bin/env python3
"""No-vendor-input S4-C fail-closed CLI admission/anti-promotion regression.

Called by the independent P6 CMake target with the same compiled G14 CLI.
This tests *mode isolation*, not water physics, new-site parity, or MET.DAT.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import tempfile


def test_cli(binary: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="cteas-s4c-water-cli-") as tmp:
        root = Path(tmp)
        no_input = root / "missing"
        output = root / "forbidden.met.dat"
        trace = root / "forbidden-state.csv"
        required = ["--met", str(no_input), "--geo", str(no_input),
                    "--surf", str(no_input), "--up", str(no_input),
                    "--hours", "6"]
        mode = ["--selected-experimental", "--water-source-preflight-only", *required]
        forbidden = (
            (["--out", str(output)], "forbids output"),
            (["--g26-normal-entry-trial"], "forbids normal G26"),
            (["--native-comp-trace", str(trace)], "forbids native COMP trace"),
            (["--probe-prefix-hours", "1"], "forbids source-hour truncation"),
            (["--max-retained-field-bytes", "1"], "forbids field retention budget"),
        )
        for flags, label in forbidden:
            p = subprocess.run([str(binary), *mode, *flags],
                               text=True, capture_output=True, timeout=20)
            assert p.returncode == 2, (label, p.returncode, p.stderr)
            assert "S4C WATER preflight forbids" in p.stderr, (label, p.stderr)
            assert "S4C_G19_WATER_SOURCE_PREFLIGHT=PASS" not in p.stdout
            assert not output.exists() and not trace.exists(), label
        for args, reason in (
            (["--water-source-preflight-only", *required], "requires research admission"),
            (["--selected-experimental", *required], "default output needed"),
        ):
            p = subprocess.run([str(binary), *args],
                               text=True, capture_output=True, timeout=20)
            assert p.returncode == 2, (reason, p.returncode, p.stderr)
            assert "S4B2 experimental ONLY" in p.stderr, (reason, p.stderr)
        for more, expected in (
            (["--water-source-preflight-only"], "duplicate S4C water preflight flag"),
            (["--hours", "6"], "S4B2 unknown/repeated argument"),
        ):
            p = subprocess.run([str(binary), *mode, *more],
                               text=True, capture_output=True, timeout=20)
            assert p.returncode == 2 and expected in p.stderr, (more, p.stderr)
        # Admission genuinely reaches the loader if otherwise well-formed;
        # invalid original inputs must fail, not emit a success certificate.
        p = subprocess.run([str(binary), *mode],
                           text=True, capture_output=True, timeout=20)
        assert p.returncode == 2 and "S4B2_FAIL_CLOSED" in p.stderr, p.stderr
        assert "S4C_G19_WATER_SOURCE_PREFLIGHT=PASS" not in p.stdout
        assert not output.exists() and not trace.exists()
    print("S4C_WATER_SOURCE_PREFLIGHT_CLI_GUARDS=PASS_SYNTHETIC_ONLY")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", required=True, type=Path)
    args = parser.parse_args()
    if not args.binary.is_file():
        parser.error("compiled S4B2 CLI required")
    test_cli(args.binary)
