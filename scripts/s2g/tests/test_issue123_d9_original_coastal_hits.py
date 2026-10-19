"""#123 D9 software-only parser/recount contracts; no authentic science claim."""
from __future__ import annotations
import csv
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.s2g.issue123_d9_original_coastal_hits import (
    parse_fixed_hit_row, compare, control_value, CATS,
)
import scripts.s2g.issue123_d9_original_coastal_hits as d9


def fmt_hit(i:int,j:int,counters:list[int]) ->str:
    flag="." if sum(counters) else "Missing"
    return f"{i:5d}{j:5d}"+ "".join(f"{x:5d}" for x in counters)+f"   {flag:<17}\n"


class D9IntegerContracts(unittest.TestCase):
    def test_fixed_width_adjacent_i5_values(self):
        row=[0]*38
        row[0]=99999
        row[1]=99999
        data=fmt_hit(1,1,row)
        got,flag=parse_fixed_hit_row(data.rstrip("\n"),0)
        self.assertEqual(got[:2],[99999,99999])
        self.assertEqual(flag,".")

    def test_missing_and_bad_flag_fail_closed(self):
        zeros=[0]*38
        row,flag=parse_fixed_hit_row(fmt_hit(1,1,zeros).rstrip("\n"),0)
        self.assertEqual(sum(row),0)
        self.assertEqual(flag,"Missing")
        bad=fmt_hit(1,1,[1]+[0]*37).replace("   .","   Missing")
        with self.assertRaisesRegex(ValueError,"FLAG_SUM"):
            parse_fixed_hit_row(bad.rstrip("\n"),0)

    def test_control_duplicate_must_fail(self):
        self.assertEqual(control_value("! NX = 200 !","NX"),"200")
        with self.assertRaisesRegex(ValueError,"NOT_UNIQUE"):
            control_value("! NX = 200 !\n! NX = 50 !","NX")

    def test_strict_2x2_integer_field_comparison(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            original=root/"lu.dat"
            native=root/"native.csv"
            with original.open("w") as fp:
                fp.write("header\n"*11)
                for idx in range(4):
                    row=[0]*38
                    row[0]=2
                    fp.write(fmt_hit(idx%2+1,idx//2+1,row))
            with native.open("w",newline="") as fp:
                writer=csv.writer(fp)
                writer.writerow(["i","j","samples"]+
                                [f"cat{k}" for k in CATS])
                for idx in range(4):
                    writer.writerow([idx%2+1,idx//2+1,2]+[2]+[0]*37)
            with patch.object(d9,"N",2),patch.object(d9,"parse_lu_header",
                                                      side_effect=lambda fp:[fp.readline() for _ in range(11)]):
                good=compare(original,native,{"test":"SYNTHETIC_ONLY"})
                self.assertEqual(good["integer_mismatches"],0)
                self.assertEqual(good["integer_fields_compared"],4*38)
                lines=native.read_text().splitlines()
                bits=lines[1].split(",")
                bits[3],bits[4]="1","1"
                lines[1]=",".join(bits)
                native.write_text("\n".join(lines)+"\n")
                wrong=compare(original,native,{"test":"SYNTHETIC_ONLY"})
                self.assertEqual(wrong["integer_mismatches"],2)
                self.assertEqual(wrong["cells_with_differences"],1)
                self.assertEqual(wrong["status"],"D9_ORIGINAL_GLCC_HITS_MISMATCH")


if __name__=="__main__":
    unittest.main()
