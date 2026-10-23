# Issue #40 S4-R1c9b — genuine NOAA second-hour G14 mixed WATER/LAND MIXHT stage 12

**Base:** main after merged #280, which has accepted authentic secondhour source-native G26A stages 0–11 and exact 320,620 REAL4 G23/G24 cross-path. This PR is scoped to a **second-hour stage-12 candidate only**, not whole-hour acceptance.

## Causal G14 handoff

The authentic 2022-06-01 first-hour 82×85×9, 2SS+1US, 63 WATER/6907 LAND G14 transaction executes and commits, preserving the 45-field original G59 audit plus 20,910 exact hidden-state REAL4 checks. On the next, distinct original NOAA SURF hour, source AA/BB and CGAMMA are inherited from that committed first-hour only. The actual G26A live stage 0–11 executor computes source-valid station STHEOR/DIAGI, INTER2 and final G24 U/V/W with no missing-wind-as-calm replacement. Stage 12 on this SAME live frame invokes G26B and genuine original-water G63 WATER neutral-state, G53/G52 source partition and native LAND MIXHT. The previous hidden state comes from the actual G14 scheduler memory, not any G54/G59/original Fortran oracle fields.

The former hard-coded `hour_index==0` guards in G52, G63 and G26B are explicitly extended **only to index 1**, with exact current-hour observed SURF start/end bounds, original six-hour series and firsthour-to-secondhour UTC contiguity. G26B stage 12 uses the exact current-hour `wind_valid` station count and source ordinal; it must preserve one-hour source-case semantics and retain the frozen firsthour behavior.

## Scientific gate

A detached second-hour frame is separately created from the same **committed firsthour** scheduler. A fresh G26A runs all native stages 0–11 using observed source and published source clocks, followed by a separate G26B stage12 (MIXHT). This is a deterministic **causal native-physics re-execution gate**, not independent pristine CALMET Fortran numerical equality. No detached arrays are supplied to the live actor.

Require bitwise identity across the following 8 REAL4 grids:

| State/forcing | REAL4 count |
|---|---:|
| MIXHT pre-AVEMIX ZI, ZICONV, DPTT | 20,910 |
| COMP-third SURFVAR temperature, QH, rho, USTAR, EL | 34,850 |
| **Total** | **55,760** |

Fail closed if the secondhour station count/IDs differ from actual source P5 validity, any WATER/LAND ordinal changes, current-hour source UTC changes, or live physical G24 is absent. Following stage12, an explicit attempt to execute **stage13 AVEMIX must be rejected**. The scheduler remains at `completed_hours==1`, committed ZI/ZICONV/DPTT equal firsthour, and upper AA/BB and CGAMMA clocks remain published only for the firsthour UTC. Retain all previous exact-head firsthour 45-field and hour2 G26A tests. No direct original-vendor hour2 MIXHT comparison is claimed.

**Unaccepted:** secondhour AVEMIX 13, WSTARR 14, TEMP3D 15, P6F 16, G14 atomic hour2 commit, original six-hour 45-field parity, generic P6/P7 and wet deposition. No automatic frozen 143-hour suite; Issue #40 OPEN. Remain Draft pending real NOAA exact-head CI.
