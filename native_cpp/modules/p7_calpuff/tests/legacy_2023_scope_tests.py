#!/usr/bin/env python3
"""2023 reference must stay distinct from formal 2022/100m acceptance."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import tempfile
import unittest
MOD = Path(__file__).resolve().parents[1]/"reference/legacy_2023_case.py"
spec=importlib.util.spec_from_file_location("p7legacy",MOD)
assert spec and spec.loader
legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
KEYS={"IBYR":2023,"IBMO":1,"IBDY":1,"IBHR":0,
      "IEYR":2023,"IEMO":1,"IEDY":5,"IEHR":23,"NX":50,"NY":50,
      "NZ":9,"METFM":1,"NSPEC":2,"NSE":1,"MWET":0,"MCHEM":0,
      "NDECAY":0,"MGAUSS":1,"MDISP":3,"IOUTU":3,"NPT1":1,
      "DGRIDKM":1,"ABTZ":"UTC+0000","LCFILES":"T",
      "METDAT":"../../deliverables/met/met.dat"}
def control(values=None) -> str:
    v=KEYS|(values or {})
    return "\n".join(f"! {k} = {val} !" for k,val in v.items())
class LegacyScopeTests(unittest.TestCase):
    def test_selected_2023(self):
        result=legacy.check_2023(control())
        self.assertEqual(result["dgrid_km"],1.0)
        self.assertIn("NOT_CANONICAL_2022",result["reference_class"])
    def test_refuse_2022_and_wrong_domain(self):
        for changed in ({"IBYR":2022},{"DGRIDKM":0.1},{"MWET":1},
                        {"METDAT":"../../../../etc/passwd"}):
            with self.subTest(changed=changed):
                with self.assertRaises(ValueError):legacy.check_2023(control(changed))
    def test_repeated_active_assignment_fails(self):
        with self.assertRaises(ValueError):legacy.check_2023(control()+"\n! NZ =9 !")
    def test_original_2023_pins_stable(self):
        self.assertEqual(legacy.PINS["run/met/met.dat"],
                         "cd0af6fed77639a5e7205bc1fc4f9e4421b41926")
if __name__=="__main__":
    unittest.main()
