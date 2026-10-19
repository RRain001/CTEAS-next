# Issue #123 D10 — real Wolsong original LFINAL=T LU.DAT F6.3 and missing-flag oracle

2026-10-20. Strict *science not preaccepted*. Depends on real [Run #39342829412](https://github.com/RRain001/CTEAS-next/actions/runs/39342829412) D8+ D9 authentic accepted artifact [#12229428757](https://github.com/RRain001/CTEAS-next/actions/runs/39342829412/artifacts/12229428757).

## Anchors
Original CTGPROC v7.0.0 `ctgproc.for` at fixed original CTEAS Git commit dfad99a78ed84d655e21411c9d25eb0d2583bf13: `LUGRID` increments USGS38 source HITS; `SVGRID` original code at lines 5314–5362 emits either `(2I5,38I5,A20)` when `LFINAL=F`, or `(2I5,38F6.3,A20)` when `LFINAL=T`. If `LMARFILL=F`, zero-HITS cells display zero fractions and `Missing` flag, not fabricated ocean hits.

## Genuine original scientific gate
- Reuse same SHA-pinned original vendor code/executable and genuine GLCC + GSHHG Full inputs as D6. Reuse same 200x200 Wolsong UTM52N control; change **only one active `LFINAL` control from F to T**. Do not use GEN, generic GLC, geospatial shapefile approximations or user-provided substitute data.
- Create a **second original CTGPROC run**, independent of earlier `LFINAL=F` original output, in ephemeral runner scratch. `LBLNREAD=F` triggers true original `COASTEXT` again; generated `coast.bln` must match original D6 BLN SHA **byte-for-byte**.
- Hard-gate input and D6 original BLN SHA plus D8 zero-difference Fortran `IPTYPE` and D9 **1,520,000 integer fields zero-difference** reports, original binary SHA, grid/unit/class header, and exact one-card control difference. Recheck actual original F and T headers and all rows.
- Compare all **1,520,000 original F6.3 three-decimal fractions** with C++ D9 original-BLN HITS, using exact source `NGRID/FLOAT(ISUM)` REAL*4 behavior and requiring identical 3-digit printed fields. For original missing cells, require zero fractions and exact original `Missing` flag, without inventing counts or using LMARFILL. No numeric tolerance.
- Archive only bounded JSON SHA provenance and mismatch statistics; keep original GSHHG/GLCC inputs, BLN, original `LU.DAT` output and executables private in ephemeral CI scratch.

## Limitations
A passing D10 scoped science run establishes original GLCC GLAZAS Wolsong source/coast physics selected options and 38 F6.3 outputs with missing flags. It **does not** establish `LMARFILL=T`, other nested levels not actually present, all original CTGPROC selectable dataset branches, or completed production-mode C++ `ORIGINAL_SAMPLING` `LU.DAT` v2.1 writer integration. Continue #123 OPEN until post-D10 integration/acceptance is separately done. Do not modify frozen #119 `EXACT_AREA_V1` or the user's GSHHG Full-only selection.
