# Issue #40 S4-R1c9a — authentic NOAA second-hour G14 STHEOR/INTER2/G24 DIAGNO, stages 7–11

**Scope:** genuine NOAA 2022-06-01 02–03 UTC, 2 SS and 1 US, 82×85×9 (6,970 horizontal cells), source-inferred LAND/WATER (63 WATER); second hour of the authoritative six-hour sequence. Stacked after merged #279 (genuine hour two G22 thermal/ELUSTR/SLOPE) and merged #278 (second-hour FRADJ). Research-scoped; not production P6/P7.

## Causal physical execution

1. Hour one is actually computed with G14 stages 0–16 and atomically commits 45 P6F output planes and the three `ZI/ZICONV/DPTT` arrays, while source AA/BB and CGAMMA clocks publish only on successful commit.
2. On **the same live second-hour G14 frame**, G26A stages 0–6 recompute observed UP/PREPDI and SURF/WIND1/FRADJ/G22 using current source input and the previous committed COMP state.
3. This PR source-admits only hour 0 and hour 1 for the original sparse-water G23 code; demands matching authoritative hourly SURF UTC bounds and preserves the original SS ordinals. The first hour retains one valid / one missing wind observation. The second uses **its own P5 hourly wind-validity mask**; require at least one source-valid station, matching candidate count and exact source SS identity in both native paths, never missing-as-calm.
4. Stages 7–11 use G23 post-SLOPE station STHEOR/MIXHTST and DIAGI from previous `ZI/ZICONV/DPTT` and source stations, then G16 INTER2 and G24 original WINDBC/SMOOTH/DIVCEL/W. The final 3-D wind is handed to the live frame as pending COMP input; no COMP/P6F or secondhour atomic commit occurs.

## Strict source-native cross-check

Recreate the identical raw NOAA second-hour source as an independently obtained `scheduler.preview_next_hour()` frame with the **same committed previous-hour hidden planes**. Rebuild independent G20 source profiles and previously calculated independent G45/G21 FRADJ; recalculate G22 thermal & SLOPE from source. Re-run G23 and G24 completely separately from the live G26A actor. The comparison is read-only; no oracle arrays enter the live actor.

| Field | REAL4 bitwise comparisons |
|---|---:|
| Original station STHEOR + INTER2 U/V (9 layers) | 125,460 |
| Final G24 U/V (9 layers) | 125,460 |
| Final G24 W (10 faces) | 69,700 |
| **Total** | **320,620** |

Also require the actual second-hour source-valid surface-station identities in original ordinal order (no fabricated station), same genuine second-hour UTC end, original stage cursor 12, identical G14 live frame `fields.u/v/w_face`, **unchanged committed** `ZI/ZICONV/DPTT`, G14 completed hours still 1, and AA/BB/CGAMMA still at hour-one UTC. An error at any stage fails closed.

## Scientific limitations

This checks two independent evaluations of source-native kernels, **not independent original CALMET Fortran numeric parity for hour two**. It does not admit G26B COMP stage12–15, P6F stage16, hour-two G14 commit, native sixhour 45-field original science, generic P6, P7, or wet deposition. Existing explicit hour-zero-only COMP/P6F guards remain untouched. Scope cannot be expanded to later hours by changing indices alone; prior hidden memory and station chronology must first be verified. CI must pass on exact PR head; complete 143h frozen regression remains manual-only. Issue #40 stays OPEN.
