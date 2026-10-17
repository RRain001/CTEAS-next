# P6D — isolated CALMET SLOPE kernel: implementation and acceptance boundary
Date: 2026-10-11. Target: original CALMET v6.5.0 L150223 / 2022 Hefei 50×50×9, 100 m.

## Scope
Implemented an independent C++20 candidate of the literal original `SLOPE`
subroutine (`calmet.for` lines 30372–30604), not a substitute for
`DIAGNO`, `WIND1`, `SIMILT`, `DIVCEL`, `MINIM` or complete P6D.

SLOPE depends on land-use water classes, `QH` (sensible heat flux; generated
by CALMET surface/BL physics), `HMAX/HMIN` and directional distances from
`TERSET`, `TEMP2D` or representative `TINF`, 2D terrain gradients, and
`ZFACE`. The candidate preserves Mahrt 1982/Horst-Doran 1985 source
formulas: stable downslope `QH < 0`, daytime upslope `QH >= 0`, water
exclusion, flow-depth `0.05 * height span`, and per-layer clipping.

- Header: `include/cteas/p6/slope_flow.hpp`
- Standalone CSV: `src/slope_flow_main.cpp`
- C++ CTest: `tests/p6_slope_flow_tests.cpp`
- Independent reference: `reference/compare_original_slope.py`
- CI: `.github/workflows/p6d-slope-original-parity.yml`

The reference test checks the immutable original `calmet.for` Git blob
`437f43bb7f0e51a1919e56664663e1a046986ed0`, extracts **unaltered**
SLOPE source for gfortran, and links only trivial XMIT/plot-output test stubs.
It executes six declared synthetic scenes: flat; stable downslope; daytime
upslope; water and zero heat; spatial vs representative temperature;
subthreshold slope. It compares 6×(50×50×9×2)=**270,000** U/V numerical
components, full field order, finite validity, and a predeclared absolute
tolerance of 2.0e-4 m/s. The CI run, not this document, determines PASS/FAIL.

## Scientific and integration gates
- `P6D_SLOPE_ISOLATED`: C++ compiled and Fortran-parity test status
  depends on CI evidence, not on branch creation or this text.
- `P6C_COMPLETE = FALSE` as of branch origin; full P6C RDSN/CGAMMA/
  observational state integration remains independently gated.
- `P6D_FULL_DIAGNOSTIC_3D = NOT_IMPLEMENTED`: FRADJ isolated PASS is
  pre-existing; SLOPE isolated PASS, if achieved, is insufficient.
- `P6D_HOURLY_REAL_CASE_UVW_PARITY = NOT_TESTED`. Cannot compare actual
  hourly slope flows without certified original hourly QH and station/
  observation inputs, followed by full Step-1/Step-2 calculation.
- `P6_WET_FORCING_VALIDATED = FALSE`: 143/143 SURF precipitation codes
  missing; `NPSTA=0`. This must not be turned into zero-rain validation.
- No original `engine/vendor/src`, historical `project/cases` or
  P1–P5 branch was modified in the SLOPE work.

## Next physical kernels after upstream P6C integration
Capture unchanged-original `WIND1/SIMILT` for observed wind interpolation,
then DIAGNO step sequence including SLOPE+FRADJ, TOPOF2, smoothing and
`MINIM/DIVCEL`. Freeze original first-hour, six-hour and 143-hour
intermediate `U/V/W`, station masks and mass-consistency metrics before
claiming complete P6D.

## Executed CI evidence — 2026-10-11

[Independent original-source SLOPE run #38113822845](https://github.com/RRain001/CTEAS/actions/runs/38113822845): **SUCCESS**, 14/14 scoped CTests PASS and six actual gfortran-vs-C++ tests PASS (270,000 component pairs; no nonfinite, ordering or tolerance mismatches). Original adjusted/active components included 15,000 downslope and 10,000 upslope component values (separate test cases). Global maximum absolute U difference **1.1923990e-7 m/s**, V **2.9806490e-8 m/s** against predeclared **2.0e-4 m/s** absolute threshold. [Machine report artifact](https://github.com/RRain001/CTEAS/actions/runs/38113822845/artifacts/11693065315).

Validated status: **P6D_SLOPE_ISOLATED_ORIGINAL_FORTRAN_PARITY = PASS**.
Unchanged: **P6D_FULL_DIAGNOSTIC_3D = NOT_IMPLEMENTED**, and **P6C_COMPLETE is not established by these P6D tests**.
