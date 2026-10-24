# Issue #40 — S4-C shared native G14 fourth-hour genuine NOAA WATER trial

Date: 2026-10-24. This is a **scoped scientific numerical comparison**, not
production P6/P7 or human independent scientific approval. PR #308 remains Draft.

## Physics and input provenance

The original `G65RealNoaaFourthHourTrialActor` is moved **without any
numerical formula changes** from `p6g_g65_noaa_firsthour_atomic_commit.hpp`
to the existing `p6g_g65_shared_noaa_firsthour_actor.hpp`. The original G65
research implementation and `cteas_p6g_s4b2_unified_selected` use the same
native hour1, hour2, hour3, hour4 G14 physics actors.

The same S4B2 executable now requires an explicit
`--selected-experimental --water-fourthhour-g14-trial-only` flag, `--hours 6`
complete **original NOAA source observations**, exactly
`--probe-prefix-hours 4`, and an unoccupied output path. The source must
be 82×85×9, 2 surface/1 upper-air stations, and 63 WATER cells. Mixing with
earlier one-, two-, three-hour trials, default G26 or source-only preflight,
no source data, unauthorized output/trace, wrong hour count or wrong prefix is
refused. The production default remains fail-closed.

The existing shared `g65_native_hour2_water_from_p6f()` decoder is reused:
precisely after **committed hour 3**, it reads the freshly native-calculated
P6F candidate's 6,970 `USTAR` and `EL` values, validates source beginning/
ending UTC timestamps and native provenance, and passes these typed physical
WATER arrays into the G65 hour-four actor's source-native G26A/G26B. No
Fortran original CALMET.DAT fields/intermediate states are solver inputs.
The G14 scheduler owns and checks committed ZI, ZICONV, DPTT between all
four real hours and publishes staged upper/gamma clocks **only after** the
17 native stages and complete 45 P6F field precommit.

For hour4, original G43/MISSFC is applied to a **detached, model-internal
five-field nonwind** source copy, with input checks proving P5 winds and
precipitation observation values unchanged. Raw SURF.DAT remains immutable;
this is a fixed original NOAA physical-source research case, not a generic
station-data filling policy.

## Native vs unchanged original Fortran science

Original unchanged 6-hour Fortran output (read-only and NOT rerun today):

`a7004fbf780212d58536be3957306c2aecc53abe2e58bfec870571b12d8b8e14`

Actual new S4B2 four-hour native MET.DAT SHA256:

`412aabb4dfa0ef02af80a70a5ba0dca63fb15ac541ded53a0bb43b484e93177d`

The **independent post-run reader**, existing
`scripts/s4/s4c_compare_noaa_unified_threehour.py` now parameterized by
`--native-hours 3|4|5|6`, validates native/original SHA256, disjoint
reference/output paths, unused evidence destination, source header/grid,
exact 45 canonical field names/order per UTC hour, unchanged frozen field
REAL4 tolerances and strictly equal INTEGER4. It reports individual fields
and first differences without feeding comparisons to solver execution. Its
old three-hour API and result string remain backward compatible; no new
per-hour duplicate comparator was introduced.

| Hour (UTC 2022-06-01) | Values | Bitwise-equal REAL4/INTEGER4 | Frozen exceedances |
| --- | ---: | ---: | ---: |
| 01–02 | 313,650 | 298,578 | 0 |
| 02–03 | 313,650 | 239,527 | 0 |
| 03–04 | 313,650 | 231,976 | 0 |
| 04–05 | 313,650 | 240,362 | 0 |
| **Total** | **1,254,600** | **1,010,443** | **0** |

Status: `PASS_SCOPED_S4C_SHARED_FOURHOUR_FORTRAN_180`.
This claim is restricted to the fixed NOAA source and frozen tolerances.
Fortran was NOT rebuilt or rerun during this increment. The only original
MET.DAT access was after native execution in this independent audit.

Both original one-/two-/three-hour *native prefix output* files were
**regenerated from the new binary** and matched previous SHA256 exactly:

- hour1: `d8e6065e2d26bc517f72619bd1822c6832d04ec7c42c4b93d12d32910a3c984c`
- hour2: `30eb55977283f7b9c09a4002e9781d32e1d58af30ac408e15959d8c928d9f0f3`
- hour3: `a80edb2467807635c2c1ea6e285533c6981f4469e41fc4dcf0031a2a035b1989`

Detailed original-vs-native results remain PRIVATE on Ubuntu:
`/home/lhy/dev/reports/cteas-s4c-unified-20261024/s4c-shared-fourhour-vs-original.json`.
Do not copy original Fortran code, files, or input data into public GitHub.

## Software safety and next actions

- Original G65 and S4B2 GCC12 targets compile against the shared fourth-hour
  actor without numerical changes.
- P6 research negative CLI CTest **6/6 PASS**, including fourth-hour false
  opt-in, duplicated/mixed research flags, wrong prefix and missing source.
  The **same** hour3 negative CLI test driver handles hour4 via
  `--research-hour 4`; no duplicated test file. The existing independent
  audit tests also validate SHA separation, corrupted files, 3..6 prefix
  bounds and protected evidence output.
- Next extend native hour-five G65 actor through shared G14, derive native
  prior WATER P6F and source G43 for hour-five; independent check 45 new
  fields against frozen original; then hour6. C1/C2 real 143h parity on
  latest SHA and independent **second source/station configuration** plus
  non-bot human scientific approval remain absent. Formal production P6,
  P7 and scientific-admission are NOT_ACCEPTED/NOT_RUN. Do not merge PR #308
  or assign science-validated/merge-verified labels. Formal Docker delivery
  follows S5.
