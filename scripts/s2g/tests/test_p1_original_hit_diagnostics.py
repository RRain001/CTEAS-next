"""No real DEM or original vendor in CI; test hit-difference math only."""
import unittest
from scripts.s2g.p1_original_hit_diagnostics import localize_hit_differences

class OriginalNativeHitLocationTests(unittest.TestCase):
    def test_adjacent_redistribution_without_global_hit_change(self):
        old=[2,4,2,3,1,2]
        new=[2,3,3,3,1,2]
        report=localize_hit_differences(old,new,3,2)
        self.assertEqual(report["cells_mismatched"],2)
        self.assertEqual(report["net_original_minus_native"],0)
        self.assertEqual(report["original_surplus_sample_hits"],1)
        self.assertEqual(report["native_surplus_sample_hits"],1)
        self.assertEqual(report["horizontal_adjacent_opposite_sign_candidates"],1)
        self.assertEqual(report["mismatch_cells_per_model_row_south_to_north"],[2,0])
        self.assertEqual(report["mismatch_cells_per_model_column_west_to_east"],[0,1,1])
        self.assertEqual(report["first30_mismatched_cells_i_j_original_native_delta"],
                         [[2,1,4,3,1],[3,1,2,3,-1]])
        self.assertEqual(report["scope"],"AGGREGATE_DIAGNOSTIC_ONLY_NO_ASSIGNMENT_REPAIR")

    def test_global_one_extra_original_sample(self):
        r=localize_hit_differences([1,2,3,4],[1,2,3,3],2,2)
        self.assertEqual((r["original_hits_total"],r["native_hits_total"]),(10,9))
        self.assertEqual(r["net_original_minus_native"],1)
        self.assertEqual(r["cells_mismatched"],1)

    def test_negative_and_bad_size_fail_closed(self):
        with self.assertRaises(ValueError):
            localize_hit_differences([1,2],[1],2,1)
        with self.assertRaises(ValueError):
            localize_hit_differences([-1],[0],1,1)

if __name__=="__main__":
    unittest.main()
