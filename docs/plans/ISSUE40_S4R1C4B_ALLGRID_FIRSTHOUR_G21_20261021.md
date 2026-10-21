# Issue #40 – S4-R1c4b: independently verify the real first-hour **whole-grid** G42/G21 wind and temperature

Baseline: `main@02da396393bcd404260e60dc3d52a05bd0b14d95` (after merged #242). Input NOAA original 2022-06-01 UTC 01→07, real 583140/583210 2SS, 58424 1US, 82×85×9 UTM50N. Original genuine GEO contains 63 WATER (IWAT 50..55) and 6907 LAND cells; inputs are produced afresh on Actions from the verified original P1–P5 chain.

## Why this increment

R1c1 #239 independently compared 63 WATER cells **first hour** WIND1 U/V, post-FRADJ U/V, original two SURFVAR temperatures; R1c3 #241 compared **all 6970** native/original surface heat/air density/stability values in first hour; R1c4a #242 compared six consecutive hours of **WIND1 only** for the 63 real WATER cells. None independently compared **all 6970 first-hour** original-vs-native WIND1/FRADJ U/V and first/second SURFVAR temperature in one dense grid audit. Nor do those scoped results validate six-hour G21/G39 causal state and previous-hour ZICONV.

## What this PR does

- Add **new test-only G46** source-backed first-hour all-grid exporter. Calls existing G44 and reads native G42 WIND1 U/V, G21 post-FRADJ U/V and two native SURFVAR temperature fields. G43 model-internal MISSFC is computed in a detached copy by frozen source algorithm; no P5 wind, static station observation, invalid pressure, or raw station timestamps are altered. G39 remains the separately accepted first-hour kernel. The exporter cannot commit G14 or return a G24/G26 state; callers lacking explicit one-hour test-only flag fail closed.
- Add scratch-only Fortran original CALMET source instrument pinned to original `calmet.for` git blob `437f43bb7f0e51a1919e56664663e1a046986ed0`. Records the same 6970 `UG,VG,TEMP2D` cells directly after original first SURFVAR and second SURFVAR at original 2022-06-01 02 UTC, not the rest of six hours. Its six-hour 45-field `CALMET.DAT` must be SHA-byte-identical to **untouched** separately compiled original. The native G46 consumes only original NOAA source files, **never** the Fortran trace, original MET or original U/V.
- Perform exactly `6970*6=41820` native/original field comparisons with explicit 63 WATER and 6907 LAND stratified maximum error and worst cell. Freeze prior R1c1 0.05 m/s absolute WIND1/FRADJ and 0.05 K temp limits. Do not relax thresholds in response to test failure.
- Exact-head real Actions workflow builds source and original from authenticated original input chain. Keeps existing Hefei, multi-site and selected SOURCE regressions; no vendor/DEM binaries published.

## Scientific acceptance conditions

Only if exact-head Actions and original-vs-native 41820 comparisons pass, classify `PASS_SCOPED_REAL_FIRST_HOUR_FULL_GRID_WIND1_FRADJ_SURFVAR`. The accepted R1c4a six-hour WIND1 is **not** promoted to six-hour G21/FRADJ or thermal.

Still **NOT_ACCEPTED**: source-history previous ZICONV/ZI across six continuous completed G14 hours; water WATER USTAR/EL/ZI; final G23/G24 physical U/V; G26 complete 45 fields × six hours; arbitrary model configurations and P7. Issue #40 remains open. Subsequent R1c5 must establish a causal source-computed native hourly state before six-hour thermal output can be claimed.
