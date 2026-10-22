# Issue #40 S4-R1c8q — shared source-native G14 through all 12 real-WATER DIAGNO stages

Depends on Draft #269 (G22 same-frame mixed LAND/WATER heat and SLOPE), Draft #267 (G19/G26 source PREPDI, sparse WIND1, FRADJ), merged #266 (G61 first-hour hidden memory original parity and G62 native carrier). **This PR remains a source-scoped scientific trial, not a production admission, actual hour commit, or an original-vendor 45-field end-to-end acceptance.**

## Native physical scope

One original G19-file-backed NOAA 2022-06-01 01–02 UTC source, 2SS/1US and 82×85×9, one actual EDITL-missing SS wind and 6907 LAND/63 WATER, one authoritative G14 scheduler and stage frame:

- G26A native stages 0–2: source-G43 nonwind MISSFC in detached COMP copy, G18E4 staged PREPDI AA/BB/CGAMMA, G20/G16 original-sparse WIND1, G21 FRADJ / two original SURFVAR passes;
- G26A stages 3–6: source G39 neutral-WATER HEATFX/AIRDEN/ELUSTR and G22 frozen SLOPE from same previous G14 state;
- **This PR:** stages 7–11: source G23 first WINDBC, station STHEOR/MIXHTST/DIAGI, G16 INTER2, and existing G24 final WINDBC/SMOOTH/DIVCEL/W on that SAME G14 frame.

The existing G23 C1/C2 dense all-LAND path remains unchanged by default. The optional G19 research WATER type explicitly activates the original missing-SS mask. `selected_station_diagi_from_previous_comp(..., true)` computes only source-valid SS STHEOR without converting missing wind to calm; `merge_g17c3_surface_diagi(..., source_wind_valid)` retains the exact 2SS + 1US original source column identity throughout DIAGI/INTER2. No station interpolation, synthetic observation, original Fortran intermediate value, or clock output is injected.

The same G26A stage 11 supplies native `U/V/W` in `frame.fields` for eventual G26B COMP. In this PR G26B stage 12–15, P6F stage 16, full-hour state commit, and any hour-2 input are **not executed**. PREPDI AA/BB and CGAMMA are still staged and uncommitted. The previous ZI/ZICONV/DPTT remains owned by the scheduler.

## Read-only verification

Existing independently executed G48 source-native original NOAA forensic path computes sparse STHEOR, post-INTER2 U/V and G24 final wind. Run it without any output fed back to G26A, then require bitwise parity for:

| REAL4 source-native comparison | Values |
|---|---:|
| INTER2 U/V (82×85×9×2) | 125460 |
| G24 final U/V (82×85×9×2) | 125460 |
| G24 W on 10 faces (82×85×10) | 69700 |
| **Total** | **320620** |

Also require the **one genuine observed valid SS identity** to agree, one missing SS to remain masked, all G26 field arrays to equal actual G24 stage output, exact source UTC and stage cursor 12, unchanged prior G14 ZI/ZICONV/DPTT, zero G14 committed hours and no published station clocks.

This same-kernel cross-path check is **not** original Fortran parity by itself. The separate authentic NOAA original sixhour numerics (WIND1, FRADJ, MIXHT/AVEMIX, full MET21) remain independent gates and cannot be bypassed. Frozen all-LAND C1/C2 science, source input data, 143h manual-only trigger policy, equations and numerical tolerances are not changed.

## Remaining blocker

The firsthour source-native G14 DIAGNO is only complete after independent numerical checks. Original neutral-WATER G26B COMP still rejects WATER sites, even though external G54 validates partial real firsthour MIXHT/AVEMIX. To achieve the **actual causal second hour**, integrate G53/G54 land + WATER COMP inside G26B, execute P6F stage 16, verify original 45 records and hidden ZI/ZICONV/DPTT + station AA/BB/CGAMMA state, then perform atomic G14 commit before advancing the original source clock. Without that, 2h, 6h, G26 and P7 remain NOT_ACCEPTED. Issue #40 remains OPEN. CI is pending on exact PR HEAD.
