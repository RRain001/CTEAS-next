#!/usr/bin/env python3
"""P7A isolated staging safety tests; no physical numerical success claimed."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location(
    "run_original_calpuff_reference", Path(__file__).resolve().parents[1] / "reference" /
    "run_original_calpuff_reference.py")
assert SPEC is not None and SPEC.loader is not None
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)

BASE = {
    "METFM": 1, "MWET": 0, "MCHEM": 0, "NX": 50, "NY": 50,
    "NZ": 9, "IOUTU": 3, "METRUN": 0, "IBYR": 2022,
    "IBMO": 1, "IBDY": 1, "IBHR": 0, "IBSEC": 0, "IEYR": 2022,
    "IEMO": 1, "IEDY": 6, "IEHR": 23, "IESEC": 0,
    "NPT1": 1, "ABTZ": "UTC+0000",
    "METDAT": "../met/met.dat", "PUFLST": "puff.lst", "CONDAT": "puff.con",
}
def control(changes: dict | None = None) -> str:
    settings = BASE | (changes or {})
    return "\n".join(f"! {k} = {v} !" for k, v in settings.items()) + "\n"

class StagingTests(unittest.TestCase):
    def test_valid_case_and_safeguards(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7a-fixture-") as tmp:
            root=Path(tmp)
            c=root/"input.puff.inp"; m=root/"input.met.dat"
            c.write_text(control())
            m.write_bytes(b"CALMET.DAT 2.1" + b"\x00"*1024)
            result=mod.stage(c,m,root/"out")
            self.assertEqual(result["status"], "REFERENCE_STAGED_NOT_EXECUTED")
            self.assertEqual(result["control_sha256"],mod.sha256(c))
            self.assertEqual(result["original_met_sha256"],mod.sha256(m))
            self.assertEqual(c.read_text(),control())
            self.assertEqual((root/"out/case/run/met/met.dat").read_bytes(),m.read_bytes())
            self.assertEqual((root/"out/case/run/MET/MET.DAT").read_bytes(),m.read_bytes())
            with self.assertRaises(FileExistsError):
                mod.stage(c,m,root/"out")
    def test_reject_bad_controls(self) -> None:
        for mutation in ({"NX":51}, {"MWET":1}, {"IEHR":22},
                         {"METDAT":"../../../../../../etc/passwd"},
                         {"ABTZ":"UTC+0800"}):
            with self.subTest(mutation=mutation):
                if mutation.get("METDAT"):
                    with tempfile.TemporaryDirectory(prefix="p7a-escape-") as tmp:
                        root=Path(tmp); c=root/"control.inp"; m=root/"met.dat"
                        c.write_text(control(mutation));m.write_bytes(b"x"*1025)
                        with self.assertRaises(ValueError):mod.stage(c,m,root/"out")
                else:
                    if "ABTZ" in mutation:
                        with self.assertRaises(ValueError):mod.validate_control(control(mutation))
                    else:
                        with self.assertRaises(ValueError):mod.validate_control(control(mutation))
    def test_required_pins(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7a-pin-") as tmp:
            root=Path(tmp); c=root/"control.inp"; m=root/"met.dat";b=root/"bin"
            c.write_text(control());m.write_bytes(b"x"*1025);b.write_bytes(b"fake-executable")
            with self.assertRaises(ValueError):
                mod.execute(c,m,b,root/"out","0"*64,"1"*64,1800)

if __name__=="__main__":
    unittest.main()
