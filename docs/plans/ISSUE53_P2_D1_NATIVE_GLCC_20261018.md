# Issue #53 P2-A D1: native original-layout GLCC IMG — scoped GEN-replay stage

This is a **software implementation and independent comparison**, not automatic certification of original CTGPROC GLAZAS or complete P2 science.

## New executable and input authority

```text
cteas_p2_glcc_raw eausgs2_0la.img NEW_OUTPUT_DIRECTORY EPSG XREFKM YREFKM DGRIDKM NX NY MESH
```

- Reads **original 156,000,000-byte** Eurasia `uint8` headerless `.img` directly with 13,000 columns × 12,000 rows, north-to-south file row order and 1-based GLCC `i,j` indices. Supports a bounded WGS84 UTM N/S profile from the existing #42 common authority; old fixed Hefei GEN CLI stays unchanged.
- Production CLI hardcodes official source SHA256 `4f2a1977d141e2040da4d36ec6a4826c5c960c84686eaf10f226f388cb3ab90a`, confirms full file length, blocks LFS pointers and source symlinks, and requires a fresh output directory. **No caller-supplied override of official SHA** exists in production. Synthetic test driver is deliberately separate.
- Uses source `0` as no-class/skip, `16` as USGS-92 `52` water. Only raw 1–24 map to the historical 38-class category order. Invalid raw values, short reads, invalid UTM, source bounds, antimeridian, large unreviewed grids, over-budget mesh and no included samples fail closed.
- Window: 3×3 UTM grid points projected to original spherical LAEA plus fixed 1.5 km margin, identical to currently selected Python source-only path. The **window coverage proof for wider/strongly curved domains has not been established**; implementation rejects footprints above 50 km side rather than claiming unrestricted geography.
- Two-step projected point placement intentionally follows **Python GEN seven-decimal lon/lat → Fortran REAL*4 → original P2 XMULTO/index rounding**. It is **not** the original direct GLAZAS LAEA-to-GLOBE sequence. No new area-intersection rule has been introduced into historical GLCC sampling.

## Outputs and evidence discipline

`p2_glcc_usgs92_gen_replay.csv`: `i,j,samples,cat11,...,cat92` 38 fixed columns, j outer/i inner, 1-based. Empty cells are explicit `MISSING` and will not be silently converted to water or zero fractions. Counts and point-normalized fractions are **not physical area statistics**, unlike D2 GLC 30m results.

`p2_manifest.json`: source/product/SHA/size, EPSG, canonical 3-decimal origins, grid/mesh, 1-based source window, raw 0–24 histogram, inside/outside count, `PRODUCED_UNVERIFIED`. Explicit `official_GLAZAS_parity=NOT_RUN`, `lu_dat=NOT_RUN`, `p3_geo_dat=NOT_RUN`. B-1 binding of immutable case/grid/time/source/output SHA and peer attestation remains #42.

## GitHub Actions acceptance tiers

1. **Automatic PR software only**: C++ strict native build; synthetic sparse original-size 156MB binary with source 0, 1, 2, 16, 18 in real north-to-south layout; independent existing Python GLCC GEN extraction with *synthetic* SHA; compare the existing GEN C++ fraction CLI vs new C++ original-row direct reader. Verify 2500 cells, identical sample counts, 38 columns, `MISSING` mask and declared fraction absolute tolerance ≤0.0005. Negative pointer/invalid-class cases.
2. **Manual `workflow_dispatch` only**: actual 156MB Git LFS checkout and official SHA, native read and same-source Python GEN comparator, preserve only SHA/provenance artifact. This is real historical-source **and selected GEN equivalence**, not original GLAZAS numeric parity. Full historical vendor/original comparison and independent source controls are still needed before science acceptance.
3. **Unfulfilled**: original direct CTGPROC GLAZAS on same authentic GLCC, matching `MESHGLAZ`, datum, coast/polar controls and 2500×38 `LU.DAT` with independent original point counts, max absolute difference ≤0.0005 and first-difference report. Do not infer equivalence from a synthetic or Python GEN run.

## Blocking follow-ups

- D1 original-GLAZAS scientific parity remains **BLOCKED** pending same-source original vendor runner, real LFS and provenance.
- D2 GLC_FCS30D 30m raw-area software was merged as PR #60; GLC35→USGS-92 candidate crosswalk including 183/190/182/210 remains **P2_MAPPING_REVIEW_REQUIRED**. Do not generate an approved LU.DAT from GLC raw fractions.
- D3 unified P2 fractions/LU.DAT original-format serializer and #46 new-site P3/MAKEGEO handoff remain open. Do not create any GEO.DAT or touch P6/P7.

This scoped stage alone is **not** a reason to close #53.
