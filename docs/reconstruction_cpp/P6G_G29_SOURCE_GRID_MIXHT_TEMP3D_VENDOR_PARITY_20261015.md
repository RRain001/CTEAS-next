# P6G G29 — original CALMET 6.5.0 multi-UP MIXHT and TEMP3D first-hour source parity

Date: 2026-10-15. PR #63 remains **Draft, unmerged**. This is selected,
source-original-format **synthetic-observation** 12 × 12, 2 surface/2 upper
station, all-land **first-hour** numerical verification. It is NOT a
production G14 multi-hour simulation, nor original full CALMET.DAT 45-field
equality or accepted P6F durable output.

## Numerical authority and exact run

- Original unmodified `engine/vendor/src/CALMET_v6.5.0_L150223/calmet.for`,
  pinned Git blob `437f43bb7f0e51a1919e56664663e1a046986ed0`.
- Independent literal original Fortran Debug+Release hosted Actions:
  [G29A exact head #38690607592](https://github.com/RRain001/CTEAS/actions/runs/38690607592)
  **SUCCESS**; [G29A+G29B #38691202487](https://github.com/RRain001/CTEAS/actions/runs/38691202487)
  **SUCCESS** in Debug and Release.
- Original source `MIXHT` (10411–10682), `MIXDT`, `MIXHMC`, `MIXHBG` and
  entire unmodified `TEMP3D` (31159–31709) are extracted independently of
  the C++ candidate. No new handmade reference-equation replacement.
- Three separately generated G19 source input cases: normal night,
  steep-terrain night, steep-terrain daylight. Per case and per build:
  MIXHT 144 cells × 3 fields = 432 comparisons; TEMP3D 144 × 9 = 1,296.
  Across 3 cases and 2 build modes: **2,592 MIXHT** and **7,776 TEMP3D**
  numerical comparisons, all with **zero tolerance exceedances**.
- Max G29A Debug absolute error across these scenarios: ZI < 5.0e-7 m,
  ZICONV < 5.0e-7 m, DPTT < 5.0e-10 K.
  Max G29B across all 9 temperature layers in Debug/Release:
  < 5.0e-7 K. Frozen P6E comparator tolerances are used **unchanged**:
  G29A absolute (0.07 m, 0.07 m, 0.004 K), relative 8e-5;
  G29B absolute 0.0005 K, relative 1e-5.
  These component tolerances are NOT the separate official 45-record
  original-Fortran science acceptance tolerances.

## Actual computation and provenance

1. G26A computes the 12 source-order DIAGNO checkpoints on one
   `UnifiedMultistationHourlyScheduler::preview_next_hour()` frame.
   G26B executes actual frozen native `MIXHT → AVEMIX → WSTARR → TEMP3D`
   selected kernels on the **same** frame; the G14/P6F final [16] stage
   remains unknown/false. No G14 hour or station-clock memory publishes.
2. G18A captures the **actual before-MIXHT input** into an audit-only result:
   physical source-UP AA and BB soundings; `JUSTA`, independently verified
   original SETCOM `NEARU` 1-based ordinals; source READCF/SETCOM scalars;
   source QH, USTAR, EL, RHO, FCORI/CMECH; **previous COMP**
   ZI/ZICONV/DPTT and the native current-hour station `MIXHTST`-updated
   DPTT. The native *output* ZI/ZICONV/DPTT is exported separately.
   The Fortran oracle never consumes that output as a computation input.
3. G18C3 captures the **actual pre-TEMP3D input**: physical AA/BB interpolated
   face temperatures, original source station local UTM coordinates,
   per-US hour brackets, READCF IRAD, current source surface temperature
   and **post-AVEMIX ZICONV**. A separate native 9-layer temperature export
   is compared to unmodified vendor TEMP3D.
4. The selected same-day 00/12Z comparator deliberately refuses unsupported
   shifted sounding brackets. G29B is not a test of next-day, cross-year,
   overwater or prognostic TEMP3D. No frozen #53 physical formula or vendor
   source is changed.
5. Night cases run original stable QH<0. The daytime case runs original
   convective grid MIXHT, uses *both* US stations (NEARU distribution
   10 / 134 cells), has 144 cells selecting physical BB as older (`JUSTA=-1`),
   and two source station cells with current COMP entering nonzero DPTT.
   This first-hour set does not by itself validate longitudinal AA/BB
   turnover or a second committed hour; earlier standalone P6E branch
   coverage is separate evidence.

## New regression artifacts

- `native_cpp/modules/p6_calmet/reference/compare_g29_source_original_mixht.py`
- `native_cpp/modules/p6_calmet/reference/compare_g29_source_original_temp3d.py`
- Read-only G18A / G18C3 / G18D4 / G26B source-invocation snapshots and
  G21 first-hour probe source/candidate exports.
- `.github/workflows/p6g-vendor-g9-g11.yml`: three G29A and three G29B
  selected-input checks in BOTH Debug and Release with JSON artifacts,
  alongside all G20–G28 source-vendor checks.

## Do not overstate acceptance — next hard gates

- Complete original multi-station `P6F` output **45 field records** plus
  literal original CALMET vendor 1-hour comparison (not candidate binary
  self-roundtrips); preserve original source record ordering, WFACE mapping,
  static GEO/station metadata and strict scientific tolerance.
- Only after that, admit **all 17 native G14 physical/output stages** and
  transactionally publish COMP and AA/BB/CGAMMA clocks after genuine
  P6F precommit/verification; do not use the current 16-stage test proxy.
- Separately validate chronological multi-site **6h, 143h and full year**
  with non-synthetic production source data, including original hourly
  AA/BB turnover and previous committed COMP effects.
- Keep PR #63 Draft and the accepted single-station #53 science files
  frozen until the complete original multi-station gate has passed.
