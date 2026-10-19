# Issue #53 — GLC_FCS30D 35 → USGS92 38 classification policy / GSHHG L1 land-versus-sea (2026-10-19)

## User's confirmed decision (supersedes initial three-way water proposal)
All 34 non-water GLC classes retain the exact user's table, including the two corrections **GLC183 → USGS77** and **GLC184 → USGS77**. The complete user-selected fixed map is recorded in [ISSUE53_GLC35_USGS38_USER_SELECTED_20261019.json](ISSUE53_GLC35_USGS38_USER_SELECTED_20261019.json). GLC210 has exactly two branches:

- **GLC210 valid water intersecting GSHHG L1 terrestrial/landward polygon** (includes lakes, rivers, reservoirs regardless of whether GSHHG L2 separately contains the feature) → **USGS52**.
- **GLC210 valid water outside the GSHHG L1 land polygon, seaward of the coastline** (includes bays, estuaries and open ocean) → **USGS55**.
- **USGS54 is not assigned by this P2-B map.** This is the user's project-wide modelling simplification; it should not be interpreted as a claim that every bay/estuary is geomorphologically open ocean or that USGS 55 is original Anderson level-II.
- On mixed shoreline pixels the fractions to 52 and 55 are their **distinct polygon intersection areas**, not a one-pixel vote; preserve `A_GLC210 = A_USGS52 + A_USGS55` per grid cell. Other 34 class areas are mapped intact. All 38 target fractions must sum to 1 for a valid completely covered model cell.
- Invalid, missing, masked or offshore-uncovered GLC (e.g. 0/250) does **not** automatically become GLC210 or USGS55. Invalid/ambiguous GSHHG geometry fails closed. Antarctica: L1 excludes Antarctica, therefore **must not** classify its GLC210 as ocean by simply taking `not in L1`; support Antarctica only after separate reviewed L5/L6 choice.

## Which source folder: GSHHS_shp, not WDBII_shp
Official [SHAPEFILES.TXT](https://github.com/GenericMappingTools/gshhg-gmt/blob/master/SHAPEFILES.TXT) says:
- `GSHHS_shp/{f,h,i,l,c}/GSHHS_<resolution>_L<level>.{shp,shx,dbf,prj}` contains **closed shoreline POLYGONS** suitable for area intersection; select **`GSHHS_shp/f/GSHHS_f_L1.shp` as the authoritative binary land/sea classifier**.
- `GSHHS_f_L2` (lakes), `GSHHS_f_L3` (lake islands), `GSHHS_f_L4` (lake-island ponds) are useful for topology diagnostics and freshwater crosschecks. Since the classification is only marine-vs-landward GLC210, **only L1 must be present to assign 52/55**; L2–L4 can validate inland water, but do not override L1 with an erroneous ocean flag.
- `GSHHS_f_L5` (Antarctic ice front) and `GSHHS_f_L6` (Antarctic grounding line) are alternative Southern polar definitions, **not** a drop-in global L1 extension.
- `WDBII_shp` contains **river and political border LINE** data such as `WDBII_river_f_L1` and `WDBII_border_f_L1`. These are not closed land/ocean polygons and **are not required** for this two-branch decision. Although the underlying WDBII database historically contributed lakes to the merged GSHHG product, do not confuse the `WDBII_shp` line folder with `GSHHS_shp` nested lake polygon levels.

## Which resolution: Full f, not High h
- Choose **GSHHG v2.3.7 Full `f`** as the P2-B baseline, because the GLC image has 30 m pixels and models may have 100 m nearshore grids; geometric shoreline simplification can flip mixed pixels' USGS52/55 fractions.
- GSHHG vector data have **no fixed 30 m horizontal resolution or proven 30 m positional accuracy**. Full means *no vertex decimation*. High `h` uses Douglas–Peucker line reduction to approximately 20% of the Full data size; `i,l,c` successively simplify by ~80%. These are source geometry reduction factors, **not measured positional error tolerances**.
- High `h` is an **optional sensitivity comparison**, not an implicit substitute for Full in science runs. For a few real 2022 coastal windows compute `A(USGS55)_f`, `A(USGS55)_h`, the resulting per-cell area/fraction differences, and discrepancies to actual mapped shoreline; report changed coastal cells rather than asserting metre-level spatial accuracy. Prefer Full even if the results differ little, since size is manageable once source geometries are spatially clipped.
- GSHHG's source coastlines are historically compiled; version v2.3.7 was released in 2017. Their coastline may not match reclaimed or modified land in a 2022 GLC image. Count/report such disagreements and require a stated acceptance tolerance for coastal science.
- Process only a bounding-box subset plus geometry-intersection buffer for the case, using spatial index and robust polygon clipping; do **not** rasterize all of global GSHHG, and do **not** publish whole global shapefile assets in the source repo.

## Source authority, reproducibility and licensing
- Official version: [GMT GSHHG v2.3.7 release](https://github.com/GenericMappingTools/gshhg-gmt/releases/tag/2.3.7); [ESRI ZIP](https://github.com/GenericMappingTools/gshhg-gmt/releases/download/2.3.7/gshhg-shp-2.3.7.zip).
- Previously published archive SHA256: `8dbbe7e071e77e9e75f2d639239099ebca8d5c16d6a07df8169729d49f15cf41`. **Not downloaded or locally SHA-verified here**. At ingestion: verify file bytes/hash, root manifest, exact Full L1 sidecar files, CRS, 2.3.7 identity, vector validity and license (LGPL), pin all hashes in produced metadata.
- Processing path: original GLC 30 m raster category areas and polygons (same case WGS84/UTM) → crop/transform GSHHG WGS84 Full L1 to model UTM → intersect valid GLC210 pixel geometry with terrestrial side of L1 → allocate to USGS52, allocate remainder to USGS55 → combine other 34 mapped areas into USGS38 → normalized `LU.DAT v2.1`.
- **Numerics:** assert `|A210 - (A52 + A55)| ≤ declared numerical tolerance` on each model cell, `Σ(A_usgs38) = A_modelcell`, and coordinate overlap/no-data tests; reject distorted polygons (especially antimeridian) or unsupported polar regions, rather than misclassifying everything outside L1 as sea.

## Approval and delivery boundaries
The **classification decision is now USER_APPROVED**, including the 210→52/55 binary rule. However, `production_authorized=false` remains until GSHHG archive provenance, real source coverage, C++ native polygon handling, 35→38 area conservation and original MAKEGEO handoff are demonstrated. The old `ISSUE53_GLC35_USGS92_REVIEW_CANDIDATES_20261018.json` remains a locked **historical, not-approved proposal** for existing audit regression; its older `183/184/210` entries are **not** the current user selection. Do not modify P2-A GLCC 1 km original-matched methods or P3 MAKEGEO physical parameters (Issue #46). No approved LU.DAT or GEO.DAT has been generated.

### Verification checklist
1. Obtain GMT v2.3.7 archive, independently verify SHA256/license and shapefile L1 projection; preserve source SHA and version.
2. Synthetic polygon test: land-side GLC210→52, sea-side→55, mixed pixel split, tiny islands, lake-with-island, mask/gaps, sums and rounding.
3. Real coastal 2022 GLC source availability and coast-boundary contradiction audit; Full f versus High h area/fraction sensitivity benchmark.
4. Test international date line, hemisphere/UTM grid boundary, shoreline near discontinuities; reject unsupported Antarctica without L5/L6 authorization.
5. Produce USGS38 `LU.DAT v2.1` only after approved data and code gates; run independent original/native P3 same-input comparison on manually triggered science workflow.
