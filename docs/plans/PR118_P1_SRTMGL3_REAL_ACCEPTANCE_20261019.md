# PR #118: SRTMGL3 90 m real-source and unchanged-original TERREL acceptance

Date: 2026-10-19. Scope: a new **explicit product choice** in the already existing P1-B OpenTopography route; not a new P1 numerical/physical branch.

## Baseline and constraints

- Closed #54 has already passed the original-vs-native P1-A user TIFF 90 m and P1-B SRTMGL1 30 m same-TIFF comparisons. Do **not** reopen it or claim these old results validate the new product.
- A = user-provided local GeoTIFF (unchanged); B = `--opentopography --dem SRTMGL1` (old default) or `--opentopography --dem SRTMGL3` (new 90 m option). No implicit substitution.
- GL3 means original **NASA SRTMGL3 v003** (3 arc-seconds), not legacy CGIAR-CSI SRTM v4.x.
- Selected product must be recorded in source and native manifests and its angular spacing independently checked, including actual TIFF hash and NoData.
- Original `CTEAS` vendor checkout pinned to `dfad99a78ed84d655e21411c9d25eb0d2583bf13`; untouched Fortran source. Numerical tolerances and C++ P1 physics unchanged.
- No secrets, raw DEM, proprietary source, original executable, full control, run logs or raw grid field may be uploaded to public Actions artifacts.

## Manual end-to-end test (must be explicitly dispatched)

The actual **same-TIFF original TERREL vs native C++ comparison** uses the existing `.github/workflows/issue54-original-terrel-manual.yml`, now extended for `P1_B_90M_DOWNLOAD` and strictly limited on the PR branch to a manually dispatched run by repository owner `RRain001`.

When reviewing PR #118, in **Actions > Issue54 original CTEAS TERREL genuine same-TIFF parity (manual only) > Run workflow**, select:

- Branch: `codex/p1-opentopo-srtmgl3-selectable`
- Route: `P1_B_90M_DOWNLOAD`

Equivalent owner-authenticated GitHub CLI instruction (from any machine with repository access):

```bash
gh workflow run issue54-original-terrel-manual.yml \
  --repo RRain001/CTEAS-next \
  --ref codex/p1-opentopo-srtmgl3-selectable \
  --field route=P1_B_90M_DOWNLOAD
```

This workflow performs: (1) protected-key OpenTopography `SRTMGL3` real download, with explicit same-product S3 fallback for pre-existing classified HTTP 406 only; (2) authentic TIFF metadata, SHA, 3-arcsecond resolution and case coverage admission; (3) run the same current native C++ P1 kernel; (4) losslessly create a compression-compatible TIFF for original `TIFFINFO.FOR` and prove unchanged full elevation pixels; (5) run **unmodified pinned Fortran TERREL** on that TIFF; (6) re-run native P1 on **exactly those repacked source bytes**; (7) independently compare every model cell against original SAV and DAT under existing absolute tolerances; (8) upload only sanitized numeric/identity evidence JSON. Existing 30 m and user-TIFF routes remain main-only.

A separate optional source-only real check is available via `.github/workflows/s2g1bb3-p1-dual-source.yml` on the PR branch with `dem=SRTMGL3`; that test is **not** an original TERREL parity test.

## Acceptance criteria

1. The manual real job must **run**, not be `skipped`. Ordinary PR CI only runs synthetic tests.
2. Source evidence: `dataset=SRTMGL3`, 3-arcsecond WGS84 EPSG:4326 single-band Int16, explicit NoData metadata, zero unexplained NoData in case window (or documented handling), bounded size/area, selected TIFF SHA256 and route `P1_B_90M_DOWNLOAD`.
3. Fail closed for HTTP rejection, quota, missing tiles or missing metadata. Neither GL1 nor CGIAR may substitute for GL3. Real public-S3 fallback requires verification of genuine remote bytes, not just mocked URL tests.
4. Original & native proof: identical georeferencing, selected byte/elevation identity; original Fortran source/commit hash pinned, original control and executable hashed; original TERREL actually executed.
5. Compare actual original/native `hits` per cell (zero mismatches); original float32 sums/hits raw mean to native within `1e-5 m`; original `TERREL.DAT` F8.1 elevations to native within `0.0500001 m`. Do not loosen tolerances.
6. Inspect scientific artifact metadata independently (result `NUMERIC_PASS_PROVISIONAL` alone does not establish authentication of the original execution and source vertical datum). Record real status in PR, including whether it passed, failed or was blocked; preserve source-provenance caveats.
7. Do not merge PR #118 until positive real download plus scientific comparison and independent metadata review are evidenced. #54 remains closed.

## Real run #39226316981 failure / remediation

The owner's true `workflow_dispatch` run [#39226316981](https://github.com/RRain001/CTEAS-next/actions/runs/39226316981) on PR head `57515f9` was **FAILURE**: pinned old CTEAS source checkout and native C++ compilation/3 CTests passed, but `p1_real_actions_case` returned `BLOCKED_REAL_SOURCE_INPUT`, `http_status=null`, `category=SOURCE_CHECK_BLOCKED`. The Fortran-vs-native numerical step was skipped. The old v1 evidence redacted the exact source error, so an actual provider or TIFF issue cannot be identified from this run alone.

