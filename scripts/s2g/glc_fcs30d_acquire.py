#!/usr/bin/env python3
"""Explicit online acquisition and credential-free offline verification for Issue #51."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import re
import tempfile
import numpy as np
import rasterio
from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[2]
GRID = 'project/cases/hefei5km_2022_reference_case_20261011/grid/grid.cmn'
DATA = 'data/landcover/glc_fcs30d/v1_2022/hefei'
ASSET = 'projects/sat-io/open-datasets/GLC-FCS30D/annual'
VERSION = '1.0.0'
CLASSES = {10,11,12,20,51,52,61,62,71,72,81,82,91,92,120,121,122,130,140,150,152,153,181,182,183,184,185,186,187,190,200,201,202,210,220}
FILL = {0,250}

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def geometry() -> dict:
    text = (ROOT / GRID).read_text()
    def value(key: str) -> str:
        matches = re.findall(r'!\s*'+key+r'\s*=\s*([^!]+)!',text)
        if len(matches) != 1:
            raise ValueError('missing/duplicate grid field: '+key)
        return matches[0].strip()
    expected = {'IMAP':'UTM','IUTMZN':'50','LSOHEM':'N','DATUM':'WGS-84','XREFKM':'510.885','YREFKM':'3531.269','DGRIDKM':'0.1','NX':'50','NY':'50'}
    if any(value(k) != v for k,v in expected.items()):
        raise ValueError('grid does not match reviewed frozen Hefei profile')
    x,y = float(value('XREFKM'))*1000,float(value('YREFKM'))*1000
    bounds = [x,y,x+int(value('NX'))*float(value('DGRIDKM'))*1000,y+int(value('NY'))*float(value('DGRIDKM'))*1000]
    buffered = [bounds[0]-60,bounds[1]-60,bounds[2]+60,bounds[3]+60]
    tr = Transformer.from_crs(32650,4326,always_xy=True)
    def ring(b):
        return [[b[0],b[1]],[b[2],b[1]],[b[2],b[3]],[b[0],b[3]],[b[0],b[1]]]
    def wgs(b):
        return [list(tr.transform(*p)) for p in ring(b)]
    return {'grid_path':GRID,'grid_sha256':sha(ROOT/GRID),'original_bounds_utm_m':bounds,'buffer_m':60,'buffered_bounds_utm_m':buffered,'original_corners_wgs84':wgs(bounds),'buffered_corners_wgs84':wgs(buffered)}

def inspect(path: Path, bounds: list[float]) -> dict:
    if not path.is_file() or not 0 < path.stat().st_size < 32*1024*1024:
        raise ValueError('missing/empty/oversize GeoTIFF')
    with rasterio.open(path) as ds:
        t = ds.transform
        if ds.driver != 'GTiff' or ds.count != 1 or ds.crs.to_epsg() != 32650:
            raise ValueError('expected single-band EPSG:32650 GeoTIFF')
        if not np.issubdtype(np.dtype(ds.dtypes[0]),np.integer):
            raise ValueError('classification must be integer')
        if not np.all(np.isfinite(tuple(t))) or not np.allclose([t.a,t.b,t.d,t.e],[30,0,0,-30],atol=1e-8,rtol=0):
            raise ValueError('expected north-up 30m affine')
        if not all(math.isfinite(v) for v in ds.bounds) or not (ds.bounds.left<=bounds[0] and ds.bounds.bottom<=bounds[1] and ds.bounds.right>=bounds[2] and ds.bounds.top>=bounds[3]):
            raise ValueError('raster does not cover requested domain')
        a = ds.read(1)
        if not set(map(int,np.unique(a))) <= CLASSES|FILL:
            raise ValueError('unknown GLC_FCS30D code')
        invalid = (ds.read_masks(1)==0)|np.isin(a,list(FILL))
        if invalid.all():
            raise ValueError('no classified pixels')
        vals,counts = np.unique(a[~invalid],return_counts=True)
        return {'crs':ds.crs.to_string(),'pixel_resolution':[t.a,-t.e],'transform':list(t)[:6],'bounds':list(ds.bounds),'width':ds.width,'height':ds.height,'dtype':ds.dtypes[0],'nodata':ds.nodata,'nodata_or_fill_count':int(invalid.sum()),'nodata_fraction':float(invalid.mean()),'classes_histogram':{str(int(v)):int(n) for v,n in zip(vals,counts)},'pixel_sha256':hashlib.sha256(a.tobytes()).hexdigest(),'sha256':sha(path),'size_bytes':path.stat().st_size}

def verify(directory: Path) -> dict:
    meta = json.loads((directory/'metadata.json').read_text())
    geo = geometry()
    for k,v in geo.items():
        if meta[k] != v:
            raise ValueError('grid geometry/provenance mismatch: '+k)
    result = inspect(directory/'hefei_2022_30m.tif',geo['buffered_bounds_utm_m'])
    for k,v in result.items():
        if meta[k] != v:
            raise ValueError('metadata mismatch: '+k)
    if (meta['asset_path'],meta['year'],meta['band'],meta['version'],meta['license']) != (ASSET,2022,'b23','v1-community-gee','CC-BY-4.0'):
        raise ValueError('source contract mismatch')
    if not meta['repeat_download']['pixels_equal'] or not meta['repeat_download']['transform_equal']:
        raise ValueError('repeat comparison failed')
    return result

def acquire(directory: Path) -> dict:
    import ee
    import requests
    if directory.exists():
        raise ValueError('output directory already exists; refuse overwrite')
    geo = geometry()
    ee.Initialize(project='cteas-earthengine')  # Authentication is an explicit user-only step.
    region = ee.Geometry.Rectangle(geo['buffered_bounds_utm_m'],proj='EPSG:32650',geodesic=False)
    collection = ee.ImageCollection(ASSET).filterBounds(region).sort('system:index',True)
    ids = collection.aggregate_array('system:id').getInfo()
    if not ids:
        raise ValueError('no intersecting tiles')
    image = collection.mosaic().select('b23')  # EE default reprojection is nearest neighbour.
    def download(path):
        try:
            url = image.getDownloadURL({'region':region,'crs':'EPSG:32650','scale':30,'format':'GEO_TIFF','filePerBand':False})
            with requests.get(url,stream=True,timeout=(30,180)) as response:
                if response.status_code != 200:
                    raise ValueError('download HTTP status '+str(response.status_code))
                total = 0
                with path.open('xb') as file:
                    for chunk in response.iter_content(65536):
                        total += len(chunk)
                        if total > 32*1024*1024:
                            raise ValueError('download exceeds 32MiB; explicit tiling required')
                        file.write(chunk)
        except Exception:
            # URLs and API error payloads can contain credentials. Never propagate them.
            raise RuntimeError('Earth Engine download failed; check project/network/request size; no URL logged') from None
    with tempfile.TemporaryDirectory(prefix='cteas-glc-') as temp:
        first,second = Path(temp)/'first.tif',Path(temp)/'second.tif'
        download(first)
        r1 = inspect(first,geo['buffered_bounds_utm_m'])
        download(second)
        r2 = inspect(second,geo['buffered_bounds_utm_m'])
        with rasterio.open(first) as a, rasterio.open(second) as b:
            same = np.array_equal(a.read(),b.read()) and np.array_equal(a.read_masks(),b.read_masks())
        if not same or any(r1[k]!=r2[k] for k in ('transform','classes_histogram','crs','width','height','nodata')):
            raise ValueError('repeat download scientific mismatch')
        meta = {**geo,**r1,'source':'GLC_FCS30D Earth Engine Community Catalog','doi':'10.5281/zenodo.8239305','version':'v1-community-gee','year':2022,'band':'b23','asset_path':ASSET,'image_ids':ids,'tile_count':len(ids),'mosaic_order':'system:index ascending; last valid pixel wins','resampling':'Earth Engine default nearest neighbour; no class remapping','license':'CC-BY-4.0','download_utc':datetime.now(timezone.utc).isoformat(),'script_version':VERSION,'script_sha256':sha(Path(__file__)),'source_catalog':'https://gee-community-catalog.org/projects/glc_fcs/','community_import_date':'2024-02-20','allowed_class_codes':sorted(CLASSES),'fill_codes':sorted(FILL),'repeat_download':{'pixels_equal':same,'transform_equal':r1['transform']==r2['transform'],'histogram_equal':r1['classes_histogram']==r2['classes_histogram'],'bytes_equal':r1['sha256']==r2['sha256'],'second_sha256':r2['sha256']},'dependencies':{p:importlib.metadata.version(p) for p in ('earthengine-api','rasterio','pyproj','numpy','requests')}}
        directory.mkdir(parents=True)
        (directory/'hefei_2022_30m.tif').write_bytes(first.read_bytes())
        (directory/'metadata.json').write_text(json.dumps(meta,indent=2)+'\n')
    return verify(directory)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['download','verify'])
    parser.add_argument('--directory',type=Path,default=ROOT/DATA)
    args = parser.parse_args()
    try:
        result = acquire(args.directory) if args.mode=='download' else verify(args.directory)
    except Exception as exc:
        # Fail closed without leaking signed URLs, tokens or local account details.
        parser.exit(1,'Acquisition/verification failed ('+type(exc).__name__+'); no sensitive error payload logged.\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':
    main()
