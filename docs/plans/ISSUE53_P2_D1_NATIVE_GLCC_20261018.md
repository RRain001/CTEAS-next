# Issue #53 P2-A: direct-LAEA production default; historical GEN comparison only

## Status update (2026-10-19)

The *selected production* direct-LAEA D1→D3 calculation passed the
unmodified CTGPROC original GLAZAS LFINAL=T/F comparison in
[manual Run #39188861410](https://github.com/RRain001/CTEAS-next/actions/runs/39188861410)
on `main@5e6fbb33`: exact **95,000/95,000 integer HITS**, zero fraction
difference for another 95,000 class fractions, total original/native
HITS **10,013/10,013**. Scientific verdict is scoped to the official
Eurasian GLCC original 156MB source, the Hefei UTM50N 50×50 100m
MESHGLAZ=20 configuration, and explicit original-Fortran comparison.
A matching computation for any other footprint, UTM zone, mesh or
fractional grid spacing **does not inherit that scientific verdict**.

The production D1 CLI now defaults to Direct LAEA (formerly explicitly
`--production-direct`); `--production-direct` remains an accepted alias.
Only the old, non-parity GEN seven-decimal geographic replay requires
`--gen-replay`. These options are mutually exclusive.

```bash
cteas_p2_glcc_raw eausgs2_0la.img out-direct 32650 510.885 3531.269 0.100 50 50 20
cteas_p2_glcc_raw eausgs2_0la.img out-old-gen 32650 510.885 3531.269 0.100 50 50 20 --gen-replay
```

Direct outputs: `p2_glcc_usgs92_direct_laea.csv`,
`p2_glcc_usgs92_hits.csv`, SHA-bound `p2_manifest.json`.
GEN outputs: `p2_glcc_usgs92_gen_replay.csv` plus its
independently produced `p2_glcc_usgs92_hits.csv`; manifest method
unambiguously identifies either method. The manual original GLAZAS
workflow retains the explicit compatibility alias; the separate
Python-GEN comparison workflow explicitly invokes `--gen-replay`.
Real original-source science is deliberately **manual-only**.

## Multi-region WGS84 UTM engineering extension (pending original science)

Direct-LAEA D1 and D3 now accept **WGS84 UTM EPSG:32601–32660 and
EPSG:32701–32760**, subject to original Eurasian GLCC source coverage,
source window checks, mesh-point and 50-km footprint budgets, and valid
coordinate transformation. Other datums/projections, LFS pointers,
uncovered GLCC locations and output overwrites still fail closed.

For an example northern region (Japan, UTM54N) or southern one (Sumatra,
UTM47S), the command form is the same as for Hefei, using the site's own
WGS84 UTM zone, exact three-decimal-km origin, spacing, dimensions,
and MESH count:

```text
cteas_p2_glcc_raw eausgs2_0la.img out-japan 32654 XREFKM YREFKM DGRIDKM NX NY MESH
cteas_p2_glcc_raw eausgs2_0la.img out-sumatra 32747 XREFKM YREFKM DGRIDKM NX NY MESH
```

For EPSG:32650 direct output the historical 50N method tag is retained
to keep the frozen Hefei provenance verifiable. For **all other**
WGS84 UTM zones the D1 and D3 manifests use
`GLCC_HEADERLESS_LAEA_DIRECT_WGS84_UTM_REAL4_GLOBE_LUGRID`,
distinct from the science-compared Hefei tag
`GLCC_HEADERLESS_LAEA_DIRECT_UTM50N_REAL4_GLOBE_LUGRID`.
Every unreviewed output's `evidence_status` remains
`PRODUCED_UNVERIFIED`, `official_GLAZAS_parity=NOT_RUN` and
`P3=NOT_RUN`. `original_science_scope` distinguishes a case *eligible*
for the frozen Hefei manual scientific comparison from other grid
configurations. It is not an assertion of scientific acceptance.

The independent authentic-original `validate_p2_glazas_hits` comparator
is now restricted not merely by EPSG/50x50/MESH=20 but also by Hefei
`XREFKM=510.885`, `YREFKM=3531.269`, `DGRIDKM=0.100` to prevent
false original-parity inheritance. Additional region/mesh/hemisphere
smoke tests use **synthetic GLCC-layout bytes**; they establish
software execution and numeric conservation only. Per-region unmodified
original CTGPROC `LFINAL=T/F` replays, projection-edge HITS and source
coverage proofs are still required for original-parity certification.
No default hidden science test is started. This is **not** validation of
30m GLC_FCS30D category crosswalk (still
`P2_MAPPING_REVIEW_REQUIRED`), P3 or G5.

## Historical implementation notes

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
