# P6D — DIVCEL original-source divergence kernel

Date: 2026-10-11. **Implementation prepared; original Fortran comparison awaits CI.**

## Source and selected branch

Original `CALMET_v6.5.0_L150223/calmet.for` `DIVCEL`, lines 6246–6303. Immutable Git blob `437f43bb7f0e51a1919e56664663e1a046986ed0`. Standalone source extracts literal `DIVCEL` and compiles with original vendor `grid.met` and `params.met`, not an independently handwritten Fortran substitute.

Implements `DUDX=(U(i+1)-U(i-1))/(2 DX)`, `DVDY=(V(j+1)-V(j-1))/(2 DY)`, `DWDZ=(W(k+1)-W(k))/DZ(k)` with **original wind-component-specific boundary U/V arrays** and layer-specific maximum absolute divergence. The original `HTOP=1.0` multiplier and normalization are preserved; i-fastest, k-slowest indexing; m/s, metres, and s^-1. The static `W` grid has NZ+1 vertical faces.

C++ implementation: `include/cteas/p6/divcel.hpp`, `src/divcel_main.cpp`, `tests/p6_divcel_tests.cpp`.
Independent reference: `reference/compare_original_divcel.py` and `.github/workflows/p6d-divcel-original-parity.yml`.
Four 50×50×9 original-Fortran-vs-C++ synthetic tests cover: calm zero divergence, linear horizontal wind gradients, vertical shear, and nonzero boundary-only flows. Explicit shape, units, nonfinite and missing-field guards. Declare tolerance `1e-6 s^-1` prior to inspecting numerical differences; 90,000 3D divergence values and 36 layer maximum values, including exact index order and active nonzero-denominator controls.

**Evidence limit:** No test here proves `MINIM` convergence or a complete 3D wind solver; an isolated divergence diagnostic can PASS while `DIAGNO/WIND1/SIMILT/TOPOF2/SMOOTH` remain absent. Original P6B 143h MET.DAT stays the scientific reference. Final P6D must compare 1h→6h→143h original/C++ U/V/W and divergence under the same inputs, including masks. No P6E/P6F/P6G or rainfall validation claim (`NPSTA=0`, 143/143 precipitation codes missing).

## Executed independent acceptance — 2026-10-11

[GitHub Actions original Fortran DIVCEL parity run #38115350648](https://github.com/RRain001/CTEAS/actions/runs/38115350648) **SUCCESS**. Strict C++20 `-Werror` CTest **15/15 PASS**; extracted untouched vendor subroutine compiled and executed under gfortran. All 4 synthetic scenes PASS, with **90,000 cell divergence values and 36 layer maximum-divergence quantities**; max absolute original-vs-C++ error **5.00017e-14 s^-1** vs predeclared `1e-6 s^-1` tolerance. Three non-calm cases had nonzero original divergence; no reshaping or denominator omission. The result does not qualify P6D full diagnostic wind, MINIM convergence or actual 2022 hourly meteorology.

**P6D_DIVCEL_ISOLATED_ORIGINAL_PARITY=PASS. P6D_FULL_UVW=NOT_PASS.**
