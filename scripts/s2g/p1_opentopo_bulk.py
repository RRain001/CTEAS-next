"""Explicit OPT-IN alternate TRANSPORT for genuine OpenTopography SRTM GL1 30m.

The original globaldem REST API remains default. This uses OpenTopography's
published anonymous public S3 bulk COG tiles for THE SAME SRTM_GL1 product
when, and only when, API HTTP 406 occurs and the caller explicitly opted in.
No other dataset, resampling, or elevation fallback is permitted.
"""
from __future__ import annotations

import math
from pathlib import Path
import urllib.error
import urllib.request

S3_ROOT = "https://opentopography.s3.sdsc.edu/raster/SRTM_GL1/SRTM_GL1_srtm"
MAX_TILES = 9
MAX_TOTAL_BYTES = 300_000_000
ARCSEC = 1.0 / 3600.0

class OpenTopoBulkError(ValueError):
    pass


def tiles_for_bbox(box:dict[str,float])->list[str]:
    try:
        west,east,south,north = (float(box[k]) for k in ("west","east","south","north"))
    except (KeyError,TypeError,ValueError) as exc:
        raise OpenTopoBulkError("invalid SRTMGL1 bbox") from exc
    if (not all(math.isfinite(x) for x in (west,east,south,north))
            or not (-180<=west<east<=180) or not (-56<=south<north<=60)):
        raise OpenTopoBulkError("SRTMGL1 bulk bbox outside supported geographic range")
    # Positive-area degree intersections, so a boundary at exactly 115E
    # requires the tile to its right, not an unneeded 114E tile.
    x0,x1=math.floor(west),math.ceil(east)
    y0,y1=math.floor(south),math.ceil(north)
    if (x1-x0)*(y1-y0)>MAX_TILES:
        raise OpenTopoBulkError("bulk transport restricted to nine 1-degree tiles")
    result=[]
    for lat in range(y0,y1):
        for lon in range(x0,x1):
            result.append(f'{"N" if lat>=0 else "S"}{abs(lat):02d}'
                          f'{"E" if lon>=0 else "W"}{abs(lon):03d}.tif')
    if not result:
        raise OpenTopoBulkError("no SRTMGL1 tiles selected")
    return result


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        raise OpenTopoBulkError("public S3 bulk mirror redirect refused")


def _fetch_tile(name:str, destination:Path, *, cap:int) -> None:
    # Names are generated exclusively from validated integer bounds.
    if name != Path(name).name or not name.endswith(".tif"):
        raise OpenTopoBulkError("bulk tile name invalid")
    req=urllib.request.Request(S3_ROOT+"/"+name,
                               headers={"User-Agent":"CTEAS-next-SRTMGL1-bulk-case-only"})
    try:
        with urllib.request.build_opener(_NoRedirect()).open(req,timeout=120) as incoming:
            with destination.open("xb") as target:
                total=0
                for block in iter(lambda:incoming.read(1<<20),b""):
                    total+=len(block)
                    if total>cap:
                        raise OpenTopoBulkError("SRTMGL1 tile exceeds bounded source bytes")
                    target.write(block)
    except OpenTopoBulkError:
        raise
    except urllib.error.HTTPError as exc:
        raise OpenTopoBulkError(
            f"official public SRTMGL1 tile HTTP {exc.code}, body withheld") from None
    except (urllib.error.URLError,OSError,TimeoutError):
        raise OpenTopoBulkError("official public SRTMGL1 tile network/IO failure") from None
    if destination.stat().st_size<512:
        raise OpenTopoBulkError("SRTMGL1 bulk tile absent/truncated")


def fetch_and_crop(box:dict[str,float],outdir:Path,destination:Path,
                   *,max_pixels:int,max_bytes:int)->list[dict]:
    """Fresh scratch only; returns actual source SHA/shape, never vendor data."""
    # Import at runtime to avoid module cycles and reuse exactly #49's
    # reviewed no-resampling, identical-overlap and NoData logic.
    from scripts.s2g.p1_terrain_source import check_raster,_build_local_mosaic
    names=tiles_for_bbox(box)
    if outdir.exists() or outdir.is_symlink() or destination.exists():
        raise OpenTopoBulkError("bulk scratch/output already exists")
    if max_bytes<=0 or max_pixels<=0:
        raise OpenTopoBulkError("bulk resource limits invalid")
    scratch=outdir
    scratch.mkdir(parents=True,exist_ok=False)
    raw=[]
    remaining=min(max_bytes,MAX_TOTAL_BYTES)
    properties=[]
    for name in names:
        dest=scratch/name
        _fetch_tile(name,dest,cap=remaining)
        remaining-=dest.stat().st_size
        if remaining<0:
            raise OpenTopoBulkError("SRTMGL1 bulk total byte budget exhausted")
        meta=check_raster(dest)
        if (abs(meta["resolution_degrees"][0]-ARCSEC)>1e-9 or
            abs(meta["resolution_degrees"][1]-ARCSEC)>1e-9):
            raise OpenTopoBulkError("official bulk SRTMGL1 resolution not 1 arc-second")
        if meta["width"]>3602 or meta["height"]>3602:
            raise OpenTopoBulkError("unexpected SRTMGL1 tile dimensions")
        properties.append(meta)
        raw.append(dest)
    _build_local_mosaic(raw,box,destination,max_pixels=max_pixels)
    return properties
