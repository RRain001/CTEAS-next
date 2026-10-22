# Issue #40 S4-R1c8x — genuine NOAA G14 second-hour WIND1, stages 0–1 (uncommitted)

**Stacked after:** Draft PR #276, which has confirmed exact-head real NOAA G65 first-hour atomic 17-stage validation and second-hour PREPDI stage-zero candidate. This PR only advances the second **actual** source hour to G26A stages 0 (PREPDI) and 1 (WIND1). No P6 production admission.

## Physics provenance

The running scheduler completes first-hour G14 stages 0–16 using actual 2022-06-01 01–02 UTC NOAA SURF/UP/GEO inputs; compares all 45 native P6F record words and the hidden `ZI/ZICONV/DPTT` against independent G59/G54 and publishes source AA/BB and CGAMMA clocks only after successful P6F precommit. The immediately following hour-two `scheduler.preview_next_hour()` has `hour_index=1`, true next observed UTC, authentic SURF/UP source bindings and the committed original-constrained hidden state.

For hour two, a new `G26SourceFileBackedG14DiagnoBridge` is constructed with this live scheduler and source clocks, then calls the existing scoped native CALMET stages **0 and 1**, in exact stage order. G18E4 computes this hour's upper buffer and CGAMMA from the committed previous state; G20 executes the actual `SIMILT` / `VERTAV` / `PREPDI` sparse-wind source columns; the existing G16/G9 WIND1 physical kernel calculates the nine-layer `U/V` first guess.

G45 is calculated separately from six real consecutive NOAA source hours, as an **independent source-only comparator**, not an input to G26A. Require `2×9×82×85 = 125460` REAL4 `U/V` values bitwise identical for hour two. The existing G45 workflow independently verifies source-native six-hour WIND1 against pinned original CALMET scratch arrays; this PR's G65 job establishes the *same live G14 frame* handoff, not a separate new Fortran parity proof.

## Fail-closed evidence

- Retain #276's first-hour `313650` P6F words, `20910` hidden COMP REAL4, rollback and station-clock gates.
- Retain real second-hour raw SURF, G43 MISSFC nonwind repair and forbidden first-hour actor-replay checks.
- Require live hour-two G26A `PREPDI` / `WIND1` both return `NativeCpp,true` in original stage order, and exact G45 source `U/V` parity.
- Require `scheduler.completed_hours()==1`, source AA/BB and CGAMMA clocks remain at hour-one UTC, live `frame.next` equals committed `ZI/ZICONV/DPTT`, and no second-hour P6F, G14 commit or clock publication.
- Preserve exact-head CI; do not fake missing SS wind as calm, fill source P5 wind or use any original CALMET numerical fields as C++ physics inputs.

**Not accepted:** second-hour FRADJ stage 2, G22/G23/G24 DIAGNO, COMP stages 12–15, P6F stage 16, independent original second-hour 45 fields, six-hour native 45-field causality, generic production P6 or P7. Do not run the frozen 143-hour suites automatically. Issue #40 remains OPEN.
