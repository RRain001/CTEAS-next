# Issue #123 D9 — authentic Wolsong GLAZAS LFINAL=F integer HITS oracle

Date: 2026-10-20. **SOFTWARE CANDIDATE — original science NOT YET ACCEPTED.**

## Exact source anchor

The original CTGPROC v7.0.0 at original CTEAS commit dfad99a78ed84d655e21411c9d25eb0d2583bf13, file ctgproc.for, uses:
- COMP GLAZAS branch, lines 2370–2515: raw historical GLCC source, MESHGLAZ=10, original GLOBE and LUGRID.
- LUGRID lines 4204–4288: 38-class indexed integers, LCOAST/T + LMARSWAP/T calls original IPTYPE; ocean gets IOCEAN55 except estuary54; landward 54/55 rejected.
- SVGRID lines 5301–5362: LFINAL=F writes exactly (2i5,38i5,a20) original HITS, and empty cells explicitly flagged Missing. **It does not write F6.3 fractions in this mode**; that is D10.

## Reused authentic data

- Frozen Wolsong grid 200x200, UTM52N, xrefkm 533.215, yrefkm 3942.629, dgridkm .100; official historical GLCC Eurasia IMG 156 MB and authenticated original GSHHG Full binary, original coast.bln extracted by D6B.
- The same original D6B workflow already uses LEGAL original GLAZAS, LFINAL=F, LCOAST=T, LMARSWAP=T, LMARFILL=F, IOCEAN55, MESHGLAZ=10. Do not secretly switch to GENERIC or a 2022 GLC raster.
- Original D6B report and real D8 original Fortran/native BLN zero-difference report **must both actually exist and pass SHA validation before D9 can be admitted**. No synthetic shortcut.
- The native candidate reuses the existing GLCC DIRECT LAEA source mesh and D7 original BLN recount on the same exact 200x200 grid, separate from GEOS and the frozen P2-B exact-area producer.

## D9 acceptance

1. Build the isolated native original-coastal-HITS C++ CLI; read exactly the real GLCC IMG and ephemeral original BLN. Emit candidate 40000 rows of 38 integer NGRID and per-cell sample counts, preserving zero-hit cells without fake ocean fill.
2. Independently read original LFINAL=F LU.DAT fixed I5 fields. This preserves 5-digit values adjacent without spaces and checks 40,000 row order, exact USGS38 category list, header format, 52N CRS, model bounds and each Missing/positive-count flag.
3. Compare exactly 200 x 200 x 38 = **1,520,000 integer fields**. Demand **zero integer differences**, zero different cell totals, and identical missing-cell count. Report source/control/native/output SHAs, totals and first 20 diffs only.
4. Read-only original/source data never uploaded. Only bounded original BLN provenance, D8 audit and D9 JSON summary may enter Actions artifacts. A scientific failure is recorded as failure, not changed to success by a parser fallback.

## Scientific limits / follow-up

- Actual original-vs-C++ Wolsong UTM52N coordinate projection accuracy is not inferred from the old Hefei UTM50N 50x50 D1 result. Difference may be genuine and require independent source-mesh coordinate diagnostics; no tolerance is introduced for INTEGER HITS.
- D9 does **not** establish D10 fractional LU.DAT, final ocean fill, P3/P6/P7 behavior, or nested Full L2–L4 coastal parity. One Wolsong original polygon is type 1.
- #119 GSHHG Full-only EXACT_AREA_V1 remains frozen; #123 remains OPEN until independent D8/D9/D10 science PASS and reviewed integration.
