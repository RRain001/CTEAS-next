# Issue #40 S4-R1c8w — first actual NOAA G14 17-stage atomic hour (research-only)

**Base:** Draft PR #275 (stage 16 P6F prepared-only), stacked after #274–#270 and merged #269. **Do not merge or claim science acceptance before exact-head CI passes.**

## New execution boundary

A new G65 research-only executable drives the existing `UnifiedMultistationHourlyScheduler::advance_with_fresh_physics`, *not* a loop of detached first-hour stage calls. On the authentic 2022-06-01 01–02 UTC NOAA 82×85×9 / 2 observed SS + 1 US / 6907 LAND + 63 WATER case, G26A runs original stages 0–11 and G26B runs stages 12–16 on the same `MultiHourFrame`. The authoritative G14 transaction validates native arrays and all 45 P6F fields **before** committing the three hidden planes `ZI/ZICONV/DPTT`.

Source `G43` MISSFC only fills missing **nonwind** model-internal surface fields. Raw ISD P5 winds and precipitation are checked unchanged. `G59` first-hour 45-field output and `G54` native COMP intermediate values are recomputed solely as **independent comparisons** and never supplied as G65 physical forcing.

## Acceptance gates in the new job

1. First full 17-stage candidate: require original-format 43 REAL4 + 2 INTEGER4 records, `45×6970 = 313650` bitwise words equal to independent G59 and all `3×6970 = 20910` hidden REAL4 values bitwise equal to G54.
2. Inject a controlled exception at the G14 precommit barrier **after** complete native physics and comparisons. Require `completed_hours=0`, original cold memory unchanged and both PREPDI AA/BB and CGAMMA clocks unpublished. The injection must be the observed cause of rejection.
3. Construct a fresh actor and repeat stages 0–16 with the same scheduler; this time allow G14 to commit. Require `completed_hours=1`, committed hidden memory bit-identical to G54 and **both clocks** published at the first-hour UTC end.
4. Check that G14 `preview_next_hour()` is on the second real NOAA UTC hour and references the just-committed `ZI/ZICONV/DPTT`. On this actual second-hour original source record, independently call the original scoped G43 `MISSFC` repair and verify both the preview's and repaired copy's wind/direction/precip remain exactly equal to raw P5. This is **input provenance only**, not second-hour physics.
5. Explicitly invoke a *fresh* G65 first-hour-only actor against that true second-hour frame and require deterministic rejection at stage 0, without advancing the scheduler or altering first-hour AA/BB/CGAMMA or the three committed hidden planes. This negative test forbids silently replaying hour zero as hour one.
6. Separately invoke authentic G18E4 PREPDI stage 0 on the scheduler's **actual second-hour frame**, reading source UP.DAT with the committed first-hour `ZI/ZICONV/DPTT` and AA/BB/CGAMMA histories. Require original upper station IDs, correct second-hour UTC, source AA/BB slot candidates, independent G18D2 station-clock preflight, and no G14/clock publication. This produces only a **real stage-0 uncommitted candidate**, not second-hour WIND1/FRADJ/COMP/P6F or second-hour original numerical parity.

The scope-specific executable refuses normal mode and emits no production CALMET.DAT or P7 artifact. The existing workflow keeps prior G41/G42/G47/G48/G54/G55/G56/G59/G61/G62 forensic gates and adds G65 with exact line receipts. The frozen C1/C2 science and expensive 143-hour suites remain manual-only.

## Remaining for S4

- True second hour with causal live AA/BB/CGAMMA + `ZI/ZICONV/DPTT`, not a detached hour-zero replay. In particular, current G63/G64 WATER COMP and P6F explicitly require `hour_index==0`; lift this only alongside independent hour-2 original Fortran parity.
- Legal NOAA six-hour loop with all 45 records **for each hour**, each hidden state and per-hour source/binary SHA; no original MET.DAT fields may backfill C++.
- Merge a supported dynamic production runner only after C1/C2 frozen regression, general site and station tests, new-site independent original CALMET comparison; Issue #40 remains OPEN and P7 is not admitted.

**2026-10-22 remediation:** Related #275/#276 builds now link the P6F CALMET.DAT writer centrally; WATER G63 stages keep unmodified COMP-third USTAR/EL for G54 audit but also expose native G53-neutral 63-WATER cells for the G64 P6F output. Strict G62 bitwise mismatch diagnostics report field/record/cell/bit patterns. The latest exact-head CI jobs remain queued; these changes are **not yet accepted**.

**Provisional status:** `G65_G14_FIRSTHOUR_ATOMIC=CI_PENDING`; `G14_SECOND_HOUR_PREPDI_STAGE0=CI_PENDING_PRECOMMIT_ONLY`; `G14_SECOND_HOUR_PHYSICS=NOT_ACCEPTED`; `NOAA_6H_45FIELDS=NOT_ACCEPTED`; `S4_P6_PRODUCTION=NOT_ACCEPTED`.
