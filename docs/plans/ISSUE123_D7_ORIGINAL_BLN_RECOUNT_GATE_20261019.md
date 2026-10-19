# Issue #123 D7 — source-faithful BLN/REAL*4 point recount candidate

## Scope

This is an **isolated C++ software candidate**, not full CTGPROC parity and not a production entrypoint. It follows D4's original-Fortran PNPOLY synthetic same-input result (568 cases, zero mismatches) and the D6 original real-BLN preparation work.

- Preserve #119 frozen `EXACT_AREA_V1`, GSHHG v2.3.7 **Full only**, unchanged P2-A source-hit producer, P3 and P6/P7.
- Reuse existing P2-A original GLCC/GLAZAS `diagnostic_mesh` projected single-precision coordinates and assigned cells; do **not** introduce a new grid or point interpolation rule.
- Add a *separately named*, opt-in `recount_glcc_original_coast_bln` using D4 `OriginalBlnIptypeR4` (original COASTRD BLN ordering and REAL*4 PNPOLY), rather than the D2 Shapefile/GEOS classifier.
- Share only the existing `LUGRID`/ `SVGRID` integer-hit bookkeeping between routes. Retain D2 as an explicitly diagnostic surrogate; its agreement is not an original-science gate.
- Reject missing original BLN classifier for `LCOAST=T`; `LCOAST=F` must still reproduce baseline P2-A counts exactly.
- Preserve actual 38 USGS categories, the estuary 54 exception, marine swapping, landward 54/55 rejection, distinct 52/55 hits, empty-cell `LMARFILL` as **display only**, and no fabricated samples.

The new regression checks an exact land polygon boundary (L1 -> ocean 0), mixed freshwater/marine hit counts, source-count conservation and empty-cell fill, entirely on synthetic polygons. It runs under the existing D3 software-only GitHub Actions job; success is `D7_PASS_SYNTHETIC_ORIGINAL_BLN_RECOUNT_CANDIDATE` only.

## Mandatory authentic science gates (NOT_RUN)

1. Obtain a **real** original `COASTEXT` BLN for the frozen Wolsong 200x200 @ 100m UTM52N grid from the SHA-pinned original GSHHS Full binary and legal GLCC/GLAZAS. Verify actual original `coast.bln` bytes, source provenance, polygon order/IDs, coordinates, closure and model overlap. GNU STREAM/EOF adapters are byte-audited I/O derivatives, **not** an unmodified original run.
2. Feed that exact BLN and exactly matched single-precision point records to **original Fortran IPTYPE** and D4 C++ `OriginalBlnIptypeR4`. Require zero type differences, including boundaries, near-edge and artificial enclosing polygons. Do not substitute GEOS or an unpinned independent Shapefile extraction.
3. Wire the opt-in D7 BLN recount behind an explicit `ORIGINAL_SAMPLING` CLI with original-source SHA and mode provenance. Compare original Fortran `LFINAL=F` **38-class integer HITS for every cell** (including empty), then `LFINAL=T` exact formatted `LU.DAT` values/missing flags. Verify original row order, `F6.3` output rounding, `LMARSWAP`/`LMARFILL` combinations, and legal input fail-closed.
4. Require no regression in frozen #119 `EXACT_AREA_V1`. Do not mark issue #123 closed or claim `PASS_SCOPED_ORIGINAL_PARITY` before gates 1–3 are independently evidenced.

## Original source oracle

`RRain001/CTEAS@dfad99a78ed84d655e21411c9d25eb0d2583bf13`, `engine/vendor/src/CTGPROC_v7.0.0_L150211/ctgproc.for`: `LUGRID`, `SVGRID`, `COASTEXT`, `COASTRD`, `IPTYPE` and `PNPOLY`. Byte-pinned original Fortran source SHA256: `719abbd2327269bb0377208b3a7a0c74000b878efc756686023bbb2ef932f281`.
