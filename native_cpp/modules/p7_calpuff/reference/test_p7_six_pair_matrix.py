#!/usr/bin/env python3
"""Fail-closed offline tests; no production model or source data required."""
from __future__ import annotations
import json
from pathlib import Path
import struct
import tempfile
import unittest

import p7_six_pair_matrix as six
import compare_p7_hourly_concentrations as conc


def write_con(path: Path, rows: list[tuple[float, ...]]) -> None:
    with path.open("wb") as stream:
        for row in rows:
            payload = b"H-3     " + b"      1" + struct.pack(f"<{len(row)}f", *row)
            stream.write(struct.pack("<i", len(payload)) + payload +
                         struct.pack("<i", len(payload)))


class SixPairTests(unittest.TestCase):
    NX = 2
    NY = 2
    HOURS = 143

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.a = self.root / "A.con"
        self.b = self.root / "B.con"
        self.c = self.root / "C.con"
        self.d = self.root / "D.con"
        # Nonzero and deterministic, with real A/C meteorological sensitivity.
        rows_a = [(0.25 + 0.001 * h, 0.0, 0.4, 0.0)
                  for h in range(self.HOURS)]
        rows_c = [(0.30 + 0.001 * h, 0.0, 0.4, 0.0)
                  for h in range(self.HOURS)]
        for file, rows in ((self.a, rows_a), (self.b, rows_a),
                           (self.c, rows_c), (self.d, rows_c)):
            write_con(file, rows)

    def direct(self):
        return six.from_files({"A": self.a, "B": self.b,
                               "C": self.c, "D": self.d},
                              self.NX, self.NY, self.HOURS)

    def archives(self):
        files = {name: conc.read_fields(p, self.NX, self.NY, self.HOURS)
                 for name, p in (("A", self.a), ("B", self.b),
                                 ("C", self.c), ("D", self.d))}
        names = ("AB", "AC", "BD", "CD")
        reports = {}
        for pair in names:
            value = conc.compare(files[pair[0]], files[pair[1]], self.NX, self.NY)
            if pair != "AC":
                value["a"] = {k: v for k, v in files[pair[0]].items() if k != "fields"}
                value["b"] = {k: v for k, v in files[pair[1]].items() if k != "fields"}
            p = self.root / (pair + ".json")
            p.write_text(json.dumps(value))
            reports[pair] = p
        prov = {
            "scope": "P7_C2_VENDOR_A_C_WITH_NONZERO_INTERNAL_SOURCE",
            "p6_pr63_sha": "7a13cc6a2f2d7b4c99e18b8866043a0319733454",
            "nx": self.NX, "ny": self.NY, "hours": self.HOURS,
            "A": {"puff_con_sha256": files["A"]["sha256"]},
            "C": {"puff_con_sha256": files["C"]["sha256"]},
        }
        path = self.root / "provenance.json"
        path.write_text(json.dumps(prov))
        return reports, path

    def test_six_direct_pairs_are_independently_measured(self) -> None:
        data = six.build_report("C1", self.direct(), self.NX, self.NY, self.HOURS)
        self.assertEqual(set(data["pair_matrix"]), set(six.PAIRS))
        self.assertEqual(data["status"], "PASS_SCOPE_RESTRICTED")
        for name in ("AB", "CD"):
            self.assertTrue(data["pair_matrix"][name]["bitwise_identical"])
        for name in six.CROSS_MET:
            self.assertEqual(data["pair_matrix"][name]["matching_real4"],
                             3 * self.HOURS)
            self.assertEqual(data["pair_matrix"][name]["provenance"],
                             "DIRECT_RECORDED_REAL4")

    def test_archive_cross_pairs_marked_derived(self) -> None:
        reports, prov = self.archives()
        data = six.build_report(
            "C2", six.from_summaries(reports, prov, self.NX, self.NY, self.HOURS),
            self.NX, self.NY, self.HOURS)
        for name in ("AD", "BC"):
            self.assertEqual(data["pair_matrix"][name]["provenance"],
                             "ALGEBRAIC_DERIVATION_NOT_REMEASURED")
        self.assertEqual(data["pair_matrix"]["AD"]["rmse_bq_m3"],
                         data["pair_matrix"]["BD"]["rmse_bq_m3"])

    def test_direct_rejects_nonidentical_same_met(self) -> None:
        write_con(self.b, [(0.26, 0, 0.4, 0)] * self.HOURS)
        with self.assertRaisesRegex(ValueError, "AB must pass"):
            self.direct()

    def test_archive_rejects_unbound_sha(self) -> None:
        reports, prov = self.archives()
        item = json.loads(reports["BD"].read_text())
        item["a"]["sha256"] = "f" * 64
        reports["BD"].write_text(json.dumps(item))
        with self.assertRaisesRegex(ValueError, "BD a input file SHA"):
            six.from_summaries(reports, prov, self.NX, self.NY, self.HOURS)

    def test_archive_rejects_tampered_hourly_meteorological_delta(self) -> None:
        reports, prov = self.archives()
        item = json.loads(reports["BD"].read_text())
        item["hourly"][0]["max_absolute_difference_bq_m3"] += 1e-4
        reports["BD"].write_text(json.dumps(item))
        with self.assertRaisesRegex(ValueError, "BD differs from AC"):
            six.from_summaries(reports, prov, self.NX, self.NY, self.HOURS)

    def test_archive_rejects_missing_hour(self) -> None:
        reports, prov = self.archives()
        item = json.loads(reports["AC"].read_text())
        item["hourly"].pop()
        reports["AC"].write_text(json.dumps(item))
        with self.assertRaisesRegex(ValueError, "AC missing complete hourly"):
            six.from_summaries(reports, prov, self.NX, self.NY, self.HOURS)

    def test_archive_rejects_same_met_mismatch(self) -> None:
        reports, prov = self.archives()
        item = json.loads(reports["AB"].read_text())
        item["bitwise_identical"] = False
        item["matching_real4"] -= 1
        reports["AB"].write_text(json.dumps(item))
        with self.assertRaisesRegex(ValueError, "contradicts aggregate"):
            six.from_summaries(reports, prov, self.NX, self.NY, self.HOURS)


if __name__ == "__main__":
    unittest.main()
