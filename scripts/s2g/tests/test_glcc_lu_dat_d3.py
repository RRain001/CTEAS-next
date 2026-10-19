"""P2 #53 D3: historical GLCC fraction -> strict LU.DAT v2.1 serialization.
All fixtures here are SYNTHETIC; not actual source/GLAZAS science.
"""
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

D3 = Path(os.environ["P2_D3_GLCC"]).resolve()
OLD = Path(os.environ["P12_OLD_ADAPTER"]).resolve()
SOURCE = "4f2a1977d141e2040da4d36ec6a4826c5c960c84686eaf10f226f388cb3ab90a"
CATS = (11,12,13,14,15,16,17,21,22,23,24,31,32,33,41,42,43,51,52,
        53,54,55,61,62,71,72,73,74,75,76,77,81,82,83,84,85,91,92)


def snapshot(nx, ny, *, epsg=32650, x0="510.885", y0="3531.269", dx=0.100):
    return dict(producer="cteas_p2_glcc_raw", source_sha256=SOURCE,
                source_size_bytes=156000000,
                method="GLCC_HEADERLESS_ROW_DIRECT_GEN_7DP_REAL4_REPLAY",
                evidence_status="PRODUCED_UNVERIFIED",
                official_GLAZAS_parity="NOT_RUN", lu_dat="NOT_RUN",
                p3_geo_dat="NOT_RUN", utm_epsg=epsg, nx=nx, ny=ny,
                xrefkm=x0, yrefkm=y0, dgridkm=dx)


def input_files(directory, nx, ny, *, fractions=None, **kw):
    manifest = snapshot(nx, ny, **kw)
    csv_path = directory / "input.csv"
    if fractions is None:
        fractions = [0.7, 0.3] + [0.] * 36
    with csv_path.open("w", newline="") as stream:
        w=csv.writer(stream, lineterminator="\n")
        w.writerow(("i","j","samples",*(f"cat{c}" for c in CATS)))
        for j in range(1,ny+1):
            for i in range(1,nx+1):
                w.writerow((i,j,4,*[f"{v:.12f}" for v in fractions]))
    manifest["fractions_csv_sha256"]=hashlib.sha256(csv_path.read_bytes()).hexdigest()
    manifest_path=directory/"p2_manifest.json"
    manifest_path.write_text(json.dumps(manifest,sort_keys=True))
    return csv_path,manifest_path


