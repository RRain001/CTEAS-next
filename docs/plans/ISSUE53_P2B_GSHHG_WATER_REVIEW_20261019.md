# Issue #53 — User-selected global GLC35→USGS38 crosswalk and GSHHG water gate (2026-10-19)

## Science decisions captured verbatim in meaning
User supplied a complete 35-row GLC_FCS30D→USGS mapping and explicitly changed `GLC183 → USGS77` and `GLC184 → USGS77`, retaining all other selections. The authoritative machine-readable decision is [ISSUE53_GLC35_USGS38_USER_SELECTED_20261019.json](ISSUE53_GLC35_USGS38_USER_SELECTED_20261019.json). All **34 non-water classes** are user-selected globally; `GLC210` remains a three-way conditional **not an approved single-code mapping**. This new decision file supersedes the candidate codes in `ISSUE53_GLC35_USGS92_REVIEW_CANDIDATES_20261018.json` **for user intent**, while the latter remains an intact historical review fixture for already-merged fail-closed audits. The selected mapping is **not** production authorization until the water gate is closed.

## Verified GSHHG source and spatial precision
- Dataset: [GSHHG version 2.3.7, GMT official release](https://github.com/GenericMappingTools/gshhg-gmt/releases/tag/2.3.7), [Shapefile download](https://github.com/GenericMappingTools/gshhg-gmt/releases/download/2.3.7/gshhg-shp-2.3.7.zip).
- Published ZIP SHA256 `8dbbe7e071e77e9e75f2d639239099ebca8d5c16d6a07df8169729d49f15cf41`; these bytes have **NOT yet been downloaded or locally hash-verified** for this issue.
- GSHHG is a **WGS84 vector polygon** collection, **not** a fixed 30 m or 100 m raster. Resolution choices `f` full, `h` high, `i` intermediate, `l` low, `c` crude refer to progressive geometry simplification, NOT a guaranteed positional accuracy in metres. Select full `f` for 30 m GLC source overlap, while explicitly tracking coastline age/accuracy mismatch.
- Official GSHHG docs [SHAPEFILES.TXT](https://github.com/GenericMappingTools/gshhg-gmt/blob/master/SHAPEFILES.TXT) describe filenames `GSHHS_f_L1.shp` etc.
- Earlier NOAA NCEI ZIP mirrors became unavailable during 2026; use verified GMT GitHub release download rather than the old `ngdc.noaa.gov/mgg/shorelines/data/...` link.

## Hierarchy, actual ocean-versus-land method
- `GSHHS_f_L1`: non-Antarctic continent/island **land polygons**; the exterior is ocean.
- `GSHHS_f_L2`: lakes inside L1 land → freshwater.
- `GSHHS_f_L3`: islands in lakes → land.
- `GSHHS_f_L4`: ponds inside lake islands → freshwater.
- `GSHHS_f_L5/L6`: Antarctic ice-front/grounding-line alternative boundaries; require an explicit separate Antarctic policy (default: refuse Antarctic coverage until selected).
- Preserve nesting as land/water parity and use full polygon intersections, *not* polygon bounding boxes or 30 m source pixel centre tests. Use geometry repair, dateline handling, WGS84→case UTM transformation and self-intersection diagnostics; *do not* invent 30 m precision for the shoreline.
- First intersect each GLC210 source 30 m footprint with validated GSHHG water/land polygons, then attribute its **area portions** to inland freshwater vs marine. Do not change original GLC210 source area, collapse uncovered pixels, or interpolate categorical codes.
- `GLC210∩L1 land` not in a mapped L2 lake is **not automatically an error**: GSHHG L2 omits many small river/reservoir/pond water bodies. Map confirmed freshwater to USGS52 by default and log conflicts.
- `GLC210` on ocean side of L1 is `MARINE_54_OR_55_UNRESOLVED`: GSHHG does NOT label bays, estuaries or open-ocean regions as separate named water categories. Additional vetted bay/estuary and large-water-body evidence is required before assigning USGS54 or USGS55. It is scientifically invalid to infer 55 merely because the location is on the marine side of a shore.
- GSHHG is not a missing-water product. A GLC source NoData (0/250), a coastline conflict, or unclassified marine water shall not be auto-filled as sea. This is essential because current D2 rejects uncovered/NoData source pixels.
- 2022 GLC imagery and v2.3.7 GSHHG release need not have coincident shorelines; report coastline disagreement area and impose an explicit science tolerance **after** real coastal tests.

## Implementation boundary and pending tests
P2-B: 35-category 30 m exact UTM planar raster-area overlap → **34 fixed mappings + conditionally split GLC210 by area** → USGS38 fractions → `LU.DAT v2.1`. Maintain exact per-cell conservation and fail closed on unresolved 54/55 decisions. Reuse **unchanged** MAKEGEO USGS38→14 physics (Issue #46), and do not modify P2-A original sampling code. No approved P2-B production `LU.DAT`, no `GEO.DAT` nor full scientific run is claimed.

Before closing the mapping gate:
1. Download official GSHHG v2.3.7 ZIP and verify SHA256, selected Full L1–L4 metadata, map geometry and license/provenance.
2. Independent synthetic and *real coastal* area-intersection tests, shore crossing, inland lakes, lake-islands, narrow rivers, 180° dateline, southern hemisphere/Antarctica reject path, input mask and category conservation.
3. Resolve additional **54 versus 55** marine data source/policy (cannot be solved by GSHHG L1 alone), then validate real GLC coastal/ocean source data coverage.
4. Only then serialize approved 38-category `LU.DAT` v2.1 and independently compare selected native MAKEGEO branch against actual original under the same inputs. Long science runs remain manual-only.
