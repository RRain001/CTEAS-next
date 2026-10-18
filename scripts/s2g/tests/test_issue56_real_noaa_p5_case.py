"""#56 manual authentic-runner staging tests. NOAA payload bytes here are SYNTHETIC."""
import tempfile
import unittest
from pathlib import Path

from native_cpp.orchestration.case_admission import admit_case, verify_immutable
from native_cpp.orchestration.plan import ContractError
from native_cpp.modules.p5_smerge.data_prep.isd_lite_wind import filename
from scripts.s2g.issue56_real_noaa_p5_case import (
    stage_case, SCENARIOS, compare_original_smerge,
)
from scripts.s3f.verify_real_noaa_2022_2023_station_selection import digest
from scripts.s3f.verify_real_noaa_2022_2023_station_selection import (
    generate_grid, P5_STATIONS, ROOT,
)


class Issue56RealRunnerStagingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="issue56-real-runner-unit-")
        self.base = Path(self.temp.name)
        self.verified = self.base / "verified"
        self.staged = self.base / "independent"
        self.staged.mkdir()
        # Two real station *coordinates*, but intentionally synthetic payload
        # content; no scientific source acceptance is inferred from these.
        from native_cpp.modules.p5_smerge.data_prep.download_isd_by_grid import parse_history_txt
        history = parse_history_txt(ROOT / "engine/resources/isd/isd-history.txt")
        chosen = {s.sid: s for s in history if s.sid in P5_STATIONS}
        self.assertEqual(set(chosen), set(P5_STATIONS))
        generate_grid(self.verified / "grid",
                      [(chosen[s].lat, chosen[s].lon) for s in P5_STATIONS])
        raw = self.verified / "surface"
        (raw / "isd_lite").mkdir(parents=True)
        for year in (2022, 2023):
            for sid in P5_STATIONS:
                (raw / f"{sid}-{year}.csv").write_bytes(b"TEST ONLY: NOT NOAA FULL ISD\n")
                (raw / "isd_lite" / filename(sid, year)).write_bytes(
                    b"TEST ONLY: NOT NOAA ISD-Lite\n")

    def tearDown(self):
        self.temp.cleanup()

    def test_two_real_geographic_single_year_cases_are_b0_admitted(self):
        for scenario in ("year2022", "year2023"):
            root, info = stage_case(self.verified, self.staged, scenario)
            evidence = admit_case(root / "case.yaml")
            verify_immutable(evidence)
            self.assertEqual(info["scenario"], scenario)
            self.assertEqual(evidence.case_name, root.name)
            self.assertEqual(len(info["raw_noaa_sha256"]), 2 * len(P5_STATIONS))
            self.assertFalse((root / "run/smerge").exists())
            self.assertFalse((root / "met/surface/isd_raw/station_selection_2022.json").exists())
            self.assertNotIn("project/current", (root / "case.yaml").read_text())

    def test_cross_year_inclusive_window_and_two_calendar_source_sets(self):
        root, info = stage_case(self.verified, self.staged, "crossyear")
        admitted = admit_case(root / "case.yaml")
        self.assertEqual(admitted.research_begin, "20221231-230000")
        self.assertEqual(admitted.research_end, "20230101-030000")
        self.assertEqual(info["year_scope"], [2022, 2023])
        self.assertEqual(len(info["raw_noaa_sha256"]), 4 * len(P5_STATIONS))
        self.assertEqual(admitted.grid_sha256, info["grid_cmn_sha256"])

    def test_no_overwrite_existing_case_or_escape_repo(self):
        stage_case(self.verified, self.staged, "year2022")
        with self.assertRaises(FileExistsError):
            stage_case(self.verified, self.staged, "year2022")
        with self.assertRaisesRegex(ValueError, "outside repository"):
            stage_case(self.verified, ROOT, "year2023")

    def _minimal_raw_surfs(self, *, altered: bool = False):
        case, _ = stage_case(self.verified, self.staged, "year2022")
        run = case / "run/smerge"
        run.mkdir(parents=True)
        ready = case / "met/surface/isd2smerge_ready"
        ready.mkdir(parents=True)
        (ready / "583140-99999.csv").write_bytes(b"TEST GENERIC INPUT\n")
        (run / "smerge.inp").write_text(
            "! SFCMET = ../../met/surface/isd2smerge_ready/583140-99999.csv !\n"
            "! SURFDAT = surf.dat !\n")
        real = b"TEST ONLY: raw SURF output\n"
        (run / "surf.dat").write_bytes(real)
        original = self.base / "fake_fortran_executable"
        output = b"DIFFERENT" if altered else real
        original.write_text(
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "Path('surf.dat').write_bytes(" + repr(output) + ")\n",
            encoding="utf-8",
        )
        original.chmod(0o755)
        return case, original, {"raw_native_surf_sha256": digest(run / "surf.dat")}

    def test_same_input_original_comparator_contract_using_fake_binary(self):
        # This is a software-copy test with a FAKE executable. Absolutely no
        # independent vendor physics or scientific equivalence is exercised.
        case, original, claim = self._minimal_raw_surfs()
        metadata = compare_original_smerge(original, case, claim, self.base)
        self.assertTrue(metadata["byte_identical"])
        self.assertEqual(metadata["original_raw_surf_sha256"],
                         metadata["native_raw_surf_sha256"])
        self.assertEqual(metadata["controls_exact_sha256"],
                         digest(case / "run/smerge/smerge.inp"))

    def test_first_diff_rejected_with_distinct_raw_surf(self):
        case, original, claim = self._minimal_raw_surfs(altered=True)
        with self.assertRaisesRegex(RuntimeError, "BYTE PARITY FAIL"):
            compare_original_smerge(original, case, claim, self.base)

    def test_missing_original_source_is_blocked_not_fabricated(self):
        source = self.verified / "surface" / f"{P5_STATIONS[0]}-2023.csv"
        source.unlink()
        with self.assertRaises(FileNotFoundError):
            stage_case(self.verified, self.staged, "crossyear")


if __name__ == "__main__":
    unittest.main()