class D3GlccLuContract(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="issue53-d3-")
        self.addCleanup(self.temp.cleanup)
        self.d=Path(self.temp.name)

    def invoke(self, manifest=None, data=None, output=None):
        return subprocess.run([str(D3),str(manifest or self.d/"p2_manifest.json"),
                               str(data or self.d/"input.csv"),str(output or self.d/"out")],
                              capture_output=True,text=True,timeout=45)

    def test_hefei_2500_rows_match_prior_frozen_serializer_exactly(self):
        csv_path,manifest=input_files(self.d,50,50)
        result=self.invoke(manifest,csv_path)
        self.assertEqual(result.returncode,0,result.stderr)
        other=self.d/"old.dat"
        ref=subprocess.run([str(OLD),"landuse",str(csv_path),str(other)],
                           capture_output=True,text=True,timeout=45)
        self.assertEqual(ref.returncode,0,ref.stderr)
        new=(self.d/"out/lu.dat").read_text().splitlines()
        old=other.read_text().splitlines()
        self.assertEqual(len(new),2511)
        self.assertEqual(new[4:11],old[4:11])
        self.assertEqual(new[11:],old[11:])
        report=json.loads((self.d/"out/p2_d3_manifest.json").read_text())
        self.assertEqual(report["rows"],2500)
        self.assertEqual(report["total_samples"],10000)
        self.assertEqual(report["original_GLAZAS_parity"],"NOT_RUN")
        self.assertEqual(report["p3_geo_dat"],"NOT_RUN")
        self.assertEqual(report["lu_dat_sha256"],hashlib.sha256(
            (self.d/"out/lu.dat").read_bytes()).hexdigest())

    def test_selected_direct_production_glcc_fraction_to_d3(self):
        # Synthetic contract; genuine original HITS gate is manual-only.
        csv_path,manifest=input_files(self.d,50,50)
        p=json.loads(manifest.read_text())
        p["method"]="GLCC_HEADERLESS_LAEA_DIRECT_UTM50N_REAL4_GLOBE_LUGRID"
        manifest.write_text(json.dumps(p))
        r=self.invoke(manifest,csv_path)
        self.assertEqual(r.returncode,0,r.stderr)
        report=json.loads((self.d/"out/p2_d3_manifest.json").read_text())
        self.assertEqual(report["input_d1_method"],p["method"])
        self.assertEqual(report["total_samples"],10000)
        self.assertEqual(report["real_source_gen_replay_ci"],
                         "NOT_APPLICABLE_DIRECT_LAEA_METHOD")
        self.assertEqual(report["original_GLAZAS_parity"],"NOT_RUN")

    def test_hefei_scoped_method_rejected_in_different_utm_zone(self):
        input_files(self.d,3,2,epsg=32651)
        p=self.d/"p2_manifest.json"
        m=json.loads(p.read_text())
        m["method"]="GLCC_HEADERLESS_LAEA_DIRECT_UTM50N_REAL4_GLOBE_LUGRID"
        p.write_text(json.dumps(m))
        r=self.invoke()
        self.assertNotEqual(r.returncode,0)
        self.assertIn("DIRECT_SCOPE_UTM50N_ONLY",r.stderr)
        self.assertFalse((self.d/"out").exists())

    def test_new_direct_multi_utm_provenance_remains_unverified(self):
        # This is D3 *software only*: non-Hefei regions may be calculated
        # but cannot be described as CTGPROC original-parity-certified.
        method="GLCC_HEADERLESS_LAEA_DIRECT_WGS84_UTM_REAL4_GLOBE_LUGRID"
        for epsg in (32654,32747):
            with self.subTest(epsg=epsg):
                with tempfile.TemporaryDirectory(prefix="glcc-d3-other-utm-") as d:
                    work=Path(d)
                    csv_path,manifest=input_files(work,3,2,epsg=epsg)
                    m=json.loads(manifest.read_text())
                    m["method"]=method
                    manifest.write_text(json.dumps(m))
                    output=work/"out"
                    run=self.invoke(manifest,csv_path,output)
                    self.assertEqual(run.returncode,0,run.stderr)
                    report=json.loads((output/"p2_d3_manifest.json").read_text())
                    self.assertEqual(report["input_d1_method"],method)
                    self.assertEqual(report["original_GLAZAS_parity"],"NOT_RUN")
                    self.assertEqual(report["p3_geo_dat"],"NOT_RUN")

    def test_non_hefei_method_cannot_disguise_hefei_zone(self):
        input_files(self.d,3,2,epsg=32650)
        p=self.d/"p2_manifest.json"
        m=json.loads(p.read_text())
        m["method"]="GLCC_HEADERLESS_LAEA_DIRECT_WGS84_UTM_REAL4_GLOBE_LUGRID"
        p.write_text(json.dumps(m))
        r=self.invoke()
        self.assertNotEqual(r.returncode,0)
        self.assertIn("CANNOT_CLAIM_HEFEI_SCOPE",r.stderr)
        self.assertFalse((self.d/"out").exists())

    def test_generic_grid_and_southern_utm(self):
        input_files(self.d,3,2,epsg=32748,x0="500.000",y0="7000.000",dx=.025)
        r=self.invoke()
        self.assertEqual(r.returncode,0,r.stderr)
        lines=(self.d/"out/lu.dat").read_text().splitlines()
        self.assertEqual(len(lines),17)
        self.assertEqual(lines[6].strip(),"48S")
        self.assertEqual([tuple(map(int,x.split()[:2])) for x in lines[11:]],
                         [(1,1),(2,1),(3,1),(1,2),(2,2),(3,2)])
        self.assertEqual(len(lines[10].split()),38)
        self.assertEqual([float(x) for x in lines[11].split()[2:-1]][:2],[.7,.3])

    def test_unapproved_glc_mapping_rejected(self):
        input_files(self.d,3,2)
        p=self.d/"p2_manifest.json"
        m=json.loads(p.read_text())
        m["producer"]="cteas_p2_glc_raw"
        p.write_text(json.dumps(m))
        r=self.invoke()
        self.assertNotEqual(r.returncode,0)
        self.assertIn("REJECT_UNAPPROVED_GLC",r.stderr)
        self.assertFalse((self.d/"out").exists())

    def test_csv_mutation_sha_rejected(self):
        src,_=input_files(self.d,3,2)
        src.write_text(src.read_text().replace("0.700000000000","0.600000000000",1))
        r=self.invoke()
        self.assertNotEqual(r.returncode,0)
        self.assertIn("CSV_SHA_MISMATCH",r.stderr)
        self.assertFalse((self.d/"out").exists())

    def test_other_source_sha_rejected(self):
        input_files(self.d,3,2)
        path=self.d/"p2_manifest.json"
        m=json.loads(path.read_text());m["source_sha256"]="0"*64
        path.write_text(json.dumps(m))
        r=self.invoke()
        self.assertNotEqual(r.returncode,0)
        self.assertIn("SOURCE_SHA_NOT_OFFICIAL",r.stderr)

    def test_bad_fraction_conservation_rejected_without_output(self):
        input_files(self.d,3,2,fractions=[.6,.3]+[0.]*36)
        r=self.invoke()
        self.assertNotEqual(r.returncode,0)
        self.assertIn("FRACTION_NOT_CONSERVED",r.stderr)
        self.assertFalse((self.d/"out").exists())

    def test_missing_sample_rejected(self):
        path,manifest=input_files(self.d,3,2)
        lines=path.read_text().splitlines()
        fields=lines[1].split(",");fields[2]="0";lines[1]=",".join(fields)
        path.write_text("\n".join(lines)+"\n")
        m=json.loads(manifest.read_text())
        m["fractions_csv_sha256"]=hashlib.sha256(path.read_bytes()).hexdigest()
        manifest.write_text(json.dumps(m))
        r=self.invoke()
        self.assertNotEqual(r.returncode,0)
        self.assertIn("EMPTY_GLCC_GRID_CELL",r.stderr)
        self.assertFalse((self.d/"out").exists())

    def test_unrepresentable_grid_origin_rejected(self):
        input_files(self.d,3,2,x0="510.884643957")
        r=self.invoke()
        self.assertNotEqual(r.returncode,0)
        self.assertIn("GRID_ORIGIN_PRECISION",r.stderr)

    def test_no_output_overwrite(self):
        input_files(self.d,3,2)
        self.assertEqual(self.invoke().returncode,0)
        r=self.invoke()
        self.assertNotEqual(r.returncode,0)
        self.assertIn("OUTPUT_EXISTS",r.stderr)


if __name__=="__main__":
    unittest.main()
