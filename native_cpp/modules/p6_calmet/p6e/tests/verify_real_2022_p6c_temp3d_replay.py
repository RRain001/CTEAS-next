#!/usr/bin/env python3
"""E18 real Hefei 2022 P6C observation replay into selected TEMP3D.

Real values from original-verified P6B 143h COMP/RDSN artifact.
Mixing heights are synthetic scenarios: no original CALMET P6E
real-2022 field numerical parity can be inferred.
"""
import argparse
import base64
import hashlib
import json
import math
import subprocess
import zlib
from pathlib import Path

PAYLOAD_SHA256 = "ac45709dec5d5c624e2fbeeede57b4e55c311e384cfcb7a127afa4b5dcc9513b"
JOINT_CSV_SHA256 = "400226164f4e17665487ec0845f3ca6025ecdf310178a12fd9bed9d53818554f"
COMP_REPORT_SHA256 = "2bf75c3de394f0fd712baa21bc4595c9445a5cd01335f48ab1947a48a9506485"
FACE_HEIGHTS = (0, 20, 40, 80, 160, 320, 640, 1200, 2000, 3000)
SCENARIO_ZICONV_M = (0., 150., 500.)
HOURS = 143
LAYERS = 9


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError("E18 " + message)


def load_case(path: Path) -> dict:
    encoded = path.read_text(encoding="ascii").strip()
    data = zlib.decompress(base64.b64decode(encoded,validate=True))
    require(hashlib.sha256(data).hexdigest() == PAYLOAD_SHA256,
            "golden fixture content hash drift")
    p = json.loads(data)
    prov = p["provenance"]
    require(p["schema"] == "CTEAS_P6E_E18_P6C_REAL_2022_COMPACT", "schema drift")
    require(prov["github_run_id"] == 38113874913 and
            prov["artifact_id"] == 11693445092 and
            prov["joint_csv_sha256"] == JOINT_CSV_SHA256 and
            prov["original_comp_report_sha256"] == COMP_REPORT_SHA256 and
            prov["original_comp_status"] == "PASS_ORIGINAL_COMP_RUNTIME_AA_BB" and
            prov["original_comp_hours"] == HOURS and
            prov["original_justa_turnovers"] == 11,
            "frozen original COMP/RDSN source evidence provenance drift")
    require(p["case"]["vertical_face_m"] == list(FACE_HEIGHTS), "face geometry drift")
    require(len(p["faces"]) == 13 and
            all(len(face) == 10 and all(math.isfinite(x) for x in face)
                for face in p["faces"]), "invalid original measured upper faces")
    require(len(p["hours"]) == HOURS, "not a full 143h real-observation capture")
    return p


