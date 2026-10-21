# Issue #40 – S4-R1c5a: independently measure authentic previous-hour ZI/ZICONV state

Date 2026-10-21. Input baseline: `main@cd6fe64168b28ea5e1339e8000a52e34938428a0` (after merged #243 full grid 6970 first-hour true G21 U/V/temperature).

## Why this is the next physics gate

R1c4a #242 validates source-native memoryless G42 WIND1 for genuine six consecutive NOAA hours. R1c4b #243 validates G42 WIND1 + G21 FRADJ and both SURFVAR temperature passes on all 6970 cells **first hour**. R1c3 #241 establishes genuine 6907-land first-hour G39 thermal after CALMET-internal G43 nonwind MISSFC. None of those proves the causal `previous.ZICONV/ZI` that G14/CGAMMA, MIXHTST, COMP and G39 must carry across hour boundaries. Merely recomputing each hour with zero previous memory, or copying an original Fortran `ZICONV` to the native solver, would incorrectly claim model reconstruction.

Original CALMET 6.5.0 `COMP` source: original pinned blob `437f43bb7f0e51a1919e56664663e1a046986ed0`, direct call `DIAGNO` at original line 4511 and post-`MIXHT` + `AVEMIX` at lines 4691–4717. The only accepted way to establish the baseline is instrumenting a private disposable original source checkout with read-only `ZI/ZICONV` writes, re-running authentic NOAA 2SS (583140 Huoshan and 583210 Luogang) + 1US (58424 Anqing), actual `82×85×9` GEO with 63 original water cells, hours ending UTC 02 through 07 on 2022-06-01, then verifying the **entire original six-hour 45-field CALMET output is byte-identical to the separate pristine original**.

## Changes

- `scripts/s4/s4r1c5a_original_comp_state_chain.py` pin-checks exact vendor original Git blob and fixed source anchors, inserts a scratch-only trace of `ZI` and `ZICONV` before each DIAGNO and after MIXHT/AVEMIX for all 6970 grid cells. P5 source files, historical vendor source, production C++, accepted G14/G19/G26 and P6E physics are unmodified.
- Six hours × two adjacent states × 6970 cells = **83,640 original state rows**. Check strictly all 5 inter-hour 6970-cell handoffs. Report per-hour positive mixing-height counts, worst original prior→next-pre difference for both ZI and ZICONV, and exact cell/time of any discrepancy. Zero exact source carry-over is a source authority requirement, not a native parity claim.
- A separate source-science Action first completes the entire already accepted R1c4b true NOAA P1–P5 + original-vs-native first-hour 6970-cell parity chain, then runs scratch original state capture and compares original state histories. Report hashes and JSON only; never upload original vendor code or raster source files.

## Acceptance and next gate

Only an exact-head fresh workflow with pristine-vs-instrumented CALMET 6h×45-field byte-identical state and the complete temporal state trace qualifies for `PASS_ORIGINAL_REFERENCE_ONLY`. It is NOT six-hour native G21/G39 or native G24. Original true state provenance is needed to **implement and independently validate actual native G14/COMP previous-hour ZI/ZICONV updates**. No native field may be read from the original trace for computing a purported native hour.

Existing independent all-land C1/C2/143h paths and P5 primary/auxiliary missing/calm invariants remain immutable. Original water friction `USTAR/EL`, water mixing heights, native 6h G24 and G26 45-field output, P7 #36 remain NOT_ACCEPTED. Keep Issue #40 OPEN.
