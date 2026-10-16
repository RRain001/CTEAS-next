# P6C: actual 2022 UP.DAT v2.1 RDHDU/RDUPN selected-path numerical audit

Date: 2026-10-11. Stage: **P6C_UP_FORMAT_AND_SELECTED_RDUPN_TRANSFORM_PASS; P6C_COMPLETE=FALSE**.

## Original physical-source correction

The actual `CALMET 6.5.0 (L150223)` `UP.DAT 2.1` (current P4 READ62 `JDAT=2,IFMT=1`) uses **`RDHDU` header reader + `RDUPN`**, not the legacy `RDUP`. Original `calmet.for` `COMP` dispatch occurs at lines **4270–4285** (BB input) and **4345–4359** (AA input), with `dataveru=2.1` calling `rdupn`, `2.2` calling `rdupn2`; `RDUP` covers previous-format data. `RDHDU` header input source L15222–15280; selected `RDUPN` L24012–24444, version 2.1 `FORMAT 3` line 24122, `FORMAT 4` line 24216, conversion L24227–24276.

**Important:** The original `RDUPN` uses 12 h atmospheric snapshots, preserves explicit begin and end stamps, returns **end** timestamps, treats v2.1 records as instantaneous, and reads five layer variables `pressure (hPa), height (m MSL), temperature (K), WD(degrees), WS(m/s)`. `P4` controls `PSTOP=500 hPa`, `IFMTU=1`. Original `ICONVRT=1` subtracts the **first observed level height** from all levels, and rotates U/V via `dir=0.0174533*wd; U=-speed*sin(dir); V=-speed*cos(dir)` for the selected UTM branch. Wind components whose source value is `>= 998.99` become missing `999`; height `>=9998` is not replaced with invented altitude.

## Implemented

- `native_cpp/modules/p6_calmet/include/cteas/p6/read_upper.hpp` implements the selected **fixed-width** `UP.DAT v2.1` C++20 reader and local `ICONVRT=1` coordinate conversion. Fields include explicit validity and dynamic station/time boundaries. It rejects corrupt file identity, unsupported input type/zone, unexpected station, nonmonotonic timestamps, malformed fixed-width 29-byte level records, extra levels, invalid/missing altitudes or out-of-scope P4 options.
- `cteas_p6_read_upper` emits per-level raw and converted fields with station IDs and UTC timestamps, indexed by sounding and level. It does **not** invent missing wind/temperature values.
- `p6_read_upper_tests.cpp` includes calm and missing wind separation, height-AGL transformation, station misidentification, missing-height rejection and malformed snapshot time rejection. All seven CTest tests in standalone P6 build PASS.
- `reference/compare_fortran_upper_rdupn.py` compiles an **independent native Fortran reader using the exact selected original RDUPN FORMAT 3/4 statements and UTM conversion formulas**; compares the same 2022 P4 `UP.DAT` against the new C++ reader. It verifies the source statements are still in original vendor file. This is **not source-identical complete RDUPN**, and cannot alone prove original AA/BB sounding bracket scheduling, temporal interpolation or vertical interpolation.

## 2022 Hefei 100m original-P4 numerical evidence

[**P6B full pipeline + P6C original selected RDUPN Fortran numerical CI, PASS**](https://github.com/RRain001/CTEAS/actions/runs/38110557735). The workflow pulls P4 precisely from `dc4e3f042e5668358fc43f2f2ae98d7a554ecfd3`; generates real 2022 IGRA `FSL`, builds C++ P4 with the historical validated byte-parity `UP.DAT` writer, runs the frozen final P4 merger and then compares the **actual new P4 2022 output `up_58424.dat`**. Historical incorrect 2023 met files never participate.

- `up_58424.dat` SHA256: **`058e8845d34aaaa5a6bedc60f512f5d24857a4534f4107d57bb97f5c3a8d9c99`**.
- **13** in-case original P4 2022 soundings, **785** height levels, **6,280 original Fortran/C++ numerical values PASS** (8 per level: pressure, height MSL, Kelvin, wind direction, wind speed, height local ground, U, V). Station/time/height-index keys match.
- Actual 2022 upper-air wind statistics: `missing_wind_levels=0/785`; `nonzero_wind_levels=768/785`, meaning the numerical test exercised actual nonzero U/V conversion and is not vacuous.
- Measured maximum errors: `P=0`, `height_MSL=0`, `temperature_K=2.10e-7`, `WD=0`, `WS=0`, `height_LGL=0`, `U=5.0e-8 m/s`, `V=4.0e-8 m/s`. Predeclared acceptance: `2e-4` for scalar inputs/height and `1e-4 m/s` for U/V. No mismatches.
- The same workflow then reran original untouched Fortran SMERGE and CALMET (reference complete PASS), decoded `CALMET.DAT` as 143 one-hour intervals×45 fields, and separately validated real P5 SURF 143×8 selected Fortran input values PASS.
- Code/Fortran snapshots are kept separate; no `main`, upstream P4/P5 or original vendor modifications.

## Remaining P6C exit gates and scientific caveats

1. **C-HEIGHT-TIME:** use actual original `COMP` AA/BB exchange cadence and independent original numeric data to certify 00/12 UTC `UP.DAT` profile selection at each model time, hourly `t` interpolation, missing-at-height policies, vertical layer interpolation and terrain-following heights. A record-format PASS is **not** time-interpolated wind equivalence.
2. **C-INTEGRATION:** compare original `GEO.DAT+SURF.DAT+UP.DAT` static/station arrays and state for 1h→6h→143 hourly bins. Derive original fields from original Fortran reference, preserve provenance, and pre-register per-field tolerances before viewing differences. No fabricated weak-wind/soil/met quality.
3. **Precipitation:** P5 `SURF.DAT` reports `IPCODE=9999` in all 143 hours; original `NPSTA=0` provides **no** validated 2022 precipitation field. P6 wind + dry microscale reference may pass, HTO wet deposition forcing remains blocked.
4. P6D existing isolated `FRADJ` pass is preserved, but P6D integrated full wind stays **HOLD until the P6C complete acceptance**. Subsequent P6E–G also HOLD.

**Stage states:** `P6A_PASS`, `P6B_PASS`, `P6C_GEO_FORMAT_PASS`, `P6C_SURF_FORMAT_PASS`, `P6C_UP_FORMAT_PASS`, `P6C_UP_CONVERSION_FORTRAN_PASS`, `P6C_FULL_OBSERVATION_TIMELINE_NOT_READY`, `P6C_COMPLETE_FALSE`, `P6D_FULL_SOLVER_HOLD`, `P6_CALPUFF_READY_FALSE`.
