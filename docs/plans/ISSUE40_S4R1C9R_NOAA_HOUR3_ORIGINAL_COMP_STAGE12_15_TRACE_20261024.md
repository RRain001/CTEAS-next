# S4-R1c9r — original CALMET third-hour COMP stage12–15 oracle

## Provenance and exact result

- Stacked after Draft PR #305 HEAD 7b01137ae310c36a798746992d085b84953d0301. This change is strictly a SHA-pinned, scratch-only original Fortran diagnostic generator, parser and negative tests. No native G26B/G63/G64 guard or production code changed.
- Genuine NOAA 2022-06-01 02–08 UTC, 82x85x9, 2SS/1US. Original CALMET 6.5.0 source SHA256 835c351d780c0200be721c2d9cbb8dc45b3a8fcd4cb8815fc47bbd26a56a7b23. Original source directory remained read-only and clean.
- Scratch instrumented GFortran11 executable SHA256 17f39d00ab0767e71efab703566d09016582d93c6e4fb4e450ae30f9d58ffa25. Full six-hour instrumented MET.DAT SHA256 a7004fbf780212d58536be3957306c2aecc53abe2e58bfec870571b12d8b8e14, byte-identical to independently frozen pristine original MET. Original COMP trace SHA256 4851f7be2d19df7a6e5e2cf5d73653c282cfea579b9c0b2444365a842d27a02e.
- Original source trace and MET remain private under /home/lhy/dev/CTEAS-next/local-science/s4-r1c9r-hour3-original-comp-20261024; no raw vendor code, executable, input or numerical field arrays uploaded.

## Original third-hour source stages (end 04 UTC)

| Stage | Capture point | Original REAL4 words |
|---|---|---:|
| 12 | After LAND MIXHT: ZI, ZICONV, QH, TEMP2D, RHO, USTAR, EL | 48,790 |
| 13 | After AVEMIX: ZI, ZICONV | 13,940 |
| 14 | After WSTARR: WSTAR | 6,970 |
| 15 | After TEMP3D: 9-level ZTEMP | 62,730 |

- **24/24 original stage records, 794,580 finite REAL4 words** over six hours, with exact hour/stage/grid sequence. Third hour has 132,430 original words available for subsequent independent native G26B comparison.
- Third-hour post-MIXHT mean ZI 944.077743 m; post-AVEMIX mean ZI 943.739087 m; WSTAR max 2.003653 m/s; TEMP3D range 284.150879–304.150116 K.

## Cross-subroutine WATER transition

- The same independent original G22 third-hour DIAGNO stage40 trace was SHA-verified alongside the original GEO mask (63 WATER cells). At original COMP stage12, after COMP WATER and LAND MIXHT, **WATER USTAR differs from DIAGNO USTAR in all 63/63 cells**, while **WATER EL remains bitwise identical in all 63/63 cells**.
- WATER USTAR COMP-minus-DIAGNO delta range 0.099064671 to 0.193589969 m/s, mean 0.175870099 m/s. This is a real source-stage transition: native hour-three COMP must not simply reuse DIAGNO WATER USTAR, nor silently zero it. The source cause is consistent with COMP WATER flux recalculation but needs dedicated native stage12 validation before asserting complete physical parity.
- The captured stage12 ZI/ZICONV are **post LAND MIXHT**, not the pre-MIXHT prior-hour state. Comparing stage12 directly against prior-hour post-AVEMIX as an equality requirement would be scientifically incorrect.

## Software tests and remaining science

- New Python parser/negative tests 11/11 PASS: original SHA drift, wrong stage/hour/grid, truncation, trailing data, nonfinite, temperature range, forged MET and source. Original instrumented source compilation and six-hour run PASS, original MET byte-identity PASS.
- **Original-vs-native third-hour COMP stages12–15 NOT_RUN.** Third-hour G26B/G63/G64 hour>1 guards remain unchanged. Third-hour stage16 P6F, positive G14 commit, hours4–6, generic P6/P7 and independent scientific review remain NOT_RUN/NOT_ACCEPTED.
- Next: introduce a strictly test-only native third-hour G26B stage12 candidate using native committed hour-two ZI/ZICONV/DPTT, native G26A hour-three final wind and current-hour COMP WATER state; compare to this independent original stage12. Only then consider stages13–16; do not relax thresholds or remove production guards.
