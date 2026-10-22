# Issue #40 — S4-R1c8l first-hour real NOAA post-COMP memory preflight

Date: 2026-10-22. Frozen base [merged #263](https://github.com/RRain001/CTEAS-next/pull/263), `main@a899c31349c57462069c8e38925ef49acffc719b`.

## Why this is the next gate

The accepted source-native first-hour `CALMET.DAT 2.1` contains 45 original OUTHR fields, but it **does not contain** G14's hidden persistent `ZICONV` or `DPTT`. Therefore the successful 45-field output cannot safely be used as a stand-in for the state handed to the next model hour. Original COMP uses the previous committed state at each hour; the source-only first-hour G54 candidate separately computes post-MIXHT `DPTT` and post-AVEMIX `ZI/ZICONV`. Do not reconstruct this hidden memory from `CALMET.DAT`, and do not infer that all DPTT is zero.

## Concrete implementation

Reuse existing native G54's **five real physical planes** (post-LAND MIXHT ZI/ZICONV; post-AVEMIX ZI/ZICONV; source-computed DPTT) and existing G59 fully assembled source-native one-hour `CALMET.DAT`, with no new physical formulas. The independent G60 comparator checks genuine 2022 NOAA 2SS (one actually wind missing)+1US, 82×85×9 with 6907 LAND+63 WATER:

- Require successful **exact-source** original pinned six-hour `MET.DAT` and write-only `MIXHT→AVEMIX` stage trace receipts, and independently accepted G54 and G59 receipts. Matching SHA256 and frozen tolerance-zero are mandatory; stale or wrong-case receipts fail closed.
- Require bitwise identical `ZI` between native G54 after AVEMIX and the actual G59 serialized 45-field `ZI` record. **No original physics is passed to either native producer.**
- Independently compare the 6970 `ZI` and 6970 `ZICONV` source-native post-AVEMIX states with the untouched original Fortran COMP stage-3 six-hour write-only trace *for the first hour*. The frozen tolerance is `abs_error <= 5e-3 m + 5e-5*max(abs(original),abs(native))`, with zero violations.
- Validate all 6970 native DPTT entries are finite and not missing. **Fortran DPTT numerical parity is NOT yet established**: unlike ZI/ZICONV, DPTT is not part of the #257 original stage trace and not stored in 45-field `MET.DAT`. Recording a finite native array is not an original-science PASS.

A strict synthetic self-test must reject altered serialized `ZI`, nonfinite DPTT, and out-of-tolerance ZI, without requiring any vendor asset. Full source gate and frozen C1/C2 regressions must pass on exact PR HEAD. Keep Draft until then; no Copilot review.

## Subsequent milestones

1. SHA-pin independent original write-only `DPTT` history at the actual relevant COMP stage and prove first-hour native/original DPTT parity. Do not infer an internal Fortran array from its name without source-level audit.
2. Bind full per-hour G54/other source actors to **one** G14 transaction with `previous = last committed ZI/ZICONV/DPTT`, no out-of-band stage replays, original missing-wind station ordinal preserved, and negative tests for skipped hour/rollback. All 17 physical slots must execute valid native kernels; do not fake stage-complete flags.
3. Run and compare authentic six consecutive hours, `6×45` full original records, with source SHA and nonzero/memory-change evidence; only later promote C1/C2 same new executable and original/P7 production admission.

This gate has the narrow success label `PASS_SOURCE_SCOPED_FIRSTHOUR_NATIVE_COMP_MEMORY_ZI_ZICONV`; **G14 state commit, DPTT original parity, six-hour causal wind, G26, and P7 are NOT_ACCEPTED.** Issue #40 remains OPEN.
