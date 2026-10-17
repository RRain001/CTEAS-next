"""Test the scoped C++ text format bridge using frozen original source values.

Input CSV is synthesized from immutable original LU/TERREL test fixtures, NOT
newly computed P1/P2: therefore passing proves parser/serializer/P3 handoff,
not complete P1/P2 native scientific input acceptance.
"""
import argparse
import csv
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ADAPTER = P3 = ROOT = None
CATS = (11,12,13,14,15,16,17,21,22,23,24,31,32,33,41,42,43,
        51,52,53,54,55,61,62,71,72,73,74,75,76,77,81,82,83,84,85,91,92)


class P12ToP3Contract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = ROOT / "project/cases/hefei5km_2022_reference_case_20261011"
        cls.terrain_ref = cls.folder / "geo/terrel/terrel.dat"
        cls.lu_ref = cls.folder / "geo/ctgproc/lu.dat"
        cls.geo_ref = cls.folder / "geo/makegeo/geo.dat"
        cls.control = cls.folder / "geo/makegeo/makegeo.inp"
        terrain_lines = cls.terrain_ref.read_text().splitlines()
        lu_lines = cls.lu_ref.read_text().splitlines()
        assert len(terrain_lines) == 260
        assert len(lu_lines) == 2511
        assert tuple(map(int,lu_lines[10].split())) == CATS
        original = [float(v) for line in terrain_lines[10:] for v in line.split()]
        assert len(original) == 2500 and all(math.isfinite(x) and x > -998 for x in original)
        cls.heights = [original[(49-j)*50+i] for j in range(50) for i in range(50)]
        cls.fractions = []
        for n, line in enumerate(lu_lines[11:]):
            row = line.split()
            assert len(row) == 41 and (int(row[0]),int(row[1])) == (n%50+1,n//50+1)
            assert row[-1] == "."
            cls.fractions.append([float(x) for x in row[2:-1]])

    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="cteas_p12_p3_")
        self.addCleanup(temp.cleanup)
        self.tmp = Path(temp.name)
        self.csv1,self.csv2 = self.tmp/"p1.csv",self.tmp/"p2.csv"
        self.terrel,self.lu = self.tmp/"terrel.dat",self.tmp/"lu.dat"
        with self.csv1.open("w", newline="") as f:
            w=csv.writer(f);w.writerow(("i","j","hits","elevation_m"))
            for n,z in enumerate(self.heights):
                w.writerow((n%50+1,n//50+1,1,f"{z:.9f}"))
        with self.csv2.open("w", newline="") as f:
            w=csv.writer(f);w.writerow(("i","j","samples",*(f"cat{n}" for n in CATS)))
            for n,values in enumerate(self.fractions):
                w.writerow((n%50+1,n//50+1,1,*(f"{x:.12f}" for x in values)))

    def run_writer(self,mode,src,dest):
        return subprocess.run([str(ADAPTER),mode,str(src),str(dest)],
                              capture_output=True,text=True,timeout=35)

    def write_both(self):
        for mode,src,dst in (("terrain",self.csv1,self.terrel),
                             ("landuse",self.csv2,self.lu)):
            p=self.run_writer(mode,src,dst)
            self.assertEqual(p.returncode,0,p.stderr)

    def test_frozen_terrain_and_landuse_values_and_headers(self):
        self.write_both()
        terra=self.terrel.read_text().splitlines()
        lu=self.lu.read_text().splitlines()
        self.assertEqual(len(terra),260)
        self.assertEqual(len(lu),2511)
        self.assertEqual(terra[0].split()[:2],["TERREL.DAT","2.0"])
        self.assertEqual(lu[0].split()[:2],["LU.DAT","2.1"])
        self.assertEqual(terra[9].split(),["W_E","N_S"])
        self.assertEqual(lu[4].strip(),"FRACTION")
        self.assertEqual(tuple(map(int,lu[10].split())),CATS)
        self.assertEqual([float(x) for line in terra[10:] for x in line.split()],
                         [float(x) for line in self.terrain_ref.read_text().splitlines()[10:]
                          for x in line.split()])
        for original,generated in zip(self.lu_ref.read_text().splitlines()[11:],lu[11:]):
            a,b=original.split(),generated.split()
            self.assertEqual(a[:2],b[:2])
            self.assertEqual(a[-1],b[-1])
            self.assertEqual(list(map(float,a[2:-1])),list(map(float,b[2:-1])))

    def test_unchanged_p3_formatted_science_values(self):
        self.write_both()
        result_csv,result_geo=self.tmp/"p3.csv",self.tmp/"geo.dat"
        p=subprocess.run([str(P3),str(self.control),str(self.lu),str(self.terrel),
                          str(result_csv),str(result_geo)],capture_output=True,text=True,timeout=40)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        report=self.tmp/"comparison.json"
        p=subprocess.run([sys.executable,str(ROOT/"native_cpp/reference/compare_p3_makegeo.py"),
                          "--reference",str(self.geo_ref),"--cpp",str(result_csv),
                          "--cpp-geo",str(result_geo),"--report",str(report)],
                          capture_output=True,text=True,timeout=40)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        data=json.loads(report.read_text())
        self.assertEqual(data["status"],"PASS_SCOPED")
        self.assertEqual(data["failures"],0)
        self.assertEqual(sum(v["compared_cells"] for v in data["writer_exact_formatted_value_gate"].values()),20000)

    def corrupt(self,file,index,field,value):
        lines=file.read_text().splitlines()
        row=lines[index].split(",")
        row[field]=value
        lines[index]=",".join(row)
        file.write_text("\n".join(lines)+"\n")

    def test_reject_terrain_nan(self):
        self.corrupt(self.csv1,1,3,"nan")
        self.assertNotEqual(self.run_writer("terrain",self.csv1,self.terrel).returncode,0)
        self.assertFalse(self.terrel.exists())

    def test_reject_uncovered_terrain(self):
        self.corrupt(self.csv1,1,2,"0")
        self.assertNotEqual(self.run_writer("terrain",self.csv1,self.terrel).returncode,0)

    def test_reject_wrong_grid_index(self):
        self.corrupt(self.csv1,2,0,"7")
        self.assertNotEqual(self.run_writer("terrain",self.csv1,self.terrel).returncode,0)

    def test_reject_missing_rows(self):
        self.csv1.write_text("\n".join(self.csv1.read_text().splitlines()[:-1])+"\n")
        self.assertNotEqual(self.run_writer("terrain",self.csv1,self.terrel).returncode,0)

    def test_reject_changed_category_order(self):
        lines=self.csv2.read_text().splitlines()
        a=lines[0].split(",");a[3],a[4]=a[4],a[3]
        lines[0]=",".join(a)
        self.csv2.write_text("\n".join(lines)+"\n")
        self.assertNotEqual(self.run_writer("landuse",self.csv2,self.lu).returncode,0)

    def test_reject_negative_fraction(self):
        self.corrupt(self.csv2,1,3,"-0.1")
        self.assertNotEqual(self.run_writer("landuse",self.csv2,self.lu).returncode,0)
        self.assertFalse(self.lu.exists())

    def test_reject_nonfinite_fraction(self):
        self.corrupt(self.csv2,1,3,"nan")
        self.assertNotEqual(self.run_writer("landuse",self.csv2,self.lu).returncode,0)

    def test_reject_incomplete_landuse_fraction(self):
        lines=self.csv2.read_text().splitlines()
        row=lines[1].split(",");row[3:]=["0.0"]*38
        lines[1]=",".join(row)
        self.csv2.write_text("\n".join(lines)+"\n")
        self.assertNotEqual(self.run_writer("landuse",self.csv2,self.lu).returncode,0)

    def test_deterministic_bytes_and_no_overwrite(self):
        self.write_both()
        a,b=self.terrel.read_bytes(),self.lu.read_bytes()
        self.assertNotEqual(self.run_writer("terrain",self.csv1,self.terrel).returncode,0)
        self.assertNotEqual(self.run_writer("landuse",self.csv2,self.lu).returncode,0)
        self.assertEqual((a,b),(self.terrel.read_bytes(),self.lu.read_bytes()))
        another=self.tmp/"terrain-second.dat"
        self.assertEqual(self.run_writer("terrain",self.csv1,another).returncode,0)
        self.assertEqual(a,another.read_bytes())

    def test_missing_native_csv_fails_closed(self):
        self.assertNotEqual(self.run_writer("terrain",self.tmp/"missing.csv",self.terrel).returncode,0)
        self.assertFalse(self.terrel.exists())


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--adapter",type=Path,required=True)
    parser.add_argument("--p3",type=Path,required=True)
    parser.add_argument("--root",type=Path,required=True)
    args=parser.parse_args()
    ADAPTER=args.adapter.resolve()
    P3=args.p3.resolve()
    ROOT=args.root.resolve()
    unittest.main(argv=[sys.argv[0]],verbosity=2)
