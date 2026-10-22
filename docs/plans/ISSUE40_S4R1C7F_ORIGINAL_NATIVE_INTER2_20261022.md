# Issue #40 S4-R1c7f — genuine NOAA original-vs-native INTER2 3D science gate

Date: 2026-10-22. Base `main@b97c17a8a279a8000d48c6e7c6d6487ddba2194a`, after independent source/station/G16 gates #249–#251 passed and merged.

## No alternative physics solver

Reuse the **same shared G16** selected WIND1/INTER2 and G17C3 STHEOR kernels (no new INTER2 formula), with real source-owned G42/G47 outputs and source-valid station IDs, not the all-LAND-only G19 full-case adapter.

The source is genuine 2022-06-01 NOAA 2SS+1US, 82×85×9, 63 WATER, 6907 LAND, 6 source hours. This PR only targets **first-hour 9-level grid post-original two-INTER2 calls**:

1. G41/G43 genuine P1–P5 SURF/UP/GEO and original model-internal MISSFC; P5 raw observed wind masks and values are immutable.
2. G42 real WIND1, independently checked against shared G16 at full 9×6970 U/V in merged #251; default G16 admission still rejects source-invalid wind.
3. G47 full 9×6970 post-FRADJ, HEATFX/ELUSTR and SLOPE accepted residual vs source in merged #248 (no original post-INTER2 U/V injection).
4. G17C3 independent valid SS source STHEOR/MIXHTST/SIMILT from #248; merge back into the **same SS1, SS2, US1** columns with the explicit binary source wind-valid mask, retain missing columns and PREPDI US without fake calm (#250).
5. Same G16 stage object's `provide_post_slope` → `provide_selected_diagi_after_wind1` → selected `DiagnoInter2` with source READCF interpolation radii, WATER versus LAND classification and layer NINTR2.
6. A new strictly opt-in `cteas_p6g_g49_real_sparse_inter2` diagnostic outputs the candidate **native** 2×82×85×9 REAL*4 U/V to a temporary binary, *never* a CALMET MET/forecast. It accepts no Fortran oracle data as CLI input.
7. Independent Python reads the pinned original six-hour scratch write-only `#249` post-INTER2 binary (tag 52 and 2022-06-01T01:00Z clock) and the native candidate. Its original-reference SHA must exactly equal the attested original report. Compare all 125,460 components at frozen **2e-4 m/s maximum abs** tolerance; report per-level residuals and first worst grid cell. Result is fail-closed `PASS_SOURCE_SCOPED_REAL_NOAA_NATIVE_G16_INTER2` only if **zero** exceedances.

## The strict scope

This is the **first actual original-vs-native INTER2 full-grid diagnostic** on this new mixed WATER / LAND site; earlier PASS of STHEOR one station, WIND1 and SLOPE does **not** imply the interpolation is correct. The PR stays Draft on any numerical failure and the residual report is the first debugging guide.

A successful test is only source-scoped **first hour post-INTER2 U/V**, not the complete DIAGNO tail (post-interpolation second WINDBC, SMOOTH, DIVCEL/W, possible lake branch), not six consecutive causal G14 COMP ZI/ZICONV, not G26 45-field MET, P7 or S4 closure. No Docker or wet deposition. Do not touch third-party vendored source, source P5 records, full original-forcing validator, or C1/C2 frozen physics.
