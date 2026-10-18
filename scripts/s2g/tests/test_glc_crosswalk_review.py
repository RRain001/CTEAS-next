"""Issue #53 scientific review candidates MUST NOT be promoted to approved P2."""
import copy
import json
from pathlib import Path
import unittest
from scripts.s2g.audit_glc_crosswalk_review import audit, AuditError

ROOT=Path(__file__).resolve().parents[3]
META=ROOT/"data/landcover/glc_fcs30d/v1_2022/hefei/metadata.json"
TIFF=META.parent/"hefei_2022_30m.tif"
PROP=ROOT/"docs/plans/ISSUE53_GLC35_USGS92_REVIEW_CANDIDATES_20261018.json"

class MappingAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta=json.loads(META.read_text())
        cls.prop=json.loads(PROP.read_text())

    def test_real_committed_tif_and_full_35_classes(self):
        report=audit(self.meta,self.prop,source_tif=TIFF)
        self.assertEqual(report["status"],"P2_MAPPING_REVIEW_REQUIRED")
        self.assertEqual(report["total_buffered_pixels"],29584)
        self.assertTrue(report["source_tif_bytes_verified"])
        self.assertEqual(report["full_legend_class_count"],35)
        self.assertEqual(report["actual_class_count"],12)
        self.assertTrue(report["not_model_grid_area_fractions"])
        self.assertIn(183,report["blocked_unmapped_classes"])
        self.assertIn(210,report["blocked_unmapped_classes"])
        self.assertEqual(report["GLC_TO_USGS92_LU_DAT"],"NOT_AUTHORIZED")

    def test_no_silent_approval(self):
        p=copy.deepcopy(self.prop);p["is_approved"]=True
        with self.assertRaisesRegex(AuditError,"UNAUTHORIZED_MAPPING_APPROVAL"):
            audit(self.meta,p)
        p=copy.deepcopy(self.prop);p["classes"][0]["approval"]="APPROVED"
        with self.assertRaisesRegex(AuditError,"UNAUTHORIZED_CLASS_MAPPING_APPROVAL"):
            audit(self.meta,p)

    def test_no_concealed_floodplain_to_wetland_or_water_to_lake(self):
        for code,target in [(183,62),(210,52)]:
            p=copy.deepcopy(self.prop)
            row=next(x for x in p["classes"] if x["code"]==code)
            row["candidate_target_usgs92"]=target
            with self.assertRaises(AuditError):
                audit(self.meta,p)

    def test_forest_open_closed_names_authoritative(self):
        for code in (51,52,61,62,71,72,81,82,91,92):
            p=copy.deepcopy(self.prop)
            row=next(x for x in p["classes"] if x["code"]==code)
            row["source_label"]="Open unknown" if code%10==1 else "Closed unknown"
            with self.assertRaisesRegex(AuditError,"FOREST_CLOSED_OPEN"):
                audit(self.meta,p)

    def test_histogram_immutable_and_source_sha(self):
        p=copy.deepcopy(self.prop)
        p["classes"][0]["observed_buffered_pixels"]+=1
        with self.assertRaisesRegex(AuditError,"HISTOGRAM_CANDIDATE_MISMATCH"):
            audit(self.meta,p)
        p=copy.deepcopy(self.prop)
        p["source_data_sha256"]="0"*64
        with self.assertRaisesRegex(AuditError,"SOURCE_SHA_MISMATCH"):
            audit(self.meta,p)

    def test_site_evidence_not_automatically_approved(self):
        p=copy.deepcopy(self.prop)
        for code in (182,190):
            row=next(x for x in p["classes"] if x["code"]==code)
            row["evidence_tier"]="candidate"
            with self.assertRaises(AuditError):
                audit(self.meta,p)
            row["evidence_tier"]="site_evidence"

    def test_duplicate_or_missing_class_rejected(self):
        for broken in (self.prop["classes"][:-1],self.prop["classes"][:-1]+[self.prop["classes"][0]]):
            p=copy.deepcopy(self.prop);p["classes"]=broken
            with self.assertRaises(AuditError):
                audit(self.meta,p)

if __name__=="__main__":
    unittest.main()
