# Issue #160 — genuine Hefei 20 km 2022 GLC_FCS30D source

Status: **HEFEI_20KM_GLC_FCS30D_2022_SOURCE_VERIFIED** (source only).
C4 independent integer HITS/F6.3/Missing and real Hefei C5 format validation
are **NOT_RUN**. Keep Issue #160 open. Historical GLCC mapping, P2-B
EXACT_AREA_V1 and P3 physical parameter calculations are unchanged.

## Delivered source

`hefei_2022_30m_20km.tif` is a fresh Earth Engine download of annual **b23 (2022)**,
not an enlarged/reused 5 km crop. It is an 84,901-byte, single-band uint8
GeoTIFF, **672 × 672**, **30 × 30 m**, **EPSG:32650**.

- File SHA256: `ee5cefc27827d84f0aa42d0e014e211fcfef67f2bffc43185d17897d840d2e58`.
- Pixel SHA256 (row-major uint8): `34868baca641a69c2906d7a52c5626437febac46b717863c9ee4a7fa72fddd7b`.
- Mask SHA256 (row-major GDAL 0/255 mask): `7c2d3bb5d012f622a9c42541fde3990e34107a99210f2950ecfb1481842ef3cd`.
- Affine: `[30, 0, 503310, 0, -30, 3543840]`.
- Actual bounds (west, south, east, north), metres:
  `[503310, 3523680, 523470, 3543840]`.
- Frozen model bounds: `[503385, 3523769, 523385, 3543769]`;
  buffered request: `[503325, 3523709, 523445, 3543829]`.
- Model: 200 × 200 at 100 m; XREFKM `503.385`, YREFKM `3523.769`.
  Center: 117.141610855°E, 31.939774444°N; origin rounded once to 1 m.
  Center offset: +0.356043 m east / +0.073032 m north.

The pixel-aligned export covers every buffered edge. Earth Engine default
nearest-neighbor classification reprojection is used, with no bilinear/cubic
interpolation, class remapping, gap filling or land/ocean substitution.
NoData is 0; both raw fill codes 0/250 remain missing, as do masked pixels.
There are **451,584 valid pixels**, **0 masked pixels**, **0 raw 0 pixels**,
**0 raw 250 pixels**, **0 missing/fill pixels (0%)**. Thirteen of the 35 legal
classes occur. Valid 210 water-body pixels: **35,336**. Source categories are
not USGS target codes. No reservoir-specific ground-truth claim is made.

## Provenance, license and reproducibility

Asset collection: `projects/sat-io/open-datasets/GLC-FCS30D/annual`.
Original selected image ID:
`projects/sat-io/open-datasets/GLC-FCS30D/annual/GLC_FCS30D_20002022_E115N35_Annual`.
Ascending `system:index` mosaic, last valid pixel wins; only one tile
intersects this request. Source version is `v1-community-gee` (catalog GEE
update 2024-02-20), linked to [Zenodo v1](https://zenodo.org/records/8239305),
not the newer Zenodo v2. The [GEE catalog](https://gee-community-catalog.org/projects/glc_fcs/)
and upstream record both declare **CC BY 4.0**, checked 2026-10-20.
Full creator/publication attribution, license link and modifications are in
[ATTRIBUTION.md](ATTRIBUTION.md). No independent checksum comparison against
the complete upstream Zenodo archive was performed; this exact received crop
and its mirror lineage are SHA-pinned.

The initial unmodified acquisition and the enhanced audit acquisition each
made two separately generated online getDownloadURL/download requests.
All four downloads have the same file SHA above. The committed metadata
records the enhanced pair: identical bytes, pixels, masks, transform,
coverage, histogram, file size and hashes. Download URLs and credentials are
never recorded. Dependencies, UTC acquisition time and acquisition script
SHA are in `metadata.json`.
The acquisition script SHA records the exact script used in source commit
`03a7029b24b21dc152581a9dc7d6198b3f807aac`; later offline verifier fixes
do not rewrite acquisition provenance. Only inverse-PROJ WGS84 diagnostic
corners allow 1e-10 degree variation across PROJ versions (about 11 µm).
Authoritative UTM origin, bounds, resolution and affine remain exact; this
does not change sampling coordinates or any science comparison tolerance.

Run from repository root with Python >=3.11, earthengine-api, numpy,
rasterio, pyproj and requests installed. The operator must already have
legitimate local Earth Engine authorization and an enabled project:

```sh
python3 -m scripts.s2g.issue160_hefei20km_glc_acquire acquire \
  --project cteas-earthengine --directory /private/tmp/hefei20km-new-reproduction
python3 -m scripts.s2g.issue160_hefei20km_glc_acquire verify
python3 -m unittest scripts.s2g.tests.test_issue160_hefei20km_source -v
```

Use a fresh destination for acquire: existing directories are rejected.
Offline verification requires no Earth Engine credentials or network.
The 84.9 kB GeoTIFF follows existing ordinary Git binary handling for small
land-cover crops; no large file or new LFS rule is needed.

## All 35 source classes (including zero counts)

| GLC source code | Valid pixels |
|---|---:|
| 10 | 52,901 |
| 11 | 7,915 |
| 12 | 0 |
| 20 | 249,526 |
| 51 | 0 |
| 52 | 2,765 |
| 61 | 0 |
| 62 | 1,157 |
| 71 | 0 |
| 72 | 23 |
| 81 | 0 |
| 82 | 0 |
| 91 | 0 |
| 92 | 0 |
| 120 | 0 |
| 121 | 0 |
| 122 | 0 |
| 130 | 4,719 |
| 140 | 0 |
| 150 | 0 |
| 152 | 0 |
| 153 | 0 |
| 181 | 37 |
| 182 | 7,578 |
| 183 | 1,366 |
| 184 | 0 |
| 185 | 0 |
| 186 | 0 |
| 187 | 0 |
| 190 | 88,099 |
| 200 | 162 |
| 201 | 0 |
| 202 | 0 |
| 210 | 35,336 |
| 220 | 0 |

NoData/missing union: **0**. Histogram totals: **451,584**.

## Verification limits

Local real-source verifier and fail-closed tests cover exact provenance,
35-class histogram, hashes, coverage, mask/0/250 semantics, repeat evidence
and refusal of old 5 km data. Native C4 producer/oracle was not run locally:
this machine has no discoverable GDAL development installation (`gdal-config`
and Homebrew GDAL are absent). No full science PASS, Actions scientific Run,
scientific Artifact, numerical HITS difference or #160 completion is claimed.
The separate source-contract CI validates only this source and offline tests.
