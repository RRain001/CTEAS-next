# #42 S3-B2 — true independent original MAKEGEO parity on fresh Huoshan S3-B1

Date: 2026-10-20. Baseline `main@ae7dc698ca30e2024bad09cf3d67decf5debb6ad`, real source stage [PR #185](https://github.com/RRain001/CTEAS-next/pull/185) and true parent-asset/run manifest [Run #39398753099](https://github.com/RRain001/CTEAS-next/actions/runs/39398753099).

The new Huoshan UTM50N (100×100 @100m, `462.305/3501.570` km) scientific validation must be **separate** from earlier Wolsong UTM52N v3.2 original-science results. Do not copy old original `GEO.DAT` files or claim full P1–P5 S3 by passing this.

## Independent original reference

Rehydrate the same two authenticated source products at actual Git LFS bytes, verify the parent real WGS84 90m SRTM source SHA `913a082c79df74ff4189fec9d94b678618b395a6fb0a64ee94e14c532362eae4` and original 156MB historical GLCC SHA `4f2a1977d141e2040da4d36ec6a4826c5c960c84686eaf10f226f388cb3ab90a`. The original source is cropped at an integer pixel lattice with exact values/no interpolation to honor P1's existing full-raster memory cap; source/crop SHA retained. Freshly produce real P1 height and `TERREL.DAT`, P2-A original-style 38-class `LU.DAT`, P3 selected no-snow C++ `GEO.DAT` under exactly the same B-0 case/grid/UTC.

Then **independently check out** `RRain001/CTEAS@dfad99a78ed84d655e21411c9d25eb0d2583bf13` `engine/vendor/src/MAKEGEO_V3.2_L110401/makegeo.for`; source SHA `8c4fb11db36d4b976b54f470b7a06ce4e38ab09e934951b0e2c613bddc34e347`, separately compile original Fortran with GNU fixed-format original options, without connecting any C++ P3 code. Stage isolated `original_geo.dat` using **the newly produced actual Huoshan** P2-A `lu.dat` and P1 `terrel.dat` file bytes, not another site or stale reference. Change only original `MAKEGEO.INP` file/path cards, leaving physical controls unchanged. The original genuinely executes under independent process/scratch.

Use previously frozen independent `native_cpp/reference/compare_p3_makegeo_dynamic.py` on original 100×100 UTM50N and native P3. Its eight per-cell category/scalar printed fields must equal **80,000 / 80,000** exactly; native higher-precision CSV must lie within existing *predeclared* original print-format tolerances. No post-result tolerance expansion. Count original LU fixed-format 2 indices + 38 standalone fractions + terminal status to fail closed on malformed actual Fortran input.

Publish **only bounded JSON** with identical B-0, parent SRTM, child original-source-window TIFF, GLCC, original fortran source, original/native `GEO.DAT`, native LU/TERREL, and direct comparison report SHA. Do not publish the source TIFF, GLCC, proprietary vendor source/binary, original raw `GEO`, native raw `GEO` or fresh LU/TERREL bytes.

Expected status **only if every check actually passes**:
`S3_HUOSHAN_SELECTED_P3_ORIGINAL_MAKEGEO_80K_SCIENCE_PASS_SCOPED`. It qualifies this new Huoshan supported no-snow 38→14 P3 physical branch, **not** original P1 terrain or P2-A GLAZAS new-site numerical parity, other MAKEGEO physics options, arbitrary stations or real `UP.DAT/SURF.DAT`. Exact Huoshan original P1/P2 scalar parity would require separate original TERREL/CTGPROC dynamic comparisons, although S2 established their selected options on separate authentic grids.

**#42 remains OPEN.** New Huoshan true NOAA 2022 IGRA/P4 and ISD/P5 `UP/SURF` plus native G19 source parser are not run. #40/#36 P6/P7 science, #161 capacity and Docker all remain deferred/outside.
