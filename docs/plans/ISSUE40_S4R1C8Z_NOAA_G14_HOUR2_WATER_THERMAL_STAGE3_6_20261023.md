# Issue #40 S4-R1c8z — real NOAA second-hour G14 HEATFX/AIRDEN/ELUSTR/SLOPE stages 3–6

**Scope:** genuine NOAA 2022-06-01 02–03 UTC, 2 SS (one real missing wind) + 1 US, 82×85×9, 6907 LAND and 63 WATER. This source-only research branch is stacked after the now-mainline #272–#278 CALMET G14 first-hour atomic commit and secondhour stage 0–2, **not general P6 production acceptance**.

## Same-frame physical causal path

- G14 scheduler successfully commits hour one with source-native 45 P6F fields and `ZI/ZICONV/DPTT`, followed by AA/BB and CGAMMA publication.
- G26A on the actual second-hour frame executes original PREPDI 0, WIND1 1 and FRADJ 2, verified against G45/G21 cross-path source-native values.
- This branch extends only the real mixed-WATER G22 source admission from `hour_index==0` to `hour_index<=1`, requiring exact original SURF start/end/source series hourly bracket and already-admitted original GEO/station/WATER layout. G26A then executes native HEATFX stage 3, AIRDEN 4, ELUSTR 5 and SLOPE 6 sequentially on that **same scheduler-owned frame**. Original source G39 HEATFX/ELUSTR must still leave WATER friction/QH/EL absent until WATER COMP; C1/C2 non-WATER path and physical formulas remain unchanged.

## Numerical science gates

Independent `G17B4TwoPassSurfvar` reconstructs the two original hourly SURFVAR passes from independently computed G45 hour-two WIND1 and the separately source-recomputed G21 FRADJ. It drives `g39_original_noow_water_postfradj_thermal_reference` and `g22_original_slope_after_elustr` as comparison-only calculations; the actual G26A stage 3–6 does **not receive** their numerical outputs.

Require all quantities bit-for-bit equal (REAL4):

| Output | Values |
|---|---:|
| HEATFX temperature, AIRDEN density | 13,940 |
| ELUSTR QH, USTAR, EL | 20,910 |
| Post-SLOPE U, V, 9 levels | 125,460 |
| **Total** | **160,310** |

Reject source UTC mismatch, forged NOAA WATER identity, staging out of original order, any changed committed hour-one `ZI/ZICONV/DPTT`, advanced G14 completed hours, or published second-hour AA/BB/CGAMMA. Retain first-hour strict 313650-word P6F/G59 and 20910-word G54 parity, forced rollback, genuine secondhour WIND1 125460 and FRADJ 146370 gates.

## Remaining not accepted

This is independent **native source-to-native source** cross-path evidence, **not independent original Fortran secondhour scientific equality**. Hour-two G23 STHEOR/INTER2, G24 final WIND1 tail, G26B stages 12–15, P6F stage16, second-hour G14 atomic commit, six-hour all-45-fields original comparison, production P6, P7 and wet deposition remain NOT_ACCEPTED. Existing hour-zero-only downstream guards must remain. Do not automatically trigger expensive 143h C1/C2 tests. Issue #40 remains OPEN.
