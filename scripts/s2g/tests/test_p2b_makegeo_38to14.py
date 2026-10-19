"""Review-only: real frozen original MAKEGEO 38 -> 14 physics-contract tests."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from scripts.s2g.audit_p2b_makegeo_38to14 import (
    CANDIDATE_ALTERNATIVES, PARAMS,
    parse_original_makegeo, surface_fingerprint, evaluate,
)
from scripts.s2g.audit_glc_crosswalk_review import AuditError

ROOT=Path(__file__).resolve().parents[3]
MAKEGEO=ROOT/"project/cases/hefei5km_2022_reference_case_20261011/geo/makegeo/makegeo.inp"
METADATA=ROOT/"data/landcover/glc_fcs30d/v1_2022/hefei/metadata.json"
PROPOSAL=ROOT/"docs/plans/ISSUE53_GLC35_USGS92_REVIEW_CANDIDATES_20261018.json"


class Makegeo38to14Review(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model=parse_original_makegeo(MAKEGEO)
        cls.meta=json.loads(METADATA.read_text())
        cls.prop=json.loads(PROPOSAL.read_text())

    def test_exact_selected_38_to_14_original_class_table(self):
        self.assertEqual(len(self.model["input_38"]),38)
        self.assertEqual(self.model["output_14"],
                         [10,-20,20,30,40,51,54,55,60,61,62,70,80,90])
        self.assertEqual(self.model["input_water"],[51,52,53,54,55])
        self.assertEqual(self.model["selected_controls"]["CFRACT"],.5)
        self.assertEqual(self.model["selected_controls"]["FLUMIN"],.96)
        self.assertEqual(self.model["selected_controls"]["NSPLIT"],0)

    def test_inland_freshwater_equal_6_parameters_same_output(self):
        d=self.model["input_38"]
        for n in (52,53):
            self.assertEqual(surface_fingerprint(d[51]),surface_fingerprint(d[n]))
        self.assertEqual(d[51]["output_14"],51)
        self.assertEqual(d[51]["z0_m"],0.001)
        self.assertTrue(d[51]["is_water_for_CFraCT"])
        self.assertEqual(d[54]["output_14"],54)
        self.assertNotEqual(surface_fingerprint(d[53]),surface_fingerprint(d[54]))

    def test_urban_same_output_but_different_physics(self):
        d=self.model["input_38"]
        self.assertEqual(d[11]["output_14"],d[16]["output_14"])
        self.assertEqual(d[11]["z0_m"],.5)
        self.assertEqual(d[16]["z0_m"],1.)
        self.assertNotEqual(surface_fingerprint(d[11]),surface_fingerprint(d[16]))

    def test_marsh_flood_flat_and_open_water_physics_differ(self):
        d=self.model["input_38"]
        self.assertEqual([d[k]["output_14"] for k in (61,62,77,52)],
                         [61,62,70,51])
        self.assertEqual([d[k]["z0_m"] for k in (61,62,77,52)],
                         [1.0,0.2,0.05,0.001])
        self.assertTrue(d[52]["is_water_for_CFraCT"])
        self.assertFalse(d[62]["is_water_for_CFraCT"])

    def test_site_review_no_fabricated_approval(self):
        report=evaluate(self.prop,self.meta,self.model)
        self.assertEqual(report["status"],"P2_MAPPING_REVIEW_REQUIRED")
        self.assertEqual(report["lu_dat_38_production"],"NOT_AUTHORIZED")
        self.assertEqual(report["p3_makegeo_14_production"],"NOT_RUN")
        cls={r["glc_code"]:r for r in report["mapping_review_by_source_class"]}
        self.assertEqual(len(cls),35)
        self.assertEqual(cls[210]["alternative_inputs_FOR_REVIEW"],[51,52,53,54])
        self.assertEqual(cls[210]["alternative_fingerprints"]["51"]["output_14"],51)
        self.assertFalse(cls[210]["all_alternatives_identical"])
        self.assertEqual(cls[183]["candidate_output_14_NOT_APPROVED"],None)
        self.assertEqual(cls[190]["candidate_output_14_NOT_APPROVED"],10)
        self.assertFalse(cls[190]["all_alternatives_identical"])
        self.assertEqual(cls[182]["candidate_output_14_NOT_APPROVED"],62)

    def test_broken_selected_38_to_14_controls_fail(self):
        real=MAKEGEO.read_text()
        for old,new in (("! NOUTCAT = 14 !","! NOUTCAT = 12 !"),
                        ("! CFRACT = 0.5  !","! CFRACT = 0.7  !"),
                        ("! X =   53,    0.001","! X =   53,    0.100")):
            with self.subTest(old=old):
                self.assertIn(old,real)
                tmp=tempfile.TemporaryDirectory()
                self.addCleanup(tmp.cleanup)
                file=Path(tmp.name)/"makegeo.inp"
                file.write_text(real.replace(old,new,1))
                if old.startswith("! X"):
                    with self.assertRaisesRegex(AuditError,"FRESHWATER"):
                        evaluate(self.prop,self.meta,parse_original_makegeo(file))
                else:
                    with self.assertRaises(AuditError):
                        parse_original_makegeo(file)

    def test_real_grid_evidence_failclosed_no_mapping_permission(self):
        evidence={"status":"P2_MAPPING_REVIEW_REQUIRED",
                  "source_data_sha256":self.meta["sha256"],
                  "comparison_basis":"REAL_MODEL_GRID_AREA_M2_NOT_BUFFERED_PIXEL_COUNTS",
                  "GLC_TO_USGS92_LU_DAT":"NOT_AUTHORIZED",
                  "model_cells":2500, "model_area_m2":25_000_000.,
                  "raw_area_by_glc_class_m2":{str(c):0. for c in self.meta["allowed_class_codes"]}}
        evidence["raw_area_by_glc_class_m2"]["210"]=340140.
        evidence["raw_area_by_glc_class_m2"]["190"]=2389205.
        evidence["raw_area_by_glc_class_m2"]["20"]=22270655.
        report=evaluate(self.prop,self.meta,self.model,modelgrid=evidence)
        self.assertEqual(report["review_required_observed_classes"],[190,210])
        evidence["model_area_m2"]+=100.
        with self.assertRaisesRegex(AuditError,"UNTRUSTED_CLASS_AREAS"):
            evaluate(self.prop,self.meta,self.model,modelgrid=evidence)
        evidence["model_area_m2"]-=100.
        evidence["status"]="PASS"
        with self.assertRaisesRegex(AuditError,"UNTRUSTED_MODELGRID_REVIEW"):
            evaluate(self.prop,self.meta,self.model,modelgrid=evidence)


if __name__=="__main__":
    unittest.main()
