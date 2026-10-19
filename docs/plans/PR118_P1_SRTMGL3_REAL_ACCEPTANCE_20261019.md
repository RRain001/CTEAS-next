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

## Status

- PR software-only CI: pending or PASS depending on latest checks.
- SRTMGL3 **actual manual API/S3 request**: RUN #39226316981, **BLOCKED_REAL_SOURCE_INPUT** (exact cause unclassified by old v1 reporter); subsequent rerun NOT_RUN.
- SRTMGL3 **authentic original TERREL same-TIFF comparison**: NOT_RUN.
- All existing #54 historical scientific acceptance remains unchanged.

## Provider references

- OpenTopography official `GET /API/globaldem`: `demtype=SRTMGL3`; GL3 API area limit 4,050,000 km².
- Official OpenTopography SRTM GL3 bulk directory: `s3://raster/SRTM_GL3/` on `opentopography.s3.sdsc.edu`; note public S3 key convention is independently checked by the actual manual run. No private API key or full authenticated URL stored.
