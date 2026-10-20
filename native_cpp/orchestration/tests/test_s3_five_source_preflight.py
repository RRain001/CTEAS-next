"""S3-0 isolated producer-proof joins; synthetic software contract only.

These fixtures do not contain NOAA, DEM, land-use or actual original science.
"""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from native_cpp.orchestration.plan import ContractError
from native_cpp.orchestration.s3_five_source_preflight import validate,STATUS


class S3B0FiveSourceSoftwareTests(unittest.TestCase):
    def setUp(self):
        tmp=TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root=Path(tmp.name)/"independent_second_case"
        root.mkdir()
        self.case=SimpleNamespace(case_path=root/"case.yaml",
            case_name=root.name,case_sha256="a"*64,
            grid_sha256="b"*64,time_sha256="c"*64,
            utm_zone=52,hemisphere="N",nx=20,ny=20,dgridkm=.2,
            research_begin="20221231-230000",research_end="20230101-020000")
        self.root=root
        sha=(self.case.case_sha256,self.case.grid_sha256,self.case.time_sha256)
        self.p2={"status":"P2C_GENERIC_CASE_PRODUCED_UNVERIFIED",
            "method":"P2_C_GLC30M_SOURCE_SUBPOINT_GLAZAS_LUGRID_R4_HITS_V1",
            "case_name":root.name,
            "case_yaml_sha256":sha[0],"grid_cmn_sha256":sha[1],
            "research_time_sha256":sha[2],"utm_epsg":32652,"nx":20,"ny":20}
        self.p3={"status":"P3_NATIVE_SAME_CASE_PRODUCED_UNVERIFIED",
            "case_name":root.name,"case_yaml_sha256":sha[0],
            "grid_cmn_sha256":sha[1],"research_time_sha256":sha[2],
            "utm_epsg":32652,"nx":20,"ny":20,"p2_kind":"C",
            "p2_method":self.p2["method"],
            "p2_attestation_sha256":"d"*64,"p2_lu_dat_sha256":"e"*64,
            "p1_tif_sha256":"1"*64,"p1_csv_sha256":"2"*64,
            "terrel_dat_sha256":"3"*64,"geo_dat_sha256":"4"*64}
        self.p4={"status":"PRODUCED_UNVERIFIED",
            "admission":{"case_root":str(root.resolve()),
                "upperair_root":str((root/"met/upperair").resolve()),
                "case.yaml":sha[0],"grid/grid.cmn":sha[1],
                "grid/research_time":sha[2]},
            "pstop_hpa":500.0,"jdat":2,"ifmt":1,
            "writer_utc":{"begin":"2022-12-31T12:00:00Z",
                          "end":"2023-01-01T12:00:00Z"},
            "candidate_final":{"status":"PRODUCED_UNVERIFIED",
                "station_count":1,"stations_csv_sha256":"5"*64,
                "files":[{"wmo":"58424","sha256":"6"*64}]}}
        self.p5={"status":"PRODUCED_UNVERIFIED",
            "case_name":root.name,"case_sha256":sha[0],
            "grid_sha256":sha[1],"research_time_sha256":sha[2],
            "published_surf_sha256":"7"*64,
            "SURF_hour_ending_expected_records":3,
            "ordered_ifstn":[583140,583210],
            "produced_output_sha256":{
               "met/surface/final/stations.csv":"8"*64}}
        self.files={"p2_attestation_sha256":"d"*64,
            "p2_lu_dat_sha256":"e"*64,
            "terrel_dat_sha256":"3"*64,"geo_dat_sha256":"4"*64,
            "upperair_stations_sha256":"5"*64,
            "upperair":{"58424":"6"*64},
            "surf_sha256":"7"*64,"surface_stations_sha256":"8"*64}

    def run_join(self):
        return validate(self.case,self.p2,self.p3,self.p4,self.p5,self.files)

    def test_same_case_source_only_pass_has_no_g19_or_p6_pass(self):
        x=self.run_join()
        self.assertEqual(x["status"],STATUS)
        self.assertEqual(x["s3_g19_native_reader"],"NOT_RUN")
        self.assertEqual(x["s3_five_product_scientific_acceptance"],"NOT_ACCEPTED")
        self.assertEqual(x["native_paths"],["P1","P2-C","P3","P4","P5"])

    def test_rejects_retired_p2b_even_if_other_shas_equal(self):
        self.p3["p2_kind"]="B"
        with self.assertRaisesRegex(ContractError,"retired P2-B"):
            self.run_join()

    def test_rejects_p2_foreign_case_and_p3_wrong_p2_lu(self):
        self.p2["case_yaml_sha256"]="0"*64
        with self.assertRaisesRegex(ContractError,"P2 wrong B0"):
            self.run_join()
        self.p2["case_yaml_sha256"]=self.case.case_sha256
        self.p3["p2_lu_dat_sha256"]="0"*64
        with self.assertRaisesRegex(ContractError,"another P2"):
            self.run_join()

    def test_rejects_old_p4_annual_case_or_station_data(self):
        self.p4["admission"]["grid/grid.cmn"]="0"*64
        with self.assertRaisesRegex(ContractError,"P4 not bound"):
            self.run_join()
        self.p4["admission"]["grid/grid.cmn"]=self.case.grid_sha256
        self.p4["candidate_final"]["files"][0]["sha256"]="0"*64
        with self.assertRaisesRegex(ContractError,"P4 native UP bytes"):
            self.run_join()

    def test_rejects_foreign_p5_b0_window_or_surf(self):
        self.p5["research_time_sha256"]="0"*64
        with self.assertRaisesRegex(ContractError,"P5 not bound"):
            self.run_join()
        self.p5["research_time_sha256"]=self.case.time_sha256
        self.p5["SURF_hour_ending_expected_records"]=2
        with self.assertRaisesRegex(ContractError,"hourly window"):
            self.run_join()
        self.p5["SURF_hour_ending_expected_records"]=3
        self.p5["published_surf_sha256"]="0"*64
        with self.assertRaisesRegex(ContractError,"actual SURF"):
            self.run_join()

    def test_rejects_unbracketed_p4_and_duplicate_p5_stations(self):
        self.p4["writer_utc"]["end"]="2023-01-01T00:00:00Z"
        with self.assertRaisesRegex(ContractError,"00/12 brackets"):
            self.run_join()
        self.p4["writer_utc"]["end"]="2023-01-01T12:00:00Z"
        self.p5["ordered_ifstn"]=[583140,583140]
        with self.assertRaisesRegex(ContractError,"duplicated"):
            self.run_join()


if __name__=="__main__":
    unittest.main()
