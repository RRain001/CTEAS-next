# Issue #40 S4-R1c8m — source-pinned original CALMET `/tjump/ DPTT` six-hour trace

Baseline: S4-R1c8l merged PR #264 (`main@35d4eee66b23c94956e45d3fc523b28c90a950bf`). This is a **research-stage scientific check**, not G14/P7 production acceptance.

## Source audit

The unchanged `RRain001/CTEAS` original CALMET 6.5.0 source at exact Git blob `437f43bb7f0e51a1919e56664663e1a046986ed0` has, in `calmet.for`:

- Original `BLOCK DATA` lines **1745–1746**: `common /tjump/ dptt(mxnx,mxny)`, initialized to zero.
- Original COMP line **3610**: `real ziconv(mxnx,mxny)` after `include 'params.met'`. COMP does not itself declare that COMMON; the temporary *diagnostic-only copy* declares the same `/tjump/` COMMON to read its true values without re-evaluation.
- Original COMP line **4511**: `call diagno(... ziconv ...)`. Just before this call is the genuine **previous-hour** COMMON state.
- Original COMP lines **4691–4699**: LAND `mixht` or `mixht2` of original `ZI/ZICONV`; original lines **4715–4717**: `avemix`. Immediately following original line 4719 is the genuine post-COMP `DPTT` state, not a value synthesized from CALMET.DAT.

Source instrumentation is limited to three additions: one matching COMMON declaration in COMP, two write-only binary snapshots (before DIAGNO and after AVEMIX), using a disposable original source. Neither source physics call, formulas, variables, nor inputs are changed. Both the original pristine and instrumented source use the same genuine NOAA 2022 case: 2SS (one true missing wind) + 1US, 82×85×9, 6907 LAND + 63 WATER, 01–07 UTC six hours. **The scratch 6h×45 CALMET.DAT SHA256 must be bitwise identical to pristine original.**

## Independent numerical gates

1. Original trace: 6×2×6970 REAL4 DPTT values with original NHRZE 2–7, stage 1 pre-DIAGNO and stage 2 post-AVEMIX. Verify all source bounds and clock/order; require exact REAL4 previous post-hour → next pre-DIAGNO DPTT for 5×6970 pairs. The original trace is a **read-only comparison authority**, not model forcing.
2. Native first hour: reuse already independently proven native G54's post-MIXHT DPTT (fifth memory plane), unmodified native G54 SHA, and accepted G60/G54 provenance receipts. Compare 6970 values with original COMP's first-hour post-AVEMIX DPTT using **predeclared** `|ΔDPTT| <= 5×10⁻³ K + 5×10⁻⁵·max(|DPTT_original|,|DPTT_native|)`, zero violations required. Any failure remains a **scientific blocker**; do not relax tolerances or overwrite native data using original.
3. Fail closed on incorrect source blob, time/stage/size, original MET changed by instrumentation, stale G54/G60 receipts, invalid DPTT, or numerically distinct native/original first-hour DPTT. Negative synthetic self-tests check stage forgery, 1 K error, and NaNs.

If passed, only first-hour physical hidden-memory source parity `ZI/ZICONV/DPTT` is accepted, with authentic **original-only** six-hour COMMON persistence. This does not prove *native* G14 causal commits or hours 2–6. S4's eventual universal P6 C1/C2 and genuine non-Hefei six-hour ×45/longer comparison still required. Issue #40 remains OPEN. Full 143-hour heavy test stays manual. P7 and wet deposition remain excluded.
