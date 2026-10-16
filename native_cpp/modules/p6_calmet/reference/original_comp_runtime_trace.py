#!/usr/bin/env python3
"""P6C original CALMET COMP runtime AA/BB observation-state audit.

No edits to vendor source. --instrument copies original Fortran to a temporary
file and adds a write-only state trace immediately before the source's validated
COMP return. --compare checks emitted runtime state for all 143 source hours
against the independent C++ joint trace and 13 original UP.DAT timestamps.
Original CALMET output SHA equivalence is independently checked by workflow.
"""
from __future__ import annotations
import argparse,csv,datetime,hashlib,json,math,re
from pathlib import Path

ORIGINAL_SHA="430381b4fb87f15127e20b13cc3e99be8a0e0fccf1d5821110af7f980558d134"
ANCHOR="      go to 140"
ADD="""      if(iu.eq.1) write(6,*)'P6C_COMP_TRACE',
     & nowtze,nsecze,ntzaa(iu),ntzbb(iu),justa(iu),
     & jusdt(iu),jaasec(iu),jbbsec(iu)
"""
def sha(p:Path):return hashlib.sha256(p.read_bytes()).hexdigest()
def instrument(source:Path,out:Path):
    if sha(source)!=ORIGINAL_SHA:
        raise ValueError("vendor source SHA drift; trace insertion not permitted")
    lines=source.read_text().splitlines(keepends=True)
    if len(lines)<4412 or lines[4267].rstrip()!=ANCHOR or       "if(abs(iupsec).lt.nsecdt.and.iupsec.ne.0) then" not in lines[4150] or       "if(jdelta.gt.maxsep*3600) then" not in lines[4235] or       "justa(iu) = -1" not in lines[4365] or       "justa(iu) = +1" not in lines[4292] or\
       "data maxsep/14/" not in lines[3653]:
        raise ValueError("source COMP anchors do not match pinned v6.5.0")
    if "call rdsn(iforms,nssta,ispack,ios,0,ibuf," not in lines[3917] or\
       "ws,wd,iceil,icc,tempk,irh,pres,ipcode)" not in lines[3919] or\
       "call missfc(iyr,ijul,ihr)" not in lines[3985] or\
       "call cgamma(" not in lines[13680].lower() or\
       "gamup(iupt))" not in lines[13681].lower() or\
       "gamup(iu))" not in lines[13694].lower():
        raise ValueError("COMP RDSN/MISSFC/CGAMMA trace anchor mismatch")
    # Exact selected original flow. Append a write-only observation record
    # after each subroutine call, keeping every original statement unchanged.
    inserts={
      3920: """      if(nssta.eq.1) then
         write(6,*)'P6C_RDSN_TIME',ndathrb,nsecb,
     &          idathrb,isecb,idathre,isece
         write(6,*)'P6C_RDSN_RAW',ws(1),wd(1),iceil(1),
     &          icc(1),tempk(1),irh(1),pres(1),ipcode(1)
      endif
""",
      3986: """      if(nssta.eq.1) write(6,*)'P6C_RDSN_POST',
     & ws(1),wd(1),iceil(1),icc(1),
     & tempk(1),irh(1),pres(1),ipcode(1)
""",
      4267: ADD,
      13682: """              write(6,*)'P6C_GAMMA_TRACE',
     &          nowtze,nsece,zupt,ziconv(iiupt,jjupt),
     &          gamup(iupt)
""",
      13695: """                if(iu.eq.1) write(6,*)'P6C_GAMMA_TRACE',
     &          nowtze,nsece,zupt,ziconv(iiup(iu),jjup(iu)),
     &          gamup(iu)
"""
    }
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text("".join(line+inserts.get(i,"")
                           for i,line in enumerate(lines,1)))
    report={"status":"ORIGINAL_COMP_WRITE_ONLY_TRACE_INSTRUMENTED",
            "source_sha256":sha(source),"instrumented_sha256":sha(out),
            "original_comp_source_lines":[4118,4412],
            "traced_fields":["COMP nowtze,nsecze,ntzaa,ntzbb,justa,jusdt,jaasec,jbbsec",
                             "RDSN pre-MISSFC time and eight raw station values",
                             "post-MISSFC eight station values",
                             "CGAMMA original scalar zupt,ziconv,gamma"],
            "no_vendor_source_edits":True,
            "original_timestep_gate":"abs(iupsec)<nsecdt and iupsec != 0",
            "original_max_gap_gate":"jdelta>maxsep*3600"}
    (out.parent/"p6c-comp-trace-instrumentation.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
def parse_profiles(p:Path):
    source={}
    for line in p.read_text().splitlines():
        if not line.startswith("   6201"):continue
        x=line.split()
        if len(x)!=14:raise ValueError("unexpected UP.DAT header")
        y,mo,d,h,s=map(int,x[7:12])
        t=datetime.datetime(y,mo,d,h,0,s,tzinfo=datetime.timezone.utc)
        if int(t.timestamp()) in source:raise ValueError("duplicate upper sounding")
        j=int(t.strftime("%j"))
        source[int(t.timestamp())]=y*100000+j*100+h
    if len(source)!=13:raise ValueError("expected 13 original sounding headers")
    return source
def compare(runtime:Path,joint:Path,up:Path,out:Path):
    trace=[]
    for line in runtime.read_text(errors="replace").splitlines():
        if "P6C_COMP_TRACE" not in line:continue
        parts=line.split("P6C_COMP_TRACE",1)[1].split()
        if len(parts)!=8:raise ValueError("original COMP trace width")
        trace.append(tuple(map(int,parts)))
    observed={"P6C_RDSN_TIME":[],"P6C_RDSN_RAW":[],"P6C_RDSN_POST":[]}
    for line in runtime.read_text(errors="replace").splitlines():
        for label in observed:
            if label in line:
                fields=line.split(label,1)[1].replace("D","E").split()
                observed[label].append([float(token) for token in fields])
    if any(len(rows)!=143 for rows in observed.values()):
        raise ValueError("RDSN raw/time/after-MISSFC original state must cover 143 hours: "+
                         repr({k:len(v) for k,v in observed.items()}))
    with joint.open(newline="") as f:
        records=list(csv.DictReader(f))
    if len(trace)!=143 or len(records)!=1287:
        raise ValueError(f"not 143 COMP states and 143x9 C++ hourly observations: {len(trace)}, {len(records)}")
    profiles=parse_profiles(up)
    stamps=list(profiles.keys())
    bad=[];turnovers=0;jorder_changes=0;last_order=1
    rdsn_raw_maxdiff={k:0.0 for k in ('ws','wd','tempk','pres')}
    rdsn_post_changes=0
    first=datetime.datetime(2022,1,1,tzinfo=datetime.timezone.utc)
    for n,state in enumerate(trace):
        now,secs,ntaa,ntbb,justa,jdelta,seca,secb=state
        hour=n+1
        instant=first+datetime.timedelta(hours=hour)
        actual_now=instant.year*100000+int(instant.strftime("%j"))*100+instant.hour
        record=records[n*9]
        rtime=observed["P6C_RDSN_TIME"][n]
        raw=observed["P6C_RDSN_RAW"][n]
        post=observed["P6C_RDSN_POST"][n]
        if len(rtime)!=6 or len(raw)!=8 or len(post)!=8:
            raise ValueError("original RDSN trace field count")
        modelbegin=int((instant-datetime.timedelta(hours=1)).strftime("%Y%j%H"))
        originalend=int(instant.strftime("%Y%j%H"))
        source_times=(int(record["start_epoch_s"]),int(record["end_epoch_s"]))
        actual_tuple=(int(rtime[0]),int(rtime[1]),int(rtime[2]),
                      int(rtime[3]),int(rtime[4]),int(rtime[5]))
        if actual_tuple!=(modelbegin,0,modelbegin,0,originalend,0):
            bad.append({"hour":hour,"field":"RDSN current/source time",
                        "actual":actual_tuple,"expected":(modelbegin,0,modelbegin,0,originalend,0)})
        if source_times!=(int((instant-datetime.timedelta(hours=1)).timestamp()),
                          int(instant.timestamp())):
            bad.append({"hour":hour,"field":"RDSN cpp UTC epoch"})
        for ncol,key,col,tol in [(0,"ws","surf_ws",0.0002),
                                  (1,"wd","surf_wd",0.0002),
                                  (4,"tempk","surf_temp_k",0.0002),
                                  (6,"pres","surf_pres",0.0002)]:
            delta=abs(raw[ncol]-float(record[col]))
            rdsn_raw_maxdiff[key]=max(rdsn_raw_maxdiff[key],delta)
            if not math.isfinite(delta) or delta>tol:
                bad.append({"hour":hour,"field":"RDSN raw "+key,"delta":delta})
        for ncol,key in [(2,"surf_ceiling"),(3,"surf_cloud"),(5,"surf_rh"),
                         (7,"surf_precip_code")]:
            if int(raw[ncol])!=int(record[key]):
                bad.append({"hour":hour,"field":"RDSN raw "+key,
                            "original":raw[ncol],"cpp":record[key]})
        for key,expected in [("rdsn_record_index",hour),("rdsn_reads",hour),
                             ("rdsn_reused",0)]:
            if int(record[key])!=expected:
                bad.append({"hour":hour,"field":"RDSN buffer "+key})
        # Missing-data replacement is applied later by original MISSFC,
        # and MUST NOT silently contaminate the raw C++ observed masks.
        if any(abs(x-y)>0.0002 for x,y in zip(raw,post)):
            rdsn_post_changes+=1
        aa_idx=int(record["aa_index"])
        bb_idx=int(record["bb_index"])
        expected_prior=profiles[stamps[aa_idx-1]]
        expected_follow=profiles[stamps[bb_idx-1]]
        # In original COMP AA and BB are *physical* buffers. JORDER JUSTA
        # indicates newest slot, so the chronological AA/BB labels switch.
        physical_aa=expected_prior if justa==1 else expected_follow
        physical_bb=expected_follow if justa==1 else expected_prior
        required={"nowtze":(now,actual_now),"nsecze":(secs,0),
                  "original_ntzaa":(ntaa,physical_aa),
                  "original_ntzbb":(ntbb,physical_bb),
                  "JUSTA_JORDER":(justa,int(record["jorder"])),
                  "original_gap_s":(jdelta,int(record["gap_s"])),
                  "original_jaasec":(seca,0),"original_jbbsec":(secb,0)}
        for name,(actual,expected) in required.items():
            if actual!=expected:
                bad.append({"hour":hour,"field":name,
                            "original":actual,"cpp_expected":expected})
        if justa!=last_order:jorder_changes+=1
        last_order=justa
        turnovers=max(turnovers,int(record["turnovers"]))
    report={"status":"PASS_ORIGINAL_COMP_RUNTIME_AA_BB" if not bad else "FAIL",
            "compared_original_hours":143,
            "physical_aa_bb_timestamps_checked":286,
            "source_time_and_sec_checks":143*3,
            "original_justa_jorder_switches":jorder_changes,
            "cpp_candidate_buffer_turnovers":turnovers,
            "rdsn_original_raw_hours":143,"rdsn_original_fields_checked":143*8,
            "rdsn_original_record_interval_checks":143*6,
            "rdsn_max_absolute_raw_field_errors":rdsn_raw_maxdiff,
            "rdsn_hours_modified_by_following_missfc":rdsn_post_changes,
            "scopes":[{"hours":h,"states":h} for h in [1,6,143]],
            "input_sha256":{"original_comp_runtime_log":sha(runtime),
                            "cpp_joint_csv":sha(joint),"up_dat":sha(up)},
            "errors":bad[:40],
            "scope":"Original COMP AA/BB plus actual original RDSN pre-MISSFC 143h input arrays/time masks. The post-MISSFC changes are counted but not source-equivalent C++ yet. CGAMMA is handled by a separate scalar comparison, no P6D field parity."}
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    if bad:raise SystemExit(1)
def main():
    p=argparse.ArgumentParser()
    subs=p.add_subparsers(dest="cmd",required=True)
    i=subs.add_parser("instrument")
    i.add_argument("--vendor",required=True,type=Path)
    i.add_argument("--out",required=True,type=Path)
    c=subs.add_parser("compare")
    for name in ("runtime","joint","up","out"):
        c.add_argument("--"+name,required=True,type=Path)
    a=p.parse_args()
    if a.cmd=="instrument":instrument(a.vendor,a.out)
    else:compare(a.runtime,a.joint,a.up,a.out)
if __name__=="__main__":main()
