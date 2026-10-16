# TERREL P1: independent 100 m Hefei reference audit

Evidence date: 2026-10-10. Baseline `60b7b1d93866fff772926b6ac32dc0af7235552b` (P1 branch starts here), vendor main `66e30ffb1ff4638a97af8a060748ce30b7578350`. This file documents **P1 only** and does not change any P4/P5 or shared headers.

## Reference identity
- Original Fortran `engine/vendor/src/TERREL_v7.0.0_L141010/terrel.for`, untouched. `LOADTIFF → SAVEELEV → CELLIND → CELLDAT → HEIGHTS → MODOUT` is the verified scoped path.
- Original execution in [GitHub Actions P1 run #2](https://github.com/RRain001/CTEAS/actions/runs/38043771518) and [strict mean comparison run #3](https://github.com/RRain001/CTEAS/actions/runs/38043842965) on github-hosted Ubuntu 24.04; no self-hosted runner or SSH used.
- `TERREL.DAT` v2.0 SHA-256 `d74a5a1045ea4cf25e120099196a3962ab012aaebdf37354ec8264fad0e27678`; `TERREL.SAV` original Fortran unformatted SHA-256 `5b09c27974eb5e77e3a0fc2126836e0c46f57a3558da5e1083930bcb6267cd74`.
- Crop 90 x 77 SRTM points (6,930 source elevation samples, no NoData), WGS84 geographic; original source extraction accepted 3,456 projected terrain points inside the 50 x 50 (100 m) UTM50N grid. `IGRID=1`, grid origin is SW corner of cell (1,1), x0 and y0 from pinned crop metadata. P1 uses average elevation (not peak), `LVOIDFIL=F`, no coastline processing.
- Original `TERREL.DAT` grid output is north-to-south within its file, whereas C++ internal terrain is south-to-north with x fastest; independent comparator reverses the text record rows before testing. Binary save uses the internal south-to-north order.

## Fortran fidelity of float conversion
The initial C++ approach used standard GDAL/PROJ UTM and divided projected metres by exact 1000. It correctly counted 3,456 input pixels but differed from original in 10 **cell** counts and 10 formatted terrain heights (3.0 m maximum). This failure was preserved in the first CI and not hidden by a tolerance change.

In `COORDLIB` (vendor original `coordlib.for`, `COORDS`), `XMULTO = 0.001` is stored as implicit `REAL*4`. `CRDIO * DBLE(XMULTO)` uses the **single-precision** value `0.0010000000474974513`; `GLOBE` then converts the km result to `REAL*4`, while `LOADTIFF` multiplies that by 1,000 for `SAVEELEV`. The C++ P1 dedicated source reproduces precisely this scoped floating-point contract. A standalone diagnostic invocation of original `GLOBE` versus C++/PROJ yielded exact float32 projected km values for **6,930 / 6,930** source pixels after emulating that factor. This diagnostic used a separate read-only vendor source driver, not a rewrite of Fortran.

## Independent original-vs-C++ comparisons

| Gate | Original | C++ | Result |
|---|---|---|---|
| Input raster | 90 x 77; 6930 source pixels | identical committed crop | PASS |
| Accepted source pixels | 3456 | 3456 | PASS |
| Exact integer hits per cell | 2500 cells | 2500 matching | PASS |
| Invalid/missing output cells | 0 | 0 | PASS |
| TERREL.DAT heights (F8.1) | 2500 floats | 2500 matching at displayed precision | PASS |
| Unrounded mean from TERREL.SAV | 2500 REAL*4 sums/counts | 2500 C++ float32 averages | PASS |
| Mean: max abs error | — | 1.271333339047942e-6 m | PASS |
| Mean: MAE | — | 5.085333356191768e-10 m | PASS |
| Mean: failure denominator | — | 0 / 2500 above fixed 1e-5 m | PASS |

No tolerance was loosened after running the comparator. The formatted output has a prespecified 0.0500001 m readout tolerance due to `F8.1`. The independent unrounded mean check uses a stricter **0.00001 m** bound. Reference artifacts are retained by Actions for seven days; archive them permanently before expiration for science reuse.

## Explicitly unsupported / not validated
- Other projections/zones/datums/GeoTIFF types, alternative source elevation formats and multi-tile blending.
- Source NoData semantics, void/noise/replacement algorithms, `LVOIDFIL`, peak heights, coastline, snow, polar/receptor data paths. The implemented P1 path **refuses** source NoData rather than inventing elevations or silently dropping points.
- Bit-for-bit equivalence for every machine/compiler/optimization; multi-platform repeatability has not been audited.
- Standalone writer equivalence for every original TERREL mode; current verified contract is cell-level numerical terrain, not full option coverage.

Classification: **PASS_REFERENCE_SCOPED_P1_GEOTIFF_UTM50N_HEFEI_100M**, NOT `P1_FULL_PROGRAM_PASS`. Independent human/code audit remains required before PR merge.

## Study-specific submission decision (2026-10-10)

The user explicitly accepts **minimum reconstruction for the 5 km × 5 km Hefei 50 × 50 @ 100 m study**, not full original TERREL option coverage. All unsupported original routines and controls are itemized in `docs/reconstruction_cpp/P1_P2_MINIMAL_SCOPE_FEATURE_MATRIX.md` (P3 PR #5), with source reference to the untouched original Fortran. This PR is submitted for **independent review** of the scoped numerical result. Neither byte-identical standalone `TERREL.DAT` file writing nor end-to-end modern P1/P2→P3 integration or downstream CALMET consumption is claimed. No main merge is authorized by this scoped submission statement.
