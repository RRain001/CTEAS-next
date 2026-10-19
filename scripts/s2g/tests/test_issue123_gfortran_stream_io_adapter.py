"""Synthetic admission tests for isolated GNU stream I/O include adapter."""
import unittest

from scripts.s2g.issue123_gfortran_stream_io_adapter import (
    ACTUAL, REPLACE, STATUS, patch
)


class TestOriginalGnuIOAdapter(unittest.TestCase):
    def test_modify_only_active_direct_parameter(self):
        source = ("c --- GNU compiler\n"
                  "c     parameter(cform='unformatted', caccess='transparent', irecl=1)\n"
                  + ACTUAL + "\n      parameter(mxnx=464,mxny=400)\n")
        modified = patch(source)
        self.assertEqual(modified, source.replace(ACTUAL, REPLACE))
        self.assertIn("STREAM_IO_ADAPTED", STATUS)

    def test_wrong_original_or_multiple_active_io_modes_fails(self):
        for text in (ACTUAL.replace("irecl=1", "irecl=4") + "\n",
                     ACTUAL + "\n" + ACTUAL + "\n",
                     "c" + ACTUAL[1:] + "\n",
                     REPLACE + "\n"):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    patch(text)


if __name__ == "__main__":
    unittest.main()