def compile_replay(p: dict):
    data = []
    swapped = positive = rain_missing = rain_measured = turns = 0
    prev = None
    for row_idx, hour in enumerate(p["hours"]):
        (end, ts, rh, cc, precip, precip_valid, older, newer,
         aa_slot, bb_slot, justa, past, to_go, gap, turnovers) = hour
        expected_end = 1640998800 + row_idx*3600
        require(end == expected_end, "nonhourly/2022 end timestamp")
        require(1 <= older < newer <= 13, "out-of-range 2022 sounding index")
        require((older, newer) == ((row_idx+1)//12+1, (row_idx+1)//12+2)
                if (row_idx+1)%12 else
                (older, newer) == ((row_idx+1)//12+1, (row_idx+1)//12+2),
                "unexpected sounding index")
        require(justa in (-1,1) and
                (aa_slot,bb_slot) == ((0,1) if justa>0 else (1,0)),
                "physical AA/BB inversion")
        require(gap == 43200 and past + to_go == gap and
                past >= 0 and to_go >= 0 and past % 3600 == 0,
                "original P6C sounding time bracket drift")
        require(turnovers == (row_idx+1)//12, "turnover count inconsistent")
        if prev is not None:
            require(end > prev, "nonmonotonic observation times")
        prev = end
        require(180 < ts < 330 and 0 <= rh <= 100 and 0 <= cc <= 10,
                "invalid real surface observations")
        require(precip_valid == 0 and precip == 9999,
                "missing precipitation treated as observed dry/rain")
        rain_missing += 1
        rain_measured += precip_valid
        swapped += int(justa == -1)
        positive += int(justa == 1)
        turns = turnovers
        aa = p["faces"][(older if justa>0 else newer)-1]
        bb = p["faces"][(newer if justa>0 else older)-1]
        for height in SCENARIO_ZICONV_M:
            data.append((past//3600,justa,aa,bb,ts,height))
    require((swapped,positive,turns,rain_missing,rain_measured) ==
            (72,71,11,143,0), "real 2022 branch coverage drift")
    return data,dict(hours=HOURS,swapped_AABB=swapped,
                     normal_AABB=positive,sounding_turnovers=turns,
                     rain_missing=rain_missing,rain_measured=rain_measured)


def run_candidate(binary: Path, testcases) -> bytes:
    rows = [f"{len(testcases)} 1 1 {LAYERS} 1"]
    for past_hour,justa,aa,bb,surface,convheight in testcases:
        rows.append(f"1 {past_hour} 100")
        rows.append(" ".join(str(v) for v in FACE_HEIGHTS))
        rows.append(f"{justa} 50 50")
        rows.extend(f"{ta:.10f} {tb:.10f}" for ta,tb in zip(aa,bb))
        rows.append(f"{surface:.10f} {convheight:.10f}")
    inp = "\n".join(rows) + "\n"
    q = subprocess.run([str(binary)],input=inp,stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE,text=True)
    require(q.returncode == 0,
            "C++ TEMP3D real-observation input replay failed: " + q.stderr[-1500:])
    return q.stdout.encode("ascii")


def check_output(raw: bytes, p: dict, cases, coverage):
    rows = raw.decode("ascii").splitlines()
    require(len(rows) == len(cases)*LAYERS, "TEMP3D missed original 2022 levels")
    temp_count=0
    by_window={1:0,6:0,143:0}
    bounds=[float("inf"),float("-inf")]
    for ci,(past_hour,justa,aa,bb,surface,conv) in enumerate(cases):
        original_hour=ci//len(SCENARIO_ZICONV_M)+1
        for k in range(LAYERS):
            tokens=rows[ci*LAYERS+k].split()
            require(len(tokens)==5, "TEMP3D source output schema")
            idx,i,j,level=(int(x) for x in tokens[:4])
            t=float(tokens[4])
            require((idx,i,j,level)==(ci+1,1,1,k+1), "TEMP3D source level order")
            require(math.isfinite(t) and 180<t<350, "nonphysical derived 2022 temperature")
            if k==0:
                require(abs(t-surface)<2e-6, "real station temperature not preserved")
            bounds[0]=min(bounds[0],t);bounds[1]=max(bounds[1],t)
            temp_count+=1
            for window in by_window:
                if original_hour<=window:by_window[window]+=1
    require(temp_count==143*3*9 and by_window=={1:27,6:162,143:3861},
            "E18 1h/6h/143h profile/window counts")
    return dict(status="PASS_REAL_OBS_SYNTHETIC_HEIGHT_TEMP3D_SMOKE",
                real_observation_hours=HOURS,scenario_heights_m=list(SCENARIO_ZICONV_M),
                profile_scalar_results=temp_count,validation_windows=by_window,
                min_max_computed_temperature_k=bounds,
                original_p6c_reference_comp="PASS_2022_143H",
                original_p6e_2022_field_parity="NOT_VERIFIED",
                p6d_diagnostic_wind="NOT_USED",rain_validated="NO",
                **coverage)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--fixture",type=Path,required=True)
    parser.add_argument("--cpp",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    p=load_case(args.fixture)
    testcases,coverage=compile_replay(p)
    result=run_candidate(args.cpp.resolve(),testcases)
    require(run_candidate(args.cpp.resolve(),testcases)==result,
            "TEMP3D real P6C observation replay not deterministic")
    report=check_output(result,p,testcases,coverage)
    report["input_canonical_sha256"]=PAYLOAD_SHA256
    report["provenance"]=p["provenance"]
    report["cpp_result_sha256"]=hashlib.sha256(result).hexdigest()
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))


if __name__=="__main__":
    main()