Diagnostic-only remediation on this PR now emits a **bounded** `source_failure_stage`, `source_failure_reason_code`, optional numeric `source_provider_http_code` and existing `provider_failure_category`. Stage distinguishes OpenTopography API request, public S3 bulk transport, source precheck, GeoTIFF metadata validation and case-window admission. Unrecognized values intentionally remain `UNCLASSIFIED_SOURCE_FAILURE`; do not print exception text or include untrusted provider bodies, API keys or URLs. The 30m/90m product choice, S3 fallback condition, native physics, Fortran original, and comparison tolerances remain unchanged.

**After offline CI passes**, rerun the same manual workflow on the *updated PR branch* with `P1_B_90M_DOWNLOAD`. Inspect sanitized job log and metadata artifact first. Do not claim real download or scientific acceptance merely from a PR CI success. If the stage/reason reports an actual issue, fix only the confirmed transport or source validation bug without replacing the requested DEM.

## Official GL3 S3 object listing and verified north-prefix repair

Owner-provided [immutable PR #118 evidence comment](https://github.com/RRain001/CTEAS-next/pull/118#issuecomment-6264039201) was **appended in place**, with direct S3 ListObjectsV2 links and local real-download proofs. The owner verified that the GL3 public object tree is:

```text
SRTM_GL3/SRTM_GL3_srtm/North/North_0_29/NxxEyyy.tif
SRTM_GL3/SRTM_GL3_srtm/North/North_30_60/NxxEyyy.tif
SRTM_GL3/SRTM_GL3_srtm/South/SxxEyyy.tif
```

The prior GL3 URL lacked `North/`; [owner-triggered run #39229622789](https://github.com/RRain001/CTEAS-next/actions/runs/39229622789) confirmed the actual failure as `S3_BULK_DOWNLOAD` / `BULK_TILE_HTTP_REJECTED` / HTTP **404**. Verified with owner-side GET (HTTP 200, not a successful full integrated Actions run):

- `N31E114.tif` (2,018,529 bytes), SHA256 `3ca1100a2518b96e72c97871d37f286ca62a285e5ee5d2b2a6ab740c5b3df1f2`.
- `N31E115.tif` (2,308,252 bytes), SHA256 `6b8d311dabe5d8663de881d9892670d800677f93796982d274ba320db8ad357a`.

Rasterio confirmed in both original downloaded tiles: 1201 × 1201, EPSG:4326, single-band Int16, 3 arcseconds, NoData sentinel -32768, **zero actual NoData**. These SHA256 digests represent the owner's downloaded bytes; they **have not** been matched against independently published official checksums. South was verified by object listing, **not** by downloading a southern tile.

PR implementation now prepends `North/` **only to GL3 northern URLs**, preserving direct `South/`, unchanged GL1 URLs, exact DEM product, 406-only same-product fallback, native scientific code and Fortran numeric gates. Exact URL tests guard the 29°/30° band boundary and the two actually downloaded northern tiles. Real source staging, mosaic and original parity must still be proven on the updated branch by another explicit manual run; **no science PASS is implied by the local download**.

## True 90m original-vs-native numerical success and official metadata review

[Owner-manual GitHub Actions run #39235263223](https://github.com/RRain001/CTEAS-next/actions/runs/39235263223) used PR head `f5115ae` with `P1_B_90M_DOWNLOAD`. All authentic stages passed: OpenTopography public S3 **same-product** GL3 download, source mosaic/coverage, native P1, unchanged pinned Fortran TERREL 7.0.0 compilation and execution, lossless identical-pixel TIFF repackaging and same-TIFF numeric comparison. The metadata-only artifact is [#12179340340](https://github.com/RRain001/CTEAS-next/actions/runs/39235263223/artifacts/12179340340). Logged status: `NUMERIC_PASS_PROVISIONAL`; the intentionally strict software evidence schema still calls scientific acceptance `NOT_ACCEPTED_INDEPENDENT_ORIGINAL_RUN_AUDIT_REQUIRED`.

Per the reviewed run's separate evidence report: model cells=2500, valid source-window pixels=5293, NoData=0; original/native hits=3438/3438, per-cell hit mismatches=0; F8.1 DAT bad cells=0, max elevation difference=0.04999999999999716 m (<0.0500001 m); SAV raw-mean bad cells=0, max absolute difference=2.542666678095884e-06 m (<1e-5 m). The uncompressed and source GeoTIFF files have **different container hashes** due to lossless repackaging; their ordered Int16 pixel values and georeferencing were checked identical, and Fortran and native used that same repacked TIFF.

### Dataset-level product identity: documented, not tile-cryptographically authenticated

- [NASA LP DAAC product SRTMGL3.003](https://doi.org/10.5067/MEASURES/SRTM/SRTMGL3.003): official SRTM Global 3 arcsecond / 90m Version 003, data product DOI and NASA product family. NASA's LP DAAC also lists **SRTMGL3S.003** and **SRTMGL3N.003** as distinct 3 arcsecond products; the family DOI does **not** by itself establish an OpenTopography GeoTIFF is byte-identical to any one of those NASA HGT granules.
- [OpenTopography collection metadata](https://portal.opentopography.org/datasetMetadata?otCollectionID=OT.042013.4326.1): source collection `OT.042013.4326.1`, product `SRTM_GL3`, published data label SRTM Version 3, sourced from NASA and its partners; coordinates WGS84 horizontal EPSG:4326. Its public S3 objects are registered under `SRTM_GL3/SRTM_GL3_srtm/`, and the true two source files were downloaded and SHA256 logged in the [source evidence comment](https://github.com/RRain001/CTEAS-next/pull/118#issuecomment-6264039201).
- **Evidence verdict**: `OFFICIAL_COLLECTION_METADATA_ONLY`. The OpenTopography SRTM_GL3 public provenance is consistent with NASA SRTM Version 3, and the actual TIFF raster properties independently meet the specified 3 arcsecond grid/type/coverage contract. **Per-granule NASA cross-check or publisher checksum for the two raw source tiles was not performed.** Therefore keep `source_product_version_authenticated=false`, and distinguish it from the now-supported *official provider dataset metadata*.

### Vertical reference: officially documented EGM96 height, not WGS84 ellipsoid

- The [OpenTopography SRTM GL3 dataset page](https://portal.opentopography.org/raster?jobId=rt1781899650092) and [full collection metadata](https://portal.opentopography.org/datasetMetadata?otCollectionID=OT.042013.4326.1) state horizontal **WGS84 EPSG:4326** and vertical **EGM1996 Geoid EPSG:5773**. The page combines the wording “WGS84 Ellipsoid/EGM1996 Geoid”, but the authoritative **EPSG:5773** vertical CRS specifically denotes the EGM96 gravity-related height system, in metres, **not WGS84 ellipsoidal height**.
- [USGS SRTM Product Specifications](https://www.usgs.gov/centers/eros/science/usgs-eros-archive-digital-elevation-shuttle-radar-topography-mission-srtm) independently lists **horizontal WGS84; vertical datum EGM96; height unit metres**.
- [EPSG:5773 definition](https://epsg.io/5773) independently defines EGM96 height as gravity-related height above the EGM96 geoid (metre).
- **Evidence verdict**: `EGM96_DECLARED_BY_OFFICIAL_DATASET_METADATA`. The downloaded GeoTIFF's **EPSG:4326 tag represents only its horizontal reference**, not proof the raster also embeds a vertical EPSG:5773 axis. Raster samples were not converted to WGS84 ellipsoidal heights; keep `height_vertical_datum_authenticated=false` as the **per-file** verification flag. The model should treat these values as provider-declared EGM96 geoid heights in m, and must not call them ellipsoidal heights nor silently apply a geoid transformation.

The new manifest `official_dataset_documentation` on GL3 carries the **documentary claims only**, explicitly marks the per-tile verification flags false and reports no vertical conversion. GL1 and local CGIAR/owner GeoTIFF workflows are unchanged. This separates **provenance-documentation PASS** from **per-granule independent authentication NOT_DONE**, while preserving the accepted **scoped real numeric parity** without lowering any scientific tolerance.

## Status

- Run #39235263223: authentic owner manual **SUCCESS** on head `f5115ae`; `NUMERIC_PASS_PROVISIONAL` with 2500 cells, 0 hit count mismatches, 0 numerical threshold violations; source mosaicking and original Fortran execution completed.
- Independent GitHub-steps/script/metadata review: **PASS_SCOPED_REAL_GL3_NUMERIC_PARITY**. Not a global source or physics certification.
- Dataset-level declared product/version: **OFFICIAL_COLLECTION_DOCUMENTED** as OpenTopography SRTM_GL3, NASA SRTM Version 3 / SRTMGL3.003 family. Specific raw OpenTopography tile-to-NASA granule byte identity: **NOT_VERIFIED**.
- Vertical datum: official OpenTopography + USGS metadata and EPSG registry document **EGM96 geoid height (EPSG:5773), metres**. Per-TIFF vertical CRS tag/granule authentication: **NOT_VERIFIED**.
- Explicit schema flags remain `source_product_version_authenticated=false` / `height_vertical_datum_authenticated=false`; do not silently promote them based on documentation.
- PR #118: **DRAFT**, real numeric tests PASS within scoped case, documentary provenance now recorded, unmerged pending final owner decision; historic Issue #54 stays closed.

## Provider references

- OpenTopography official `GET /API/globaldem`: `demtype=SRTMGL3`; GL3 API area limit 4,050,000 km².
- Official OpenTopography SRTM GL3 bulk directory: `s3://raster/SRTM_GL3/` on `opentopography.s3.sdsc.edu`; note public S3 key convention is independently checked by the actual manual run. No private API key or full authenticated URL stored.
