"""#160 C5 format-only independent consumer positive and fail-closed gates."""
import tempfile
import unittest
from pathlib import Path
from scripts.s2g.issue160_p3_lu_format_contract import (
    USGS38,read_v21_f63,
)
class FormatGate(unittest.TestCase):
    def build(self,*,bad=None):
        head=(
            f"{'LU.DAT':<16}{'2.1':<16}Coordinate parameters and LandUse categories\n"
            "   2\nFirst provenance comment\nSecond provenance comment\n"
            "FRACTION\nUTM\n  52N   \nWGS-84  02-21-2003\n"
            f"{2:>8}{2:>8}{533.215:>12.3f}{3942.629:>12.3f}"
            f"{.1:>12.3f}{.1:>12.3f}{38:>6}\nKM  \n"
            + "".join(f"{k:>6}" for k in USGS38)+"\n")
        rows=[]
        for j in range(1,3):
            for i in range(1,3):
                fractions=[0.]*38
                marker="."
                if i==1 and j==1:
                    fractions[USGS38.index(52)]=.25
                    fractions[USGS38.index(55)]=.75
                elif i==2 and j==1:
                    marker="Missing"
                else:
                    fractions[USGS38.index(21)]=1.
                rows.append(f"{i:>5}{j:>5}"+
                    "".join(f"{value:>6.3f}" for value in fractions)+
                    f"{marker:<20}\n")
        full=head+"".join(rows)
        if bad=="wrong_order":
            full=full.replace(f"{2:>5}{1:>5}",f"{1:>5}{2:>5}",1)
        elif bad=="wrong_category":
            altered=list(USGS38);altered[0],altered[1]=altered[1],altered[0]
            full=full.replace("".join(f"{k:>6}" for k in USGS38),
                              "".join(f"{k:>6}" for k in altered))
        elif bad=="bad_missing":
            full=full.replace(f"{'Missing':<20}",f"{'.':<20}")
        elif bad=="wrong_zone":
            full=full.replace("52N","50N")
        elif bad=="truncated":
            full=full[:-40]  # remove required F6.3 fields, not just trailing A20 spaces
        return full
    def parse(self,kind):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"lu.dat"
            p.write_text(self.build(bad=kind))
            return read_v21_f63(p,epsg=32652,x0="533.215",
                               y0="3942.629",nx=2,ny=2)
    def test_independent_header_rows_and_mixed_52_55(self):
        s=self.parse(None)
        self.assertEqual((s["fraction_fields"],s["nonempty_cells"],
                          s["missing_cells"]),(152,3,1))
        self.assertEqual(s["mixed_water_cells"],1)
        self.assertEqual(s["f52_positive_cells"],1)
        self.assertEqual(s["f55_positive_cells"],1)
    def test_fail_closed_alterations(self):
        for key in ("wrong_order","wrong_category","bad_missing",
                    "wrong_zone","truncated"):
            with self.subTest(key=key),self.assertRaises(ValueError):
                self.parse(key)
if __name__=="__main__":
    unittest.main()
