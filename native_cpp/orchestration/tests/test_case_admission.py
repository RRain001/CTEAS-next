"""#42 B-0 immutable case/grid/time contract; synthetic, no data download."""
import tempfile
import unittest
from pathlib import Path

from native_cpp.orchestration.case_admission import admit_case, verify_immutable
from native_cpp.orchestration.plan import ContractError


class CaseAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cteas-b0-")
        self.root = Path(self.temp.name) / "newsite_2022"
        (self.root / "grid").mkdir(parents=True)
        self.case = self.root / "case.yaml"
        self.grid = self.root / "grid/grid.cmn"
        self.time = self.root / "grid/research_time"
        self.grid.write_text("\n".join((
            "! IMAP = UTM !", "! DATUM = WGS-84 !", "! IUTMZN = 50 !",
            "! LSOHEM = N !", "! XREFKM = 510.885 !", "! YREFKM = 3531.269 !",
            "! DGRIDKM = 0.100 !", "! NX = 50 !", "! NY = 50 !",
            "! NZ = 1 !", "! ZFACE = 0 !", "! ZFACE = 100 !", "")), encoding="utf-8")
        self.time.write_text("BEGIN:20220101-000000\nEND:20220101-030000\n", encoding="utf-8")
        self.case.write_text("""
case_name: newsite_2022
settings:
  timezone: UTC+0000
preprocess:
  grid:
    utm_zone: 50
    hemisphere: N
    nz: 1
    resolution_km: 0.1
    domain:
      length_km: 5
      width_km: 5
    center:
      latitude: 31.939774444
      longitude: 117.141610855
  research_time:
    begin: 20220101-000000
    end: 20220101-030000
""".lstrip(), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def replace(self, path, original, updated):
        data = path.read_text(encoding="utf-8")
        self.assertIn(original, data)
        path.write_text(data.replace(original, updated), encoding="utf-8")

    def deny(self, expected):
        with self.assertRaisesRegex((ContractError, ValueError), expected):
            admit_case(self.case)

    def test_pass_and_hash_check(self):
        record = admit_case(self.case)
        self.assertEqual(record.xrefkm_text, "510.885")
        self.assertEqual(record.utm_zone, 50)
        self.assertEqual(record.nx * record.ny, 2500)
        verify_immutable(record)
        self.replace(self.time, "030000", "040000")
        with self.assertRaisesRegex(ContractError, "changed"):
            verify_immutable(record)

    def test_second_legal_grid_and_crossyear_clock(self):
        """Second independent B-0 geometry/time tuple; not model science."""
        self.replace(self.grid, "NX = 50", "NX = 60")
        self.replace(self.grid, "NY = 50", "NY = 40")
        self.replace(self.grid, "DGRIDKM = 0.100", "DGRIDKM = 0.200")
        self.replace(self.case, "resolution_km: 0.1", "resolution_km: 0.2")
        self.replace(self.case, "length_km: 5", "length_km: 12")
        self.replace(self.case, "width_km: 5", "width_km: 8")
        self.replace(self.time, "20220101-000000", "20221231-230000")
        self.replace(self.time, "20220101-030000", "20230101-020000")
        self.replace(self.case, "20220101-000000", "20221231-230000")
        self.replace(self.case, "20220101-030000", "20230101-020000")
        admitted = admit_case(self.case)
        self.assertEqual((admitted.nx, admitted.ny, admitted.dgridkm), (60, 40, 0.2))
        self.assertEqual((admitted.research_begin, admitted.research_end),
                         ("20221231-230000", "20230101-020000"))
        self.assertEqual((admitted.xrefkm_text, admitted.yrefkm_text),
                         ("510.885", "3531.269"))
        verify_immutable(admitted)
        self.replace(self.grid, "DGRIDKM = 0.200", "DGRIDKM = 0.100")
        self.deny("disagreement")

    def test_origin_precision_and_duplicate(self):
        self.replace(self.grid, "510.885", "510.885000")
        self.deny("three decimal")
        self.replace(self.grid, "510.885000", "510.885")
        with self.grid.open("a") as out:
            out.write("! NX = 50 !\n")
        self.deny("duplicated")

    def test_numeric_rejections(self):
        self.replace(self.grid, "IUTMZN = 50", "IUTMZN = 50.5")
        self.deny("integer literal")
        self.replace(self.grid, "IUTMZN = 50.5", "IUTMZN = 50")
        self.replace(self.grid, "NX = 50", "NX = 0")
        self.deny("zone or grid dimensions")

    def test_case_grid_mismatch_and_duplicate_yaml(self):
        self.replace(self.case, "utm_zone: 50", "utm_zone: 49")
        self.deny("disagreement")
        self.replace(self.case, "utm_zone: 49", "utm_zone: 50")
        with self.case.open("a") as out:
            out.write("case_name: newsite_2022\n")
        self.deny("duplicate")

    def test_research_window(self):
        self.replace(self.time, "030000", "023000")
        self.deny("whole UTC hours")
        self.replace(self.time, "023000", "030000")
        self.replace(self.time, "BEGIN:20220101-000000", "BEGIN:20220101-050000")
        self.deny("earlier")
        self.replace(self.time, "050000", "000000")
        with self.time.open("a") as out:
            out.write("END:20220102-000000\n")
        self.deny("duplicate")

    def test_case_rejects_external_alias_and_symlink(self):
        self.replace(self.case, "case_name: newsite_2022", "case_name: other_site")
        self.deny("name differs")
        self.replace(self.case, "case_name: other_site", "case_name: newsite_2022")
        self.grid.unlink()
        self.grid.symlink_to(self.case)
        self.deny("symlink")

    def test_inactive_shadowed_grid_authority_refused(self):
        with self.grid.open("a") as out:
            out.write("* NX = 60 *\n")
        self.deny("inactive grid record")

    def test_inactive_shadowed_origin_refused(self):
        with self.grid.open("a") as out:
            out.write("* XREFKM = 510.886 *\n")
        self.deny("inactive grid record")

    def test_case_field_time_mismatch(self):
        self.replace(self.case, "end: 20220101-030000", "end: 20220101-020000")
        self.deny("disagrees")


if __name__ == "__main__":
    unittest.main()
