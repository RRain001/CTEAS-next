"""#53 direct LAEA -> UTM candidate: software only, not original science."""
import csv
import hashlib
from pathlib import Path
import tempfile
import unittest
from native_cpp.reference.validate_p2_glazas_hits import (
    read_direct_candidate_hits,compare_integer_hits,
)
from native_cpp.reference.validate_p2_glazas_original import CATS,SRC_SHA,GateError

class DirectLaeaCandidateContract(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(prefix="p2-direct-laea-")
        self.addCleanup(tmp.cleanup)
        self.path=Path(tmp.name)/"candidate.csv"

    def create_candidate(self,move_one=False):
        with self.path.open("w",newline="",encoding="utf-8") as f:
            w=csv.writer(f)
            w.writerow(["i","j","samples"]+[f"cat{x}" for x in CATS])
            for idx in range(2500):
                classes=[0]*38
                classes[7]=1
                if move_one and idx==0:
                    classes[7]=0
                    classes[8]=1
                w.writerow([idx%50+1,idx//50+1,1,*classes])
        return {"source_sha256":SRC_SHA,
                "direct_laea_candidate_hits_csv_sha256":
                    hashlib.sha256(self.path.read_bytes()).hexdigest()}

    def test_candidate_95k_exact_integers_remain_diagnostic(self):
        manifest=self.create_candidate()
        actual,samples=read_direct_candidate_hits(self.path,manifest)
        self.assertEqual(len(actual),2500)
        self.assertEqual(sum(samples),2500)
        self.assertTrue(all(sum(r)==1 for r in actual))
        fractions=[[float(v) for v in row] for row in actual]
        r=compare_integer_hits(actual,actual,samples,fractions,fractions)
        self.assertEqual(r["integer_values_compared"],95000)
        self.assertEqual(r["integer_gate"],"PASS")
        self.assertNotIn("overall",r) # candidate cannot grant full science PASS

    def test_candidate_mismatch_remains_detectable(self):
        manifest=self.create_candidate(move_one=True)
        actual,samples=read_direct_candidate_hits(self.path,manifest)
        original=[list(row) for row in actual]
        original[0][7]=1;original[0][8]=0
        fractions=[[float(v) for v in row] for row in original]
        r=compare_integer_hits(original,actual,samples,fractions,fractions)
        self.assertEqual(r["integer_exceedances"],2)
        self.assertEqual(r["integer_gate"],"FAIL")

    def test_tampered_sha_and_source_refused(self):
        manifest=self.create_candidate()
        with self.assertRaisesRegex(GateError,"DIRECT_PROBE_SHA_MISMATCH"):
            read_direct_candidate_hits(self.path,dict(manifest,
                    direct_laea_candidate_hits_csv_sha256="0"*64))
        with self.assertRaisesRegex(GateError,"DIRECT_PROBE_UNTRUSTED_SOURCE"):
            read_direct_candidate_hits(self.path,dict(manifest,
                    source_sha256="0"*64))

    def test_bad_row_sum_and_non_integer_refused(self):
        manifest=self.create_candidate()
        lines=self.path.read_text().splitlines()
        values=lines[1].split(",")
        values[2]="2"
        lines[1]=",".join(values)
        self.path.write_text("\n".join(lines)+"\n")
        manifest["direct_laea_candidate_hits_csv_sha256"]=hashlib.sha256(
             self.path.read_bytes()).hexdigest()
        with self.assertRaisesRegex(GateError,"DIRECT_PROBE_ROW_SUM"):
            read_direct_candidate_hits(self.path,manifest)

if __name__=="__main__":
    unittest.main()
