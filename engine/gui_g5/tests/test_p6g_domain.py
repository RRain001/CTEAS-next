"""P6G G6 station-envelope planning: explicit inputs, no implicit native physics."""
import json
import math
import tempfile
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

import yaml
import unittest
from pathlib import Path

from engine.gui_g5.case_setup import initial_config, write_case_grid
from engine.gui_g5 import p6_domain
from engine.gui_g5.p6_domain import Station, fit_domain, read_stations
from engine.run_met.common import lon_lat_to_utm_km
from engine.run_met.station_grid import load_strict_utm_grid,lon_lat_in_utm_grid


class G6DomainTests(unittest.TestCase):
    def setUp(self):
        self.config=initial_config("G6_TEST")
        g=self.config["preprocess"]["grid"]
        g["center"]={"longitude":117.14,"latitude":31.94}
        g["domain"]={"length_km":5.0,"width_km":5.0}
        g["resolution_km"]=0.1
        self.stations=[
            Station("S1","surface",117.14,31.94),
            Station("S2","surface",117.32,31.95),
            Station("U1","upper",117.12,31.92),
            Station("U2","upper",117.38,31.99),
        ]

    def test_expansion_and_coarsening_preserve_all_four_stations(self):
        plan=fit_domain(self.config,self.stations,margin_km=3.0,
                        max_horizontal_cells=2500)
        target=plan["recommended"]
        self.assertGreater(target["length_km"],5)
        self.assertGreater(target["width_km"],5)
        self.assertGreater(target["spacing_km"],0.1)
        self.assertLessEqual(target["horizontal_cells"],2500)
        self.assertEqual(plan["station_counts"],{"surface":2,"upper":2})
        self.assertFalse(plan["native_p6d_physics_accepted"])
        self.assertEqual(self.config["preprocess"]["grid"]["resolution_km"],0.1)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            write_case_grid(root,plan["proposed_config"])
            grid=load_strict_utm_grid(root/"grid"/"grid.cmn")
            self.assertEqual((grid.nx,grid.ny),
                             (target["nx"],target["ny"]))
            for s in self.stations:
                self.assertTrue(lon_lat_in_utm_grid(s.lon,s.lat,grid),s.id)

    def test_explicit_10km_annual_multisite_test_grid_without_touching_baseline(self):
        plan=fit_domain(self.config,self.stations,margin_km=6,
                        max_horizontal_cells=100,
                        fixed_spacing_km=10.0)
        grid=plan["recommended"]
        self.assertEqual(grid["spacing_km"],10.0)
        self.assertEqual(plan["requested_spacing_km"],10.0)
        self.assertLessEqual(grid["horizontal_cells"],100)
        self.assertEqual(plan["station_counts"],{"surface":2,"upper":2})
        self.assertEqual(self.config["preprocess"]["grid"]["resolution_km"],0.1)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            write_case_grid(root,plan["proposed_config"])
            published=load_strict_utm_grid(root/"grid"/"grid.cmn")
            self.assertEqual(published.dgridkm,10.0)
            self.assertEqual((published.nx,published.ny),(grid["nx"],grid["ny"]))
            for station in self.stations:
                self.assertTrue(lon_lat_in_utm_grid(station.lon,station.lat,published))

    def test_reject_10km_grid_when_station_envelope_exceeds_budget(self):
        with self.assertRaisesRegex(ValueError,"Cannot fit"):
            fit_domain(self.config,self.stations,margin_km=10,
                       max_horizontal_cells=1,fixed_spacing_km=10.0)
        with self.assertRaisesRegex(ValueError,"cannot refine"):
            fit_domain(self.config,self.stations,fixed_spacing_km=0.05)

    def test_short_envelope_no_forced_coarsening(self):
        near=[Station("S","surface",117.14,31.94),
              Station("U","upper",117.1402,31.9401)]
        p=fit_domain(self.config,near,margin_km=0.0,
                     max_horizontal_cells=2500)
        self.assertAlmostEqual(p["recommended"]["spacing_km"],0.1)
        self.assertEqual(p["recommended"]["nx"],50)

    def test_reject_cross_hemisphere_and_distant_utm_zone(self):
        bad=[Station("x","upper",150.0,31.94)]
        with self.assertRaisesRegex(ValueError,"meridian"):
            fit_domain(self.config,bad)
        with self.assertRaisesRegex(ValueError,"hemisphere"):
            fit_domain(self.config,[Station("y","upper",117.14,-10.0)])

    def test_reject_infeasible_budget_and_invalid_station_manifest(self):
        with self.assertRaisesRegex(ValueError,"Cannot fit"):
            fit_domain(self.config,self.stations,max_horizontal_cells=1)
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/"stations.json"
            p.write_text(json.dumps([
                {"id":"U1","kind":"upper","lon":117.14,"lat":31.94},
                {"id":"U1","kind":"upper","lon":117.15,"lat":31.95}]))
            with self.assertRaisesRegex(ValueError,"Duplicate"):
                read_stations(p)
            p.write_text(json.dumps([
                {"id":"S1","kind":"surface","lon":117.14,"lat":31.94},
                {"id":"U1","kind":"upper","lon":117.16,"lat":31.92}]))
            self.assertEqual(len(read_stations(p)),2)

    def test_cli_default_dryrun_apply_and_frozen_case_protection(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/"run/met").mkdir(parents=True)
            case_file=root/"case.yaml"
            case_file.write_text(yaml.safe_dump(self.config),encoding="utf-8")
            write_case_grid(root,self.config)
            station_file=root/"stations.json"
            station_file.write_text(json.dumps([
                {"kind":r.kind,"id":r.id,"lon":r.lon,"lat":r.lat}
                for r in self.stations
            ]),encoding="utf-8")
            args=["--case","G6_TEST","--stations",str(station_file),
                  "--max-horizontal-cells","2500"]
            with patch.object(p6_domain,"case_dir",return_value=root):
                prior=case_file.read_bytes()
                buf=StringIO()
                with redirect_stdout(buf):
                    self.assertEqual(p6_domain.main(args),0)
                self.assertEqual(prior,case_file.read_bytes())
                self.assertFalse(json.loads(buf.getvalue())["applied"])
                buf=StringIO()
                with redirect_stdout(buf):
                    self.assertEqual(p6_domain.main(args+["--apply"]),0)
                self.assertTrue(json.loads(buf.getvalue())["applied"])
                self.assertGreater(float(
                    yaml.safe_load(case_file.read_text())["preprocess"]["grid"]["resolution_km"]),0.1)
                stable=case_file.read_bytes()
                (root/"run/met/met.dat").write_text("PROTECTED")
                with self.assertRaises(SystemExit):
                    p6_domain.main(args+["--apply"])
                self.assertEqual(stable,case_file.read_bytes())

    def test_immutable_planner_and_cost_separation(self):
        source=initial_config("IMMUTABLE")
        old=source["preprocess"]["grid"]["domain"]["length_km"]
        plan=fit_domain(source,[Station("S","surface",117.14,31.94)],
                        max_horizontal_cells=5000)
        self.assertEqual(source["preprocess"]["grid"]["domain"]["length_km"],old)
        self.assertEqual(plan["existing"]["horizontal_cells"],2500)
        self.assertGreater(plan["recommended"]["3d_cells"],0)


if __name__=="__main__":
    unittest.main()
