"""P3 D4 attestation fail-closed SOFTWARE fixtures, not original scientific data."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from native_cpp.orchestration import p3_d4_science_handoff as mod
from native_cpp.orchestration.plan import ContractError

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path

def jwrite(path, obj):
    write(path,json.dumps(obj,sort_keys=True))
    return path

class D4GenuineFortranHandoffContract(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix="p3d4-")
        self.addCleanup(temp.cleanup)
        root=Path(temp.name)
        self.site=root/"p3_d2_wolsong_2022"
        self.site.mkdir()
        self.lu=write(self.site/"geo/ctgproc/p2c_case/lu.dat","synthetic 38-class LU")
        self.geo=write(self.site/"geo/makegeo/p3_case/geo.dat","synthetic cpp GEO")
        self.csv=write(self.site/"geo/makegeo/p3_case/p3.csv","synthetic cpp CSV")
        self.ctrl=write(self.site/"geo/makegeo/p3_case/makegeo.inp","synthetic controls")
        self.fortran=write(root/"fortran_original.geo.dat","synthetic separate original GEO")
        self.compare=root/"comparison.json"
        self.dest=self.site/"evidence/p3-d4-scoped-science.json"
        source={"schema":"p2","status":"P2C_GENERIC_CASE_PRODUCED_UNVERIFIED",
             "method":mod.SELECTED_P2C,"mode":"coastal",
             "source_tiff_sha256":mod.WOLSONG_GLC30M_SHA256,
             "source_bln_sha256":mod.FULL_ORIGINAL_COAST_BNL_SHA256,
             "mapping_policy_sha256":mod.FROZEN_30M_POLICY_SHA256,
             "case_name":"p3_d2_wolsong_2022",
             "case_yaml_sha256":"a"*64,"grid_cmn_sha256":"b"*64,
             "research_time_sha256":"c"*64,
             "utm_epsg":32652,"nx":200,"ny":200,"lu_dat_sha256":digest(self.lu),
             "hits_csv_sha256":"d"*64}
        self.p2_path=self.site/"evidence/p2.json"
        jwrite(self.p2_path,source)
        p3={"status":"P3_NATIVE_SAME_CASE_PRODUCED_UNVERIFIED",
             "p2_kind":"C","p2_method":mod.SELECTED_P2C,
             "p1_tif_sha256":mod.WOLSONG_SRTMGL1_SHA256,
             "p3_original_makegeo_science":"NOT_RUN",
             "case_name":source["case_name"],"case_yaml_sha256":source["case_yaml_sha256"],
             "grid_cmn_sha256":source["grid_cmn_sha256"],
             "research_time_sha256":source["research_time_sha256"],
             "utm_epsg":32652,"nx":200,"ny":200,"xrefkm":"533.215",
             "yrefkm":"3942.629","dgridkm":0.1,
             "p2_attestation_sha256":digest(self.p2_path),"p2_lu_dat_sha256":digest(self.lu),
             "geo_dat_sha256":digest(self.geo),"p3_csv_sha256":digest(self.csv),
             "makegeo_controls_sha256":digest(self.ctrl),
             "research_begin_utc":"20220101-000000","research_end_utc":"20221231-230000",
             "p1_bin_sha256":"1"*64,"p3_bin_sha256":"2"*64,
             "dat_bin_sha256":"3"*64,"terrel_dat_sha256":"4"*64,
             "makegeo_template_sha256":"5"*64}
        self.p3_path=self.site/"evidence/p3.json"
        jwrite(self.p3_path,p3)
        cmp={"status":"P3_NONHEFEI_ORIGINAL_MAKEGEO_PASS","failures":0,
             "values_compared":320000,"formatted_values_compared":320000,
             "nx":200,"ny":200,"utm_zone":52,"utm_hemisphere":"N",
             "xrefkm":533.215,"yrefkm":3942.629,"dgridkm":.1,
             "native_geo_sha256":digest(self.geo),"native_csv_sha256":digest(self.csv),
             "original_geo_sha256":digest(self.fortran),
             "metrics":{name:{"compared_cells":40000,
                              "displayed_value_mismatches":0,
                              "csv_outside_fixed_precision_tolerance":0}
                        for name in mod.FIELDS}}
        jwrite(self.compare,cmp)

    def accept(self):
        return mod.accept(case_root=self.site,original_geo=self.fortran,
                          comparison_path=self.compare,destination=self.dest)

    def test_software_fixture_attested_but_not_s3(self):
        r=self.accept()
        self.assertEqual(r["status"],mod.SELECTED_STATUS)
        self.assertEqual(r["s3_five_product_stack"],"NOT_ACCEPTED")
        self.assertEqual(r["p4_up_dat"],"NOT_RUN")
        self.assertEqual(r["original_displayed_value_mismatches"],0)
        self.assertEqual(r["p2_lu_dat_sha256"],digest(self.lu))
        with self.assertRaisesRegex(ContractError,"fresh output"):
            self.accept()

    def test_original_science_mismatch_never_certified(self):
        x=json.loads(self.compare.read_text())
        x["metrics"]["z0_m"]["displayed_value_mismatches"]=1
        jwrite(self.compare,x)
        with self.assertRaisesRegex(ContractError,"field failed science"):
            self.accept()
        self.assertFalse(self.dest.exists())

    def test_original_geo_mutation_never_certified(self):
        self.fortran.write_text("different original file")
        with self.assertRaisesRegex(ContractError,"actual files"):
            self.accept()

    def test_stale_p2_case_attestation_fails_before_certificate(self):
        x=json.loads(self.p2_path.read_text())
        x["grid_cmn_sha256"]="0"*64
        jwrite(self.p2_path,x)
        with self.assertRaisesRegex(ContractError,"B-0 mismatch"):
            self.accept()

    def test_missing_native_integer_hits_sha_never_attested(self):
        original=json.loads(self.p2_path.read_text())
        original.pop("hits_csv_sha256")
        jwrite(self.p2_path,original)
        with self.assertRaisesRegex(ContractError,"integer HITS CSV SHA missing"):
            self.accept()
        self.assertFalse(self.dest.exists())

    def test_native_lu_bytes_cannot_change_after_d3(self):
        self.lu.write_text("mutated 38-class file")
        with self.assertRaisesRegex(ContractError,"LU bytes"):
            self.accept()


if __name__=="__main__":
    unittest.main()
