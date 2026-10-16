#!/usr/bin/env python3
"""P6E CALMET.DAT 2.1 output-contract CTest.

Proves that the P6E micrometeorology output layout is self-consistent
(write -> read -> per-field comparison), that the frozen original OUTHD/OUTHR
record semantics and units are enforced fail-closed, that missing values are
excluded from the error denominators, and that the truth-comparison harness
reports an explicit BLOCKED status instead of a silent pass.
"""
import argparse
import json
import pathlib
import struct
import subprocess
import sys
import tempfile

HOURS=3
NX=8
NY=5
NZ=3
CELLS=NX*NY
LABELS_PER_HOUR=4*NZ+9


def run(command):
    return subprocess.run([str(x) for x in command],capture_output=True,text=True)


def walk(data):
    """Yield (marker_offset, length, payload_offset) for every Fortran record."""
    records=[]
    offset=0
    while offset+8<=len(data):
        length=struct.unpack_from("<i",data,offset)[0]
        if length<0 or offset+8+length>len(data):
            break
        payload=offset+4
        if struct.unpack_from("<i",data,payload+length)[0]!=length:
            break
        records.append((offset,length,payload))
        offset=payload+length+4
    return records


def find_label(data,records,label):
    target=label.rstrip()
    for _,_,payload in records:
        if data[payload:payload+8].decode("ascii","replace").rstrip()==target:
            return payload
    raise AssertionError("record not found: "+label)


def check(tool,path):
    return run([tool,"check","--file",path])


def compare(tool,reference,candidate):
    return run([tool,"compare","--reference",reference,"--candidate",candidate])


