"""Synthetic ZIP contract only; NEVER substitutes a test ZIP for official GSHHG."""
import hashlib
import io
import unittest
import warnings
from zipfile import ZipFile

from scripts.s2g import gshhg_full_hierarchy as full


def archive_bytes(exclude=None, duplicate=None, blank=None):
    mem = io.BytesIO()
    with ZipFile(mem, "w") as z:
        for lev in full.LAYERS:
            for ext in full.base.EXTENSIONS:
                path = f"GSHHS_shp/f/GSHHS_f_L{lev}{ext}"
                if path == exclude:
                    continue
                z.writestr(path, b"" if path == blank else b"synthetic")
                if path == duplicate:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", UserWarning)
                        z.writestr(path, b"synthetic2")
    return mem.getvalue()


class TestFullOnlyHierarchyContract(unittest.TestCase):
    def test_exact_four_levels_and_16_sidecars(self):
        with ZipFile(io.BytesIO(archive_bytes())) as z:
            found = full.members(z)
            self.assertEqual(len(found), 16)
            for (lev, ext), member in found.items():
                self.assertTrue(member.filename.endswith(f"GSHHS_f_L{lev}{ext}"))
                self.assertEqual(full.archived_sha(z, member),
                                 hashlib.sha256(b"synthetic").hexdigest())

    def test_missing_duplicate_and_empty_member_fail_closed(self):
        target = "GSHHS_shp/f/GSHHS_f_L3.shx"
        for kw in ({"exclude": target}, {"duplicate": target}, {"blank": target}):
            with self.subTest(kw=kw):
                with ZipFile(io.BytesIO(archive_bytes(**kw))) as z:
                    with self.assertRaisesRegex(ValueError, "GSHHG_FULL_L3_BAD_MEMBER"):
                        full.members(z)

    def test_no_high_or_l1_only_fallback(self):
        buf = io.BytesIO()
        with ZipFile(buf, "w") as z:
            for level in range(1, 5):
                for ext in full.base.EXTENSIONS:
                    z.writestr(f"GSHHS_shp/h/GSHHS_h_L{level}{ext}", b"high")
        with ZipFile(io.BytesIO(buf.getvalue())) as z:
            with self.assertRaisesRegex(ValueError, "GSHHG_FULL_L1_BAD_MEMBER"):
                full.members(z)


if __name__ == "__main__":
    unittest.main()
