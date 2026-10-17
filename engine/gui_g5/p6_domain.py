"""P6G domain-fit planning without enabling unaccepted CALMET physics.

Broaden the UTM model domain to contain specified surface + upper stations,
then choose a COARSER cell spacing only when needed for the cell budget.
No input data is invented and no case is changed unless --apply is explicit.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
from dataclasses import dataclass
from pathlib import Path

import yaml

from engine.core.paths import case_dir
from engine.gui_g5.case_setup import write_case_grid
from engine.preprocess.grid.configure_grid_cmn import lon_lat_to_utm
from engine.run_met.common import lon_lat_to_utm_km

SPACINGS_KM = (0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0)


@dataclass(frozen=True)
class Station:
    id: str
    kind: str
    lon: float
    lat: float


def read_stations(path: Path) -> list[Station]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not payload:
        raise ValueError("Station manifest must contain a nonempty JSON array")
    result = []
    seen: set[tuple[str, str]] = set()
    for row in payload:
        if not isinstance(row, dict):
            raise ValueError("Station records must be JSON objects")
        kind = str(row.get("kind", "")).strip().lower()
        identity = str(row.get("id", "")).strip()
        if kind not in ("surface", "upper") or not identity:
            raise ValueError("Station kind must be surface/upper and id nonempty")
        if (kind, identity) in seen:
            raise ValueError(f"Duplicate station identity: {kind}/{identity}")
        seen.add((kind, identity))
        try:
            lon,lat=float(row["lon"]),float(row["lat"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid coordinates: {identity}") from exc
        if not (math.isfinite(lon) and math.isfinite(lat) and
                -180<=lon<=180 and -80<=lat<=84):
            raise ValueError(f"Station coordinates outside WGS84 UTM: {identity}")
        result.append(Station(identity,kind,lon,lat))
    return result


def _positive(value: object, field: str) -> float:
    try:
        number=float(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{field} is not numeric") from exc
    if not math.isfinite(number) or number<=0:
        raise ValueError(f"{field} must be finite and positive")
    return number


def fit_domain(config: dict, stations: list[Station], *,
               margin_km: float = 5.0, max_horizontal_cells: int = 10000,
               spacings_km: tuple[float,...] = SPACINGS_KM,
               fixed_spacing_km: float | None = None) -> dict:
    if not stations:
        raise ValueError("Explicit station positions are required to fit P6 grid")
    if not math.isfinite(margin_km) or margin_km < 0:
        raise ValueError("margin_km must be finite and nonnegative")
    if max_horizontal_cells<1 or max_horizontal_cells>4_000_000:
        raise ValueError("max_horizontal_cells outside 1..4000000")
    if fixed_spacing_km is not None:
        fixed_spacing_km = _positive(fixed_spacing_km, "fixed_spacing_km")
    grid=config["preprocess"]["grid"]
    center=grid["center"]
    lon=float(center["longitude"])
    lat=float(center["latitude"])
    zone, xc_m, yc_m = lon_lat_to_utm(lon,lat)
    northern=lat>=0
    central_meridian=(zone-1)*6-180+3
    xc,yc=xc_m/1000.0,yc_m/1000.0
    original_length=_positive(grid["domain"]["length_km"],"length_km")
    original_width=_positive(grid["domain"]["width_km"],"width_km")
    resolution=_positive(grid["resolution_km"],"resolution_km")
    nz=int(grid["nz"])
    if nz<1:
        raise ValueError("P6 NZ must be positive")
    max_dx=original_length/2.0
    max_dy=original_width/2.0
    observations=[]
    counts={"surface":0,"upper":0}
    for station in stations:
        delta=((station.lon-central_meridian+180)%360)-180
        if abs(delta)>6.0:
            raise ValueError(
                f"Station {station.id} is >6 degrees from case UTM meridian; "
                "review domain/projection instead of extrapolating large UTM grid")
        if northern != (station.lat>=0):
            raise ValueError("One UTM hemisphere cannot span station hemispheres")
        x,y=lon_lat_to_utm_km(station.lon,station.lat,zone,northern)
        max_dx=max(max_dx,abs(x-xc)+margin_km+0.002)
        max_dy=max(max_dy,abs(y-yc)+margin_km+0.002)
        counts[station.kind]+=1
        observations.append((station,x,y))
    # Existing centre stays fixed, preserving stack/receptor coordinates.
    # Grid origin is rounded to .001km; 2m of guard avoids rounding exclusion.
    length=2*max_dx
    width=2*max_dy
    if fixed_spacing_km is not None and fixed_spacing_km < resolution:
        raise ValueError("fixed_spacing_km cannot refine an existing grid")
    candidates=([fixed_spacing_km] if fixed_spacing_km is not None else
                sorted({float(s) for s in (*spacings_km,resolution)
                        if math.isfinite(float(s)) and float(s)>=resolution}))
    selected=None
    for dkm in candidates:
        nx=math.ceil(length/dkm)
        ny=math.ceil(width/dkm)
        if nx*ny<=max_horizontal_cells:
            selected=(dkm,nx,ny)
            break
    if selected is None:
        raise ValueError("Cannot fit domain inside cell budget at permitted spacings")
    spacing,nx,ny=selected
    # case_setup uses original requested km for xref; honour cell count by
    # making the physical width/length nx/ny*dgridkm.
    final_length=nx*spacing
    final_width=ny*spacing
    xref=round(xc-final_length/2.0,3)
    yref=round(yc-final_width/2.0,3)
    for station,x,y in observations:
        if not (xref<=x<=xref+final_length and yref<=y<=yref+final_width):
            raise ValueError(f"Planner grid excludes station {station.id}")
    previous_nx=math.ceil(original_length/resolution)
    previous_ny=math.ceil(original_width/resolution)
    new=copy.deepcopy(config)
    dst=new["preprocess"]["grid"]
    dst["domain"]["length_km"]=round(final_length,9)
    dst["domain"]["width_km"]=round(final_width,9)
    dst["resolution_km"]=spacing
    return {
        "case_center":{"lon":lon,"lat":lat,"utm_zone":zone,
                       "hemisphere":"N" if northern else "S"},
        "existing":{"length_km":original_length,"width_km":original_width,
                    "spacing_km":resolution,"nx":previous_nx,"ny":previous_ny,
                    "horizontal_cells":previous_nx*previous_ny},
        "recommended":{"length_km":final_length,"width_km":final_width,
                       "spacing_km":spacing,"nx":nx,"ny":ny,
                       "nz":nz,"horizontal_cells":nx*ny,
                       "3d_cells":nx*ny*nz,"xref_km":xref,"yref_km":yref},
        "station_counts":counts,
        "station_ids":[{"kind":s.kind,"id":s.id} for s,_,_ in observations],
        "margin_km":margin_km,
        "max_horizontal_cells":max_horizontal_cells,
        "requested_spacing_km":fixed_spacing_km,
        "station_geometry_verified":True,
        "native_p6d_physics_accepted":False,
        "proposed_config":new,
    }


def main(argv: list[str] | None = None) -> int:
    ap=argparse.ArgumentParser(description="P6G station-envelope grid fit; no physics execution")
    ap.add_argument("--case",required=True,help="Case directory name within project/cases")
    ap.add_argument("--stations",required=True,type=Path,
                    help="JSON station list: id, kind=surface/upper, lon, lat")
    ap.add_argument("--margin-km",type=float,default=5.0)
    ap.add_argument("--max-horizontal-cells",type=int,default=10000)
    ap.add_argument("--spacing-km",type=float,default=None,
                    help="Explicit fixed horizontal spacing (e.g. 10 for multi-site stress tests)")
    ap.add_argument("--apply",action="store_true",help="Explicitly update case.yaml/grid.cmn")
    args=ap.parse_args(argv)
    root=case_dir(args.case)
    manifest=root/"case.yaml"
    config=yaml.safe_load(manifest.read_text(encoding="utf-8"))
    plan=fit_domain(config,read_stations(args.stations),
                    margin_km=args.margin_km,
                    max_horizontal_cells=args.max_horizontal_cells,
                    fixed_spacing_km=args.spacing_km)
    if args.apply:
        if any((root/"run/met"/name).is_file() for name in ("met.dat","MET.DAT")):
            ap.error("Refusing to mutate existing P6 outputs; clone a new G5 case")
        from engine.gui_g5.pipeline import validate_case
        validate_case(plan["proposed_config"])
        write_case_grid(root,plan["proposed_config"])
        manifest.write_text(yaml.safe_dump(plan["proposed_config"],
                              allow_unicode=True,sort_keys=False),encoding="utf-8")
    # Do not put full scenario configuration in machine-readable summary.
    plan.pop("proposed_config")
    plan["applied"]=args.apply
    print(json.dumps(plan,indent=2,ensure_ascii=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
