"""#123 callback offline synthetic only; never contacts GitHub."""
from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
from scripts.s2g.issue123_science_run_callback import report_body


class ScienceCallbackTests(unittest.TestCase):
    def test_empty_reports_not_misrepresented(self):
        with tempfile.TemporaryDirectory() as temp:
            text=report_body(Path(temp),39312345678,"a"*40)
            self.assertIn("39312345678",text)
            self.assertEqual(text.count("REPORT_NOT_PRESENT_OR_INVALID"),4)
            self.assertIn("Do not infer full ORIGINAL_SAMPLING",text)

    def test_success_labels_are_reports_not_verdicts(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/"issue123-d6b-original-run").mkdir()
            (root/"issue123-d8-oracle").mkdir()
            (root/"issue123-d6b-original-run/original_coastext_report.json").write_text(
              json.dumps({"status":
                "D6B_GNU_SPLIT_IO_EOF_ADAPTED_ORIGINAL_COASTEXT_GENERATED_BLN_SCOPED",
                "original_source_sha256":"b"*64,
                "original_bln_sha256":"c"*64}))
            (root/"issue123-d8-oracle/d8_iptype_report.json").write_text(json.dumps(
              {"status":"D8_REAL_ORIGINAL_BLN_IPTYPE_ZERO_MISMATCH_PASS_SCOPED"}))
            (root/"issue123-d9-hits-report.json").write_text(json.dumps(
              {"status":"D9_ORIGINAL_GLCC_HITS_MISMATCH"}))
            body=report_body(root,39312345679,"d"*40)
            self.assertIn("D8_REAL_ORIGINAL_BLN_IPTYPE_ZERO_MISMATCH_PASS_SCOPED",body)
            self.assertIn("(report exists; verify artifact)",body)
            self.assertIn("D9_ORIGINAL_GLCC_HITS_MISMATCH (not accepted)",body)

    def test_reject_unsafe_ref_or_identifier(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError,"INVALID_RUN_OR_COMMIT"):
                report_body(Path(temp),0,"a"*40)
            with self.assertRaisesRegex(ValueError,"INVALID_RUN_OR_COMMIT"):
                report_body(Path(temp),1,"main")


if __name__=="__main__":
    unittest.main()
