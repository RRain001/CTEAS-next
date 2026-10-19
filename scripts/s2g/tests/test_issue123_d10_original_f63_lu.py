"""D10 independent F6.3 field and exact F/T control-contract tests only."""
from __future__ import annotations
import unittest
from unittest.mock import patch
from scripts.s2g.issue123_d10_original_f63_lu import (
    rounded_source_fraction,parse_fraction_row,validate_fraction_header,
    D10_STATUS,
)


class D10OriginalFractionContracts(unittest.TestCase):
    def test_real4_rounded_three_decimals(self):
        self.assertEqual(rounded_source_fraction(1,3),"0.333")
        self.assertEqual(rounded_source_fraction(2,3),"0.667")
        self.assertEqual(rounded_source_fraction(0,3),"0.000")
        self.assertEqual(rounded_source_fraction(3,3),"1.000")
        with self.assertRaises(ValueError):
            rounded_source_fraction(1,0)

    def test_exact_38_fixed_f6_3_and_missing(self):
        with patch("scripts.s2g.issue123_d10_original_f63_lu.N",2):
            fields=["0.000"]*38
            fields[0]="0.333"; fields[1]="0.667"
            row=f"{1:5d}{1:5d}"+ "".join(f"{s:>6}" for s in fields)+"   .                "
            got,flag=parse_fraction_row(row,0)
            self.assertEqual(flag,".")
            self.assertEqual(got[:2],["0.333","0.667"])
            with self.assertRaisesRegex(ValueError,"NOT_F6_3"):
                parse_fraction_row(row.replace("0.333","0.33 ",1),0)
            empty=f"{2:5d}{1:5d}"+ "".join(f"{'0.000':>6}" for _ in range(38))+"   Missing          "
            got,flag=parse_fraction_row(empty,1)
            self.assertEqual(flag,"Missing")
            self.assertEqual(sum(map(float,got)),0.)

    def test_grid_header_requirements(self):
        def header(mode:str):
            return ["LU.DAT   2.1","desc","year","note",mode,"UTM","52N",
                    "WGS-84","200 200 533.215 3942.629 0.100 0.100 38",
                    "KM"," ".join(map(str,(11,12,13,14,15,16,17,21,22,23,24,
                         31,32,33,41,42,43,51,52,53,54,55,61,62,71,
                         72,73,74,75,76,77,81,82,83,84,85,91,92)))]
        validate_fraction_header(header("HITS"),header("FRACTION"))
        wrong=header("FRACTION")
        wrong[6]="50N"
        with self.assertRaisesRegex(ValueError,"HEADER_DRIFT"):
            validate_fraction_header(header("HITS"),wrong)


if __name__=="__main__":
    unittest.main()
