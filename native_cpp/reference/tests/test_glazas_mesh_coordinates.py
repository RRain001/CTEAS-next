"""Synthetic coordinate QA diagnostics only, never a scientific GLAZAS oracle."""
import csv
from pathlib import Path
import tempfile
import unittest
from native_cpp.reference.diagnose_glazas_mesh_coordinates import (
    audit,fortran_original_cell,f32,inside_margin,load_fortran,load_native,
    summarize,
)

class MeshCoordinatesDiagnostic(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root=Path(t.name)

    def test_near_100m_boundary_can_change_integer_bin(self):
        y=3531.320
        original=(510.98480,y)
        native=(510.98520,y)
        self.assertNotEqual(fortran_original_cell(*original),
                            fortran_original_cell(*native))
        row={"source_i":8150,"source_j":7550,"mesh_i":1,"mesh_j":1,
             "usgs_category":21,"x":native[0],"y":native[1],
             "assigned_i":fortran_original_cell(*native)[0],
             "assigned_j":fortran_original_cell(*native)[1]}
        r=summarize([original],[row])
        self.assertEqual(r["matched_points"],1)
        self.assertEqual(len(r["coordinate_cell_assignment_disagreements_first_50"]),1)
        self.assertLess(r["max_matched_projected_offset_m"],1)

    def test_consistent_original_native_bins(self):
        x,y=510.930,3531.310
        i,j=fortran_original_cell(x,y)
        row={"source_i":1,"source_j":1,"mesh_i":1,"mesh_j":1,
             "usgs_category":21,"x":x+0.00001,"y":y,
             "assigned_i":i,"assigned_j":j}
        r=summarize([(x,y)],[row])
        self.assertEqual(r["matched_points"],1)
        self.assertEqual(r["coordinate_cell_assignment_disagreements_first_50"],[])
        self.assertEqual(r["unmatched_original_points"],0)

    def test_missing_matching_point_is_reported_not_accepted(self):
        r=summarize([(510.92,3531.30)],[])
        self.assertEqual(r["matched_points"],0)
        self.assertEqual(r["unmatched_original_points"],1)
        self.assertEqual(r["status"],"DIAGNOSTIC_ONLY_NOT_SCIENTIFIC_ORACLE")

    def test_text_csv_paired_input(self):
        qa=self.root/"qamesh.dat"
        qa.write_text("  510.93500  3531.32000\n")
        native=self.root/"native.csv"
        with native.open("w",newline="") as fp:
            wr=csv.writer(fp)
            wr.writerow(["source_i","source_j","mesh_i","mesh_j","usgs_category",
                         "x_km","y_km","assigned_i","assigned_j"])
            wr.writerow([8110,7020,3,11,21,510.93500,3531.32000,
                         *fortran_original_cell(510.93500,3531.32000)])
        result=audit(qa,native)
        self.assertEqual(result["matched_points"],1)

    def test_outside_window_is_filtered(self):
        self.assertFalse(inside_margin(511.0,3600.0))
        self.assertTrue(inside_margin(512.0,3533.0))

    def test_single_precision_quantization_is_explicit(self):
        self.assertIsInstance(f32(510.985),float)
        self.assertEqual(f32(f32(510.985)),f32(510.985))

if __name__=="__main__":
    unittest.main()
