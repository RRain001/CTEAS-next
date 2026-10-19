"""Indexed source-coordinate diagnostics: synthetic QA only, not a science gate."""
import csv
import hashlib
import struct
from pathlib import Path
import tempfile
import unittest
from native_cpp.reference.exact_glazas_coordinate_lineage import (
    BEGIN_SECTION,END_SECTION,OPEN_MARKER,WRITE_MARKER,CLOSE_MARKER,
    instrument_global_only,read_original,read_native,summarize_lineage,
    HEADER_GEN,HEADER_DIRECT,
)
from native_cpp.reference.validate_p2_glazas_original import GateError
from native_cpp.reference.coordlib_stage_trace import (
    BEGIN as COORD_BEGIN, END as COORD_END,
    P11_MARK, DAT_MARK, P09_MARK, KM_MARK,
    instrument_coordlib, read_staged_records, summarize_staged_records,
)
from native_cpp.reference.diagnose_glazas_mesh_coordinates import f32

class ExactLineageContract(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory(prefix="p2-indexed-")
        self.addCleanup(t.cleanup)
        self.d=Path(t.name)

    def fixture(self):
        # Exactly one GLOBAL branch, the other projections must stay untouched.
        section="\n".join((BEGIN_SECTION,OPEN_MARKER,
                           "                  xmesh=1.0",
                           WRITE_MARKER,CLOSE_MARKER,END_SECTION))
        return "PREFIX\n"+section+"\nOTHER ORIGINAL BRANCH\n"+WRITE_MARKER+"\n"

    def test_instrument_only_one_scoped_global_original_block(self):
        before=self.fixture()
        after=instrument_global_only(before)
        self.assertEqual(after.count("write(98,*)"),1)
        self.assertEqual(after.count("open(98,"),1)
        self.assertEqual(after.count("close(98)"),1)
        self.assertEqual(after.count(WRITE_MARKER),1) # other branch untouched
        self.assertEqual(after.split(END_SECTION)[1],
                         before.split(END_SECTION)[1])

    def test_refuses_unexpected_vendor_patch_shape(self):
        with self.assertRaisesRegex(GateError,"SECTION_NOT_FOUND"):
            instrument_global_only("a totally different source")
        with self.assertRaisesRegex(GateError,"PATCH_DRIFT"):
            instrument_global_only(self.fixture().replace(WRITE_MARKER,"missing"))

    def write_native(self,filename,header,rows):
        p=self.d/filename
        with p.open("w",encoding="utf8",newline="") as f:
            w=csv.writer(f);w.writerow(header);w.writerows(rows)
        return p,hashlib.sha256(p.read_bytes()).hexdigest()

    def test_exact_source_keys_not_nearest_neighbor(self):
        indexed=self.d/"qaindexed.dat"
        qa=self.d/"qamesh.dat"
        indexed.write_text(
          " 9614 4210 18 17 21  1613.0 -1289.0 511.485107 3531.31641\n"
          " 9614 4210 19 17 21  1613.1 -1289.0 511.535107 3531.31641\n")
        qa.write_text(" 511.485107 3531.31641\n 511.535107 3531.31641\n")
        # Raw records in the opposite order, to prove key matching.
        g,gh=self.write_native("gen.csv",HEADER_GEN,[
          [9614,4210,19,17,21,511.535107,3531.31641,7,1],
          [9614,4210,18,17,21,511.484985,3531.31641,6,1],
        ])
        d,dh=self.write_native("direct.csv",HEADER_DIRECT,[
          [9614,4210,19,17,21,1613.1,-1289.0,511.535107,3531.31641,7,1],
          [9614,4210,18,17,21,1613.0,-1289.0,511.485107,3531.31641,7,1],
        ])
        original=read_original(indexed,qa)
        self.assertEqual(original["total"],2)
        report=summarize_lineage(original["rows"],
                                 read_native(g,HEADER_GEN,gh),
                                 read_native(d,HEADER_DIRECT,dh))
        self.assertEqual(report["same_source_sample_key_matches"],2)
        self.assertEqual(report["gen_cell_bin_disagreements_on_shared_keys"],1)
        self.assertEqual(report["direct_cell_bin_disagreements_on_shared_keys"],0)
        self.assertAlmostEqual(report["max_original_to_gen_utm_offset_m"],.122,places=3)
        self.assertEqual(report["max_original_to_direct_source_laea_offset_m"],0)
        self.assertEqual(report["status"],
                         "DIAGNOSTIC_ONLY_NOT_ORIGINAL_NUMERIC_ACCEPTANCE")

    def test_fails_closed_on_index_vs_existing_qa_drift(self):
        indexed=self.d/"qaindexed.dat";qa=self.d/"qamesh.dat"
        indexed.write_text("9614 4210 1 1 21 0 0 511.0 3531.5\n")
        qa.write_text("511.5 3531.5\n")
        with self.assertRaisesRegex(GateError,"INDEXED_QAMESH_VALUES_DISAGREE"):
            read_original(indexed,qa)

    def test_coordlib_instrument_is_bounded_and_injects_four_hex_stages(self):
        # Synthetic excerpt: assert unique guarded patch sites without
        # embedding or publishing any vendor source.
        original=("HEADER\\n"+COORD_BEGIN+"\\n"+P11_MARK+"\\n"
                  +DAT_MARK+"\\n"+P09_MARK+"\\n"+COORD_END+"\\n"
                  +KM_MARK+"\\nFOOTER")
        transformed=instrument_coordlib(original)
        self.assertEqual(transformed.count("write(99,"),4)
        for tag in ("P11","DAT","P09","KM"):
            self.assertIn("'"+tag+"'",transformed)
        self.assertEqual(transformed.split(COORD_END)[-1].split("FOOTER")[-1],"")
        with self.assertRaisesRegex(GateError,"BRANCH_DRIFT"):
            instrument_coordlib(original.replace(COORD_BEGIN,"NOT_THE_BRANCH"))
        with self.assertRaisesRegex(GateError,"MARKER_DRIFT"):
            instrument_coordlib(original.replace(P09_MARK,"MISSING_P09"))

    def test_original_real8_hex_stage_trace_matches_real4_output(self):
        source_x=f32(1612.42505)
        source_y=f32(-1286.57495)
        easting_m=511085.175
        northing_m=3534540.04
        mult=float(f32(.001))
        def line(tag,x,y):
            vals=(float(source_x),float(source_y),float(x),float(y))
            return tag+" "+" ".join(
                format(struct.unpack(">Q",struct.pack(">d",v))[0],"016X")
                for v in vals)+"\\n"
        stage_file=self.d/"fort.99"
        stage_file.write_text("".join((
            line("P11",117.11,31.9),
            line("DAT",117.11,31.9),
            line("P09",easting_m,northing_m),
            line("KM",easting_m*mult,northing_m*mult),
        )))
        original={(9613,4213,19,19):{
            "laea_x":source_x,"laea_y":source_y,
            "x":f32(easting_m*mult),"y":f32(northing_m*mult)}}
        trace=read_staged_records(stage_file)
        result=summarize_staged_records(original,trace)
        self.assertEqual(result["original_indexed_stage_matches"],1)
        self.assertEqual(result["original_indexed_stage_missing"],0)
        self.assertEqual(result["max_XMULTO_real8_stage_residual_m"],0)
        self.assertEqual(result["max_GLOBE_real4_stage_residual_m"],0)
        self.assertEqual(result["max_PJ11_to_DAT2DAT_delta_deg"],0)
        # Truncated/forged records cannot be mistaken for completed science.
        stage_file.write_text(line("P11",117.11,31.9))
        with self.assertRaisesRegex(GateError,"COVERAGE_INCOMPLETE"):
            summarize_staged_records(original,read_staged_records(stage_file))
        stage_file.write_text(line("P11",117.11,31.9)*2)
        with self.assertRaisesRegex(GateError,"DUPLICATE_SOURCE_STAGE"):
            read_staged_records(stage_file)

    def test_fails_closed_on_sha_and_duplicate_key(self):
        p,h=self.write_native("gen.csv",HEADER_GEN,
            [[9614,4210,18,17,21,511.48,3531.31,6,1],
             [9614,4210,18,17,21,511.48,3531.31,6,1]])
        with self.assertRaisesRegex(GateError,"INDEXED_NATIVE_DUPLICATE"):
            read_native(p,HEADER_GEN,h)
        with self.assertRaisesRegex(GateError,"INDEXED_NATIVE_TRACE_SHA_OR_FILE"):
            read_native(p,HEADER_GEN,"0"*64)

if __name__=="__main__":
    unittest.main()
