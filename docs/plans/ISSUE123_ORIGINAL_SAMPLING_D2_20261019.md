# Issue #123 D2 — original CTGPROC IPTYPE hierarchy, scoped C++ implementation (2026-10-19)

## Frozen scope
- #119 `EXACT_AREA_V1_FROZEN_PASS_SCOPED_WOLSONG_2022` remains unchanged, GSHHG **Full f** only for the user's future modelling. No Full-vs-High acceptance comparison.
- D2 only adds an independently callable, non-production C++ point classifier. It is not yet connected to the existing P2-A GLCC/GLAZAS point-counter, and original Fortran numerical equivalence is explicitly `NOT_RUN`.
- Original vendor code is read-only, not copied or redistributed. Source: [CTEAS original CTGPROC](https://github.com/RRain001/CTEAS/blob/dfad99a78ed84d655e21411c9d25eb0d2583bf13/engine/vendor/src/CTGPROC_v7.0.0_L150211/ctgproc.for), `IPTYPE/PNPOLY` and `COASTEXT/COASTRD`.

## Original Fortran behaviors used in D2
- `IPTYPE` iterates extracted shoreline polygons; initial type 0 (ocean), `LCOAST=F` returns 1, skips polygons with level <= current type and fast bbox excludes.
- Five point classes: 0 ocean, 1 mainland/marine island, 2 lake, 3 lake island, 4 pond-on-lake-island.
- Inside a polygon, retain the maximum type; on a polygon edge: L1->0, L2->2, L3->2, L4->4. This is a **semantic software** replica. Fortran `PNPOLY` uses exact REAL*4 point/vertex comparisons; `GEOS/OGR` `Touches/Within` in D2 is not yet an original numerical oracle, particularly close to coast edges.
- Original `COASTEXT/COASTRD` uses full-resolution GSHHS coastlines in projected model grid, includes surrounding polygon and clipping behavior, and the original binary/BLN input format; D2 instead reads official **full-resolution** L1–L4 shapefile layers separately. It has not reproduced all original GSHHS binary extraction, surrounding pseudo-polygon or DATUM/GLOBE rounding behaviors.
- Loader validates EPSG:326xx/327xx, <=50 km window, Full `GSHHS_f_L{1,2,3,4}.shp` names, all WGS84 layers, valid polygons, and bounding region. Caller must verify the **official SHA-pinned v2.3.7 archive and all L1–L4 sidecars** independently before production use; D2 loader does not claim an authenticated source or real-science gate.

## Implemented files
- `native_cpp/include/cteas/geo/ctgproc_original_iptype.hpp` — isolated API accepting Fortran-style REAL*4 model km.
- `native_cpp/src/geo/ctgproc_original_iptype.cpp` — hierarchical GEOS point-in-polygon and boundary categorization; separately accessible Full L1–L4 shape loading.
- `native_cpp/tests/p2_original_iptype_tests.cpp` — synthetic nested L1–L4 geometries, boundary table, sample policy bridge to D1 `LUGRID/SVGRID`, and generated on-the-fly synthetic WGS84 shapefiles used to exercise actual loader. No real GSHHG usage or original Fortran binary.
- `.github/workflows/issue123-original-iptype-ci.yml` — PR-triggered synthetic-only CTest. NO automatic full original GSHHG or Fortran science.

## D2 and later acceptance levels
1. D2 PR contract: `PASS_SOFTWARE_IPTYPE_HIERARCHY_SCOPED` only when synthetic CI succeeds.
2. Next: independently restore all authentic **GSHHG v2.3.7 Full f L1–L4** from pinned ZIP and validate their sidecar hashes. Pin source provenance and produce bounded real-region reports; user-requested no High path.
3. Original lineages: compare actual original `COASTEXT/COASTRD` extracted polygon IDs, types and projected vertices to the C++ shapefile loader, including coast edge/holes/lakes and surrounding land/ocean windows. Diagnose REAL*4 `PNPOLY` vs GEOS difference rather than relaxing original parity thresholds.
4. Reuse P2-A existing `NGRID`, GLAZAS source mesh, `SVGRID`-compatible output; integrate optional 'ORIGINAL_SAMPLING' only through an independently gated new mode. Original `GENERIC + LCOAST` remains forbidden.
5. User-manually-run real CTGPROC original-vs-C++ comparisons must demand exact per-cell integer HITS and three-decimal final fractions. Full science workflow remains manual.

## Scientific boundaries
`USGS52` in the frozen EXACT_AREA route is GLC210 landward water under fixed L1, not an observed freshwater claim. D2 uses the full GSHHG hierarchical polygon types, **not** the area method. P3/P6/P7 scientific status remains unchanged.
