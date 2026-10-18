# Issue #54 — P1 D1-A generic UTM kernel (scoped software slice)

Baseline: merged PR #58, `main@4f4ad2ab10a48374c5e99259f263213fe8bd16f8`.

This change **only parameterizes the WGS84 geographic-to-UTM projection** in the existing selected native TERREL sampling kernel. It retains the original float32 pixel-center arithmetic, `COORDLIB`-style scale, `CELLIND` indexing, float sums and averaging, NoData rejection and south-to-north CSV layout. The frozen `cteas_p1_terrain` binary continues using zone 50N and its 50×50/100m Hefei origin refusal. No new physics/DEM source/resampling policy is introduced.

`UtmProjection{zone,southern_hemisphere}` explicitly selects EPSG 32601–32660 or 32701–32760; invalid UTM zones fail closed. The pre-existing `TerrainGridSpec` already accepts non-square NX/NY and variable cell-size in metres. The added unit tests use synthetic one-pixel WGS84 terrain in two northern zones and one southern zone; they compare legacy 50N wrapper to generic 50N byte-for-byte at the in-memory result level, and reject out-of-range zones.

**Not yet delivered:** approved shared #42 raw `grid.cmn` parser / three-decimal-km literal validation and B-1 manifest schema; new case CLI; #49 adapter wired to generic native CLI; aligned DEM windows/resource budget/coverage fail-closed; multi-TIFF P1-A end-to-end; cached real SRTMGL1 P1-B; independent same-source original TERREL comparison; dynamic `TERREL.DAT` owned by #46.

CI in `.github/workflows/issue54-p1-d1-offline.yml` runs bounded GDAL C++ CTests on PRs without any API key, original vendor data, or science simulation. It may establish only `P1_D1_DYNAMIC_UTM_SOFTWARE` after a successful run; scientific P1-A/P1-B acceptance remains `NOT_RUN`. Heavy real-asset scientific replay must be manually dispatched under the repository's existing rules. This PR does not close #54 or unblock #42.
