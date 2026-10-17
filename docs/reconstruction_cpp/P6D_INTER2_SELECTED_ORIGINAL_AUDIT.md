# P6D — CALMET INTER2 original-source selected path

Date 2026-10-11. **Original CALMET selected-path INTER2 source parity PASS**, limited to the documented four synthetic scenarios.

Freeze original CALMET v6.5.0 L150223 unchanged source blob `437f43bb7f0e51a1919e56664663e1a046986ed0`; `INTER2` L8124–8616, original `FMINF` L7256 and `XMIT` L36951. Selected control branch `IWFCOD=1` (`I3DCTW=1`), `IPROG=0`, `NBAR=0`, `NOOBS=0`, no prognostic field injection. `LVARY` is an explicitly configured runtime input and tested in both modes, not guessed from CASE INP.

INTER2 computes grid-center km coordinates, per-station distances, enforces RMIN, stable nearest-station tie selection, per-layer NINTRP filtering, land surface/upper vs water radii, skips invalid station-component observations, optionally falls back to nearest valid station under LVARY, and uses double-precision weighting with original REAL*4 output. No synthetic missing observation may be marked valid; unsupported nonzero NBAR/IPROG/NOOBS is fail-closed.

C++20 header `include/cteas/p6/inter2_selected.hpp`, CLI `src/inter2_selected_main.cpp`, CTest `p6_inter2_selected_tests.cpp`. Independent literal Fortran comparison `reference/compare_original_inter2.py` links original extracted INTER2/FMINF/XMIT and a **test-only BARIER stub that is unreachable with NBAR=0**. The original vendor Fortran and P1–P5 are untouched. Four synthetic 50×50×9 scenes assess multi-station observations, missing vertical observations and mixed land/water masks, LVARY nearest-source fallback, duplicate distances and zero observational WO weighting. A numeric PASS requires **90,000 scalar component matches**, nonzero actual blends, exact k/row/i ordering and preregistered `2e-4 m/s` absolute tolerance.

Even success cannot mark `P6D_FULL=PASS`: actual 2022 first-hour/six-hour/143-hour U/V/W requires source-faithful WIND1/SIMILT, real step-1 prognostic/station states, FRADJ/SLOPE and complete DIAGNO interoperation. Never confuse original P6B meteorological output with C++ new output. `NPSTA=0`, surface IPCODE missing 143/143, wet forcing remains unqualified.

## CI execution blocker (2026-10-11)

[INTER2 CI run #38117154802](https://github.com/RRain001/CTEAS/actions/runs/38117154802) failed before any job step in both attempt 1 and manual retry attempt 2. All eleven pre-existing P6/P6C/P6D workflows triggered by the same PR head SHA `f33b498d780f50c1aaddb1df2e241ec428eb8df1` also failed at the same timestamp within approximately three seconds, without job logs or test-step reports. This is an infrastructure/execution **candidate cause**, not a proven GitHub billing or service diagnosis. The independent original Fortran comparison did **NOT RUN** and must not be reported as a failed numerical parity or as PASS.

**Acceptance**: `P6D_INTER2_ORIGINAL_FORTRAN_PARITY=NOT_EXECUTED`; `P6D_INTER2_CXX_BUILD=NOT_EXECUTED`; `P6D_INTER2_PR_MERGE_ALLOWED=FALSE` pending an actual green job and inspection of JSON evidence. No base-branch merge, physics source modification, fallback to manufactured parity, or downstream P6D full-field claims are allowed.

## Independent numerical acceptance — self-hosted Linux CI, 2026-10-11

[GitHub Actions run #38121613553](https://github.com/RRain001/CTEAS/actions/runs/38121613553): **SUCCESS** after the GitHub HTTPS connection issue recovered. The self-hosted runner's C++20 GCC 12.3 / Fortran 11.4 toolchains compiled the unchanged original routine extraction and the independent C++ implementation. **19/19 CTests passed**. Four 50×50×9 arrays × 1 component yield **90,000 reference/modern scalar comparisons**, all with no tolerance exceedances. Original-vs-C++ maximum absolute error is **9.536745997351659e-7 m/s** versus preregistered **2e-4 m/s**. Nontrivial observation blends per case: 22,500 / 22,500 / 22,500 / 14,850.

Artifact: [p6d-original-inter2-selected-evidence](https://github.com/RRain001/CTEAS/actions/runs/38121613553) (retained 14 days, sha256 digest `e5e0b5e43fb129449de90a05c88288046e9919e4910d2d98d3da55caf8a12e0f`). Immutable vendor source Git blob: `437f43bb7f0e51a1919e56664663e1a046986ed0`. Tested and qualified selected scope: `IPROG=0`, `NOOBS=0`, `NBAR=0`, explicit `LVARY` on/off, `IWFCOD=1`. The earlier sections documenting the transient CI outage remain historical; current acceptance supersedes `NOT_EXECUTED` for this specific test, not for other original/wind paths.

**P6D_INTER2_SELECTED_ORIGINAL_PARITY=PASS**; **P6D_FULL_2022_UVW=NOT_PASS**. Original 2022 observational `WIND1/SIMILT` source-specific parity, full `DIAGNO` physics orchestration and real-case 1h/6h/143h U/V/W checks remain required.
