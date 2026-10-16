# G18A — multi-station candidate COMP MIXHT/WSTARR through frozen #53 kernels

Date: 2026-10-14. Development PR #63 stacked on PR #53. Status: **selected/test-scoped**, not accepted generic multi-SS hourly COMP/P6F.

## Scientific rationale

The original CALMET 6.5.0 sequence in the accepted PR #53 is stateful: PREPDI/CGAMMA and DIAGI STHEOR/MIXHTST read the **previous committed** `ZI/ZICONV/DPTT` state; MIXHTST additionally mutates the *current-hour* station-cell `/TJMP/ DPTT` before the gridded COMP MIXHT and WSTARR routines run. Treating each hour as independent, reusing the previous hour twice or passing a stale QH from HEATFX into COMP loses numerical equivalence.

G18A adds the selected `p6g_g18a_selected_comp_mixht.hpp` bridge **without** duplicating MIXHT/MIXHMC/MIXHBG or WSTARR formulas:

1. Require actual G17D native 9-layer U/V/10-face W fields and source-stamped same-hour G17C1 heat plus G17C2 ELUSTR-updated QH/USTAR/EL; reject absent/nonfinite wind, missing grid state, wrong hour or station count.
2. Accept explicit **test-only** complete upper-air sounding buffers `AA/BB`, `JUSTA`, `NEARU`, upper site indices and source P6E controls. An actual multi-station PREPDI/COMP buffer authority is **not** yet attached, so these controls must not be mistaken for native validated production met.inp state.
3. Initialize all `ZI/ZICONV/DPTT` from `MultiHourFrame.previous` (the last atomically committed grid state), never from mutable `frame.next`.
4. Inject the current-hour MIXHTST station-cell `DPTT` mutation from G17C3 individually for each surface station. Check source station IDs, time, unique cell and explicit upper-site mapping; do **not** use the frozen one-station `dptt_refresh` workaround for two independent station cells.
5. Execute **unchanged** `p6e::mixht_observed_mc` and then **unchanged** `p6e::wstarr` for the selected land grid. Return a `candidate_next` memory plus WSTAR, **not** a scheduler commit or claim of `NativeCpp,true` production COMP.
6. Leave `frame.previous` and `frame.next` unmodified. Only G14's full 17-stage production scheduler may atomically publish new `ZI/ZICONV/DPTT` after all stages, including AVEMIX, TEMP3D, P6F and the full field check, have succeeded.

## CI / regression contract

The existing G17B4 source-selected CTest now runs G18A during two 2SS+2US daytime/night fixture hours on the 12x12/9 level 10 km selected test domain. It independently constructs the source `p6e::MixhtObservedMcInput`, including each station's current-hour injected DPTT and the explicit 2-UP AA/BB buffer values. It calls the frozen kernels a second time and requires **exact USTAR/QH provenance and bit-for-bit `ZI/ZICONV/DPTT/WSTAR` equality**. Negative tests: unmarked test controls, bad SS→US `NEARU` at a site, duplicate station-cell writes, missing G17D 3D W, and accidental premature COMP state commit.

The frozen PR #53 163-core-file hash guard and separate strict 143 h / 45-field Hefei acceptance continue unchanged; no comparison tolerance was adjusted.

## Remaining G18 work, in order

- G18B: source-authoritative independent per-UP AA/BB, JUSTA/NEARU/IUPT and temperature-face interpolation for all multi-site soundings; model the /TJMP/ DPTT update and PREPDI/CGAMMA previous-ZICONV temporal authority for every actual station, not selected fixtures.
- G18C: source-authentic water/land, AVEMIX, grid WSTARR, TEMP3D, all remaining P6E callbacks, and full dynamic P6F output.
- G18D: run **one G14 process-authoritative** continuous multi-site model (no hourly independent reset) with full original CALMET 45-field numerical parity at 1 h, 6 h, 143 h, year/cross-year; original Fortran is an oracle only, never production backfill. PR #63 remains Draft until acceptance.

## GitHub-hosted Ubuntu evidence

Workflow: `P6G multistation on accepted single-station baseline` on the exact PR #63 commit. A selected CTest pass validates this handoff only. Independently check frozen-core guard, original G9/G10/G11 Fortran source tests, and the inherited full single-site 143h scientific gate. This document does not claim any new CI result before it completes.
