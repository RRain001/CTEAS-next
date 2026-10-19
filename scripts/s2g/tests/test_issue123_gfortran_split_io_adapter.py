"""Offline tests: GNU GSHHG STREAM must not break GLCC DIRECT+REC."""
import hashlib
import unittest
from unittest.mock import patch as monkey

from scripts.s2g import issue123_gfortran_split_io_adapter as target


class SplitBinaryAccess(unittest.TestCase):
    @staticmethod
    def fixture():
        return (b"      subroutine coastext\n" +
                target.OLD_OPEN.encode("ascii") +
                b"\n      end\n      subroutine breadh(x)\n" +
                b"      read(iogshhs,end=99) x\n      end\n" +
                b"      subroutine comp\n" +
                b"            Read(ioinp,rec=kcnt)kbuf\n      end\n")

    def test_gshhg_only_open_and_direct_glcc(self):
        sample = self.fixture()
        with monkey.object(target, "ORIGINAL_SOURCE_SHA", hashlib.sha256(sample).hexdigest()), \
             monkey.object(target, "AFTER_EOF_SHA", hashlib.sha256(sample).hexdigest()):
            out, m = target.patch(sample, sample)
        self.assertEqual(out.count(target.NEW_OPEN.encode("ascii")), 1)
        self.assertEqual(out.count(b"read(iogshhs,end=99)"), 1)
        self.assertEqual(out.count(b"Read(ioinp,rec=kcnt)kbuf"), 1)
        self.assertNotIn(target.OLD_OPEN.encode("ascii"), out)
        self.assertTrue(m["glcc_direct_access_preserved"])
        self.assertTrue(m["gshhg_stream_only"])
        self.assertFalse(m["computational_physics_changes"])

    def test_params_direct_must_remain_exact(self):
        params = (target.DIRECT_PARAM + "\n").encode("ascii")
        with monkey.object(target, "ORIGINAL_PARAMS_SHA", hashlib.sha256(params).hexdigest()):
            target.check_params(params, params)
            with self.assertRaisesRegex(ValueError, "SHA_OR_COPY_DRIFT"):
                target.check_params(params, params.replace(b"direct", b"stream"))

    def test_fail_closed_missing_or_duplicate_gshhg_open(self):
        sample = self.fixture()
        for changed in (sample.replace(target.OLD_OPEN.encode("ascii"), b""),
                        sample.replace(target.OLD_OPEN.encode("ascii"),
                                       target.OLD_OPEN.encode("ascii") * 2),
                        sample.replace(b"Read(ioinp,rec=kcnt)kbuf", b"")):
            with self.subTest(length=len(changed)):
                with monkey.object(target, "ORIGINAL_SOURCE_SHA", hashlib.sha256(changed).hexdigest()), \
                     monkey.object(target, "AFTER_EOF_SHA", hashlib.sha256(changed).hexdigest()):
                    with self.assertRaises(ValueError):
                        target.patch(changed, changed)

    def test_sha_pins_reject_drift(self):
        sample = self.fixture()
        with self.assertRaisesRegex(ValueError, "SHA_DRIFT"):
            target.patch(sample, sample)


if __name__ == "__main__":
    unittest.main()
