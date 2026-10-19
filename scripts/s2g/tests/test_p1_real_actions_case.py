"""Only stage B0 real-site geometry; never fetch a true DEM in PR CI."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts.s2g import p1_real_actions_case as actions
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
    def test_real_gl3_route_explicitly_pins_original_90m_product(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/"staged"
            mock_source={"case_window_valid_pixels":10,"case_window_nodata_pixels":0,
                         "mosaic_created":False,"transport":"opentopography_globaldem_api",
                         "bulk_recovery_used":False,
                         "official_dataset_documentation":{
                             "provider_product":"SRTM_GL3",
                             "declared_vertical_datum":"EGM96 geoid",
                             "evidence_level":"OFFICIAL_COLLECTION_METADATA_ONLY",
                             "tile_matches_independent_nasa_granule":False}}
            fake_native={"row_count":2500,"grid_sha256":"a"*64,
                         "case_sha256":"b"*64,"time_sha256":"c"*64,
                         "source_manifest_sha256":"d"*64,"selected_tif_sha256":"e"*64,
                         "terrain_csv_sha256":"f"*64,"source_pixel_hits":123}
            with patch.object(actions,"prepare",return_value=mock_source) as mocked_download:
                with patch.object(actions,"run_case",return_value=fake_native) as mocked_native:
                    report=actions.run(root=root,route="P1_B_90M_DOWNLOAD",
                                       binary=Path(td)/"not_executed",tif_dir=None)
            self.assertEqual(mocked_download.call_args.kwargs["dem"],"SRTMGL3")
            self.assertEqual(mocked_native.call_args.kwargs["source_product"],"SRTMGL3")
            self.assertEqual(report["route"],"P1_B_90M_DOWNLOAD")
            self.assertEqual(report["source_product_declaration"],"SRTMGL3")
            self.assertEqual(
                report["official_dataset_documentation"]["provider_product"],"SRTM_GL3")
            self.assertEqual(
                report["official_dataset_documentation"]["evidence_level"],
                "OFFICIAL_COLLECTION_METADATA_ONLY")
            self.assertFalse(report["source_product_version_authenticated"])
            self.assertFalse(report["height_vertical_datum_authenticated"])
            self.assertEqual(report["science_acceptance"],"NOT_ACCEPTED")

if __name__=="__main__":
    unittest.main()
