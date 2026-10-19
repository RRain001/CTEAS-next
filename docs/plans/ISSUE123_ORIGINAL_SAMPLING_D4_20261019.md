# Issue #123 D4 — CTGPROC COASTRD/PNPOLY REAL*4 diagnostic candidate (2026-10-19)

## Goal and frozen predecessor
User-approved Wolsong `P2B_EXACT_AREA_V1_FROZEN_PASS_SCOPED_WOLSONG_2022` (Issue #119) is unchanged; continue to use official GSHHG v2.3.7 **Full** exclusively. The separate original CTGPROC sampling reconstruction remains Issue #123.

Official Full f L1–L4 source archive SHA256 is `8dbbe7e071e77e9e75f2d639239099ebca8d5c16d6a07df8169729d49f15cf41`, verified in [user-manual Run #39248802609](https://github.com/RRain001/CTEAS-next/actions/runs/39248802609). All 16 `.shp/.shx/.dbf/.prj` sidecars were compared with the **same authenticated ZIP**; the complete source-sha manifest is [artifact #12184138675](https://github.com/RRain001/CTEAS-next/actions/runs/39248802609/artifacts/12184138675). `AUTHENTIC_FULL_L1_L4_SOURCE_VERIFIED` is a provenance gate, not a coast geometric/Fortran parity gate.

## Original source inspected, not vendor-redistributed
Read-only reference [original CTGPROC v7.0.0](https://github.com/RRain001/CTEAS/blob/dfad99a78ed84d655e21411c9d25eb0d2583bf13/engine/vendor/src/CTGPROC_v7.0.0_L150211/ctgproc.for), especially:
- `COASTEXT` constructs *clipped and occasionally synthetic surrounding* polygons, then writes BLN with the record header `i7,i1,"i1,i1,i6"` and coordinates as projected-km `f12.6,f12.6`. It is **not** just polygon inclusion against raw shapefiles.
- `COASTRD` reads that BLN, retains **original polygon sequence**, type, source and ID; computes per-polygon min/max and checks the BLN intersects the declared grid.
- `IPTYPE` initializes 0 ocean; when `LCOAST=F` returns 1 land; on each eligible polygon (level above current type, bbox overlap) invokes `PNPOLY`. Inside becomes max type; boundary assignments: L1=>0, L2=>2, L3=>2, L4=>4.
- Original `PNPOLY` is single-precision REAL, not a GEOS `Touches/Within` predicate. It handles exact float zero for vertices and horizontal/vertical edges, skips degenerate zero-length segments and computes `(YI*XJ-XI*YJ)/(XJ-XI)` for crossing decisions.

## This D4 PR: carefully bounded additional pathway
- Introduces `ctgproc_original_bln_pnpoly.{hpp,cpp}` **independent** of D2's GEOS shapefile classifier. Its input is the **actual original extracted BLN** and point coordinates in km `float`; no GDAL projections or shoreline reconstruction inside the new module.
- Implements original per-edge ray-crossing branches in float (compiler `-ffp-contract=off`, no tolerance/epsilon) and original `IPTYPE` polygon-level preference/edge table.
- BLN reader preserves parsed order and the original type/source/id fields, enforces numeric finiteness, bounded file/polygon/vertex budgets and original domain overlap. Invalid/empty/wrong-domain BLN fails closed.
- Synthetic CTest validates points inside/outside, four special boundary levels, polygon order, clockwise/counterclockwise, zero-length segment, header parsing, wrong-window/invalid data, and standalone compatibility with D1 original `LUGRID` 52/55/54 rules.
- This is a **synthetic software candidate only**. It does NOT implement `COASTEXT`, does NOT read vendor original GSHHS binary, does NOT assume shapefile geometry equals the Fortran-extracted clipped BLN, does NOT integrate into the production P2-A GLCC source mesh, and does NOT claim Fortran bitwise equivalence or original full CTGPROC completion.

## Critical D4 scientific next gate (not automated)
1. Use original unmodified Fortran `COASTEXT` on the same Wolsong domain / model CRS to generate the **authentic original BLN**. Current Full f L1–L4 shapefile provenance alone is insufficient to claim input bit-equivalence with CTGPROC original GSHHS binary input. Require explicit matching source-version lineage or note unreconciled source representation.
2. With the **same original BLN** and same list of model-km REAL*4 sample points, obtain original Fortran `PNPOLY` and `IPTYPE` reference categories; compare C++ at *exact integer category level* at inland, ocean, islands, lakes, all boundaries, near-edge points and surrounding polygon corner cases. Never loosen the level agreement gate on numerical tolerance.
3. Compare D2 GEOS output to the exact-BLN REAL*4 pathway as a **diagnostic difference map**, not a substitute for authentic original Fortran output. If Fortran differs from the candidate, inspect GLOBE REAL*4 coordinates, polygon clipping/ordering, original PNPOLY compile flags, and F12.6 BLN formatting.
4. Only after the original same-input point gate PASS, integrate the accepted pathway with D3 opt-in GLCC trace recount into a **separate** explicit original-mode CLI and validate Fortran/C++ 38 integer HITS + printed fractions under manual science workflow.
5. All original scientific workflows remain `workflow_dispatch` user-manual; PR tests must stay synthetic. No change to P3 #46 or P6/P7.

### Acceptance level
On CI PASS only: `D4_PASS_SOFTWARE_COASTRD_BNL_PNPOLY_R4_SCOPED`. The following MUST remain `NOT_RUN`: authentic original Fortran same-BLN `IPTYPE/PNPOLY` parity, `COASTEXT` clipping parity and whole original CTGPROC `HITS/LU.DAT` equivalence. Issue #123 stays **OPEN**.
