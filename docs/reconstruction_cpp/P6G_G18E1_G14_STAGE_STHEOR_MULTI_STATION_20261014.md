# P6G G18E1 — G14-stage STHEOR/MIXHTST/DIAGI multi-station handoff

Date: 2026-10-14. PR #63 remains **Draft**, stacked on the
accepted and frozen PR #53 single-station CALMET hourly physics.

## What G18E1 actually changes

The original selected 2SS/2US G17C3 calculation was previously performed
manually by the integration test, then supplied to G17's pre-INTER2
DIAGI handoff. G18E1 now executes that same G17C3
`selected_station_diagi_from_previous_comp` **inside**
`NativeHourStage::DiagnoStheorElustr2Mixhtst`, which is the ninth
(0-based index 8) stage in frozen PR #53's 17-stage
`kHefeiOriginalStageOrder` array.

At this exact stage it:

1. Reads the same frame's immutable **previous-hour** ZI, ZICONV and
   DPTT and source-stamped multi-SS and multi-UP observations.
2. Executes the existing, independently tested frozen #53
   ELUSTR2/MIXHTST/SIMILT kernels through G17C3; no physics formula is copied.
3. Combines only the **surface** DIAGI station columns into G16
   INTER2 input, retaining the original neutral WIND1 profiles and the
   original PREPDI upper-air columns.
4. Calls G17's mandatory first-WINDBC-then-DIAGI handoff. INTER2
   cannot execute before that handoff.
5. Exposes the exact station results to the subsequent selected G18A
   MIXHT and G18D4 4-stage COMP path. The independent direct G17C3
   result remains only a **numerical comparison oracle**, not the
   selected COMP input.

The integration test compares station IDs, selected upper station IDs,
site indices, filled vertical layers, station MIXHTST DPTT and complete
SIMILT U/V arrays. It also verifies untouched WIND1, preserved upper
PREPDI columns, and downstream G18A / G18D4 candidate equality.

## Fail-closed boundaries

- Production `MultiHourPhysics::run` returns `{Unknown,false}`.
- A stage other than `DiagnoStheorElustr2Mixhtst` is rejected.
- Wrong input hour, missing source controls, unmarked test-only
  configuration and repeated stage execution are rejected.
- G17 refuses DIAGI before original first WINDBC, and G16 refuses
  INTER2 before a valid DIAGI refresh.
- No arbitrary changes to original CALMET/PR #53 physics,
  tolerance, or source-file ownership were made.

## CI and incomplete science

At commit `0d3233c4c126c862e180e339ae5896425cb98255`:
- P6G selected Debug/Release:
  https://github.com/RRain001/CTEAS/actions/runs/38583268006 — PASS.
- Single-station 143h P6D/P6E/P6F:
  https://github.com/RRain001/CTEAS/actions/runs/38583267740 — PASS.
- Three older P6D jobs failed because their sparse checkout lacked the
  independently required P6G source met.inp/output; this is a CI
  fixture-ownership failure, not measured Fortran/C++ physical divergence.
  Their workflow CTests were restricted to the existing P6D scope.
  Verify those workflow re-runs on the latest branch SHA separately.

**NOT accepted:** complete production native G14 17-stage multi-SS/UP
physical executor, all-hour state publication, real 2SS/2US original
CALMET.DAT 45-field parity at 1/6/143/annual time spans, or full P6F
transactional restart. The selected-hour adapter alone cannot prove them.
Keep #63 Draft, only use GitHub-hosted Ubuntu and retain frozen #53.
