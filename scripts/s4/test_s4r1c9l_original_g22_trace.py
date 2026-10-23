#!/usr/bin/env python3
"""Software-only tests: synthetic bytes are NEVER scientific evidence."""
from __future__ import annotations

from array import array
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

MODULE = Path(__file__).with_name("s4r1c9l_original_g22_trace.py")
SPEC = importlib.util.spec_from_file_location("g22_trace", MODULE)
assert SPEC is not None and SPEC.loader is not None
trace = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(trace)


def fixture_bytes() -> bytes:
    data = bytearray()
    for hour in range(2, 8):
        for stage, names in trace.STAGE_ARRAYS.items():
            data += struct.pack("<5i", hour, trace.NX, trace.NY, trace.NZ, stage)
            count = trace.NX * trace.NY * (trace.NZ if stage == 50 else 1) * len(names)
            data += array("f", [float(stage)] * count).tobytes()
    return bytes(data)


class OriginalTraceTests(unittest.TestCase):
    def test_synthetic_valid_six_hour_format(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "synthetic.bin"
            path.write_bytes(fixture_bytes())
            result = trace.parse(path)
            self.assertEqual(result["hours"], list(range(2, 8)))
            self.assertEqual(len(result["events"]), 30)
            self.assertEqual(result["independent_native_parity"], "NOT_RUN")
            self.assertEqual(result["production_admission"], "NOT_ACCEPTED")

    def test_truncated_trace_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "truncated.bin"
            path.write_bytes(fixture_bytes()[:-4])
            with self.assertRaisesRegex(ValueError, "truncated"):
                trace.parse(path)

    def test_wrong_stage_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "badstage.bin"
            data = bytearray(fixture_bytes())
            struct.pack_into("<i", data, 16, 99)
            path.write_bytes(data)
            with self.assertRaisesRegex(ValueError, "invalid original trace event"):
                trace.parse(path)

    def test_unpinned_source_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            src = Path(temp) / "fake.for"
            src.write_text("this is not vendor CALMET")
            with self.assertRaisesRegex(ValueError, "SHA drift"):
                trace.prepare(src, Path(temp) / "out.for")


if __name__ == "__main__":
    unittest.main()
