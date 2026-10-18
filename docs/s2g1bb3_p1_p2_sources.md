# S2-G1B-B3: Eurasia GLCC P2 source and P1 SRTM on-demand acquisition

## Source of truth: user's new root-level LFS asset

- **`eausgs2_0la.img`** is a Git LFS object, not a normal text file. SHA-256 **`4f2a1977d141e2040da4d36ec6a4826c5c960c84686eaf10f226f388cb3ab90a`**, size **156,000,000** bytes, **13,000×12,000** unsigned 8-bit, raw/headerless Eurasia GLCC 2.0 Lambert equal-area grid.
- Use `git lfs pull --include="eausgs2_0la.img"` and independently verify full binary SHA. A 134-byte Git pointer is invalid imagery; the new P2 source converter refuses it. For extra-Europe cases, **no automatic replacement/water fill**: wait for an explicitly provided new regional image and scientifically verify its projection, coding and digest.
- Original source science and detailed projection legend: [`eausgs2_0la.md`](../eausgs2_0la.md), and [`docs/terrain_landuse_crop.md`](terrain_landuse_crop.md).
- The older [`scripts/crop_terrain_landuse_data.py`](../scripts/crop_terrain_landuse_data.py) handles both terrain and GLCC. New **`scripts/s2g/real_glcc_landuse_from_grid.py`** isolates just GLCC from an independent case `grid.cmn` (WGS84 UTM), retaining the old Lambert inverse transform, 24→USGS-92 38 class translation and exact `GENERIC.LANDUSE 1.0` point science. It does not build P2 LU.DAT or P3 GEO.DAT.
- GLCC source class **0** is unclassified background/missing, *not* water. **16** is source water and becomes CTGPROC output class **52**. Never average raw category integer codes or infer improved resolution from mesh sampling.
- GLCC reflects **1992–1993** landcover. Fine grid mesh (e.g. 50 m) is only a point-sampling strategy for 1 km GLCC source. No claim of 2022 physical landcover.

### Automated P2 input-crop command

```bash
git lfs pull --include="eausgs2_0la.img"
python3 -m pip install "numpy>=1.23,<3" "rasterio>=1.3,<2"

python3 -m scripts.s2g.real_glcc_landuse_from_grid \
  --grid /scratch/new_site/grid/grid.cmn \
  --landuse-file eausgs2_0la.img \
  --out-dir /scratch/new_site/geo/ctgproc/glcc_source \
  --mesh-cells 20 \
  --buffer-km 1.5 \
  --max-points 3000000 \
  --preview-tif
```

Output: **`glcc.generic.txt`** in the selected *new* directory, `glcc_source_manifest.json` with raw full-file SHA, projection window, source-class distribution, output SHA and historical-period flag; optional `glcc_source_preview_laea.tif`. Avoid overwriting any existing case file. A source file with wrong size/digest, improper three-decimal-kilometer UTM origin, unsupported region, unknown original category, all-unclassified pixels, insufficient margin or output resource budget is rejected.

Use exactly **`--lulc-type GEN`** and ensure **`DNZGEN=ESR-S`** in original `ctgproc.inp`; existing **`auto_select_landuse_to_ctgproc.py`** synchronizes this header/datum from the GENERIC input. This is for an original-format comparison and not an original Fortran fallback in the planned native P1–P7 flow. The current **native P2 CLI** (`native_cpp/src/p2_gen_fraction_cli.cpp`) still hardcodes **Hefei 50×50@100m, UTM50N, frozen origin**; a new-grid native P2 fraction builder and P3 GEO must be generalized and independently tested before marking G1B-B3 accepted. Input source extraction is a distinct admission step.

The regular PR CI tests **synthetic** original-compatible 156 MB sparse raster layouts with known class bytes, not the actual LFS binary. Genuine source execution with 156 MB LFS pull is a separate manual/authorized scientific verification step; do not misreport passing synthetic source tests as a real landuse scientific result.

