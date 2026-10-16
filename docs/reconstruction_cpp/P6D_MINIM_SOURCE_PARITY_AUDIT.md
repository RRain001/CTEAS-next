# P6D — MINIM + DIVCEL + WINDBC original-source audit

Date: 2026-10-11. Original CALMET 6.5.0 `calmet.for`, immutable blob `437f43bb7f0e51a1919e56664663e1a046986ed0`.
Source routines: `DIVCEL` L6246–6303; `MINIM` L9645–9761; `WINDBC` L36404–36441. Original Fortran is extracted unchanged into a test-only build. C++ never modifies `engine/vendor/src/**`.

Original MINIM computes per-layer divergence, makes up to NITER iterations with **four directional in-place scans per iteration**, recomputes divergence after each scan, and refreshes U/V boundaries via WINDBC *after* that divergence calculation. W remains fixed, consistent with original MINIM. The C++ code respects the original field and scan ordering, Fortran REAL*4 literal coefficients, strict dimensions and finite status; supported branch is the no lake-breeze/no exceptional physical-missing synthetic diagnostic path.

C++: `include/cteas/p6/minim.hpp`, CLI `src/minim_main.cpp`, `p6_minim_tests.cpp`. Reference harness `reference/compare_original_minim.py`, workflow `.github/workflows/p6d-minim-original-parity.yml`. Three active noncalm and one calm/zero-iteration tests are run at 50×50×9. Compare original/C++ final U/V, divergence and U/V boundary fields with predeclared `2e-4 m/s` and `1e-6 s^-1` tolerances; zero and nonzero adjustment denominators must be reported. **Status is unverified until CI is inspected.**

This work does not implement full `DIAGNO/WIND1/SIMILT/TOPOF2/SMOOTH` and does not qualify actual original/C++ 2022 1h/6h/143h U/V/W field parity. `P6D_FULL_DIAGNOSTIC_3D=NOT_PASS`. `P6C_SELECTED_HEFEI_2022=PASS`. P6E–P6G and wet forcing remain separate gates; original `NPSTA=0` and precipitation missing 143/143.

## Independent execution and source-routing qualification

[GitHub Actions #38115632414](https://github.com/RRain001/CTEAS/actions/runs/38115632414): **SUCCESS** after a test-driver-only fix (explicit Fortran INTEGER boundary-loop index). Full C++20 strict CTest **16/16 PASS**. Source-extracted `DIVCEL + MINIM + WINDBC` with original Fortran compiler produced **270,000 final U/V/DIV numeric component comparisons** and **7,200 U/V boundary component comparisons** over four 50×50×9 synthetic scenes, zero exceeded thresholds; maximum original-vs-C++ wind-component error **5.0e-12 m/s**, maximum divergence error **5.1e-15 s^-1**, far inside the predeclared tolerances. Three active cases changed **22,374**, **17,380**, **17,690** actual original U/V cell pairs respectively, so the PASS does not consist merely of inactive zero fields.

**Important control-flow distinction:** Original `DIAGNO` calls `MINIM` on initial-guess winds only if `IKINE==1` (L5628), and on the final wind field only if `IOBR==1` (L6180). With `IKINE=0, IOBR=0` this isolated kernel is implemented and verified but is **not invoked by that specific selected-control path**. `DIVCEL` remains used to compute W in the selected model regardless. No claim of full P6D assimilation/wind parity.

**P6D_MINIM_ISOLATED_ORIGINAL_PARITY=PASS; P6D_FULL_DIAGNOSTIC_WIND=NOT_PASS.**
