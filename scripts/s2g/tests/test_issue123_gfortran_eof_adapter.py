"""Offline synthetic tests for controlled original BREADH EOF compatibility."""
import hashlib
import unittest
from unittest.mock import patch as monkey

from scripts.s2g import issue123_gfortran_eof_adapter as target


class GnuRawHeaderEOF(unittest.TestCase):
    @staticmethod
    def fixture(count=8):
        data = ("      program sample\n"
                "      read(iogshhs,err=99)\n"
                "      subroutine breadh(il1)\n" +
                ("      read(iogshhs,err=99)\n" * count) +
                "      end\n"
                "      subroutine breadp(x)\n"
                "      read(iogshhs,err=99)\n"
                "      end\n").encode("ascii")
        return data

    def test_only_eight_breadh_io_specifiers_change(self):
        source = self.fixture()
        with monkey.object(target, "SOURCE_SHA", hashlib.sha256(source).hexdigest()):
            derivative, record = target.patch(source)
        self.assertEqual(record["patched_header_reads"], 8)
        self.assertEqual(record["computational_physics_changes"], False)
        self.assertEqual(len(derivative), len(source))
        self.assertIn(b"read(iogshhs,end=99)", derivative)
        self.assertEqual(derivative.count(b"read(iogshhs,end=99)"), 8)
        self.assertEqual(derivative.count(b"read(iogshhs,err=99)"), 2)

    def test_missing_or_more_header_reads_fail_closed(self):
        for n in (0, 3, 7, 9, 15):
            source = self.fixture(n)
            with self.subTest(n=n):
                with monkey.object(target, "SOURCE_SHA", hashlib.sha256(source).hexdigest()):
                    with self.assertRaises(ValueError):
                        target.patch(source)

    def test_unpinned_source_rejected(self):
        with self.assertRaisesRegex(ValueError, "SOURCE_SHA_DRIFT"):
            target.patch(self.fixture())


if __name__ == "__main__":
    unittest.main()