## P1 SRTM: location-bounded, current official retrieval options

**Recommended for automated per-case downloads:** [OpenTopography Global DEM API](https://opentopography.org/developers) / [API schema](https://portal.opentopography.org/apidocs/).

Source example with only the case WGS84 buffered bbox (south/north/west/east derived from `grid.cmn`, do not guess station-radius). **SRTMGL1 ≈ 30m** original SRTM (1 arcsecond); API key required and **must only come from local env/secrets**, never a repository file, URL in logs, CI output, or PR comment. The API may enforce area limits (~450,000 km² for 30m) and rate limits; multi-tile cases require bounded split/stitch with CRS, nodata and SHA checks.

```bash
# Environment: your own private API key, NOT a committed string.
export OPENTOPOGRAPHY_API_KEY=...  # set privately, not in a shared shell log
# Official GET /API/globaldem:
# https://portal.opentopography.org/API/globaldem?demtype=SRTMGL1&south=31.8&north=32.1&west=117.0&east=117.3&outputFormat=GTiff&API_Key=<PRIVATE_KEY>
```

NASA alternative: official [SRTMGL1 V003](https://data.nasa.gov/dataset/nasa-shuttle-radar-topography-mission-global-1-arc-second-v003-e47e1) through [Earthdata Search](https://search.earthdata.nasa.gov/) + authenticated granule download and [CMR bounding_box search](https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html). SRTM 1 arcsecond extends approximately 60°N to 56°S; Eurasia GLCC coverage extends beyond that in northern latitudes: **no silent replacement** with COP30/other DEM or fabricated elevations. If outside SRTM coverage, choose a separately accepted alternative DEM with declared accuracy/vertical datum/format and independent tests.

The same API also offers **SRTMGL3 (~90 m)** with a broader single-request area quota (up to ~4,050,000 km² vs 450,000 km² for 30 m), but **SRTM GL3/NASA V003 is NOT byte-identical to the historical CGIAR-CSI SRTM v4.x 3-arcsecond original archive**; distinguish source versions and void-filling treatment even when resolution matches. Choose a single pinned provider/version per research case and record the specific raster SHA and sampled original area; no source swapping within scientific regression. [OpenTopography SRTM GL3 details](https://portal.opentopography.org/raster?jobId=rt1790016242276).\n\n**Do not conflate the historical Hefei terrain capture**: original CTEAS Hefei reference was derived from **CGIAR SRTM 3-arcsecond (~90 m)** `srtm_60_06.tif`. New SRTMGL1 (~30 m) has different pixel grid/nodata/possibly vertical and preprocessing branches; scientific comparison must report data-source differences rather than demand exact old Hefei P1 equality. Use frozen 90m source only for old scientific regression and 30m for new case after separate P1 numeric acceptance. Existing `engine/preprocess/terrel/auto_select_srtm_to_terrel.py` searches `srtm_*.tif` **and** relies on name-index or `.bbox`; an API-result TIFF therefore needs a verified case-relative name like `srtm_..._site.tif` and a real `.bbox` sidecar or an updated strict TIFF geobounds detector.

### Next scientific gates (both OPEN)

1. **G1B-B3 P1**: select DEM provider/version and case bbox, download authorized original SRTM, verify GeoTIFF WGS84, nodata/no-gap/vertical unit/datum, source SHA and P1 original vs native physical terrain field results.
2. **G1B-B3 P2**: pull exact root Git LFS asset, run *real-source* new UTM GLCC crop, execute newly generalized **native** P2 fractions, compare independent original CTGPROC `LU.DAT` under identical source coordinates, and feed P3. New-site `GEO.DAT` cannot be marked accepted from this source extraction alone.

No vendor Fortran redistribution, no full P6/P7 143h automatic CI, no pretending multi-option CALMET/CALPUFF are completely reconstructed.
