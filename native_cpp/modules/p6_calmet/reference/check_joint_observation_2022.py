#!/usr/bin/env python3
"""P6C selected 2022 hourly GEO+SURF+UP joint-state crosscheck.

Independent original-format/source-backed comparison values:
  * original Fortran GEO selected input fields (not full READGE routine);
  * original Fortran SURF selected input records (not full RDSN routine);
  * literal original VERTAV->PREPDI wind-source expression;
  * literal original FACET+INTP source routines for temperature faces.
AA/BB slot turnover is an explicitly separate candidate-only invariant:
this is NOT an instrumented original COMP or CGAMMA comparison.
"""
from __future__ import annotations
import argparse,bisect,csv,datetime,hashlib,json,math
from pathlib import Path

def csvrows(p:Path):
    with p.open(newline="") as f:return list(csv.DictReader(f))
def source_rows(p:Path):
    return [row.split() for row in p.read_text().splitlines() if row.strip()]
def sha(p:Path):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser()
    for opt in ("joint","original-geo","original-surf","original-prepdi",
                "original-facet","up","out"):
        ap.add_argument("--"+opt,required=True,type=Path)
    a=ap.parse_args()
    result=csvrows(a.joint)
    geo=source_rows(a.original_geo)
    surf=source_rows(a.original_surf)
    prep=source_rows(a.original_prepdi)
    face=source_rows(a.original_facet)
    if [len(result),len(geo),len(surf),len(prep),len(face)] != [1287,2500,143,1287,130]:
        raise ValueError("joint/Fortran GEO/SURF/PREPDI/FACET record count drift")
    first_center=geo[24*50+24]
    if (int(first_center[0]),int(first_center[1]))!=(25,25):
        raise ValueError("original GEO center index not 25,25")
    ftemp={(int(t[0]),int(t[1])):float(t[2]) for t in face}
    stamps=[]
    for line in a.up.read_text().splitlines():
        if not line.startswith("   6201"):continue
        x=line.split()
        if len(x)!=14 or x[0]!="6201":raise ValueError("UP sounding header invalid")
        y,mo,day,h,sec=map(int,x[7:12])
        stamps.append(int(datetime.datetime(y,mo,day,h,0,sec,
                           tzinfo=datetime.timezone.utc).timestamp()))
    if len(stamps)!=13 or stamps!=sorted(set(stamps)):
        raise ValueError("expected 13 source profiles")
    start=int(datetime.datetime(2022,1,1,tzinfo=datetime.timezone.utc).timestamp())
    maxerr={"u":0.,"v":0.,"temperature_faces_k":0.,"surface_ws":0.,
            "surface_wd":0.,"surface_temperature_k":0.,"terrain_m":0.,"roughness_m":0.}
    bad=[];rain_missing=0;turnovers=0;jorder_changes=0;previous_order=1
    windows=[]
    for total in (1,6,143):
        windows.append({"hours":total,"layers":total*9,"wind_components":total*18})
    for h in range(143):
        hour=h+1;rows=result[h*9:(h+1)*9]
        t=start+hour*3600
        next_idx=bisect.bisect_right(stamps,t)
        if not 1<=next_idx<13:raise ValueError("original timestamp not bracketed")
        aa,bb=next_idx,next_idx+1  # 1-based sounding positions
        if h==0:prior_index=aa
        if aa!=prior_index:
            if aa!=prior_index+1:raise ValueError("unexpected original profile index leap")
            turnovers+=1
            prior_index=aa
        slot_a=turnovers%2
        slot_b=1-slot_a
        order=1 if slot_a==0 else -1
        if order!=previous_order:jorder_changes+=1
        previous_order=order
        sf=surf[h]
        if len(sf)!=17:raise ValueError("Fortran surface record width drift")
        start_sf=datetime.datetime(int(sf[1]),1,1,tzinfo=datetime.timezone.utc)+datetime.timedelta(
            days=int(sf[2])-1,hours=int(sf[3]),seconds=int(sf[4]))
        end_sf=datetime.datetime(int(sf[5]),1,1,tzinfo=datetime.timezone.utc)+datetime.timedelta(
            days=int(sf[6])-1,hours=int(sf[7]),seconds=int(sf[8]))
        if int(start_sf.timestamp())!=t-3600 or int(end_sf.timestamp())!=t:
            raise ValueError("original SURF timestamp discontinuity")
        first=rows[0]
        if int(first["precip_valid"])==0:rain_missing+=1
        if int(first["precip_valid"])!=0 or int(first["surf_precip_code"])!=9999:
            raise ValueError("rainfall unexpectedly present: keep wet-forcing gate independent")
        for rawname,outname,tolerance in [
            ("ws","surf_ws",0.0002),("wd","surf_wd",0.0002),
            ("tempk","surf_temp_k",0.0002)]:
            pos={"ws":9,"wd":10,"tempk":13}[rawname]
            diff=abs(float(sf[pos])-float(first[outname]))
            key={"ws":"surface_ws","wd":"surface_wd","tempk":"surface_temperature_k"}[rawname]
            maxerr[key]=max(maxerr[key],diff)
            if diff>tolerance:bad.append({"hour":hour,"field":key,"difference":diff})
        if int(sf[0])!=int(first["surf_station_id"]) or           int(sf[12])!=int(first["surf_cloud"]) or           int(first["wind_valid"])!=1 or int(first["cloud_valid"])!=1:
            bad.append({"hour":hour,"field":"SURF station/cloud/mask"})
        for col,key,refval in (
            ("geo_center_terrain_m","terrain_m",3),
            ("geo_center_z0_m","roughness_m",4)):
            diff=abs(float(first[col])-float(first_center[refval]))
            maxerr[key]=max(maxerr[key],diff)
            if diff>0.00001:bad.append({"hour":hour,"field":key,"difference":diff})
        for k,row in enumerate(rows,1):
            p=prep[h*9+k-1]
            if len(p)!=4 or int(p[0])!=hour or int(p[1])!=k:
                raise ValueError("original PREPDI index drift")
            required={"hour_index":hour,"layer":k,"start_epoch_s":t-3600,
                      "end_epoch_s":t,"aa_index":aa,"bb_index":bb,
                      "aa_slot":slot_a,"bb_slot":slot_b,"jorder":order,
                      "turnovers":turnovers,"total_reads":2+turnovers,
                      "gap_s":stamps[next_idx]-stamps[next_idx-1],
                      "elapsed_s":t-stamps[next_idx-1],
                      "to_go_s":stamps[next_idx]-t}
            for key,value in required.items():
                if int(row[key])!=value:
                    bad.append({"hour":hour,"layer":k,"field":key,
                                "expected":value,"observed":row[key]})
            for key,pos,name in (("upper_u",2,"u"),("upper_v",3,"v")):
                diff=abs(float(row[key])-float(p[pos]))
                maxerr[name]=max(maxerr[name],diff)
                if not math.isfinite(diff) or diff>0.0003:
                    bad.append({"hour":hour,"layer":k,"field":name,"difference":diff})
            for col,profile,face_index in (
                ("aa_temp_face_low_k",aa,k),("aa_temp_face_high_k",aa,k+1),
                ("bb_temp_face_low_k",bb,k),("bb_temp_face_high_k",bb,k+1)):
                diff=abs(float(row[col])-ftemp[(profile,face_index)])
                maxerr["temperature_faces_k"]=max(maxerr["temperature_faces_k"],diff)
                if not math.isfinite(diff) or diff>0.0003:
                    bad.append({"hour":hour,"layer":k,"field":col,"difference":diff})
    out={"status":"PASS_SELECTED_CROSSCHECK" if not bad else "FAIL",
         "real_input_hours":143,"wind_components":2574,
         "linked_temperature_face_samples":143*9*4,
         "surface_hours":143,"geo_center_original_fortran_hours":143,
         "candidate_aa_bb_turnovers":turnovers,"candidate_jorder_changes":jorder_changes,
         "precipitation_missing_hours":rain_missing,
         "scopes":windows,"max_absolute_errors":maxerr,
         "first_mismatches":bad[:25],
         "inputs_sha256":{name:sha(getattr(a,name.replace("-","_"))) for name in
            ("joint","original-geo","original-surf","original-prepdi","original-facet","up")},
         "qualification":"Selected real-input integration and source-backed values, candidate AA/BB order only. Full original COMP buffer/CGAMMA station observation state still NOT VERIFIED; P6C remains PARTIAL."}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps(out,indent=2))
    if bad:raise SystemExit(1)

if __name__=="__main__":main()
