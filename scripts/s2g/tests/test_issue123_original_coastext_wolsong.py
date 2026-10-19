"""#123 D6-B: synthetic offline control and original BLN audit contracts."""
import tempfile
from pathlib import Path
import unittest

from scripts.s2g.issue123_original_coastext_wolsong import (
    build_deck, parse_bln, GRID
)

BASE = """INPUT GROUP: 0
NDBF= ! NDBF = 1 !
1 !GLAZAS = ignored.img !    !END!
"""
VALUES = {
    "NDBF": "1", "LCFILES": "T", "GSHHSIN": "",
    "COASTBLN": "", "LUDAT": "lu.dat", "RUNLST": "ctgproc.lst",
    "LFINAL": "T", "LPREV": "F", "LCOAST": "F",
    "LMARSWAP": "F", "LMARFILL": "T", "LBLNREAD": "T",
    "IOCEAN": "55", "MESHGLAZ": "5", "LQACELL": "F",
    "LSNOW": "F", "DUSGSLA": "ESR-S", "PMAP": "UTM",
    "IUTMZN": "50", "UTMHEM": "N", "DATUM": "WGS-84",
    "XREFKM": "510.885", "YREFKM": "3531.269",
    "NX": "50", "NY": "50", "DGRIDKM": "0.100",
}


def template():
    return BASE + "\n".join(f"! {k} = {v} !" for k, v in VALUES.items())


def bln(header='5,0,"1,2,72"', closed=True):
    end = "533.216,3942.630" if closed else "533.219,3942.630"
    return (header + "\n" +
            "533.216,3942.630\n533.220,3942.630\n"
            "533.220,3942.635\n533.216,3942.635\n" + end + "\n")


class OriginalWolsongContract(unittest.TestCase):
    def test_legal_original_glazas_deck(self):
        deck = build_deck(template())
        for item in (
            "1 !GLAZAS = glcc.img !", "! LCOAST = T ", "! LBLNREAD = F ",
            "! LMARSWAP = T ", "! LMARFILL = F ", "! IUTMZN = 52 ",
            "! XREFKM = 533.215 ", "! YREFKM = 3942.629 ",
            "! NX = 200 ", "! NY = 200 ",
        ):
            self.assertIn(item, deck)
        self.assertNotIn("!GEN =", deck)

    def test_illegal_source_or_duplicate_cards_fail(self):
        bad = (template().replace("!GLAZAS =", "!GEN ="),
               template() + "\n! LCOAST = T !",
               template().replace("! LCOAST = F !", ""),
               template() + "\n1 !GLAZAS = another.img ! !END!")
        for item in bad:
            with self.subTest(case=item[-100:]):
                with self.assertRaises(Exception):
                    build_deck(item)

    def test_real_bln_format_and_ocean_surrounding_type(self):
        text = bln() + bln('5,1,"0,2,80"')
        with tempfile.TemporaryDirectory() as root:
            p = Path(root) / "coast.bln"
            p.write_text(text)
            report = parse_bln(p)
            self.assertEqual(report["polygons"], 2)
            self.assertEqual(report["vertices"], 10)
            self.assertEqual(report["classes"]["0"], 1)
            self.assertEqual(report["classes"]["1"], 1)

    def test_malformed_unclosed_and_wrong_grid_fail_closed(self):
        for item in (bln(closed=False), bln("5,1,\\"1,2,72\\""),
                     bln().replace("533.216", "200.000"),
                     bln().splitlines()[0] + "\n"):
            with self.subTest(item=item[:80]):
                with tempfile.TemporaryDirectory() as root:
                    p = Path(root) / "coast.bln"
                    p.write_text(item)
                    with self.assertRaises(ValueError):
                        parse_bln(p)

    def test_frozen_case(self):
        self.assertEqual(GRID["epsg"], 32652)
        self.assertEqual(GRID["nx"] * GRID["ny"], 40_000)


if __name__ == "__main__":
    unittest.main()
