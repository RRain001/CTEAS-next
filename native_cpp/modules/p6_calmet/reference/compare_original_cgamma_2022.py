#!/usr/bin/env python3
"""Original *running* CALMET 6.5 CGAMMA vs C++ for actual 143 2022 hours.

The Fortran inputs ZUPT and ZICONV are extracted from the write-only source
instrumentation, not reconstructed or inferred from a guessed mixing height.
Original upper-air T and stateful convective carry are independently computed
in C++ using the same UP.DAT. Reference has original CGAMMA source unchanged.
"""
from __future__ import annotations
import argparse,csv,datetime,hashlib,json,math,subprocess
from pathlib import Path

def sha(p:Path):return hashlib.sha256(p.read_bytes()).hexdigest()
def parse(log:Path):
    observations=[]
    for line in log.read_text(errors="replace").splitlines():
        if "P6C_GAMMA_TRACE" not in line:continue
        values=line.split("P6C_GAMMA_TRACE",1)[1].replace("D","E").split()
        if len(values)!=5:raise ValueError("original CGAMMA trace width differs")
        now,sec=int(values[0]),int(values[1])
        year=now//100000
        jul=(now//100)%1000
        hour=now%100
        if year!=2022 or jul<1 or jul>365 or hour>23 or sec!=0:
            raise ValueError(f"bad original CGAMMA timestamp {now}/{sec}")
        date=datetime.datetime(year,1,1,tzinfo=datetime.timezone.utc)+datetime.timedelta(
            days=jul-1,hours=hour,seconds=sec)
        observations.append([int(date.timestamp()),*map(float,values[2:])])
    if len(observations)!=143:
        raise ValueError(f"expected 143 original selected CGAMMA source calls, got {len(observations)}")
    first=int(datetime.datetime(2022,1,1,tzinfo=datetime.timezone.utc).timestamp())
    for index,row in enumerate(observations,1):
        if row[0]!=first+index*3600:
            raise ValueError(f"CGAMMA source call timeline gap at hour {index}")
        if any(not math.isfinite(v) for v in row[1:]):
            raise ValueError("nonfinite original CGAMMA lapse or forcing")
        if row[1]<=0:
            raise ValueError("CGAMMA ZUPT nonpositive")
    return observations
def main():
    p=argparse.ArgumentParser()
    for name in ("runtime","up","cpp","out"):
        p.add_argument("--"+name,required=True,type=Path)
    a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    rows=parse(a.runtime)
    forcing=a.out/"original_cgamma_real_forcing.csv"
    with forcing.open("w",newline="") as f:
        w=csv.writer(f,lineterminator="\n")
        w.writerow(["hour_index","end_epoch_s","zupt_m","ziconv_m","original_gamma"])
        for n,(epoch,zupt,ziconv,gamma) in enumerate(rows,1):
            w.writerow([n,epoch,f"{zupt:.12g}",f"{ziconv:.12g}",f"{gamma:.12g}"])
    modern=a.out/"modern_cgamma_real.csv"
    proc=subprocess.run([str(a.cpp),str(a.up),str(forcing),str(modern),"58424"],
                        capture_output=True,text=True)
    if proc.returncode:
        raise RuntimeError(f"C++ CGAMMA failed: {proc.returncode} {proc.stderr[-2000:]}")
    with modern.open(newline="") as f:
        candidate=list(csv.DictReader(f))
    if len(candidate)!=143:raise ValueError("C++ CGAMMA hour count drift")
    maxdiff=0.0;first_fail=[];branches={}
    for n,(obs,c) in enumerate(zip(rows,candidate),1):
        epoch,zupt,ziconv,gamma=obs
        if int(c["hour_index"])!=n or int(c["end_epoch_s"])!=epoch or\
           abs(float(c["zupt_m"])-zupt)>1.e-3 or\
           abs(float(c["ziconv_m"])-ziconv)>1.e-2:
            first_fail.append({"hour":n,"error":"CGAMMA forcing/time divergence"})
        val=float(c["candidate_gamma"])
        delta=abs(gamma-val)
        if not math.isfinite(delta):raise ValueError("nonfinite C++ gamma difference")
        maxdiff=max(maxdiff,delta)
        if delta>3.e-6 and len(first_fail)<25:
            first_fail.append({"hour":n,"gamma_original":gamma,
                               "gamma_cpp":val,"abs_error":delta})
        branch=int(c["branch"])
        branches[str(branch)]=branches.get(str(branch),0)+1
    result={"status":"PASS_ORIGINAL_CGAMMA_RUNTIME" if not first_fail else "FAIL",
            "original_cgamma_live_calls":143,
            "hour_windows":[1,6,143],
            "convective_branch_counts":{"0_no_convective_carry":branches.get("0",0),
                "1_current_hour_adiabatic":branches.get("1",0),
                "2_retain_last_convective":branches.get("2",0)},
            "max_abs_lapse_error_K_per_m":maxdiff,
            "acceptance_tolerance_K_per_m":3.e-6,
            "first_differences":first_fail[:25],
            "input_provenance":{"runtime_sha256":sha(a.runtime),"up_sha256":sha(a.up),
                                "original_forcing_sha256":sha(forcing)},
            "limits":"Original CALMET CGAMMA actual subroutine call outputs and source ZICONV, C++ independent profile-temperature and last-convective carry; no P6E mixing-height model or P6D gamma grid parity."}
    (a.out/"p6c-real-cgamma-parity.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
    if first_fail:raise SystemExit(1)
if __name__=="__main__":main()
