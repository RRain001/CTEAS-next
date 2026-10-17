# P6G G18B3–B5: original IUPT, candidate NEARU, frozen CGAMMA and FACET (2026-10-14)

Development PR #63 (Draft), stacked on PR #53's **unaltered** source-accepted Hefei single-station 143-hour model. This is a controlled 2SS/2US selected-stage integration, not a complete independent original Fortran multi-station scientific acceptance.

## G18B3 — source IUPT and candidate NEARU

- Parse **IUPT** from the exact original `met.inp` using the existing strict source-key parser. Missing, duplicated, malformed or out-of-range values fail; only `-1` (per-cell selection) and valid one-based positive US ordinals are allowed.
- `g18b3_source_deck_upper_choice` derives a **candidate** NEARU grid based on ordered US coordinates from actual met.inp READCF station deck. It uses the G17B accepted REAL*4 cell center conventions and strict `<` squared-distance tie selection; the positive IUPT override is handed to the already frozen `p6e::mixht_observed_mc` input without destroying the underlying geometric NEARU map.
- **Scientific limitation:** the exact general CALMET multi-US SETCOM NEARU Fortran assignment remains to be checked independently. A `G18B3UpperChoice` is explicitly `independently_fortran_verified=false` and can only bind into `MixhtObservedMcInput` when `explicitly_test_only=true`. This is NOT production NEARU authority yet.
- Tests reject invalid IUPT variants, duplicated keys, invalid US UTM, missing explicit fixture mark; source-deck -1 and user-chosen positive US mode and first-ordinal floating-distance ties are checked.

## G18B4 — independent upper-station CGAMMA history

- `p6g_g18b4_cgamma_clock.hpp` directly calls the **unchanged PR #53** `p6::CGammaState::calculate` once for each original US; G18B1 source-bound AA/BB/JUSTA and timestamp brackets are converted to a two-sounding `Upper2022 / CompBufferedHour` view. **No lapse/CGAMMA physical formula is reimplemented.** Each hour copies the accepted per-station CGAMMA state into an isolated candidate; a later invalid site or COMP/P6F failure does not alter committed history.
- State may be committed only with an externally supplied *successful complete* G14 hour count, never at PREPDI/CGAMMA candidate preparation. Tests prove separate current-convective and retained-convective branch histories for two upper stations, direct exact equality to independent calls to frozen CGAMMA, and retry/duplicate/premature commit rejects.
- **Scientific limitation:** the per-upper `previous ZICONV` sampling authority and `ZUPT` are explicit **test-only** inputs. No invented previous-hour field or arbitrary upper-station sampling is marked production. The CGAMMA state commit interface is prepared, **not integrated with a complete real 17-stage G14 physical scheduler**.

## G18B5 — frozen FACE temperature interpolation

- `p6g_g18b5_upper_temp_faces.hpp` consumes the G18B1 source-backed physical AA/BB thermal observations and the exact original met.inp `ZFACE(1..10)` and invokes the **unchanged PR #53** `p6::calmet_facet_temperatures` for each original upper station. Results carry station IDs, hour stamp, JUSTA and per-station past/to-go intervals. Both physical AA and BB are 10-face vectors in site-major order.
- A cross-year 30-hour 2US selected *input/state* test independently recomputes frozen kernel FACET at all 10 faces per US, validates physical slot swaps across asynchronous soundings, and rejects invalid original ZFACE.
- **Scientific limitation:** real multi-station TEMP3D grid spatial weights, bracketed temperature *time* interpolation, AVEMIX and P6F still require original Fortran end-to-end acceptance. The test's independently supplied ZFACE is a source-selected standalone test control; it is not a live G14 P6E call.

## Preserved guardrails and next steps

- PR #53 frozen 163-file guard, native original 143-hour 45-field single-site science gate, and selected vendor G9/G10/G11 oracle tests remain mandatory; no tolerance or accepted physical source modified.
- G18B6: compare candidate NEARU directly against source original Fortran at ties, multiple upper site counts, and broad grid locations; bind `ZUPT`/per-US prior ZICONV and thermal controls from authoritative original CALMET execution, not fixture values.
- G18C: complete source-ordered AVEMIX, TEMP3D, WSTARR, COMP and P6F under one G14 scheduler with atomic hourly state, then independently compare multi-site vendor 45 fields for 1h, 6h, 143h and a year/cross-year. Until then #63 stays Draft.
- CI: `P6G multistation on accepted single-station baseline` runs Debug and Release 17/17 CTests and the frozen-core guard, on GitHub-hosted Ubuntu. Check exact commit SHA and distinguish these source-selected checks from an actual complete multi-station 45-field original Fortran comparison.
