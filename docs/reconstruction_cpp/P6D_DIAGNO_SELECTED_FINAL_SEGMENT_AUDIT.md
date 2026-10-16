# P6D — original CALMET DIAGNO final-wind selected segment

2026-10-11. **Candidate awaits independent CI numerical acceptance.**

The literal original `DIAGNO` source from CALMET 6.5.0 `calmet.for` lines 6119–6148 defines this contiguous selected pathway:
1. `SMOOTH(U,V,UB,VB,NSMTH)` sequential in-place per-layer.
2. Initialize **all** `W` faces to zero.
3. Evaluate `DIVCEL` for **every** vertical layer before any W integration.
4. Integrate `W(k+1)=-DZ(k)*DIV(k)+W(k)` from lowest to highest layer.
5. After each layer, refresh U/V edge conditions with `WINDBC`.

**Two loops matter**: computing all divergences first, followed by integrating W, is not equivalent to computing DIVCEL and integrating W one layer at a time. Boundary updates are also after full divergence calculation, and must not enter as zero-flux assumed values.

The independent test extracts literal original `SMOOTH` (L30606), `DIVCEL` (L6246), `WINDBC` (L36404), and inserts verbatim `DIAGNO` L6119–6148 as executable original Fortran source into a test-only driver. It checks the original immutable vendor blob `437f43bb7f0e51a1919e56664663e1a046986ed0`. A test-only `XMIT` helper initializes W exactly and test-only `BOX` cannot execute because `LLBREZE=.FALSE.`. Original Fortran physics is not changed.

C++ kernel: `include/cteas/p6/diagno_segment.hpp`, CLI `src/diagno_segment_main.cpp`, CTest `p6_diagno_segment_tests.cpp`; comparison `reference/compare_original_diagno_final_segment.py`; workflow `.github/workflows/p6d-diagno-final-segment-parity.yml`. Four 50×50×9 cases: calm, analytic divergent flow, layer-selective smoothing, heterogeneous wind and boundary. All `U,V,DIV,W_below,W_above` and `UB,VB` fields are compared, declared 2e-4 m/s wind and 1e-6 s^-1 divergence tolerances. Nonzero original W fields are required in three cases.

No claim of `WIND1/SIMILT/INTER2/FRADJ/SLOPE` sequencing nor complete DIAGNO. `IOBR=0`, no selected lake-breeze boxes. Real 2022 original-vs-modern hourly wind fields (1h/6h/143h) and downstream P6E/F/G remain gated. Wet precipitation forcing still invalid (`NPSTA=0`, missing 143/143 IPCODE).

## Independent acceptance evidence — 2026-10-11

[GitHub Actions #38116193083](https://github.com/RRain001/CTEAS/actions/runs/38116193083): **SUCCESS**. Source-frozen literal DIAGNO L6119–6148 + unchanged SMOOTH, DIVCEL and WINDBC original Fortran verified against C++ after correcting the independent Fortran driver grid initialization (`DX=DY=100 m`; no physics code/threshold changes). Strict **18/18 CTests PASS**. Four original Fortran vs modern scenarios compared **450,000 U/V/DIV/W component values** and **7,200 boundary wind values** without mismatches. Three physically active scenes contained 22,482, 22,498 and 22,499 nonzero W cells. Maximum observed original-vs-C++ W absolute error approximately **5.1e-11 m/s**, maximal divergence error approximately **5.1e-14 s^-1**, against preregistered tolerances of `2e-4 m/s` and `1e-6 s^-1`. All rows, masks and index order checked.

**P6D_SELECTED_DIAGNO_FINAL_SEGMENT_ORIGINAL_FORTRAN_PARITY = PASS**, but **P6D_FULL_DIAGNOSTIC_UVW = NOT_PASS**. Upstream genuine station interpolation/WIND1 and FRADJ/SLOPE real-hour combined paths remain.
