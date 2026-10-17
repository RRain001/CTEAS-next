# P6D8 WIND1 selected first-guess wind reconstruction audit

Date: 2026-10-11. Original reference: CALMET 6.5.0 L150223, vendor Git blob `437f43bb7f0e51a1919e56664663e1a046986ed0`.

## Source anchors and selected physical route

The original unchanged Fortran source `calmet.for` contains `WIND1` at **L35829–36402**; the independent neutral `SIMILT` at **L30097–30371**. The frozen 2022 Hefei selected control requires one surface wind station and one upper-air station, `NOWSTA=0`, `NBAR=0`, `IEXTRP=-4`, nine vertical layers on a 50×50, 100 m grid.

- WIND1 L36017–36029: station counts and copies of observed U/V into temporary station profiles.
- L36110–36199: selected surface profile; calm winds are treated separately; `IEXTRP=-4` invokes original neutral SIMILT.
- L36204–36252: `1/R²` horizontal weights, saturated to 1 within one grid-cell radius, normalized across surface and upper station. The actual station coordinate is relative to grid origin, not silently rounded to a cell.
- L36254–36289: independent BIAS(k) correction, allowing both surface-favoring negative bias and upper-favoring positive bias.
- L36292–36317: selected `ICALM=0` treatment removes surface calm-wind weights aloft and renormalizes other stations.
- L36319–36345: missing upper-air data triggers layerwise weight redistribution except when `BIAS=-1` excludes upper wind.
- L36348–36380: barrier handling; excluded by the chosen `NBAR=0` contract.
- L36384–36402: final 3-D first-guess `UG`/`VG` accumulation.

## C++ implementation scope

The earlier [D8A observation adapter](../../native_cpp/modules/p6_calmet/include/cteas/p6/wind1_selected_station_hour.hpp) is independently **software PASS** via [CI #38124817807](https://github.com/RRain001/CTEAS/actions/runs/38124817807): 21/21 CTests and previously frozen source-parity SIMILT 216/216 U/V fields. It does not interpolate onto the grid.

D8B provides `wind1_selected_firstguess.hpp`, a strict nine-layer 3-D gridding kernel and an independent trace executable. Its selected contracts explicitly reject unsupported multi-station, overwater, barriers, prognostic wind and incorrect source fields; those omissions are **not** claims that original CALMET lacks such capabilities.

## Unchanged-original numeric test — ACCEPTED for selected WIND1 first guess

The comparator `reference/compare_original_wind1_firstguess.py` compiles the original, extracted **unchanged** `WIND1+SIMILT` and compares the separate C++20 output on six synthetic scenes:

1. No BIAS; 2. positive BIAS; 3. negative BIAS; 4. missing upper-air layers; 5. calm surface with `ICALM=0`; 6. calm surface with `ICALM=1`.

Each scene includes 50×50×9×2 = 45,000 U/V values, **270,000 total**. Frozen acceptance tolerance: **2×10⁻⁴ m/s absolute difference**, zero mismatches; CMake `-Werror` and full scoped P6 regression CTests must also pass. The source SHA must remain unchanged. The independent [dedicated Runner CI #38125704104](https://github.com/RRain001/CTEAS/actions/runs/38125704104) completed **SUCCESS** at code SHA `74f1a8a85adf256fc36830706e4adaba34318ed9`: **22/22 software CTests**, **six source-compiled unchanged original WIND1+SIMILT scenarios PASS**, **270,000/270,000 U/V components PASS**, reported maximum absolute error **0.0 m/s** under the frozen **2×10⁻⁴ m/s** acceptance limit. Source version was locked to vendor Git blob `437f43bb7f0e51a1919e56664663e1a046986ed0`; CI JSON artifact `p6d8b-wind1-firstguess-source-parity` was uploaded. Formal scoped tag: **`P6D8B_ORIGINAL_WIND1_SELECTED_PARITY=PASS`**.

## Important limits

Even a D8B PASS will not establish original 2022 hour-by-hour `WIND1` (including actual chosen BIAS and meteorological observations), fully coupled `FRADJ/SLOPE/INTER2/DIAGNO`, terrain/vertical-W field equality, **1h, 6h or 143h 2022 full-field original equivalence**, or wet atmospheric precipitation forcing. The final P6D stage remains `IN_PROGRESS / FULL_2022_UVW_NOT_PASS`; P6E/P6F/P6G and full CALPUFF acceptance remain independent gates.

CI: [dedicated WIND1 first-guess source parity workflow](https://github.com/RRain001/CTEAS/actions/workflows/p6d8b-wind1-firstguess-original-parity.yml). PR #22 has passed independent selected-path original-source numerical acceptance; full 2022 input/DIAGNO remains outside this test.
