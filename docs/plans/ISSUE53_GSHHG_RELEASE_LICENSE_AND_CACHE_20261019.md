# GSHHG v2.3.7 Full L1: retained project data asset and Shanghai real coastal P2-B proposal

## Source licensing and actual storage status

The [GMT original GSHHG repository](https://github.com/GenericMappingTools/gshhg-gmt/blob/master/README.md) and [v2.3.7 release](https://github.com/GenericMappingTools/gshhg-gmt/releases/tag/2.3.7) say GSHHG is LGPL-3.0-or-later, with the original archive containing license/copyright and notices. Retain those files unchanged within the original ZIP; do not strip terms or represent it as project-owned data. Authors Paul Wessel and Walter H. F. Smith; source date/version 2.3.7 (2017). See official [LICENSE.TXT](https://sources.debian.org/src/gmt-gshhg/2.3.7-5/LICENSE.TXT).

- Exact official archived file: `gshhg-shp-2.3.7.zip`.
- Official upstream URL: `https://github.com/GenericMappingTools/gshhg-gmt/releases/download/2.3.7/gshhg-shp-2.3.7.zip`.
- SHA256: `8dbbe7e071e77e9e75f2d639239099ebca8d5c16d6a07df8169729d49f15cf41`.
- Extracted Full L1 `GSHHS_f_L1.shp` SHA256: `121435427911ea80624802e0f352d777eaf6ba6966ca5f07e687650e95329fd9`.
- Only `GSHHS_shp/f/GSHHS_f_L1.{shp,shx,dbf,prj}` are **required** for P2-B binary inland/sea GLC210; WDBII river/border lines are not required. GSHHG Full is geometrically detailed, not independently 30m-position-accurate.
- The complete ~100+MB data ZIP **must not be committed to Git history**. Permanent project **GitHub Release asset** is the chosen repository-hosted storage, uploaded with the exact original bytes, preserving license and version. Proposed tag: `gshhg-data-v2.3.7`; asset `gshhg-shp-2.3.7.zip`. The release asset is a separate GitHub object, not a tracked Git file. **Do not claim published until the owner-manual Publish workflow succeeds.**

## Explicit owner-manual initial publication
After review/merge:
`Actions → Publish reusable official GSHHG 2.3.7 dataset to project Release (manual only) → Run workflow (main)`.

It downloads original ZIP, verifies official SHA256, validates Full L1 members and per-file original SHA, then creates or verifies the same-byte GitHub Release asset. If the asset exists and differs, it fails; never replaces the release with unverified data. It needs GitHub Actions `contents:write` and runs solely when manually dispatched.

Direct use thereafter (Mac/Linux, network only for first restore):
```sh
python3 -m scripts.s2g.gshhg_v237_cache fetch --source project-release --cache .cache/gshhg/2.3.7
python3 -m scripts.s2g.gshhg_v237_cache verify --cache .cache/gshhg/2.3.7
# Full L1 is at .cache/gshhg/2.3.7/GSHHS_f_L1/GSHHS_f_L1.shp
```
For initial work **before publication** choose `--source official`. Subsequent runs use cached verified bytes offline; `verify` NEVER accesses network. Permanent GitHub Release requires publication once, local cache persists until deliberately deleted. No automatic network access during physics runs, no auto-water fill for missing raster classes.

## Shanghai Dongtan coastal candidate (2022)
Site is a **preliminary experimental box**, not already geospatially accepted. Goal is simultaneously classify both inland USGS52 and marine USGS55 under the same native CALMET model grid.

- Approximate centre: **121.98°E, 31.52°N** in eastern Chongming/Dongtan, Shanghai, at the Yangtze Estuary. Not a statement that a coastline has been verified to cross the exact model box.
- Coordinate definition: **WGS84 / UTM 51N, EPSG:32651**; south-west corner **XREFKM=400.655, YREFKM=3485.184**, 100 m resolution, **NX=NY=50**, total 5km × 5km, 25 km². Geometry, coastline intersection, and 2022 shoreline offsets must be verified using true GSHHG Full L1 before declaring the site correctly positioned.
- GLC source: same community Earth Engine **`projects/sat-io/open-datasets/GLC-FCS30D/annual`**, year2022 **`b23`**, UTM51N 30m nearest-neighbour categorical, buffered 60m; source product/legend frozen to same original-v1 profile as Hefei, not silently upgraded to Zenodo v2.
- Download/verify uses explicit owner-authenticated Earth Engine account already used for Hefei. **There is no public GLC2022 Shanghai tif in this repository now**. The pipeline does not inject credentials into GitHub; full uncompressed Zenodo source E120–E125 is multi-GB and is not downloaded for CI. Do not substitute ESA WorldCover or another product as if it were GLC_FCS30D.
```sh
# On user's already-authenticated Earth Engine machine, from repo root:
python3 -m scripts.s2g.glc_fcs30d_shanghai_acquire download
python3 -m scripts.s2g.glc_fcs30d_shanghai_acquire verify
# Review /data/landcover/glc_fcs30d/v1_2022/shanghai_dongtan/metadata.json,
# commit the small real TIFF + metadata + attribution when genuine source verified.
```

## Coastal approval gate
Once genuine Shanghai TIFF and provenance are committed, run the manual Shanghai coastal science-source workflow. It requires exact TIFF SHA, correct EPSG:32651, full grid valid source coverage and no 0/250 intersecting the 5km grid, same 34 fixed mappings, real GSHHG v2.3.7 Full L1 area intersections, source GLC210 present, **both inland USGS52 area >0 AND marine USGS55 area >0** (otherwise fails). Report per-cell 35-class→38-class conservation and row ordering. It must NOT invent seaward water where GLC is NoData. If the 2022 product masks sea, record `BLOCKED_GLC_OFFSHORE_NODATA` instead of fabricating a PASS; then separately decide if a compatible external marine-water supplement may be introduced and which dataset/version/uncertainty governs it.

GSHHG coastline source is 2017-vintage versus 2022 imagery. Even a successful area split is only a **real-source coastal engineering gate**; full-vs-high spatial sensitivity, original P3 same-input parity (Issue #46) and downstream water category physics require separate results.

## Reproduction
`scripts/s2g/gshhg_v237_cache.py`, `scripts/s2g/glc_fcs30d_shanghai_acquire.py`; `.github/workflows/issue53-gshhg-publish-project-release.yml` (manual); `.github/workflows/issue46-p2b-shanghai-real-coastal-2022.yml` (manual); unit/contract checks (PR lightweight only). Closed historical Issue #53 must remain closed. New SCIENCE follow-up tracked via open Issue #46 or a distinct dedicated issue.
