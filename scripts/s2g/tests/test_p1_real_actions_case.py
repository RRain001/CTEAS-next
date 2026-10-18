"""Only stage B0 real-site geometry; never fetch a true DEM in PR CI."""
import tempfile
import unittest
from pathlib import Path
from scripts.s2g.p1_real_actions_case import stage_case,CASE_NAME
from native_cpp.orchestration.case_admission import admit_case
from scripts.s2g.p1_real_srtm90_admission import required_names
from scripts.s2g.p1_terrain_source import case_bbox

class RealP1CaseStageTests(unittest.TestCase):
    def test_exact_seam_grid_reproduces_and_crosses_two_tiles(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            case=stage_case(root)
            self.assertEqual(case.name,CASE_NAME)
            admitted=admit_case(case/"case.yaml")
            self.assertEqual(admitted.nx*admitted.ny,2500)
            self.assertEqual((admitted.utm_zone,admitted.hemisphere),(50,"N"))
            box=case_bbox(case/"grid/grid.cmn")
            self.assertLess(box["west"],115)
            self.assertGreater(box["east"],115)
            self.assertEqual(required_names(box),["srtm_59_06.tif","srtm_60_06.tif"])
            with self.assertRaisesRegex(ValueError,"already exists"):
                stage_case(root)
if __name__=="__main__":
    unittest.main()
