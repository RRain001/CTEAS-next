# Issue #54 — official OpenTopography SRTMGL1 public bulk recovery (2026-10-18)

## Trigger and scope
The previously executed *real* SRTMGL1 30m requests on GitHub Actions failed with
`OpenTopography HTTP 406 [UNCLASSIFIED_PROVIDER_REJECTION]`, even though
native P1 C++ compiled and 3/3 CTests passed. The reason for HTTP 406 has
**not** been established; do not assume the API key is invalid or guess
the provider's motive.

OpenTopography itself documents a **public, anonymous S3 bulk download**
for the very same `SRTM_GL1` product:
`https://portal.opentopography.org/raster?opentopoID=OTSRTM.082015.4326.1`
(the site's Bulk Download section explains the no-sign-request
`s3://raster/SRTM_GL1/` service). The raw 1° COG path is
`https://opentopography.s3.sdsc.edu/raster/SRTM_GL1/SRTM_GL1_srtm/{TILE}.tif`,
for example `N31E114.tif` and `N31E115.tif` for this reviewed 115°E seam case.

This is **an alternate transport for route P1-B, not a third DEM
product, not 90m fallback and not a new physics branch**.

## Guardrails
- Default remains the existing authenticated `/API/globaldem` route. The
  alternate transport is enabled only by the explicit
  `--allow-public-srtmgl1-bulk-fallback` flag or the separately reviewed
  issue #54 **manual-only** GitHub Actions B runner. It runs only after
  `HTTP 406 [UNCLASSIFIED_PROVIDER_REJECTION]`, **not** after a recognized
  key rejection, quota/rate limit, HTTP 401/403, or malformed/non-TIFF
  successful API response. All other API failures remain fail-closed.
- The fallback uses the exact SRTM_GL1 mirror and geographic 1° source
  tiles; `MAX_TILES=9`, `MAX_TOTAL_BYTES=300MB`, mandatory valid SRTM
  footprint and 1-arcsec WGS84 single-band Int16 GeoTIFF/NoData metadata.
  All sources must be on the same raster lattice. The original #49
  no-resampling / equality-on-overlap mosaic logic is reused unchanged,
  writing only a buffered output via the same selected TIFF contract.
- Both source routes still feed the **same** approved #62 C++ P1 kernel,
  with exact shared B0 case/grid/time SHA256. Provenance marks
  `transport=opentopography_official_public_s3_bulk`,
  `public_bulk_opt_in=true` and `bulk_recovery_used=true`;
  file-level raw SHA256/geometry remains recorded locally. Repository
  and Actions artifacts contain only bounded summary metadata; no DEM
  files, API secrets or vendor binaries are re-published.
- Actual product version, vertical datum, and independently authenticated
  provider checks still require audit. Original Fortran TERREL on the
  **same selected cropped TIFF** is a separate gate. Success must remain
  `PRODUCED_UNVERIFIED`, not `SCIENCE_ACCEPTED`.

## Actions
Normal PR CI is offline mock source tests only. After the PR merges, the
authorized issue #54 owner command
`/cteas-p1-real-30m` creates an actual `workflow_dispatch` on
`main` and runs a real OpenTopography source attempt with this *explicit*
opt-in fallback. A failure shall preserve a source blocker; the HTTP
status and authorized B route must be independently reported.
