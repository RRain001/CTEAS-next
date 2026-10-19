"""Issue #53: user-confirmed 34-class mapping; 210 must fail closed."""
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[3]
POLICY=ROOT/"docs/plans/ISSUE53_GLC35_USGS38_USER_SELECTED_20261019.json"
METADATA=ROOT/"data/landcover/glc_fcs30d/v1_2022/hefei/metadata.json"
EXPECTED={10:21,11:21,12:22,20:21,51:42,52:42,61:41,62:41,71:42,72:42,81:41,82:41,91:43,92:43,120:32,121:32,122:32,130:31,140:83,150:77,152:77,153:77,181:61,182:62,183:77,184:77,185:61,186:62,187:72,190:16,200:77,201:74,202:73,220:91}

class TestP2BUserMapping(unittest.TestCase):
    def test_exact_user_mapping_and_source_legend(self):
        p=json.loads(POLICY.read_text(encoding="utf-8"))
        m=json.loads(METADATA.read_text(encoding="utf-8"))
        self.assertEqual(p["schema"],"cteas.p2b.glc35_usgs38_user_selected_mapping.v1")
        self.assertFalse(p["production_authorized"])
        self.assertFalse(p["p3_makegeo_modified"])
        self.assertFalse(p["legacy_p2a_modified"])
        self.assertEqual(p["reference_hefei_glc_2022_sha256"],m["sha256"])
        rows=p["fixed_classes"]; self.assertEqual(len(rows),34)
        mapping={x["glc_code"]:x["usgs_code"] for x in rows}
        self.assertEqual(mapping,EXPECTED)
        self.assertEqual(set(mapping)|{210},set(m["allowed_class_codes"]))
        self.assertEqual(len(p["conditional_classes"]),1)
        water=p["conditional_classes"][0]
        self.assertEqual(water["glc_code"],210)
        self.assertIsNone(water["fallback_usgs"])
        self.assertEqual({x["usgs_code"] for x in water["outcomes"]},{52,55})
        self.assertEqual(
            [x["usgs_code"] for x in water["outcomes"]], [52,55])
        self.assertEqual(water["policy_status"],
            "USER_APPROVED_BINARY_RULE_PENDING_GSHHG_SOURCE_AND_IMPLEMENTATION_VALIDATION")
        self.assertEqual(water["shoreline_cutting_method"].startswith("Exact"),True)
        self.assertIsNone(water["fallback_usgs"])
        self.assertEqual(p["source_authentication"]["selected_resolution"],"f")
        self.assertEqual(p["source_authentication"]["primary_land_sea_polygon"],
            "GSHHS_shp/f/GSHHS_f_L1.shp")
        self.assertFalse(p["source_authentication"]["wdbii_required_for_binary_water_split"])
        self.assertFalse(p["source_authentication"]["zip_downloaded_and_verified"])
        self.assertIn("VERIFY_FULL_VS_HIGH_COASTLINE_CLASS_DIFFERENCE_AND_TRACE_CONFLICTS",p["gates"])
        self.assertNotIn("REVIEW_54_VS_55_MARINE_DISAMBIGUATION",p["gates"])

if __name__=="__main__": unittest.main()
