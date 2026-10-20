"""D11 format/gate regression, deliberately synthetic and not science PASS."""
from __future__ import annotations
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import scripts.s2g.issue123_d11_native_lu_verify as d11
from native_cpp.reference.validate_p2_glazas_original import CATS


def lu_rows(difference: bool=False):
    header=[
       "LU.DAT   2.1", "   2","source","version","FRACTION","UTM",
       "  52N   ","WGS-84  02-21-2003",
       "2 2 533.215 3942.629 0.100 0.100 38","KM  ",
       "          "+"".join(f"{v:6d}" for v in CATS),
    ]
    body=[]
    for idx in range(4):
        if idx==0:
            values=["0.333","0.667"]+["0.000"]*36
            flag="."
        else:
            values=["0.000"]*38
            flag="Missing"
        if difference and idx==0:
            values[0]="0.334"
        body.append(f"{idx%2+1:5d}{idx//2+1:5d}"+
            "".join(f"{v:>6}" for v in values)+f"{flag:<20}")
    return "\n".join(header+body)+"\n"


class D11ProductionParityTests(unittest.TestCase):
    def test_full_fraction_matrix_and_missing_flags(self):
        with tempfile.TemporaryDirectory() as td, \
             patch.object(d11,"N",2), \
             patch("scripts.s2g.issue123_d10_original_f63_lu.N",2):
            a=Path(td)/"original";b=Path(td)/"native"
            a.write_text(lu_rows())
            b.write_text(lu_rows())
            m=d11.compare(a,b,{"scope":"SYNTHETIC"})
            self.assertEqual(m["fraction_fields_compared"],4*38)
            self.assertEqual(m["fraction_3dp_differences"],0)
            self.assertEqual(m["missing_flag_differences"],0)
            b.write_text(lu_rows(difference=True))
            m=d11.compare(a,b,{})
            self.assertEqual(m["fraction_3dp_differences"],1)
            self.assertEqual(m["status"],"D11_REAL_ORIGINAL_VS_NATIVE_LU_MISMATCH")

    def test_incompatible_categories_fail_closed(self):
        with tempfile.TemporaryDirectory() as td,patch.object(d11,"N",2):
            a=Path(td)/"original";b=Path(td)/"native"
            a.write_text(lu_rows())
            b.write_text(lu_rows().replace(f"{CATS[0]:6d}",f"{99:6d}",1))
            with self.assertRaisesRegex(ValueError,"USGS38_CATEGORY_ORDER"):
                d11.compare(a,b,{})


if __name__=="__main__":
    unittest.main()
