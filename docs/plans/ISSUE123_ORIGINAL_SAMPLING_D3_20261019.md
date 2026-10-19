# Issue #123 D3 — official Full L1–L4 provenance and opt-in original point recount (2026-10-19)

## Immutable predecessor
User accepted #119 as `P2B_EXACT_AREA_V1_FROZEN_PASS_SCOPED_WOLSONG_2022`, fixing the modelling baseline to **official GSHHG Full f L1**, not High. D3 does NOT change this algorithm, GLC2022 data, GLCC production route, source datum projection, existing production LU.DAT, or the P6/P7 options.

## D3 scoped implementation (no original science claim)
- `scripts/s2g/gshhg_full_hierarchy.py`: requires the existing official archive SHA-verified GSHHG v2.3.7 ZIP and the already pinned/verified f L1 cache. Restores **Full f L1/L2/L3/L4**, each `.shp/.shx/.dbf/.prj` with independent SHA256 comparisons against bytes in that **same verified official ZIP**. Stores `verified_gshhs_full_l1_l4.json` containing all 16 immutable sidecar hashes and file sizes. No High, no network, no redistribution of source shapefiles. Missing, duplicate, unsupported, non-shapefile or corrupted layers are fail-closed. Existing L1 files are not silently replaced.
- `native_cpp/include/cteas/geo/ctgproc_original_sampling_recount.hpp` + `src/geo/ctgproc_original_sampling_recount.cpp`: **standalone non-production C++ library** consuming the existing P2-A original GLCC/GLAZAS `GlccRawResult.diagnostic_mesh` and pre-existing assigned `i,j`/REAL*4 model `x_km,y_km`. It reuses **rather than reconstructs** the GLCC source mesh/projection/assignments. In opt-in coastal mode, D2's nested Full L1–L4 `IPTYPE` candidate supplies 0–4, D1 coastal policy maps per original `LUGRID`: marine 54 remains 54, other marine classes become IOCEAN, landward 54/55 discarded. NGRID and ISUM are *integer per-sample counts*. When `LMARFILL` is on, empty marine cells get **a separate display-only IOCEAN fraction** with no invented sample hits.
- The same recount with `LCOAST=false` requires **exact integer equality** to the P2-A input counts/samples/included/outside; failure is fatal. Invalid coast options, missing D2 point classifier, incomplete mesh trace and inconsistent counts fail.
- This library is **not attached to the existing production CLI**. A future separately approved original-sampling CLI can call it after explicit authenticated source verification. There is no implicit change to old P2-A or P2-B runs.

## D3 synthetic CI and authentic-source manual gate
- [Synthetic D3 PR CI](https://github.com/RRain001/CTEAS-next/actions/workflows/issue123-original-sampling-d3-ci.yml): D1 + D2 + D3 CTest, plus ZIP-member selection/negative-test contracts. No authentic GSHHG download, no original Fortran science, no GLCC 156 MB authentic runs.
- [Manual authentic Full-only source validator](https://github.com/RRain001/CTEAS-next/actions/workflows/issue123-original-full-source-manual.yml): **workflow_dispatch only**, fetch pinned official ZIP/released SHA and run L1–L4 16-sidecar equality verification. Artifact contains SHA manifest only; source binary is never uploaded. User must trigger manually; no science run is implied.
- Authentic source verification **not run** until the manual workflow finishes on merged main; C++ parity with original Fortran **NOT_RUN**.

## Mandatory future gates — still #123 OPEN
1. Authenticate real v2.3.7 **Full f L1–L4** in manual-only CI; pin exact 16 individual SHA256 values and archive SHA from artifact. This proves bytes, **not** original scientific parity.
2. Compare Fortran `COASTEXT/COASTRD/IPTYPE/PNPOLY` polygon selection, nesting, coastline edge cases and original spherical/datum conversion against D2 C++. Original Fortran uses REAL*4 PNPOLY and some artificial enclosing polygons; GEOS `Touches/Within` is a **semantic surrogate** and may differ close to a boundary. Fully validate before enabling production.
3. Bind this new library behind an explicit, SHA-gated original sampling CLI; use existing genuine GLCC P2-A source mesh/HITS and legal non-GENERIC+LCOAST source. Ensure exact original LFINAL=F per-cell 38-category integer HITS and LFINAL=T printed fractions; do not relax tolerances or confuse counts with 30m GLC area.
4. Expand to documented original option matrix, additional legal source/datum cases, real inland/coastal cases; all real scientific workflows **manually triggered only**.
5. P3 MAKEGEO real Wolsong Fortran/native output remains separate (#46).

## D3 result syntax
`D3_PASS_SYNTHETIC_RECOUNT_AND_PROVENANCE_CONTRACT` means software only. It never grants `PASS_FULL_ORIGINAL_CTGPROC_PARITY` nor changes `EXACT_AREA_V1_FROZEN_PASS_SCOPED`.
