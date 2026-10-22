# Issue #40 S4-R1c8d — genuine G24-driven first-hour native WATER

Date 2026-10-22. Baseline main `034865bd27331d576e05a220aef41315dfb43279`, merged #255. First actually source-computed NOAA first-hour G24 U/V/W and COMP third SURFVAR from merged #253/#254.

## Scientific gap solved or being tested

Earlier S4-N/O/P/Q separately established true original 63 WATER cells × 6 NOAA hours water Z0, USTAR, QH, EL, ZI, WS10, PGT, FCORI, and narrow scalar test-only C++ G35/G36/G37 reference parity, **but fed original Fortran WS10/U/V as reference inputs**; this did not make WATER in the native G14 physical chain. Merged #253 independently established actual first-hour source-only C++ G24 final U/V is numerically equivalent to original Fortran over all 82x85x9 cells. Merged #255 admitted exact genuine 6907 LAND/63 WATER immutable source partition, but no physical WATER.

This PR's `g53_real_source_g24_neutral_water_reference()` executes **the same frozen G37→G35→G36 kernels** on the **genuine computed G24 layer-1 U/V** and actual G41 source-only model, guarded by G52 original source ordinal, strict original `FCORIOL`, `CONSTW`, `ZIMINW`, `ZIMAXW`, `NOWSTA=0,ITWPROG=0,ICOARE=10,IMIXH=1` READCF and source geometry. Real-water pseudo-calm is NEVER made from missing observations. No original Fortran field is passed to native CLI. The next-stage PARTIAL results are separate from the G26B production actor and must not be committed as previous-hour G14 state. We explicitly deny unmarked source entry, malformed water mask, nonfinite G24 U/V, bad source clock, bad control values.

## Independent true original science gate

- Independent fresh pristine original six-hour CALMET 45-field baseline, 2SS (583140, 583210)+1US (58424), 2022-06-01 UTC, 82x85x9 63 WATER.
- Same pinned original vendor blob `437f43bb7f0e51a1919e56664663e1a046986ed0` instrumented *only a scratch write-only WATER trace* using the already audited S4N instrument. The fully recomputed trace **must leave all six-hour CALMET MET.DAT bytes unchanged** vs pristine original. Strict 378 records, 63 true cells at each of six exact source hours and same GEO.
- G53 generates the candidate for the **first original source hour** from real final G24, not trace data. A completely separate Python comparator checks all 63 real source WATER cells for `WS10,Z0,USTAR,EL,ZI,QH,WSTAR,WT`, including PGT D and ZICONV/ZICOLD=0. Frozen strict source-subset tolerances from earlier original standalone validations, e.g. WS10 abs 2e-4 m/s, USTAR abs 2e-8+rel 5e-5, ZI abs 5e-3 m + rel 5e-5, Z0 abs 1e-10+rel 8e-6, exact neutral zero WT/QH/WSTAR and PGT D. Any failure **blocks merge** and reports field/cell residuals.
- Pass may be recorded as `PASS_SCOPED_REAL_NOAA_G24_NATIVE_WATER_NEUTRAL` **only after exact-head Actions pass**. This would be the first real *native-final-wind-driven* partial WATER result, not a re-run of original-field-injected S4O/P.

## Explicit exclusions

Even if source-scoped pass, the shared G26B existing WATER rejection stays fail-closed. This PR doesn't execute real land G18A MIXHT, AVEMIX, WSTARR, TEMP3D, actual pre/post six-hour COMP causal history, full 45-field native P6F, #36 P7, wet deposition, Docker, S5. It does not validate WATERP, non-neutral WT, water observational station temperatures, or geographic FCORIOL>998. Source original/vendor and C1/C2 143h physics are unchanged.
