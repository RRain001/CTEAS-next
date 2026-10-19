"""Synthetic contract tests ONLY for new regional original-science runner."""
import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from native_cpp.reference.validate_p2_glazas_original import CATS, GateError
from native_cpp.reference.validate_p2_glazas_regions import (
    REGIONS, METHOD, control_for_region, parse_lu,
    parse_native_hits, compare,
)

ROOT = Path(__file__).resolve().parents[3]
TEMPLATE = ROOT/"project/cases/hefei5km_2022_reference_case_20261011/geo/ctgproc/ctgproc.inp"


def synthetic_lu(case, *, hits):
    header = ["LU.DAT  2.1 Coordinates", " 2", "Synthetic test only",
              "Synthetic test only", "HITS" if hits else "FRACTION",
              "UTM", f"{case.zone}{case.hem}", "WGS-84  02-21-2003",
              f"{case.nx} {case.ny} {case.xrefkm} {case.yrefkm} "
              f"{case.dgridkm} {case.dgridkm} 38",
              "KM", " ".join(map(str,CATS))]
    first = ["5"] + ["0"]*37 if hits else ["1.000"]+["0.000"]*37
    rows = [f"{i} {j} " + " ".join(first) + " ." for j in range(1,case.ny+1)
            for i in range(1,case.nx+1)]
    return "\n".join(header+rows)+"\n"


class RegionalOriginalSoftwareOnly(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="regional-glazas-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_science_decks_really_use_separate_utm_hemisphere_and_modes(self):
        raw = TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("1 !GEN =",raw)
        for case in REGIONS.values():
            with self.subTest(case=case.name):
                frac = control_for_region(raw,case,hits=False)
                hits = control_for_region(raw,case,hits=True)
                for deck in (frac,hits):
                    self.assertIn("1 !GLAZAS = glcc.img !",deck)
                    self.assertNotIn("1 !GEN =",deck)
                    self.assertIn(f"! IUTMZN = {case.zone} !",deck)
                    self.assertIn(f"! UTMHEM = {case.hem} !",deck)
                    self.assertIn(f"! NX = {case.nx} !",deck)
                    self.assertIn(f"! NY = {case.ny} !",deck)
                self.assertIn("! LFINAL = T !",frac)
                self.assertIn("! LFINAL = F !",hits)
        self.assertIn("1 !GEN =",raw)

    def test_both_regions_original_lu_formats_and_zero_differences(self):
        for case in REGIONS.values():
            with self.subTest(case=case.name):
                original_hits=self.root/(case.name+"-hits.dat")
                original_fraction=self.root/(case.name+"-fraction.dat")
                original_hits.write_text(synthetic_lu(case,hits=True))
                original_fraction.write_text(synthetic_lu(case,hits=False))
                oh=parse_lu(original_hits,case,hits=True)
                of=parse_lu(original_fraction,case,hits=False)
                assert len(oh)==len(of)==case.nx*case.ny
                ns=[5]*(case.nx*case.ny)
                answer=compare(case,oh,of,oh,of,ns)
                self.assertEqual(answer["overall"],
                                 "PASS_SCOPED_ORIGINAL_GLAZAS_REGIONAL")
                self.assertEqual(answer["compared_values"],
                                 case.nx*case.ny*38)
                self.assertEqual(answer["integer_exceedances"],0)
                self.assertEqual(answer["fraction_exceedances"],0)
                self.assertEqual(answer["original_submesh_hits"],
                                 case.nx*case.ny*5)
                changed=[row.copy() for row in oh]
                changed[0][0]-=1
                changed[0][1]+=1
                r=compare(case,oh,of,changed,of,ns)
                self.assertEqual(r["integer_exceedances"],2)
                self.assertEqual(r["overall"],
                                 "FAIL_REGIONAL_ORIGINAL_GLAZAS_SCIENCE")

    def test_wrong_region_header_and_mode_do_not_pass(self):
        cases=list(REGIONS.values())
        a,b=cases[0],cases[1]
        f=self.root/"fake.dat"
        f.write_text(synthetic_lu(a,hits=True))
        with self.assertRaisesRegex(GateError,"REGIONAL_LU_CRS"):
            parse_lu(f,b,hits=True)
        with self.assertRaisesRegex(GateError,"REGIONAL_LU_WRONG_MODE"):
            parse_lu(f,a,hits=False)
        f.write_text(synthetic_lu(a,hits=True).replace("WGS-84","NAD-83"))
        with self.assertRaisesRegex(GateError,"REGIONAL_LU_CRS"):
            parse_lu(f,a,hits=True)

    def test_native_region_manifest_hash_and_zero_hit_guard(self):
        from native_cpp.reference.validate_p2_glazas_original import SRC_SHA
        for case in REGIONS.values():
            with self.subTest(case=case.name):
                path=self.root/(case.name+"-native.csv")
                with path.open("w",newline="",encoding="utf-8") as fp:
                    w=csv.writer(fp)
                    w.writerow(["i","j","samples"]+[f"cat{k}" for k in CATS])
                    for j in range(1,case.ny+1):
                        for i in range(1,case.nx+1):
                            w.writerow([i,j,5,5]+[0]*37)
                manifest=dict(producer="cteas_p2_glcc_raw",
                              source_sha256=SRC_SHA,method=METHOD,
                              utm_epsg=case.epsg,nx=case.nx,ny=case.ny,
                              mesh=case.mesh,xrefkm=case.xrefkm,
                              yrefkm=case.yrefkm,dgridkm=float(case.dgridkm),
                              included=5*case.nx*case.ny,
                              hits_csv_sha256=hashlib.sha256(
                                  path.read_bytes()).hexdigest())
                values,samples=parse_native_hits(path,case,manifest)
                self.assertEqual(len(values),case.nx*case.ny)
                self.assertEqual(sum(samples),manifest["included"])
                tamper=dict(manifest,hits_csv_sha256="0"*64)
                with self.assertRaisesRegex(GateError,"UNTRUSTED_NATIVE"):
                    parse_native_hits(path,case,tamper)
                tamper=dict(manifest,method="HEFEI_FAKE_SCIENCE_PASS")
                with self.assertRaisesRegex(GateError,"UNTRUSTED_NATIVE"):
                    parse_native_hits(path,case,tamper)


if __name__ == "__main__":
    unittest.main()
