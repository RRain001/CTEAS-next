"""D3 comparator tests using captured frozen original GEO *only* as parser fixture.
Not proof of Wolsong original parity or a replacement original run.
"""
from pathlib import Path
import csv
import tempfile
import unittest

from native_cpp.reference.compare_p3_makegeo_dynamic import parse_geo,compare,FIELDS,COLS

ROOT=Path(__file__).resolve().parents[3]
FROZEN=ROOT/"project/cases/hefei5km_2022_reference_case_20261011/geo/makegeo/geo.dat"


class DynamicOriginalGeoComparatorTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="p3-d3-parser-")
        self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name)
        self.geo=self.base/"original.geo.dat"
        self.geo.write_bytes(FROZEN.read_bytes())
        self.csv=self.base/"same-original-fields.csv"
        self.ref=parse_geo(self.geo,nx=50,ny=50,zone=50,hem="N",
                            x0=510.885,y0=3531.269,dx=.1)
        with self.csv.open("w",newline="") as f:
            w=csv.DictWriter(f,fieldnames=COLS,lineterminator="\n")
            w.writeheader()
            for n in range(2500):
                row={"i":n%50+1,"j":n//50+1}
                row.update({key:self.ref[key][n] for key,_,_ in FIELDS})
                w.writerow(row)

    def test_same_original_parser_values_are_exact(self):
        result=compare(self.geo,self.csv,self.geo,self.base/"verdict.json",
                 zone=50,hem="N",nx=50,ny=50,x0=510.885,y0=3531.269,dx=.1)
        self.assertEqual(result["failures"],0)
        self.assertEqual(result["values_compared"],20000)
        self.assertEqual(result["status"],"P3_NONHEFEI_ORIGINAL_MAKEGEO_PASS")

    def test_mismatch_raw_category_fails_even_if_formatted_geo_equal(self):
        data=self.csv.read_text().splitlines()
        pieces=data[1].split(",")
        pieces[2]=str(int(float(pieces[2]))+1)
        data[1]=",".join(pieces)
        self.csv.write_text("\n".join(data)+"\n")
        result=compare(self.geo,self.csv,self.geo,self.base/"bad.json",
                 zone=50,hem="N",nx=50,ny=50,x0=510.885,y0=3531.269,dx=.1)
        self.assertGreater(result["failures"],0)
        self.assertGreater(result["metrics"]["category"]["csv_outside_fixed_precision_tolerance"],0)

    def test_reject_dynamic_wrong_crs_shape_and_origin(self):
        for values in (
            dict(nx=40,ny=50,zone=50,hem="N",x0=510.885,y0=3531.269,dx=.1),
            dict(nx=50,ny=50,zone=52,hem="N",x0=510.885,y0=3531.269,dx=.1),
            dict(nx=50,ny=50,zone=50,hem="N",x0=510.886,y0=3531.269,dx=.1),
        ):
            with self.subTest(values=values):
                with self.assertRaisesRegex(ValueError,"P3_D3_ORIGINAL_COMPARISON"):
                    parse_geo(self.geo,**values)


if __name__=="__main__":
    unittest.main()
