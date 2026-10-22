# Issue #40 S4-R1c8o — first shared G19/G14 source entry for authentic NOAA mixed WATER (no hour commit)

## Purpose

Reduce the real integration gap between the separately verified source-native G54/G59/G62 physics and **the same G19 → G14 clock/source owner** that executes previously frozen C2 17-stage calculations. This PR **does not execute a second hour** and **does not re-label the G62 firsthour state candidate as committed G14 memory**.

## Source-bounded behavior

The original `g19_load_original_source_case(paths)` admission retains unchanged **all-LAND default** behavior. New explicit research-only `g19_load_original_source_case(paths, true)` must use the existing G38 `NOWSTA=0`, `ITWPROG=0`, `ICOARE=10`, `NOOBS=0`, `IAVET=1`, `ISURFT=-1`, default HFLUX, neutral WATER-source controls, including exact source WATER ordinal inventory. It constructs **the same `G19FileBackedCase`** with original GEO/SURF/UP/deck station ordering and G14 scheduler, rather than manufacturing any second station, fictitious wind, `DPTT`, or `ZICONV`.

G62 now also loads this explicit source-ready case, builds **one scheduler** from it, previews the first authoritative G14 frame, and executes the **real G26A's original stage-zero G18E4 PREPDI source AA/BB and per-US CGAMMA staging, followed on the same frame by the genuine G26A G20/G16 sparse-WIND1 stage** against that frame with `G18D2StationClockAuthority`. This checks original source UTC, station cardinality, preflight state, and that **no station clock is published before a completed G14 hour**. It then compares real G54 candidate memory to first-hour source-native G59 output as before (20,910 REAL4 bit-identical). Existing original Fortran sixhour DPTT COMMON independent parity is retained from G61.

The `G62` evidence explicitly emits `G14_SOURCE_PREPDI=STAGED_UNPUBLISHED` **and** `G14_STAGE1_WIND1=G26_NATIVE_BITWISE_G42`. G26's 82×85×9 grid U and V WIND1 fields (125,460 REAL4 values) are compared bitwise with a separately calculated G42 genuine NOAA WIND1. That independent reference is never used as the G26 actor's forcing; both use original source data and the frozen native G9 arithmetic. The stage-2 checkpoint checks 146,370 REAL4 numbers (9×82×85×2 FRADJ U/V plus 3×82×85 GAMMA/TEMP2D fields) against the independently called G41 original-source branch using frozen native G21 arithmetic, never original output fields. Both markers are required by the existing scientific gate. Without a real 17-stage execution, the actual G14 scheduler counter remains zero and next-hour `PREPDI/DIAGNO/COMP/P6F` cannot be marked accepted. **A preflight is not a transaction or a physical stage-result admission.**

## Original COMP MISSFC materialization and negative provenance

Original CALMET `COMP` calls `MISSFC` *before* `DIAGNO`, so source-owned cloud/ceiling/temperature/humidity/pressure must be repaired internally before the genuine IAVET SURFVAR/FRADJ physical stage. G62 now uses the existing Fortran-source-scoped G43 implementation to create a detached, first-hour model-internal source copy and passes that same resolved content to both the G19/G14 candidate and independent G41/G42 audit path. The original NOAA P5 surface observation buffer remains unchanged: neither missing wind `wind_valid=false` nor wind speed/direction/precipitation is imputed. All five nonwind fields must become source-valid. The accepted G43 source case is the only source of their repair; original CALMET output or trace values are never input to native code. The CI receipt must report `S4R1C8O_G14_G43_RAW_P5_WIND=UNCHANGED`.

The independent G42/G41 bitwise comparisons are **shared native-kernel reproducibility** checks, not a standalone independent Fortran result. The preexisting `S4-R1c4b` frozen original-vs-native WIND1/FRADJ science and original-source numeric checks remain separate, and the scientific gate cannot be promoted to native G14 production solely based on these source-path comparisons.

A lightweight workflow `issue40-s4r1c8o-g14-three-stage-compile.yml` also builds the real C++ G62/G19/G26 executable and runs negative tests on an ordinary PR. It avoids the repeated full data restoration cost of the separate authentic NOAA 6h × 45-field science gate. Full C1/C2 143-hour workflows stay `workflow_dispatch` only.

## Why this does not already make C2 G14 accept the real case

The former G26 DIAGNO stage-1 dense G20 mask has been replaced by the **existing sparse source-option G20/G16 kernel only for explicit G38 opt-in**, preserving dense C1/C2 operation. The G26 **stage 2 FRADJ** now also consumes that same-frame WIND1 and PREPDI CGAMMA through original-source G21 with explicit G38 WATER mode. G26 stages **3–11** (HEATFX/ELUSTR, STHEOR/INTER2, wind tail) and G26B all-land COMP still need mixed-WATER scientific admission; true WATER/land merged mixing from G53/G54 has not yet been moved **inside the single G14 17-stage actor**, nor tested as next-hour history. Changing the G19 input contract alone cannot fix these physical dependencies. G26A/G26B production `run()` remains fail-closed. No original model values are input to native physics.

## Subsequent acceptance

1. **Done as code, pending exact-head CI:** reuse G41/G42 sparse missing-WIND1 inside G26 G14 stage 1 with 125,460-field bitwise parity, and the source-owned G21 FRADJ in G26 stage 2 with 146,370-field G41 cross-check.
2. Reuse accepted WATER heat/neutral mixing, G23 sparse STHEOR/DIAGI and G53/G54 LAND/WATER MIXHT/AVEMIX in G26/G26B on that **one** G14 frame. Preserve previous `ZI/ZICONV/DPTT` exactly and do not source them from `CALMET.DAT`.
3. Only after native P6F, source clocks, and physical memory pass independent original-vendor firsthour 45 field + hidden state, allow atomic commit. Run authentic hour 2 with actual hour-1 committed prior. Independently compare 2h then 6h×45 vs pristine original, including hidden DPTT history and failure rollback.
4. Retain the C1/C2 original-scoped 143h scientific baselines and the S4-A existing architecture audit. Do not automatically trigger full 143h. Issue #40 remains OPEN, P7 and wet deposition NOT_ACCEPTED.

**Status:** G14 true next-hour causal execution = `NOT_ACCEPTED`; first-hour source clock and G62 COMP seed gate = `CI_PENDING` until exact-head validation.
