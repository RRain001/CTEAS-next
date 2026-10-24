"""Tests for fail-closed scratch-only original DIAGNO G23/G24 wind trace."""
import math
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from scripts.s4 import s4r1c9p_original_wind_tail_trace as mod


class OriginalWindTailTests(unittest.TestCase):
    def test_source_sha_drift_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            src = Path(directory) / "calmet.for"
            src.write_text("not vendor source")
            with self.assertRaisesRegex(ValueError, "SHA drift"):
                mod.prepare(src, Path(directory) / "instrumented.for")

    def test_original_dir_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            src = Path(directory) / "calmet.for"
            src.write_text("not vendor source")
            with patch.object(mod, "sha", return_value=mod.ORIGINAL_SHA):
                with self.assertRaisesRegex(ValueError, "vendor tree"):
                    mod.prepare(src, Path(directory) / "new.for")

    def test_missing_anchor_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            vendor = Path(directory) / "vendor"
            vendor.mkdir()
            src = vendor / "calmet.for"
            src.write_text("      subroutine diagno(\n      subroutine next(\n")
            with patch.object(mod, "sha", return_value=mod.ORIGINAL_SHA):
                with self.assertRaisesRegex(ValueError, "anchor not unique"):
                    mod.prepare(src, Path(directory) / "other" / "new.for")

    def test_stage_payload_extent_and_order(self):
        self.assertEqual(list(mod.STAGES), [90, 100, 110])
        self.assertEqual(mod.STAGES[90], 2 * 9 * 82 * 85)
        self.assertEqual(mod.STAGES[110], 28 * 82 * 85)
        self.assertIn("S4_DIAGNO_WINDTAIL.BIN", mod.emit(90))
        self.assertIn("w(i,j,k)", mod.emit(110))
        self.assertNotIn("w(i,j,k)", mod.emit(100))

    @staticmethod
    def synthetic():
        data = bytearray()
        for hour in range(2, 8):
            for stage, count in mod.STAGES.items():
                data.extend(mod.HEADER.pack(hour, mod.NX, mod.NY, mod.NZ, stage))
                data.extend(b"\x00" * (4 * count))
        return data

    def test_valid_sixhour_trace(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "trace.bin"
            p.write_bytes(self.synthetic())
            result = mod.parse(p)
            self.assertEqual(result["stage_events"], 18)
            self.assertEqual(result["hours"], 6)
            self.assertEqual(result["native_g23_g24_original_parity"], "NOT_RUN")
            self.assertEqual(result["g23_hour_index_gt_1_guard"], "UNCHANGED")

    def test_truncated_trace_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "trace.bin"
            p.write_bytes(self.synthetic()[:-4])
            with self.assertRaisesRegex(ValueError, "truncated"):
                mod.parse(p)

    def test_wrong_stage_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "trace.bin"
            raw = self.synthetic()
            struct.pack_into("<i", raw, 16, 999)
            p.write_bytes(raw)
            with self.assertRaisesRegex(ValueError, "stage/clock drift"):
                mod.parse(p)

    def test_nonfinite_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "trace.bin"
            raw = self.synthetic()
            struct.pack_into("<f", raw, mod.HEADER.size, math.nan)
            p.write_bytes(raw)
            with self.assertRaisesRegex(ValueError, "nonfinite"):
                mod.parse(p)

    def test_trailing_bytes_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "trace.bin"
            p.write_bytes(self.synthetic() + b"\x00")
            with self.assertRaisesRegex(ValueError, "trailing"):
                mod.parse(p)


    @classmethod
    def synthetic_final_met_pair(cls):
        trace = cls.synthetic()
        met = []
        offset = 0
        for hour in range(6):
            hourly = {}
            for k in range(1, mod.NZ + 1):
                hourly[f"U-LEV  {k}"] = bytes(4 * mod.NC)
                hourly[f"V-LEV  {k}"] = bytes(4 * mod.NC)
                hourly[f"WFACE  {k}"] = struct.pack("<f", float(k)) * mod.NC
            met.append(hourly)
            for stage, count in mod.STAGES.items():
                offset += mod.HEADER.size
                if stage == 110:
                    offset += 4 * 2 * mod.NZ * mod.NC
                    for face in range(mod.NZ + 1):
                        word = struct.pack("<f", float(face))
                        for _ in range(mod.NC):
                            trace[offset:offset + 4] = word
                            offset += 4
                else:
                    offset += 4 * count
        return bytes(trace), met

    def test_original_outhr_wface_is_top_face_kplus1(self):
        raw, met = self.synthetic_final_met_pair()
        result = mod.compare_final_met(raw, met)
        self.assertEqual(result["real4_words"], 1129140)
        self.assertEqual(result["native_g23_g24_parity"], "NOT_RUN")

    def test_original_outhr_wrong_face_rejected(self):
        raw, met = self.synthetic_final_met_pair()
        met[0]["WFACE  1"] = struct.pack("<f", 0.0) * mod.NC
        with self.assertRaisesRegex(ValueError, "WFACE mismatch"):
            mod.compare_final_met(raw, met)


if __name__ == "__main__":
    unittest.main()
