"""Offline synthetic parser checks; never claim original-source science."""
import io
import struct
import unittest
import warnings
from zipfile import ZipFile

from scripts.s2g import issue123_gshhg_binary_full as binary


def fake_header(*, level=1, version=12, npts=4):
    return struct.pack(">11i", 12, npts, level | (version << 8),
                       0, 0, 0, 0, 10, 10, -1, -1)


def archive_with(entries):
    out = io.BytesIO()
    with ZipFile(out, "w") as z:
        for name, body in entries:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                z.writestr(name, body)
    return io.BytesIO(out.getvalue())


class TestGshhsOriginalFullBinaryContract(unittest.TestCase):
    def test_only_full_member_is_selected(self):
        payload = fake_header() + b"testdata"
        with ZipFile(archive_with([
            ("GSHHS_bin/gshhs_f.b", payload),
            ("GSHHS_bin/gshhs_h.b", payload),
        ])) as z:
            found = binary.choose_full_member(z)
            self.assertEqual(found.filename, "GSHHS_bin/gshhs_f.b")
            with z.open(found) as f:
                parsed = binary.inspect_header(f.read(44))
            self.assertEqual(parsed["first_polygon_level"], 1)
            self.assertEqual(parsed["packed_header_version"], 12)

    def test_missing_duplicate_or_empty_full_fails(self):
        data = fake_header()
        for entries in (
            [("bin/gshhs_h.b", data)],
            [("a/gshhs_f.b", data), ("b/gshhs_f.b", data)],
            [("bin/gshhs_f.b", b"")],
        ):
            with self.subTest(entries=entries):
                with ZipFile(archive_with(entries)) as z:
                    with self.assertRaises(ValueError):
                        binary.choose_full_member(z)

    def test_old_or_corrupt_header_fails(self):
        for payload in (
            b"short", fake_header(level=5), fake_header(version=4),
            fake_header(npts=0),
        ):
            with self.subTest(payload=payload[:12]):
                with self.assertRaisesRegex(ValueError, "HEADER_"):
                    binary.inspect_header(payload)

    def test_source_pin_is_upstream_binary_release(self):
        self.assertEqual(binary.BINARY, "gshhs_f.b")
        self.assertEqual(binary.ZIP_SHA256,
                         "28600e8f7a08645aab43079326df6504212ec5ccb2b4bcf3b5f4f12ed60e82bc")
        self.assertTrue(binary.OFFICIAL.endswith("/2.3.7/gshhg-bin-2.3.7.zip"))


if __name__ == "__main__":
    unittest.main()
