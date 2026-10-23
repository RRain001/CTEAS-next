# Issue #40 S4-R1c9c — authentic NOAA second-hour AVEMIX stage 13 (source-only)

Base: accepted #280 (G26A stages 0–11) and #281 (secondhour G26B MIXHT stage 12). The first authentic 2022-06-01 NOAA hour has fully committed to G14, including native firsthour 45-field P6F source parity and ZI/ZICONV/DPTT; station AA/BB and CGAMMA clocks are published ONLY following that commit. The second hour has 82×85 cells, 9 layers, 2SS/1US and 63 original WATER cells.

On the same uncommitted secondhour G14 scheduler frame, G26B runs stage 13 AVEMIX only after physical original-source MIXHT stage 12. It uses the source READCF `ILEVZI`, `MNMDAV`, `HAFANG`, authentic final 9-level G24 wind U/V and the stage12 pre-AVEMIX ZI/ZICONV. **No independent/reference array enters the live G26B actor.** The hour-index scope remains strictly limited to hours 0 and 1; original hour-zero implementation remains unchanged and the secondhour phase >1 (WSTARR/P6F) remains denied.

## Bitwise science gate

Two read-only comparators must equal the live G26B stage13 result:

1. A separate source-native G26A stages 0–11 + G26B stages 12–13 causal reconstruction from `scheduler.preview_next_hour()` with the same verified firsthour G14 committed memory and source clocks.
2. Direct `g18c1_original_avemix_rebuild` driven by independently computed secondhour source G23/G24 final U/V and the separately reconstructed secondhour MIXHT ZI/ZICONV; original READCF controls and native physics only.

Both `ZI` and `ZICONV` 82×85 REAL4 grids must be bitwise identical, **13,940 REAL4 values** per comparison. Check stage13 is native completion without G14 atomic commit. An attempt at secondhour stage14 WSTARR MUST fail closed. Committed firsthour ZI/ZICONV/DPTT arrays and published AA/BB/CGAMMA clocks must be unchanged, with `scheduler.completed_hours()==1`.

This is **source-native cross-path and causal replay equivalence**, not independently computed *pristine original CALMET Fortran* hour-two parity. Hours 2–5, secondhour WSTARR/TEMP3D/P6F, atomic commit, full sixhour 45-field CALMET.DAT, general P6/P7 and wet deposition remain unaccepted. Do not automatically run the 143-hour frozen full suites. Keep Draft pending latest exact-head CI. Issue #40 OPEN.
