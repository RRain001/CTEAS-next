"""P2-B scientific mapping *review only* on actual model-grid areas.

Synthetic fixtures cover exact area, candidate-only preview, ambiguous
floodplain/water/urban/marsh isolation, and all fail-closed contracts.
"""
import copy
import csv
import json
from pathlib import Path
import tempfile
import unittest

from scripts.s2g.audit_glc_modelgrid_crosswalk import compute
from scripts.s2g.audit_glc_crosswalk_review import AuditError

ROOT=Path(__file__).resolve().parents[3]
META=ROOT/"data/landcover/glc_fcs30d/v1_2022/hefei/metadata.json"
PROPOSAL=ROOT/"docs/plans/ISSUE53_GLC35_USGS92_REVIEW_CANDIDATES_20261018.json"
TIFF=META.parent/"hefei_2022_30m.tif"


class RealModelGridCrosswalkReview(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta=json.loads(META.read_text())
        cls.proposal=json.loads(PROPOSAL.read_text())

    def setUp(self):
        tmp=tempfile.TemporaryDirectory(prefix="glc-grid-review-")
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.manifest={
            "producer":"cteas_p2_glc_raw",
            "source_kind":"GLC_FCS30D_2022_30m",
            "source_sha256":self.meta["sha256"],
            "raw_category_namespace":"GLC_FCS30D_35",
            "method":"exact_north_up_same_utm_pixel_cell_rectangle_intersection",
            "coverage_policy":"REJECT_ANY_NODATA_OR_INCOMPLETE_CELL",
            "crosswalk_status":"P2_MAPPING_REVIEW_REQUIRED",
            "usgs92_lu_dat":"NOT_RUN",
            "p3_geo_dat":"NOT_RUN",
            "utm_epsg":32650,"nx":2,"ny":2,"dgridkm":0.1,
            "xrefkm":"510.885","yrefkm":"3531.269",
            "evidence_status":"PRODUCED_UNVERIFIED"
        }
        self.fraction=self.root/"p2_raw_fractions.csv"
        self.area=self.root/"p2_raw_class_area_m2.csv"
        self.cells=[
            {10:5000,183:2500,190:2500},
            {20:10000},
            {210:6000,182:4000},
            {52:5000,11:5000}
        ]
        self.write_fixture()

    def write_fixture(self):
        codes=self.meta["allowed_class_codes"]
        with self.fraction.open("w",newline="") as a,self.area.open("w",newline="") as b:
            fw=csv.writer(a);aw=csv.writer(b)
            fw.writerow(["i","j","cell_area_m2","valid_area_m2","coverage_fraction"]+
                        [f"glc{x}" for x in codes])
            aw.writerow(["i","j"]+[f"glc{x}" for x in codes])
            for idx,d in enumerate(self.cells):
                base=[idx%2+1,idx//2+1]
                fw.writerow(base+[10000.,10000.,1.]+
                            [f"{d.get(k,0)/10000.:.12f}" for k in codes])
                aw.writerow(base+[f"{d.get(k,0):.8f}" for k in codes])

    def run_audit(self, *, proposal=None,manifest=None):
        return compute(self.meta,proposal or self.proposal,
                       manifest or self.manifest,
                       self.fraction,self.area,source_tif=TIFF)

    def test_exact_grid_area_policy_and_ambiguous_codes_not_falsely_mapped(self):
        report,rows=self.run_audit()
        self.assertEqual(report["model_cells"],4)
        self.assertEqual(report["model_area_m2"],40000.)
        self.assertEqual(report["area_by_review_tier_m2"],
                         {"candidate":25000.,"site_evidence":6500.,"blocked":8500.})
        self.assertEqual(report["fraction_by_review_tier"],
                         {"candidate":0.625,"site_evidence":0.1625,"blocked":0.2125})
        self.assertEqual(report["cells_containing_blocked_mapping"],2)
        self.assertEqual(report["cells_requiring_site_evidence"],2)
        self.assertEqual(report["raw_area_by_glc_class_m2"]["183"],2500.)
        self.assertEqual(report["raw_area_by_glc_class_m2"]["210"],6000.)
        self.assertEqual(float(rows[0]["candidate_usgs21"]),0.5)
        self.assertEqual(float(rows[0]["unmapped_blocked_fraction"]),0.25)
        self.assertEqual(float(rows[2]["site_evidence_fraction"]),0.4)
        self.assertEqual(float(rows[2]["unmapped_blocked_fraction"]),0.6)
        self.assertEqual(float(rows[2]["candidate_usgs52"]),0.)
        self.assertEqual(report["GLC_TO_USGS92_LU_DAT"],"NOT_AUTHORIZED")
        self.assertEqual(report["P3_GEO_DAT"],"NOT_RUN")

    def test_no_fabricated_complete_crosswalk(self):
        proposal=copy.deepcopy(self.proposal)
        proposal["is_approved"]=True
        with self.assertRaisesRegex(AuditError,"UNAUTHORIZED_MAPPING_APPROVAL"):
            self.run_audit(proposal=proposal)
        proposal=copy.deepcopy(self.proposal)
        row=next(x for x in proposal["classes"] if x["code"]==210)
        row["candidate_target_usgs92"]=52
        with self.assertRaisesRegex(AuditError,"INVALID_CANDIDATE_USGS92"):
            self.run_audit(proposal=proposal)

    def test_source_method_and_kind_must_remain_true(self):
        for bad in ({"method":"point_sampling"}, {"source_sha256":"0"*64},
                    {"crosswalk_status":"PASS"},{"usgs92_lu_dat":"RUN"},
                    {"utm_epsg":3857}):
            with self.subTest(bad=bad):
                m=dict(self.manifest,**bad)
                with self.assertRaises(AuditError):
                    self.run_audit(manifest=m)

    def test_fraction_and_area_not_interchangeable(self):
        self.cells[0]={10:2500,183:2500,190:2500}
        self.write_fixture()
        with self.assertRaisesRegex(AuditError,"AREA_OR_TIER_CONSERVATION"):
            self.run_audit()
        self.cells[0]={10:5000,183:2500,190:2500}
        self.write_fixture()
        contents=self.fraction.read_text().replace("0.500000000000","0.510000000000",1)
        self.fraction.write_text(contents)
        with self.assertRaisesRegex(AuditError,"FRACTION_AREA_MISMATCH"):
            self.run_audit()

    def test_no_partial_coverage_or_cell_reorder(self):
        contents=self.fraction.read_text().replace(",10000.0,10000.0,1.0,",
                                                     ",10000.0,9000.0,0.9,",1)
        self.fraction.write_text(contents)
        with self.assertRaisesRegex(AuditError,"INCOMPLETE_COVERAGE"):
            self.run_audit()
        self.write_fixture()
        contents=self.area.read_text().replace("1,1,","2,1,",1)
        self.area.write_text(contents)
        with self.assertRaisesRegex(AuditError,"MODEL_GRID_CELL_ORDER"):
            self.run_audit()

    def test_missing_cell_or_illegal_class(self):
        lines=self.area.read_text().splitlines()
        self.area.write_text("\n".join(lines[:-1])+"\n")
        with self.assertRaisesRegex(AuditError,"ROW_COUNT"):
            self.run_audit()
        self.write_fixture()
        lines=self.fraction.read_text().splitlines()
        lines[0]=lines[0].replace("glc210","glc999")
        self.fraction.write_text("\n".join(lines)+"\n")
        with self.assertRaisesRegex(AuditError,"CSV_SCHEMA_DRIFT"):
            self.run_audit()


if __name__=="__main__":
    unittest.main()
