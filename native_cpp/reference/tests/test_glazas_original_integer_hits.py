"""#53 integer GLAZAS science comparator software fixtures; no original science here."""
import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from native_cpp.reference.validate_p2_glazas_original import (
    CATS, SRC_SHA, GateError, make_glazas_control, _edit_card, FLOAT_TOL,
)
from native_cpp.reference.validate_p2_glazas_hits import (
    read_hits, read_native_hits, compare_integer_hits,
)

ROOT=Path(__file__).resolve().parents[3]
FROZEN=ROOT/"project/cases/hefei5km_2022_reference_case_20261011/geo/ctgproc"
class IntegerHitsSoftware(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory(prefix="p2-integer-hits-")
        self.addCleanup(t.cleanup)
        self.root=Path(t.name)

    def make_inputs(self, *, mutate_original=None):
        """2500×38 exact integer synthetic counts with real source **FORMAT** only."""
        original=FROZEN/"lu.dat"
        lines=original.read_text().splitlines()
        # Use original file header fields but switch from FRACTION to HITS.
        lines[4]="HITS    "
        hits=[]
        native=[]
        with (self.root/"native_hits.csv").open("w",newline="") as fp:
            w=csv.writer(fp)
            w.writerow(["i","j","samples"]+[f"cat{k}" for k in CATS])
            for idx in range(2500):
                counts=[0]*38
                counts[idx%38]=4
                if mutate_original is not None and idx==0:
                    other=counts[:]
                    other[idx%38]-=1
                    other[(idx+1)%38]+=1
                else:
                    other=counts
                native.append(counts)
                hits.append(other)
                w.writerow([idx%50+1,idx//50+1,4,*counts])
        lines=lines[:11]+[
            f"{idx%50+1:5d}{idx//50+1:5d}"+
            "".join(f"{q:5d}" for q in row)+"   ."
            for idx,row in enumerate(hits)
        ]
        h=self.root/"original_hits.dat"
        h.write_text("\n".join(lines)+"\n")
        fn=self.root/"native_hits.csv"
        manifest={
            "producer":"cteas_p2_glcc_raw",
            "source_sha256":SRC_SHA,
            "method":"GLCC_HEADERLESS_ROW_DIRECT_GEN_7DP_REAL4_REPLAY",
            "nx":50,"ny":50,"utm_epsg":32650,"mesh":20,
            "included":10000,
            "hits_csv_sha256":hashlib.sha256(fn.read_bytes()).hexdigest()
        }
        return h,fn,manifest,hits,native

    def test_lfinal_f_is_separate_true_original_glazas(self):
        deck=make_glazas_control((FROZEN/"ctgproc.inp").read_text())
        hits_deck=_edit_card(deck,"LFINAL","F")
        self.assertIn("1 !GLAZAS = glcc.img !",hits_deck)
        self.assertIn("! LFINAL = F !",hits_deck)
        self.assertNotIn("1 !GEN =",hits_deck)
        self.assertIn("! MESHGLAZ = 20 !",hits_deck)

    def test_two_independent_integer_formats_and_95000_values(self):
        h,n,m,oh,nh=self.make_inputs()
        self.assertEqual(read_hits(h),oh)
        actual,samples=read_native_hits(n,m)
        self.assertEqual(actual,nh)
        self.assertEqual(sum(samples),10000)
        frac=[[float(v)/sum(row) for v in row] for row in oh]
        x=compare_integer_hits(oh,actual,samples,frac,frac)
        self.assertEqual(x["integer_values_compared"],95000)
        self.assertEqual(x["integer_gate"],"PASS")
        self.assertEqual(x["max_integer_absolute_difference"],0)
        self.assertEqual(x["original_integer_submesh_hits_total"],10000)

    def test_fraction_rounding_can_hide_real_integer_mismatch(self):
        h,n,m,oh,nh=self.make_inputs(mutate_original=1)
        oh=read_hits(h);nh,samples=read_native_hits(n,m)
        fractions=[[float(v)/sum(row) for v in row] for row in oh]
        r=compare_integer_hits(oh,nh,samples,fractions,fractions)
        self.assertEqual(r["fraction_exceedances"] if "fraction_exceedances" in r else 0,0)
        self.assertEqual(r["integer_exceedances"],2)
        self.assertEqual(r["integer_gate"],"FAIL")
        self.assertEqual(r["max_integer_absolute_difference"],1)
        self.assertEqual(r["different_cell_total_hit_counts"],0)

    def test_sha_or_manifest_source_drift_is_rejected(self):
        h,n,m,oh,nh=self.make_inputs()
        altered=dict(m,hits_csv_sha256="0"*64)
        with self.assertRaisesRegex(GateError,"SHA_MISMATCH"):
            read_native_hits(n,altered)
        altered=dict(m,source_sha256="0"*64)
        with self.assertRaisesRegex(GateError,"UNTRUSTED_PRODUCER"):
            read_native_hits(n,altered)

    def test_production_direct_scientific_comparator_requires_source_sha(self):
        h,n,m,oh,nh=self.make_inputs()
        m["method"]="GLCC_HEADERLESS_LAEA_DIRECT_UTM50N_REAL4_GLOBE_LUGRID"
        direct,samples=read_native_hits(n,m)
        self.assertEqual(direct,nh)
        self.assertEqual(sum(samples),10000)
        invalid=dict(m,method="GLCC_DIRECT_UNREVIEWED_FAKE")
        with self.assertRaisesRegex(GateError,"UNTRUSTED_PRODUCER"):
            read_native_hits(n,invalid)
        invalid=dict(m,hits_csv_sha256="0"*64)
        with self.assertRaisesRegex(GateError,"SHA_MISMATCH"):
            read_native_hits(n,invalid)

    def test_mode_is_required_not_fraction_as_fake_hits(self):
        h,n,m,oh,nh=self.make_inputs()
        s=h.read_text().replace("\nHITS    \n","\nFRACTION\n")
        h.write_text(s)
        with self.assertRaisesRegex(GateError,"NOT_INTEGER_HITS_MODE"):
            read_hits(h)

    def test_noninteger_and_grid_cell_mismatch_denied(self):
        h,n,m,oh,nh=self.make_inputs()
        s=h.read_text().splitlines()
        s[11]=s[11].replace("    4","    X",1)
        h.write_text("\n".join(s)+"\n")
        with self.assertRaises(GateError):
            read_hits(h)

    def test_d1_producer_hits_counts_not_reconstructed_from_three_decimal_lu(self):
        h,n,m,oh,nh=self.make_inputs()
        self.assertGreater(n.stat().st_size,0)
        manifest=dict(m)
        native,samples=read_native_hits(n,manifest)
        self.assertEqual(native[0][0],4)
        self.assertTrue(all(sum(row)==4 for row in native))
        self.assertEqual(len(CATS),38)

if __name__=="__main__":
    unittest.main()