def harness(harness_path,tool,arguments):
    return run([sys.executable,harness_path,"--tool",tool]+arguments)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--tool",required=True)
    parser.add_argument("--harness",required=True)
    parser.add_argument("--real-reference")
    parser.add_argument("--real-reference-sha256",default="")
    args=parser.parse_args()
    tool=args.tool
    harness_path=args.harness
    with tempfile.TemporaryDirectory(prefix="p6e-calmet21-") as work:
        root=pathlib.Path(work)
        reference=root/"synthetic-reference.dat"
        emitted=run([tool,"emit-synthetic","--out",reference,"--hours",HOURS,
                     "--nx",NX,"--ny",NY,"--nz",NZ])
        assert emitted.returncode==0, emitted.stderr
        # ---- 1. write -> read -> per-field comparison is exact -------------
        report=check(tool,reference)
        assert report.returncode==0, report.stderr
        inventory=json.loads(report.stdout)
        assert inventory["status"]=="PASS", inventory
        assert inventory["intervals"]==HOURS, inventory
        assert inventory["fields_per_hour"]==LABELS_PER_HOUR, inventory
        assert inventory["cells"]==CELLS, inventory
        assert inventory["record_bytes"]==24+4*CELLS, inventory
        assert inventory["header"]["irtype"]==1
        assert inventory["header"]["iwfcod"]==1
        assert inventory["header"]["lcalgrd"] is True
        assert inventory["header"]["npsta"]==0
        assert inventory["internal_only_absent"] is True
        # OUTHR writes U, V and W inside one level loop, so the sequence is
        # pinned here independently of the reader/writer pair under test.
        expected=["U-LEV  1","V-LEV  1","WFACE  1","U-LEV  2","V-LEV  2","WFACE  2",
                  "U-LEV  3","V-LEV  3","WFACE  3","T-LEV  1","T-LEV  2","T-LEV  3",
                  "IPGT","USTAR","ZI","EL","WSTAR","TEMPK","RHO","QSW","IRH"]
        assert inventory["hourly_labels"]==expected, inventory["hourly_labels"]
        assert inventory["invariants"]["T_LEV1_equals_TEMPK_mismatches"]==0, inventory
        owners={field["owner"] for field in inventory["field_inventory"]}
        assert "p6e" in owners and "p6d" in owners, owners
        unimplemented=set(inventory["not_implemented_in_p6e"])
        assert len(unimplemented)==3*NZ, sorted(unimplemented)   # U/V/W per level
        for label in ("U-LEV  1","V-LEV  1","WFACE  1"):
            assert label in unimplemented, sorted(unimplemented)
        assert "TEMPK" not in unimplemented
        for field in inventory["field_inventory"]:
            assert field["missing"]==0, field
        self_compare=compare(tool,reference,reference)
        assert self_compare.returncode==0, self_compare.stderr
        identical=json.loads(self_compare.stdout)
        assert identical["status"]=="PASS" and identical["total_exceedances"]==0
        for field in identical["fields"]:
            assert field["denominator"]==HOURS*CELLS, field
            assert field["missing_reference"]==0 and field["missing_candidate"]==0
        # ---- 1b. byte-exact rewrite round trip -----------------------------
        rewritten=root/"rewritten.dat"
        rewrite=run([tool,"check","--file",reference,"--rewrite",rewritten])
        assert rewrite.returncode==0, rewrite.stderr
        assert rewritten.read_bytes()==reference.read_bytes(), "rewrite is not byte exact"
        data=bytearray(reference.read_bytes())
        records=walk(data)
        assert len(records)==16+HOURS*LABELS_PER_HOUR, len(records)
        # ---- 2. fail-closed layout violations -----------------------------
        def rejected(name,mutate):
            broken=root/("broken-"+name+".dat")
            candidate=bytearray(data)
            mutate(candidate)
            broken.write_bytes(bytes(candidate))
            result=check(tool,broken)
            assert result.returncode!=0, name+" was accepted"
            assert "CALMET.DAT 2.1" in result.stderr, result.stderr
        first_hourly=find_label(data,records,"U-LEV  1")
        rejected("label",lambda b: b.__setitem__(first_hourly+3,ord('X')))
        controls=[r for r in records if bytes(data[r[2]+40:r[2]+48])==b"UTC+0000"][0][2]
        rejected("irtype",lambda b: struct.pack_into("<i",b,controls+52,0))
        rejected("truncated",lambda b: b.__delitem__(slice(len(b)-4,len(b))))
        marker=[r for r in records if data[r[2]:r[2]+8].decode("ascii","replace").rstrip()=="ZI"][0][0]
        rejected("length-marker",lambda b: struct.pack_into("<i",b,marker,12345))
        # ---- 3. missing values leave the error denominator ----------------
        ustar_payload=find_label(data,records,"USTAR")
        missing_candidate=root/"candidate-missing.dat"
        patched=bytearray(data)
        struct.pack_into("<f",patched,ustar_payload+24,9999.0)
        missing_candidate.write_bytes(bytes(patched))
        missing=json.loads(compare(tool,reference,missing_candidate).stdout)
        ustar=[f for f in missing["fields"] if f["label"]=="USTAR"][0]
        assert ustar["missing_candidate"]==1, ustar
        assert ustar["missing_reference"]==0, ustar
        assert ustar["denominator"]==HOURS*CELLS-1, ustar
        assert ustar["exceedances"]==0, ustar
        # ---- 4. numeric exceedance statistics -----------------------------
        zi_payload=find_label(data,records,"ZI")
        perturbed=root/"candidate-perturbed.dat"
        patched=bytearray(data)
        original=struct.unpack_from("<f",patched,zi_payload+24+4*3)[0]
        struct.pack_into("<f",patched,zi_payload+24+4*3,original+0.5)
        perturbed.write_bytes(bytes(patched))
        result=compare(tool,reference,perturbed)
        assert result.returncode==1, result.stdout+result.stderr
        numeric=json.loads(result.stdout)
        assert numeric["status"]=="FAIL_NUMERIC", numeric
        zi=[f for f in numeric["fields"] if f["label"]=="ZI"][0]
        assert zi["exceedances"]==1, zi
        assert abs(zi["max_abs_error"]-0.5)<1e-6, zi
        assert zi["first_exceedances"][0]["cell"]==4, zi
        assert zi["first_exceedances"][0]["hour"]==1, zi
        assert numeric["total_exceedances"]==1, numeric
        # ---- 5. BLOCKED instead of a silent pass --------------------------
        missing_reference=root/"absent.dat"
        blocked=harness(harness_path,tool,
                        ["--reference",missing_reference,"--reference-sha256","00"])
        assert blocked.returncode==3, blocked.stdout
        assert json.loads(blocked.stdout)["status"]=="BLOCKED_REFERENCE_MISSING"
        no_sha=harness(harness_path,tool,["--reference",reference])
        assert no_sha.returncode==3, no_sha.stdout
        assert json.loads(no_sha.stdout)["status"]=="BLOCKED_REFERENCE_SHA256_MISSING"
        import hashlib
        digest=hashlib.sha256(reference.read_bytes()).hexdigest()
        wrong_sha=harness(harness_path,tool,["--reference",reference,
                                            "--reference-sha256","de"*32])
        assert wrong_sha.returncode==2, wrong_sha.stdout
        assert json.loads(wrong_sha.stdout)["status"]=="FAIL_REFERENCE_SHA256"
        no_candidate=harness(harness_path,tool,["--reference",reference,
                                                "--reference-sha256",digest])
        assert no_candidate.returncode==3, no_candidate.stdout
        pinned=json.loads(no_candidate.stdout)
        assert pinned["status"]=="BLOCKED_CANDIDATE_MISSING", pinned
        assert pinned["reference_layout"]["status"]=="PASS", pinned
        full=harness(harness_path,tool,["--reference",reference,
                                        "--reference-sha256",digest,
                                        "--candidate",reference])
        assert full.returncode==0, full.stdout
        assert json.loads(full.stdout)["status"]=="PASS"
        # ---- 5b. real-input partial candidate mode ------------------------
        observations=root/"observations.csv"
        profile="0.0:280.0;100.0:279.0;200.0:278.0"
        faces="280.0;279.5;279.0"
        tail=","+profile+","+profile+","+faces+","+faces+"\n"
        observations.write_text(
            "hour_index,air_temperature_k,pressure_mb,humidity_pct,opaque_cloud_tenths,"
            "ceiling_hundreds_ft,justa,past_s,to_go_s,aa_profile,bb_profile,aa_face_t,bb_face_t\n"+
            "1,279.25,1028.2,52,0,722,1,3600,39600"+tail+
            "2,281.75,1027.9,46,0,999,1,7200,36000"+tail+
            "3,276.50,1025.1,87,0,999,1,10800,32400"+tail)
        candidate=root/"realcase-candidate.dat"
        emitted_real=run([tool,"emit-realcase","--reference",reference,
                          "--observations",observations,"--out",candidate])
        assert emitted_real.returncode==0, emitted_real.stderr
        real_report=json.loads(emitted_real.stdout)
        assert real_report["produced_fields"]==["TEMPK","IRH","T-LEV  1","QSW","RHO"], real_report
        assert real_report["base_timezone_hours"]==0, real_report
        assert real_report["shortwave_constants"]["ha1"]==990.0, real_report
        assert len(real_report["missing_sentinel_fields"])==LABELS_PER_HOUR-5
        partial=json.loads(compare(tool,reference,candidate).stdout)
        for field in partial["fields"]:
            expected=HOURS*CELLS if field["label"] in ("TEMPK","IRH","T-LEV  1","QSW","RHO") else 0
            assert field["denominator"]==expected, field
            if expected==0:
                assert field["missing_candidate"]==HOURS*CELLS, field
        partial_harness=harness(harness_path,tool,["--reference",reference,
            "--reference-sha256",digest,"--candidate",candidate])
        assert partial_harness.returncode in (0,1), partial_harness.stdout
        assert json.loads(partial_harness.stdout)["status"] in ("PASS","FAIL_NUMERIC")
        bad_observations=root/"short-observations.csv"
        bad_observations.write_text(
            "hour_index,air_temperature_k,pressure_mb,humidity_pct,opaque_cloud_tenths,"
            "ceiling_hundreds_ft,justa,past_s,to_go_s,aa_profile,bb_profile,aa_face_t,bb_face_t\n"
            "1,279.0,1028.2,52,0,999,1,3600,39600"+tail)
        assert run([tool,"emit-realcase","--reference",reference,
                    "--observations",bad_observations,
                    "--out",root/"no.dat"]).returncode!=0
        real_note="real_reference=not supplied"
        # ---- 6. optional frozen real CALMET.DAT 2.1 reference -------------
        if args.real_reference:
            import hashlib
            real=pathlib.Path(args.real_reference)
            assert real.is_file(), real
            assert args.real_reference_sha256, "frozen reference SHA-256 is required"
            assert hashlib.sha256(real.read_bytes()).hexdigest()==\
                   args.real_reference_sha256.lower(), "real reference SHA-256 mismatch"
            real_inventory=json.loads(check(tool,real).stdout)
            assert real_inventory["status"]=="PASS", real_inventory
            assert real_inventory["intervals"]==143, real_inventory["intervals"]
            assert real_inventory["fields_per_hour"]==45, real_inventory["fields_per_hour"]
            assert real_inventory["cells"]==2500, real_inventory["cells"]
            assert real_inventory["header"]["irlg"]==143
            assert len(real_inventory["not_implemented_in_p6e"])==27
            assert real_inventory["invariants"]=={"T_LEV1_equals_TEMPK_mismatches":0,
                "WSTAR_negative_values":0,"ZI_negative_values":0,
                "USTAR_below_0p05_over_land":0,"IRH_outside_0_100":0,
                "IPGT_outside_1_8":0}, real_inventory["invariants"]
            real_rewrite=root/"real-rewritten.dat"
            rewrite_real=run([tool,"check","--file",real,"--rewrite",real_rewrite])
            assert rewrite_real.returncode==0, rewrite_real.stderr
            assert real_rewrite.read_bytes()==real.read_bytes(), \
                "real reference rewrite is not byte exact"
            real_blocked=harness(harness_path,tool,["--reference",real,
                "--reference-sha256",args.real_reference_sha256.lower()])
            assert real_blocked.returncode==3, real_blocked.stdout
            assert json.loads(real_blocked.stdout)["status"]=="BLOCKED_CANDIDATE_MISSING"
            real_note="real_reference=byte_exact+inventory+BLOCKED"
    print("PASS_P6E_E22_CALMET_DAT21_OUTPUT_CONTRACT "
          "hours=%d fields_per_hour=%d cells=%d round_trip=PASS "
          "byte_exact_rewrite=PASS layout_fail_closed=4/4 missing_excluded=PASS "
          "exceedance_stats=PASS "
          "blocked_statuses=4/4 %s"%(HOURS,LABELS_PER_HOUR,CELLS,real_note))
    return 0


if __name__=="__main__":
    sys.exit(main())
