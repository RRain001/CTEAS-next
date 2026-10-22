# Issue #40 S4-R1c8t — true same-frame NOAA G26B COMP WSTARR stage 14

Stacked on Draft #272 (G26B stage 13 AVEMIX) → #271 (stage 12 genuine native WATER/LAND MIXHT) → #270 (12 DIAGNO stages) → #269/#267, with already merged #266 G61 original-vendor hidden state parity and G62 source-native memory carrier.

## Bounded first-hour physical execution

NOAA actual 2022-06-01 01–02 UTC 2SS/1US (one missing SS wind), 82×85×9, 6907 LAND and 63 WATER, G38 neutral NOWSTA=0. The existing immutable `p6e::wstarr` physics now executes as **G26B stage 14** on the same `MultiHourFrame`, taking `ZICONV` exclusively from its actual G26B stage 13 post-AVEMIX candidate and QH, near-surface TEMP2D and density exclusively from its actual stage 12 original COMP third SURFVAR/HEATFX result. Uses genuine grid WATER category, with initial WSTAR zero for original firsthour cold start. Rejects negative/nonfinite WSTAR and any nonzero WSTAR across 63 original neutral-water cells.

Frozen original-source G55 is computed completely separately and **only for comparison** against the live G26B actor after stage 14. Require 6,970 bit-identical REAL4 WSTAR values and exact original source clock. Neither G55 nor any Fortran original output/trace supplies WSTAR input to G26B. The same gate continues requiring stage 12's 55,760 G54 exact words, stage 13's 13,940 exact G54 post-AVEMIX ZI/ZICONV, all 12 G26A source DIAGNO stages, G61 genuine Fortran original sixhour DPTT COMMON, native G62 20,910 source memory words and real NOAA source-backed 45-field firsthour output.

## Hard rejection

The immediate next G26B **stage 15 TEMP3D must explicitly refuse execution** on this PR. No stage 16 native 45-field P6F, no station AA/BB CGAMMA publication, no completed G14 17-stage hour, no actual hour 2 consumption of previous ZI/ZICONV/DPTT, and no sixhour ×45 causal comparison. The original previous state is immutable; `frame.next` must remain unchanged until an all-stage, precommit-validated transaction. Any source-native cross-path comparison failure blocks acceptance: never relax frozen tolerance, invent weather or substitute original Fortran values as native inputs.

The C1/C2 all-LAND path, manual-only 143-hour tests, original physics and P7 policy remain unchanged. Issue #40 OPEN. This stacked PR remains Draft pending exact-head CI, original numerical receipts and downstream dependency merges.
