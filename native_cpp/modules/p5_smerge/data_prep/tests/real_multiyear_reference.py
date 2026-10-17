"""Independent end-to-end REAL NOAA 2-station x 2-year P5 reference fixture.

58321099999 (Hefei) / 58314099999 (Huoshan) are separate real sites;
NEVER present them as physically co-located inside a 5km research grid.
This test verifies real heterogeneous input, yearly roles, long sparse
time axes, a calendar-year boundary, and C++/original-Fortran output parity.

Run:
  python -m ...real_multiyear_reference prepare
  python -m ...real_multiyear_reference audit
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path

import pandas as pd

from engine.core.paths import current_project_path, engine_path
from native_cpp.modules.p5_smerge.data_prep.download_isd_by_grid import (
    parse_history_txt, download_one, original_coverage, expected_hours_in_year
)
from native_cpp.modules.p5_smerge.data_prep.isd_lite_wind import (
    download_lite_one, filename as lite_filename, lite_time_coverage,
    parse_lite_winds, sha256_file
)
from native_cpp.modules.p5_smerge.data_prep.station_identity import numeric_station_ids

SIDS = ("58321099999", "58314099999")
YEARS = (2022, 2023)
BEGIN = datetime(2022, 1, 1, 0)
END = datetime(2023, 12, 31, 23)
EVIDENCE = Path("real-multiyear-evidence")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")


def ingest():
    root = current_project_path()
    raw = root / "met/surface/isd_raw"
    lite_dir = raw / "isd_lite"
    raw.mkdir(parents=True, exist_ok=True)
    grid = root / "grid"
    grid.mkdir(parents=True, exist_ok=True)
    (grid / "center_location").write_text("latitude: 31.939774444\nlongitude: 117.141610855\n")
    (grid / "grid.cmn").write_text("! DGRIDKM = 0.1 !\n! NX = 50 !\n! NY = 50 !\n")
    (grid / "research_time").write_text(
        "BEGIN: 20220101-000000\nEND: 20231231-230000\n")
    run = root / "run/smerge"
    run.mkdir(parents=True, exist_ok=True)
    (run / "smerge.inp").write_text(engine_path("templates", "smerge.inp").read_text())
    stations = {s.sid: s for s in parse_history_txt(
        engine_path("resources", "isd", "isd-history.txt")) if s.sid in SIDS}
    if set(stations) != set(SIDS):
        raise RuntimeError(f"station IDs missing in authoritative NOAA history: {set(SIDS)-set(stations)}")
    aliases = numeric_station_ids(list(SIDS))
    annual = []
    inputs = []
    for year in YEARS:
        times = expected_hours_in_year(year)
        candidates = []
        for sid in SIDS:
            success, msg, cache = download_one(year, sid, raw, 70)
            if not success:
                raise RuntimeError(f"full NOAA ISD download failed {sid} {year}: {msg}")
            success, msg, cache = download_lite_one(year, sid, lite_dir, 70)
            if not success:
                raise RuntimeError(f"NOAA ISD-Lite download failed {sid} {year}: {msg}")
            full_path = raw / f"{sid}-{year}.csv"
            lite_path = lite_dir / lite_filename(sid, year)
            full_count, full_expected = original_coverage(full_path, year, sid)
            lite_count, lite_expected = lite_time_coverage(lite_path, year, sid)
            if (full_expected, lite_expected) != (times, times):
                raise RuntimeError(f"annual denominator wrong {year}/{sid}")
            if min(full_count, lite_count) < 1:
                raise RuntimeError(f"missing NOAA raw observations {year}/{sid}")
            candidates.append((sid, lite_count, full_count))
            inputs.append({
                "station": sid, "year": year, "denominator": times,
                "original_full_isd_hours": full_count,
                "original_lite_hours": lite_count,
                "full_isd_coverage": full_count/times,
                "lite_coverage": lite_count/times,
                "full_sha256": sha(full_path),
                "lite_sha256": sha256_file(lite_path),
            })
        # EXACT production ranking: Lite original hours, full ISD original
        # hours, ascending ID. Do not use filled or union hours to rank.
        primary = sorted(candidates,key=lambda x:(-x[1],-x[2],x[0]))[0][0]
        selected = []
        for sid, lc, fc in candidates:
            st = stations[sid]
            selected.append({
                "sid": sid, "name": st.name, "country": st.country,
                "begin": st.begin, "end": st.end,
                "lat": st.lat, "lon": st.lon, "elev": st.elev,
                "source_lat": st.lat, "source_lon": st.lon,
                "source_elev": st.elev, "relocated": False,
                "ifstn": aliases[sid],
                "isd_lite_raw_hours": lc,
                "full_isd_raw_hours": fc,
                "expected_hours": times,
                "isd_lite_coverage": lc / times,
                "full_isd_coverage": fc / times,
                "wind_treatment": ("COMPLETE_FILL_AND_CALM_REPLACE"
                                   if sid == primary else "RAW_SPARSE_STANDARDIZE_ONLY"),
                "wind_data_source": "NOAA_ISD_LITE",
            })
        manifest = {
            "year": year,
            "mode": "OBSERVED",
            "station_selection_case": "IN_DOMAIN_MULTIPLE",
            "primary_sid": primary, "stations": selected,
            "validation_only_cross_region": True,
            "scientific_scope": ("actual NOAA meteorological sources at true original "
                                 "locations; FOR SOFTWARE / SMERGE PARITY ONLY; "
                                 "NOT a physically co-located 5km CALMET experiment"),
            "alias_scope": "ALL_SELECTED_STATION_IDENTITIES_ACROSS_RESEARCH_YEARS",
        }
        record(raw / f"station_selection_{year}.json", manifest)
        annual.append({
            "year": year, "primary_sid": primary,
            "coverage_ranking": candidates,
            "station_roles": {x["sid"]: x["wind_treatment"] for x in selected},
        })
        print("P5_REAL_ANNUAL_SELECTION", json.dumps(annual[-1]),flush=True)
    result = {
        "status": "REAL_ORIGINAL_SOURCES_PREPARED",
        "annual": annual,
        "input_sources": inputs,
        "cross_region_software_only": True,
        "research_begin": BEGIN.isoformat(),
        "research_end": END.isoformat(),
    }
    record(EVIDENCE / "real-original-inputs.json", result)
    assert len(inputs) == len(SIDS)*len(YEARS)
    assert len({aliases[s] for s in SIDS})==len(SIDS)
    print("P5_REAL_MULTIYEAR_4_NOAA_PAIRS=PASS",len(inputs),flush=True)


def _generic(path: Path) -> tuple[list[str],pd.DataFrame]:
    with path.open(encoding="utf-8") as f:
        head=[next(f).strip() for _ in range(3)]
    cols=head[2].split(",")
    df=pd.read_csv(path,skiprows=3,header=None,names=cols)
    times=pd.to_datetime(dict(year=df.Year.astype(int),month=df.Month.astype(int),
                  day=df.Day.astype(int),hour=(df.Hour.astype(int)//100)))
    df.index=pd.DatetimeIndex(times)
    if df.index.has_duplicates:
        raise RuntimeError(f"duplicate generic hours: {path}")
    return head,df


def verify_prepared():
    root=current_project_path()
    raw=root/"met/surface/isd_raw"
    prepared=root/"met/surface/isd2smerge_and_fill"
    ready=root/"met/surface/isd2smerge_ready"
    info=[]
    for year in YEARS:
        m=json.loads((raw/f"station_selection_{year}.json").read_text())
        roles={x["sid"]:x["wind_treatment"] for x in m["stations"]}
        chosen=sorted(m["stations"],key=lambda r:(
            -r["isd_lite_raw_hours"],-r["full_isd_raw_hours"],r["sid"]))[0]["sid"]
        assert chosen==m["primary_sid"]
        assert sum(v=="COMPLETE_FILL_AND_CALM_REPLACE" for v in roles.values())==1
        for sid in SIDS:
            stem=f"{sid[:6]}-{sid[6:]}-{year}"
            _,df=_generic(prepared/f"{stem}_filled.csv")
            wind=parse_lite_winds(raw/"isd_lite"/lite_filename(sid,year),year,sid)
            original_isd_csv=raw/f"{sid}-{year}.csv"
            source_hours=set()
            with original_isd_csv.open(newline="",encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    try:
                        time=datetime.fromisoformat(row["DATE"])
                    except (KeyError, ValueError):
                        continue
                    hour=time.replace(minute=0,second=0,microsecond=0)
                    if time.minute<=10:
                        source_hours.add(hour)
                    elif time.minute>=50:
                        source_hours.add(hour+timedelta(hours=1))
            union=set(source_hours)|set(wind)
            # production helper allows occasional rounded year spillovers;
            # verify EXACT formal data-prep union set where dates are in year.
            if roles[sid]=="RAW_SPARSE_STANDARDIZE_ONLY":
                assert set(df.index.to_pydatetime())==union,(year,sid,len(df),len(union))
                assert len(df)<expected_hours_in_year(year),(year,sid,len(df))
                assert not ((df["deg"]==9999) ^ (df["ms-1"]==9999)).any()
                assert not (((df["deg"]==0) & (df["ms-1"]>0))).any()
                assert not ((df["ms-1"]==0) & (df["deg"]!=0)).any()
            else:
                assert len(df)==expected_hours_in_year(year),(year,sid,len(df))
                assert (df["deg"].between(0.01,360) & df["ms-1"].gt(0)).all()
                assert (prepared/f"{stem}_cleaned.csv").exists()
                assert (prepared/f"{stem}_calm_interpolated.csv").exists()
            info.append({
                "year":year,"sid":sid,"role":roles[sid],
                "original_union_source_hours":len(union),"prepared_rows":len(df),
                "source_absent_hours":expected_hours_in_year(year)-len(union),
                "yearly_full":expected_hours_in_year(year),
            })
    _,station_a=_generic(ready/"583210-99999.csv")
    _,station_b=_generic(ready/"583140-99999.csv")
    assert len(station_a)==17520,len(station_a)
    assert len(station_b)<17520,len(station_b)
    assert station_a.index.min()==BEGIN and station_a.index.max()==END
    assert pd.Timestamp("2022-12-31 23:00") in station_a.index
    assert pd.Timestamp("2023-01-01 00:00") in station_a.index
    out={"status":"REAL_TWO_YEAR_PREPARED=PASS","annual_station_audits":info,
         "primary_hours_in_combined_2022_2023":len(station_a),
         "auxiliary_hours_in_combined_2022_2023":len(station_b),
         "year_seam_2022_12_31_23_to_2023_01_01_00":True,
         "all_source_coordinates_authentic":True,"same_5km_domain":False}
    record(EVIDENCE/"prepared-audit.json",out)
    print("P5_REAL_TWO_YEAR_PRIMARY_AND_SPARSE_AUX=PASS",json.dumps(out),flush=True)


def parity():
    case=current_project_path()
    work=case/"run/smerge"
    reference=work/"surf.dat"
    native=work/"native_real_2022_2023.dat"
    a=reference.read_bytes()
    b=native.read_bytes()
    al=a.splitlines()
    bl=b.splitlines()
    # Two whole non-leap years; SMERGE's IB 00 -> first completed hour 01.
    expected_hours=int((END-BEGIN).total_seconds()/3600)
    expected_lines=6+len(SIDS)+expected_hours*(1+len(SIDS))
    assert expected_hours==17519
    assert len(al)==expected_lines,(len(al),expected_lines)
    unequal=[(i+1,x.decode(errors="replace"),y.decode(errors="replace"))
             for i,(x,y) in enumerate(zip(al,bl)) if x!=y]
    outcome={
        "status":"P5_REAL_MULTIYEAR_BYTE_PARITY_PASS" if a==b else "FAIL",
        "real_station_ids":SIDS,"calendar_years":YEARS,
        "original_bytes":len(a),"native_bytes":len(b),
        "original_lines":len(al),"native_lines":len(bl),
        "expected_hours":expected_hours,
        "expected_output_lines":expected_lines,
        "byte_identical":a==b,
        "original_sha256":sha(reference),"native_sha256":sha(native),
        "first_differences":unequal[:25],
        "cross_region_software_only":True,
    }
    record(EVIDENCE/"real-two-year-byte-parity.json",outcome)
    print("P5_REAL_MULTIYEAR_BYTE_PARITY_RESULT",json.dumps(outcome),flush=True)
    if a!=b:
        raise RuntimeError("real two-year multi-station SURF.DAT byte parity failed")
    print("P5_REAL_2STATION_2YEAR_SURFDAT_BYTE_PARITY=PASS",flush=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("phase",choices=("prepare","audit","parity"))
    args=parser.parse_args()
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    {"prepare":ingest,"audit":verify_prepared,"parity":parity}[args.phase]()


if __name__=="__main__":
    main()
