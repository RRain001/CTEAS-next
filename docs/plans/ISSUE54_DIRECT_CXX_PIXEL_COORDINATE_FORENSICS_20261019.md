# Issue #54: direct C++ coordinate lineage (forensic-only, PR)

## Scope and independent evidence

The pinned original TERREL 7.0.0 and unmodified native P1 both read the
same lossless Compression=1 real SRTM raster. The last authentic manual
comparisons remained strict numeric FAIL for SRTM90m and SRTMGL1 30m.
PR #93 made the original-vs-pyproj proxy analysis statistically valid by
excluding source samples outside the actual case grid. However pyproj is
not evidence of the actual C++ GDAL call or C++ REAL*4 arithmetic.

This change adds a **scratch-only direct C++ pixel trace**, using a copy of
the actual native `terrain_grid.cpp` instrumented after its exact
`cell_index_terrel` call. The forensic compile uses the actual
`terrain.cpp` GDAL reader and `p1_terrain_case_cli.cpp`, not a
reimplemented Python projection or independently coded C++ surrogate.
The normal production source, P1 binary, original TERREL Fortran,
source TIFF, case grid, tolerance, and original DAT/SAV/CSV comparator
are **not changed**.

At a genuine manual numeric FAIL the ephemeral runner now records:
- original TERREL original-pixel `(i,j)`, final projected x/y and CELLIND;
- identical native pixel `(i,j)`, final REAL*4 x/y, actual C++ CELLIND,
  projected pre-staging doubles and input lon/lat;
- direct join by pixel `(i,j)` (fail closed for duplicates or unequal sets);
- source-pixel counts, actual in-domain assignments by direction and bounded
  projected-coordinate residuals.

Only aggregate metadata and at most 20 **grid cell** discrepancies appear
in the existing metadata-only artifact. No per-pixel source coordinates,
source elevations, complete traces, original/vendor Fortran, TIFF, binaries,
control decks, full stdout/stderr, or API credentials may be uploaded.

## Gates and outcomes

PR validation uses synthetic WGS84 Int16 GeoTIFF tests and a GDAL/g++
scratch build of the actual C++ source. It does not run original TERREL or
real proprietary terrain, and is not scientific acceptance.

Real scientific replay remains **manual-only on main** via the existing
`workflow_dispatch` (one route at a time). A new report field
`coordinate_diagnostic_only.direct_cpp` reports direct original-vs-C++
pixel classification; its accepted hit totals are independently bound
to genuine original SAV and unmodified C++ CSV totals.
If direct C++ forensic compilation or comparison fails, only that
nested diagnostic is marked BLOCKED, without erasing proxy diagnostics
or overriding strict original-vs-native numeric FAIL.

A decisive projection remedy remains **out of scope** until authentic
direct C++ traces from both SRTM90m and SRTMGL1 independently verify
the stage and mechanism of differences. Do not apply coordinate shifts,
relax tolerance, substitute source products, or declare D2/D3/D4 PASS
from these diagnostics. #54 stays open pending D2/D3 strict original
numeric equivalence, D4 source/version/datum/licensing audit and #46
contract handoff.
