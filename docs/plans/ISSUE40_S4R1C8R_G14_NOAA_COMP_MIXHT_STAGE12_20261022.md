# Issue #40 S4-R1c8r — original-source real NOAA G26B COMP stage 12 on the same native G14 frame

Depends on Draft #270 (0–11 stages, sparse STHEOR/INTER2/G24), #269 (same-frame G39/G22 WATER thermal/SLOPE), #267 (G19/G26 firsthour PREPDI/WIND1/FRADJ), merged #266 (G61 authentic Fortran hidden-state parity + G62 native ZI/ZICONV/DPTT seed).

**Scope:** firsthour 2022-06-01 01–02 UTC only, genuine NOAA 2SS/1US (one SS missing wind), 82×85×9, 6907 LAND+63 WATER, original G38 NOWSTA=0 neutral WATER. Research opt-in must be explicit; all prior C1/C2 all-land selected stage paths are unchanged.

## The first true COMP stage within one actor

New `p6g_g63_real_noaa_g14_comp_mixht.hpp` computes the **G26B stage 12 MIXHT** from the *same live G14 frame* populated by the actual G26A stages 0–11, without reading any independent G54 outputs:

1. G26B requires the original G24 final native 3D U/V/W on `frame.fields`, source PREPDI UP, G23 valid STHEOR/MIXHTST site DPTT, G19/G38 original controls, and still-unmodified previous `ZI/ZICONV/DPTT`.
2. Reproduce the original COMP third `SURFVAR(IALL=1)` from G26A's actual WIND1, FRADJ and G24 final U/V. Recompute COMP-stage HEATFX and ELUSTR using frozen P6E kernels with G38 original neutral-water defaults.
3. Compute original neutral WATER `NOWSTA=0` ZI, QH, USTAR and EL from the **live** G24 wind through existing G53/G37/G35/G36; bind the original source-water 63 cell indices. No original or independent G54 Fortran values are injected.
4. Set initial-land `ZI/ZICONV/DPTT` from `frame.previous`, inject the single observed-valid SS MIXHTST DPTT into its original grid cell without renumbering the missing SS, and calculate LAND MIXHT through unchanged P6E `mixht_observed_mc`. Assert its WATER ZI/ZICONV remain exactly unchanged.
5. Keep `frame.next` identical to `frame.previous`. G26B stores an uncommitted, source-only stage-12 candidate, never a P6F or production result.

The separate real NOAA G54 source-native pipeline is then run strictly **after** stage 12 and its result used only for comparison. Require **8×6970=55,760 REAL4 words byte-exact** for pre-AVEMIX ZI/ZICONV/DPTT, COMP-third temperature, QH, density, USTAR and EL; independently require the 6907 LAND/63 WATER cells and one valid/one missing SS. Reject any discrepancy without relaxing tolerance, using original CALMET intermediate as input, modifying source P5 wind or carrying external numerical memory.

## Fail-closed gates

The unimplemented G26B stage 13 (AVEMIX) is expressly attempted by the forensic check and **must reject it** without altering native `frame.next`, previous memory or station clocks. Stages 13–16, true firsthour 17-stage commit, second-hour causal previous-state use, sixhour native 45-field equivalence, production P6/P7 and wet deposition all remain `NOT_ACCEPTED`. The existing original Fortran DPTT COMMON and authentic original MET 45-field science checks are still separately mandatory.

No complete 143-hour acceptance can be automatically triggered. Issue #40 remains OPEN. This PR stays Draft until exact-head compile, independent source comparisons and real NOAA checks pass.
