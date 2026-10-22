# Issue #40 — S4-R1c8e: real source COMP WATER → LAND MIXHT → AVEMIX stage-state gate

Date: 2026-10-22. Base is merged #256 `main@500591dd22e17ec85893f45387dbede0945ae2e8`.

## Purpose

Previously, #256 established that native final G24 WIND (not Fortran-fed) drives frozen G37/G35/G36 selected neutral WATER over all 63 genuine NOAA water cells with independent first-hour source parity; it did **not** establish what happens when full original COMP executes LAND MIXHT and whole-grid AVEMIX. One physically consequential detail is that original `MIXHT` writes LAND only, but `AVEMIX` subsequently operates on the **entire 82×85 grid, WATER included**. Prematurely committing the unaveraged water ZI as a final COMP state would be scientifically incorrect.

## Verified original source program locations

Pinned original CALMET `calmet.for` Git blob `437f43bb7f0e51a1919e56664663e1a046986ed0`:
- Before source L4691: `COMP` after `WATER` and `ELUSTR`, before the original LAND `MIXHT` call at L4692–4693.
- Before source L4701: `MIXHT` completed, before source AVEMIX.
- Before source L4719: original `AVEMIX` call at L4715–4716 and conditional `ENDIF` completed.
All original physical source lines and input files stay **byte unchanged**; only a scratch copy receives six source-only stream writes per hour (two arrays at each of three stage boundaries). The write-only data are not passed into the native C++ executable or its physics.

## Numerical checks

Regenerate independently the authentic NOAA 2022-06-01 original model with exactly 2 genuine surface stations (583140,583210), 1 observed upper station (58424), 82×85×9 and 63 original WATER cells. The pristine original six-hour 45-field `MET.DAT` must be byte-identical with the source-instrumented rerun. Inspect 6 hours × 3 stage boundaries × 6,970 cells × 2 REAL4 (ZI,ZICONV), source-hour and stage tags fully pinned. At each hour, LAND MIXHT **must not alter any WATER ZI or WATER ZICONV** between stages 1 and 2, and must change at least some actual LAND state. Report the count of WATER changed by original AVEMIX between stage 2 and 3, **do not require it to be zero**.

Then independently compare genuine native G53 first-hour WATER ZI/ZICONV (computed from true final native G24 U/V in #256's same workflow) against **both** genuine original first-hour stage 1 and stage 2 WATER values. 126 ZI comparisons at already frozen absolute `5e-3 m` + relative `5e-5`; all 126 native/original ZICONV checks exactly zero; preserve water cell i/j identity and unchanged source geo. Every exceedance fails the PR.

No LAND native MIXHT, AVEMIX, WSTARR, TEMP3D, source COMP causal history or G26/P7 production claim comes from this source-state handoff. This is a necessary **pre-MIXHT→post-MIXHT original staged reference and WATER coupling validation**, not the endpoint. The next actual task is source-backed native 6907 LAND MIXHT with actual G24, COMP-third TEMP2D and authentic *prior-hour* ZI/ZICONV/DPTT + source PREPDI/NEARU AA/BB, then compare original stage 2 all-land before averaging; only following that can shared AVEMIX be run with full native 6970 ZI/ZICONV and compared against source stage 3. Never feed original ZI/ZICONV as native start state just to make tests pass.

C1/C2 143h physics untouched, no Copilot code review, no wet deposition/Docker/S5.
