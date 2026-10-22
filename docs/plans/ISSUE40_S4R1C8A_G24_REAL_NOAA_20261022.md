# Issue #40 S4-R1c8a — authentic real NOAA post-INTER2 G24 first-hour tail

Date: 2026-10-22. Parent #252 original-vs-native real first-hour INTER2 post-field passed 125460 comparisons, worst |Δ|=1.1921e-7 m/s, merged `main@46f88e4bca5887b1849bf82a0b0d00aba99d1cd1`.

## Physical path

The existing source-selected `g24_selected_original_wind_tail` originally accepted only `G19FileBackedCase` for the all-LAND selected C1/C2 route, while real source with 63 WATER cells is `G41SelectedNoowWaterFirstHourSource` and `G19SourceClockCase`, intentionally non-convertible. Do not cast or bypass those source gates. This PR factors only the **single existing** selected tail arithmetic into `g24_selected_original_wind_tail_from_g16` and retains the full G19 geometry/clock/matrix checks in its original wrapper.

On authentic NOAA 2022-06-01 six-hour 2SS+1US, 82×85×9 mixed 6907 LAND/63 WATER source, G50 uses the existing G48/G42 source and G47 post-SLOPE plus the accepted shared G16 INTER2 and masked G17C3 native STHEOR. It passes **only** same-native-hour G16 INTER2 field arrays, immutable first WINDBC snapshots, source ZFACE and NSMTH to the **same frozen `p6::original_smooth_divcel_w`** kernel used by the all-LAND G24 wrapper. The second WINDBC is formed from post-INTER2 U/V exactly as the selected original HTFAC>0 branch. G50 is opt-in and emits a temporary raw REAL4 U/V/W/DIV/UB/VB diagnostic; G26 writer and COMP scheduler are not entered.

## Independent original source

A separate SHA-pinned original vendor `calmet.for` (blob `437f43bb7f0e51a1919e56664663e1a046986ed0`) is instrumented with **only a write-only trace after original DIAGNO L6119–6148** (the real SMOOTH/DIVCEL/W sequence). Original P1–P5 decks, original formulas and MET writer unchanged. Re-run all six original NOAA hours from the same untouched source reference; require instrumented `MET.DAT` byte identical to completely pristine original six-hour 45-field `MET.DAT`. Capture six ordered original U/V (9 layers), W (10 faces), divergence (9 layers), and UB/VB boundary values. The stage-specific six-hour trace is private to the workflow, never an input to native C++ or an uploaded raw scientific field.

Independent Python compares the **first** original source hour against native full grid for all six groups. Frozen tolerances: U,V,W and boundary `2e-4 m/s`; DIV `1e-6 s^-1`. Every value finite, all components/clock/source SHA pinned, no greater-than-tolerance residuals; report per-field maximum and mean, counts, first mismatches. If this science check fails, keep Draft and diagnose rather than relaxing thresholds or manufacturing original wind values.

## Limits

Passing would establish `PASS_SCOPED_REAL_NOAA_ORIGINAL_NATIVE_G24_FIRST_HOUR` **only** for the original-selected no-lake, IOBR=0, HTFAC>0 first-hour DIAGNO tail. This is not an entire native hour: it cannot accept 6h causal COMP/ZI/ZICONV, 45-field G26, #36 P7, wet deposition, S5 or deployment. Neither the original Fortran nor C1/C2 frozen 143h numeric physics may be changed. Keep both issues open until true full chain.
