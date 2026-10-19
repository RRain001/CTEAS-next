"""Synthetic D8 contract only; never counted as an authentic BLN science pass."""
from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
from scripts.s2g.issue123_d8_real_bln_iptype import (
    make_points, compare, sha, source_subroutine, f32,
)


class D8SourceAndComparison(unittest.TestCase):
    def test_extract_exactly_one_fortran_routine(self):
        text = "      integer function iptype(px,py)\n      iptype=0\n      end\n"
        got = source_subroutine(
            text, r"\s*integer\s+function\s+iptype\s*\(\s*px\s*,\s*py\s*\)\s*")
        self.assertEqual(got,text)
        with self.assertRaisesRegex(ValueError,"UNIQUE_ANCHOR"):
            source_subroutine(text + text,
                r"\s*integer\s+function\s+iptype\s*\(\s*px\s*,\s*py\s*\)\s*")

    def test_wolsong_points_are_deterministic_and_contain_real_bln_edges(self):
        with tempfile.TemporaryDirectory() as temp:
            bln=Path(temp)/"coast.bln"
            bln.write_text('      5,0,"1,2,    72"\n'
                '533.215000,3942.629000\n'
                '534.215000,3942.629000\n'
                '534.215000,3943.629000\n'
                '533.215000,3943.629000\n'
                '533.215000,3942.629000\n')
            a=make_points(bln)
            self.assertEqual(a,make_points(bln))
            self.assertEqual(len(a),40000+5*5+4+2048)
            self.assertIn((f32(533.215),f32(3942.629)),a)

    def test_comparison_fails_on_any_integer_mismatch(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)
            (p/"points.txt").write_text("3\n533.215 3942.629\n533.25 3942.66\n534 3943\n")
            (p/"d8_provenance.json").write_text(json.dumps({
                "status":"D8_REAL_BLN_SAME_INPUT_READY",
                "points_sha256":sha(p/"points.txt"),"point_count":3}))
            (p/"fortran_classes.txt").write_text("0\n1\n2\n")
            (p/"cpp_classes.txt").write_text("0\n1\n2\n")
            self.assertEqual(compare(p)["mismatch_count"],0)
            (p/"cpp_classes.txt").write_text("0\n1\n0\n")
            with self.assertRaisesRegex(ValueError,"CLASS_MISMATCH"):
                compare(p)
            self.assertEqual(json.loads((p/"d8_iptype_report.json").read_text())
                             ["mismatch_count"],1)


if __name__=="__main__":
    unittest.main()
