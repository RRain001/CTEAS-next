# P6C original RDSN / MISSFC and CGAMMA — real 2022 observation integration

Date: 2026-10-11. Target is strictly the selected Hefei 2022 CALMET 6.5.0 case, **not every CALMET optional input or physics mode**. Original vendor Fortran source SHA256 `430381b4fb87f15127e20b13cc3e99be8a0e0fccf1d5821110af7f980558d134`. The repository's `engine/vendor/src` remains untouched.

## Actual surface station execution — independent source runtime PASS

[Original real 143-hour RDSN + COMP trace, CI #38113500059](https://github.com/RRain001/CTEAS/actions/runs/38113500059) passed. A temporary identical Fortran source with **write-only** COMP observations around original `RDSN` and `MISSFC` is compiled for reference. `MET.DAT` SHA256 is required identical to untouched original execution and passed. The 143-hour original raw RDSN observation input arrays compare against the C++ stateful hourly `GEO/SURF/UP` trace.

- **143/143 real station records and physical time states PASS**.
- **1,144/1,144 values** (WS, WD, ICEIL, ICC, TEMPK, IRH, PRES, IPCODE) PASS; original 6 timestamp/seconds fields per hour, **858/858** PASS.
- For float fields: max |WS| = `5.0e-9 m/s`, WD = 0, |T| = `1.04e-7 K`, |P| = `4.414e-6 hPa`; strict predeclared per-field comparison threshold `2e-4`. No source-vs-native failures.
- Original `MISSFC` **changed none of the eight monitored raw station fields in any of the 143 hours**. Thus this selected case needs no replacement of raw station fields. Original MISSFC L9762–10002 may fill ICEIL, ICC, TEMPK, IRH, PRES from nearby stations, but never WS, WD or IPCODE. **Other missing/multistation conditions are not claimed implemented**.
- Original RDSN L23526–23534 retains records if they cover the current timestep start; L23598–23636 requires duration ≤3600 s and source coverage. The C++ `surface_hourly_state.hpp` has explicit new-read/reuse and fail-closed malformed timestep/gap/frequency contracts, with standalone CTest.

## CGAMMA interface — original values, not invented ZICONV

Original `CGAMMA` L3031–3250 is called from PREPDI for the diagnostic branch (`NOOBS=0, IWFCOD=1, IDIOPT(2)=0`); this is a *temperature lapse* calculation, not an independent boundary-layer model. `ZICONV` originates in the original model's mixing-height physics. The C++ `cgamma.hpp` **does not** simulate or invent `ZICONV`: `original_comp_runtime_trace.py` captures original `ZUPT, ZICONV` and output `GAMMA` at the live callsite, and `compare_original_cgamma_2022.py` uses those sources for independent C++ replay of all actual 143 hourly soundings. The kernel retains the last convective-hour state and the original `JORDER` physical-slot ordering, including source branches:

1. `ZICONV >= ZUPT`: dry adiabatic `GAMMA = -0.0098 K/m` and save last convective time.
2. Otherwise, interpolate raw upper-air surface and `ZUPT` temperature (original `INTP`) between AA/BB in `JORDER` direction.
3. If the previous convective time falls strictly within the bracket and precedes the present hour, use the original last-convective correction.

**CGAMMA original real-runtime numerical gate: PASS.** [P6B original + P6C COMP/RDSN/CGAMMA 143-hour CI #38113874913](https://github.com/RRain001/CTEAS/actions/runs/38113874913) completed successfully after fixing the independent forcing CSV CRLF/LF schema mismatch. All **143/143 original live CGAMMA calls** compared within the frozen `3.0e-6 K/m` tolerance; max absolute error **5.00000007e-11 K/m**, zero failures. Branches exercised: **86** ordinary soundings, **51** current-hour adiabatic, **6** last-convective retained. The original temporary write-only instrumentation preserved the untouched `MET.DAT` byte hash. This verifies the CGAMMA vertical-temperature process driven by real original `ZICONV`, **not** the P6E mixing-height physics producing `ZICONV`.

## Independent scientific limits

- P6C selected-case observation scope: 50×50×9, 100 m, one surface virtual station, one `UP.DAT v2.1` upper station, 143 actual one-hour periods, source-validated GEO/UP/SURF. Not a general CALMET multi-station/alternative-format implementation.
- Original `IPCODE=9999` **143/143 hours**, `NPSTA=0`: wet forcing remains **unqualified**, regardless of any successful dry-air diagnostic wind benchmark.
- **P6C selected-case observation subsystem PASS:** original 2022 one-surface/one-upper station, real 143-hour `GEO/SURF/UP` and original `COMP/RDSN/PREPDI/VERTAV/FACET/CGAMMA` scalar-state acceptance is complete. `P6A/P6B=PASS`, `P6C=PASS_SCOPED_HEFEI_2022_OBSERVATIONS`; **P6D may begin integrated implementation but is NOT PASS**, P6E–G remain unimplemented/untested; P6 CALPUFF-ready **FALSE**.
