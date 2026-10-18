"""#54 synthetic DAT/SAV and provenance tests, never real TERREL science."""
from __future__ import annotations
import csv
import hashlib
import json
import struct
import tempfile
import unittest
from pathlib import Path
from native_cpp.reference.compare_p1_general import compare,ComparisonError

def hash_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def record(b):
    marker=struct.pack("<i",len(b))
    return marker+b+marker

class GeneralP1ComparatorTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory(prefix="p1-general-parity-")
        self.folder=Path(self.temporary.name)
    def tearDown(self):
        self.temporary.cleanup()
    def make_fixture(self,nx=3,ny=5,route="P1_A_90M_LOCAL"):
        grid={"nx":nx,"ny":ny,"zone":50,"hemisphere":"N",
              "xrefkm":"510.885","yrefkm":"3531.269","dgridkm":0.1}
        elev=[float(100+10*j+i) for j in range(ny) for i in range(nx)]
        native=self.folder/"native.csv"
        with native.open("w",newline="") as f:
            w=csv.writer(f);w.writerow(["i","j","hits","elevation_m"])
            for k,z in enumerate(elev):
                w.writerow([k%nx+1,k//nx+1,2,f"{z:.9f}"])
        dat=self.folder/"terrel.dat"
        lines=["TERREL.DAT      2.0 Synthetic fixture","   2",
               "Not original Fortran","TEST ONLY","UTM","50N",
               "WGS-84  02-21-2003",
               f'{nx:8d}{ny:8d}{grid["xrefkm"]:>12}{grid["yrefkm"]:>12}{0.1:12.3f}{0.1:12.3f}',
               "KM  M","W_E N_S"]
        for j in range(ny-1,-1,-1):
            row=elev[j*nx:(j+1)*nx]
            for k in range(0,nx,10):
                lines.append("".join(f"{z:8.1f}" for z in row[k:k+10]))
        dat.write_text("\n".join(lines)+"\n")
        sav=self.folder/"terrel.sav";n=nx*ny
        sav.write_bytes(record(struct.pack("<7i",0,0,0,0,nx,ny,0))+
                        record(struct.pack(f"<{n}f",*(2*z for z in elev)))+
                        record(struct.pack(f"<{n}i",*([2]*n)))+
                        record(struct.pack(f"<{n}f",*elev)))
        tif=self.folder/"selected.tif";tif.write_bytes(b"MOCK_NOT_REAL_SRTM")
        control=self.folder/"terrel.inp"
        control.write_text("\n".join((
          "!PMAP = UTM !", "!DATUM = WGS-84 !",
          "!UTMHEM = N !", "!IUTMZN = 50 !",
          "!XREFKM = 510.885 !", "!YREFKM = 3531.269 !",
          f"!NX = {nx} !", f"!NY = {ny} !",
          "!DGRIDKM = 0.100 !", "!NTDF = 1 !",
          "1 !GEOTIFF = selected.tif !    !END!", "")))
        binary=self.folder/"terrel.x";binary.write_bytes(b"MOCK_NOT_REAL_FORTRAN")
        native_manifest=self.folder/"p1_native_manifest.json"
        native_manifest.write_text(json.dumps({
          "grid":grid,"producer_issue":54,"status":"PRODUCED_UNVERIFIED",
          "route":route,"selected_tif_sha256":hash_file(tif),
          "grid_sha256":"a"*64,"terrain_csv_sha256":hash_file(native)
        }))
        attestation=self.folder/"original_attestation.json"
        attestation.write_text(json.dumps({
           "route":route,"grid_sha256":"a"*64,
           "selected_tif_sha256":hash_file(tif),
           "original_terrel_dat_sha256":hash_file(dat),
           "original_terrel_sav_sha256":hash_file(sav),
           "original_control_sha256":hash_file(control),
           "original_executable_sha256":hash_file(binary)
        }))
        return dict(native_manifest=native_manifest,original_attestation=attestation,
                    native_terrain=native,original_dat_path=dat,original_sav_path=sav,
                    original_control=control,original_executable=binary,
                    selected_tif=tif,report=self.folder/"comparison.json")
    def test_non_square_3x5_and_row_direction(self):
        files=self.make_fixture()
        result=compare(**files)
        self.assertEqual(result["numeric_parity"],"NUMERIC_PASS_PROVISIONAL")
        self.assertEqual(result["science_acceptance"],
                         "NOT_ACCEPTED_INDEPENDENT_ORIGINAL_RUN_AUDIT_REQUIRED")
        self.assertEqual(result["cells"],15)
    def test_non_multiple_ten_13x2_30m_route(self):
        files=self.make_fixture(nx=13,ny=2,route="P1_B_30M_DOWNLOAD")
        result=compare(**files)
        self.assertEqual(result["numeric_parity"],"NUMERIC_PASS_PROVISIONAL")
        self.assertEqual(result["route"],"P1_B_30M_DOWNLOAD")
    def test_changed_dem_sha_rejected(self):
        files=self.make_fixture()
        files["selected_tif"].write_bytes(b"CHANGED_BYTES")
        with self.assertRaisesRegex(ComparisonError,"selected TIFF"):
            compare(**files)
        self.assertFalse(files["report"].exists())
    def test_wrong_original_source_route_rejected(self):
        files=self.make_fixture()
        att=json.loads(files["original_attestation"].read_text())
        att["route"]="P1_B_30M_DOWNLOAD"
        files["original_attestation"].write_text(json.dumps(att))
        with self.assertRaisesRegex(ComparisonError,"route identities"):
            compare(**files)
    def test_original_projection_mismatch_rejected(self):
        files=self.make_fixture()
        dat=files["original_dat_path"]
        dat.write_text(dat.read_text().replace("50N\n","49N\n"))
        att=json.loads(files["original_attestation"].read_text())
        att["original_terrel_dat_sha256"]=hash_file(dat)
        files["original_attestation"].write_text(json.dumps(att))
        with self.assertRaisesRegex(ComparisonError,"projection"):
            compare(**files)
    def test_broken_sav_record_marker_rejected(self):
        files=self.make_fixture()
        sav=files["original_sav_path"]
        raw=bytearray(sav.read_bytes());raw[32:36]=b"xxxx";sav.write_bytes(raw)
        att=json.loads(files["original_attestation"].read_text())
        att["original_terrel_sav_sha256"]=hash_file(sav)
        files["original_attestation"].write_text(json.dumps(att))
        with self.assertRaisesRegex(ComparisonError,"closing marker"):
            compare(**files)
    def test_first_difference_located_not_auto_accepted(self):
        files=self.make_fixture()
        native=files["native_terrain"]
        lines=native.read_text().splitlines()
        lines[1]=lines[1].replace("100.000000000","101.000000000")
        native.write_text("\n".join(lines)+"\n")
        meta=json.loads(files["native_manifest"].read_text())
        meta["terrain_csv_sha256"]=hash_file(native)
        files["native_manifest"].write_text(json.dumps(meta))
        result=compare(**files)
        self.assertEqual(result["numeric_parity"],"NUMERIC_FAIL")
        self.assertEqual(result["dat_bad_cells"],1)
        self.assertEqual(result["raw_mean_bad_cells"],1)
        self.assertEqual(result["dat_first20"][0][:2],[1,1])

    def update_control_attestation(self,files):
        att=json.loads(files["original_attestation"].read_text())
        att["original_control_sha256"]=hash_file(files["original_control"])
        files["original_attestation"].write_text(json.dumps(att))

    def test_original_control_wrong_tiff_rejected_even_with_attested_hash(self):
        files=self.make_fixture()
        (self.folder/"other.tif").write_bytes(b"DIFFERENT_REAL_BYTES")
        ctrl=files["original_control"]
        ctrl.write_text(ctrl.read_text().replace("selected.tif","other.tif"))
        self.update_control_attestation(files)
        with self.assertRaisesRegex(ComparisonError,"GEOTIFF bytes differ"):
            compare(**files)

    def test_original_control_grid_mismatch_rejected_even_with_hash(self):
        files=self.make_fixture()
        ctrl=files["original_control"]
        ctrl.write_text(ctrl.read_text().replace("!NX = 3 !","!NX = 4 !"))
        self.update_control_attestation(files)
        with self.assertRaisesRegex(ComparisonError,"mismatched NX"):
            compare(**files)

    def test_original_control_multiple_tifs_refused(self):
        files=self.make_fixture()
        ctrl=files["original_control"]
        with ctrl.open("a") as stream:
            stream.write("2 !GEOTIFF = selected.tif !    !END!\n")
        self.update_control_attestation(files)
        with self.assertRaisesRegex(ComparisonError,"one numbered GEOTIFF"):
            compare(**files)

    def test_original_control_missing_tiff_refused(self):
        files=self.make_fixture()
        ctrl=files["original_control"]
        ctrl.write_text(ctrl.read_text().replace("selected.tif","missing.tif"))
        self.update_control_attestation(files)
        with self.assertRaisesRegex(ComparisonError,"missing/empty"):
            compare(**files)

    def test_sav_shape_mismatch_rejected(self):
        files=self.make_fixture()
        sav=files["original_sav_path"]
        raw=bytearray(sav.read_bytes())
        struct.pack_into("<i",raw,20,999);sav.write_bytes(raw)
        att=json.loads(files["original_attestation"].read_text())
        att["original_terrel_sav_sha256"]=hash_file(sav)
        files["original_attestation"].write_text(json.dumps(att))
        with self.assertRaisesRegex(ComparisonError,"dimensions differ"):
            compare(**files)

if __name__=="__main__":
    unittest.main()
