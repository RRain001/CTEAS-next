"""#53 GLAZAS gate SOFTWARE ONLY tests. Captured historical LU is a FORMAT
fixture (GEN path); NEVER considered original same-source GLAZAS evidence.
"""
from pathlib import Path
import hashlib
import json
import tempfile
import unittest
from native_cpp.reference.validate_p2_glazas_original import (
    CATS, SRC_SHA, GateError, make_glazas_control, parse_lu,
    parse_original_used, compare, safe_original_file,
)

ROOT=Path(__file__).resolve().parents[3]
CASE=ROOT/"project/cases/hefei5km_2022_reference_case_20261011/geo/ctgproc"
class OriginalGlazasGates(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(prefix="cteas-p2-glazas-gate-")
        self.addCleanup(tmp.cleanup)
        self.out=Path(tmp.name)

    def test_rewrite_only_one_GLCC_GLAZAS_and_mesh20(self):
        raw=(CASE/"ctgproc.inp").read_text()
        result=make_glazas_control(raw)
        self.assertIn("!GLAZAS = glcc.img !",result)
        self.assertIn("! MESHGLAZ = 20 !",result)
        self.assertIn("! LCOAST = F",result)
        self.assertIn("! DUSGSLA  = ESR-S",result)
        self.assertNotIn("1 !GEN =",result)
        self.assertIn("! XREFKM = 510.885",result)
        self.assertIn("! YREFKM = 3531.269",result)
        self.assertIn("! IUTMZN = 50",result)
        self.assertIn("! NX = 50",result)
        self.assertIn("! NY = 50",result)
        self.assertEqual(result.count("1 !GLAZAS ="),1)
        # Prove control was changed solely in isolated copy.
        self.assertIn("1 !GEN =",raw)

    def test_requires_original_one_dataset_no_fake_acceptance(self):
        s=(CASE/"ctgproc.inp").read_text()
        for bad in (s.replace("1 !GEN =","1 !GLAZAS ="),
                    s.replace("1 !GEN =","2 !GEN ="),
                    s.replace("1 !GEN =","1 !GEN =")+"1 !GEN = x !END!\n"):
            with self.assertRaises(GateError):
                make_glazas_control(bad)

    def test_reference_lu_38_categories_and_2500_rows(self):
        # The repo fixture comes from a historical GEN pathway, not GLAZAS.
        r=parse_lu(CASE/"lu.dat")
        self.assertEqual(len(r),2500)
        self.assertTrue(all(len(x)==38 for x in r))
        self.assertEqual(len(CATS),38)

    def create_manifest(self,lu: Path,used=10011):
        p=self.out/"d3.json"
        p.write_text(json.dumps({
            "producer":"cteas_p2_glcc_lu_dat",
            "source_sha256":SRC_SHA,
            "lu_dat_sha256":hashlib.sha256(lu.read_bytes()).hexdigest(),
            "rows":2500,"classes":38,"total_samples":used
        }))
        return p

    def test_field_comparator_tolerance_and_point_count_independent(self):
        src=CASE/"lu.dat"
        copy=self.out/"native.dat";copy.write_bytes(src.read_bytes())
        lst=self.out/"ctgproc.lst"
        lst.write_text("Number of data points used to update grid: 10011\n")
        manifest=self.create_manifest(copy)
        v=compare(src,copy,lst,manifest)
        self.assertEqual(v["compared_values"],95000)
        self.assertEqual(v["exceedances"],0)
        self.assertEqual(v["max_absolute_fraction_difference"],0)
        self.assertEqual(v["original_glcc_source_pixels_used"],10011)
        self.assertEqual(v["native_d1_d3_submesh_hits"],10011)
        self.assertEqual(v["point_count_comparison"],"NOT_COMPARABLE_DIFFERENT_UNITS")
        self.assertEqual(v["overall"],"PASS_FRACTION_ONLY_PENDING_INTEGER_HITS")
        # Matching parent-pixel and mesh-hit numeric values by coincidence MUST NOT
        # imply scientific original parity, and changing ncount MUST NOT fail
        # fraction-only numeric agreement.
        lst.write_text("Number of data points used to update grid: 56\n")
        v=compare(src,copy,lst,manifest)
        self.assertEqual(v["original_glcc_source_pixels_used"],56)
        self.assertEqual(v["native_d1_d3_submesh_hits"],10011)
        self.assertEqual(v["numeric_gate"],"PASS")
        self.assertEqual(v["point_count_comparison"],"NOT_COMPARABLE_DIFFERENT_UNITS")
        self.assertEqual(v["overall"],"PASS_FRACTION_ONLY_PENDING_INTEGER_HITS")

    def test_nonzero_difference_exceeds_predeclared_threshold(self):
        original=CASE/"lu.dat"
        native=self.out/"native.dat";native.write_bytes(original.read_bytes())
        lines=native.read_text().splitlines()
        # Overwrite one category in a known row while retaining all 41 fields.
        fields=lines[11].split()
        fields[2]="0.999" if fields[2]!="0.999" else "0.000"
        lines[11]=" ".join(fields)
        native.write_text("\n".join(lines)+"\n")
        # Result can fail on summed fractions due to deliberate alteration.
        with self.assertRaises(GateError):
            parse_lu(native)

    def test_invalid_source_lfs_pointer_and_binary_sha(self):
        p=self.out/"img";p.write_text("version https://git-lfs.github.com/spec/v1")
        with self.assertRaisesRegex(GateError,"WRONG_SOURCE_SIZE"):
            safe_original_file(p,expected=SRC_SHA,exact_size=156_000_000)
        with self.assertRaisesRegex(GateError,"SOURCE_SHA256_MISMATCH"):
            safe_original_file(p,expected=SRC_SHA)

    def test_unpinned_original_log_point_count_denied(self):
        l=self.out/"ctgproc.lst";l.write_text("GLAZAS completed\n")
        with self.assertRaisesRegex(GateError,"POINT_COUNT_MISSING"):
            parse_original_used(l)

if __name__=="__main__":
    unittest.main()
