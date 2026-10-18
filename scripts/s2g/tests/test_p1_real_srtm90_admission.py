"""#54 D2 owner-byte admission logic: synthetic metadata only; real SRTM NOT_RUN."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts.s2g import p1_real_srtm90_admission as gate

def mock_props(path):
    digest,left,right,bottom,top=gate.APPROVED[path.name]
    return {"sha256":digest,"bytes":gate.TILE_SIZE,"width":6000,"height":6000,
            "resolution_degrees":[1/1200,1/1200],"nodata":-32768,
            "bounds":[left,bottom,right,top]}

class D2SRTM90Admissions(unittest.TestCase):
    def test_border_crossings_and_coverage(self):
        seam={"west":114.99,"east":115.01,"south":31.99,"north":32.01}
        self.assertEqual(gate.required_names(seam),["srtm_59_06.tif","srtm_60_06.tif"])
        self.assertEqual(gate.required_names({"west":119.9,"east":120.1,
                                              "south":29.9,"north":30.1}),
                         ["srtm_60_06.tif","srtm_60_07.tif",
                          "srtm_61_06.tif","srtm_61_07.tif"])
        with self.assertRaisesRegex(gate.D2AssetError,"exceeds"):
            gate.required_names({"west":114,"east":126,"south":31,"north":32})
        with self.assertRaisesRegex(gate.D2AssetError,"invalid"):
            gate.required_names({"west":115,"east":115,"south":31,"north":32})

    def test_actual_git_lfs_pointer_rejected_before_raster_open(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            (folder/"srtm_59_06.tif").write_bytes(b"version https://git-lfs.github.com/spec/v1\n"+b"x"*88)
            with patch.object(gate,"case_bbox",return_value={
                "west":111,"east":112,"south":31,"north":32}):
                with self.assertRaisesRegex(gate.D2AssetError,"pointer or truncated"):
                    gate.admit(Path("unused.grid"),folder)

    def test_byte_gate_report_remains_unverified_even_if_metadata_mock_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            for name in ("srtm_59_06.tif","srtm_60_06.tif"):
                (folder/name).write_bytes(b"FOUR_BYTES_NONREAL")
            with patch.object(gate,"TILE_SIZE",len(b"FOUR_BYTES_NONREAL")):
                with patch.object(gate,"check_raster",side_effect=mock_props):
                    with patch.object(gate,"case_bbox",return_value={
                        "west":114.99,"east":115.01,"south":31.9,"north":32.1}):
                        result=gate.admit(Path("fake.grid"),folder)
            self.assertEqual(len(result["required_tiles"]),2)
            self.assertEqual(result["source_product_version"],"NOT_AUTHENTICATED")
            self.assertEqual(result["science_acceptance"],"NOT_ACCEPTED")
            self.assertEqual(result["original_terrel_parity"],"NOT_RUN")

    def test_changed_owner_sha_denied_even_if_geometry_mock_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);(folder/"srtm_60_06.tif").write_bytes(b"PLACEHOLDER_BYTES")
            def invalid_props(path):
                props=mock_props(path)
                props["sha256"]="0"*64
                return props
            with patch.object(gate,"TILE_SIZE",len(b"PLACEHOLDER_BYTES")):
                with patch.object(gate,"check_raster",side_effect=invalid_props):
                    with patch.object(gate,"case_bbox",return_value={
                        "west":116,"east":117,"south":31,"north":32}):
                        with self.assertRaisesRegex(gate.D2AssetError,"SHA mismatch"):
                            gate.admit(Path("fake.grid"),folder)

    def test_missing_tile_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            with patch.object(gate,"case_bbox",return_value={
                "west":114.99,"east":115.01,"south":31,"north":32}):
                with self.assertRaisesRegex(gate.D2AssetError,"absent"):
                    gate.admit(Path("fake.grid"),folder)

if __name__=="__main__":
    unittest.main()
