# S4-R1c8b — Genuine NOAA original/native COMP third SURFVAR

Date 2026-10-22; baseline main a95e32796256e605e43d5e1f7a61610db00d647c (merged PR #253).

## Physical target

After authentic 2SS+1US NOAA P1–P5 source, same 82×85×9 with 63 water cells, previous merged science covers native G42 WIND1 → G47 FRADJ/thermal/SLOPE → G17C3 sparse station STHEOR → shared G16 INTER2 → **shared G24 final U/V/W/DIV**. PR #253 compared 260896 original vs native scalar components (zero frozen-threshold exceedances).

Original CALMET `COMP` then independently calls `SURFVAR(U,V,Tprog,TEMP2D,IRH2D,IPCODE2D,IALL=1)` at pinned vendor `calmet.for` L4567 **with the final G24 U/V**, not the second DIAGNO SURFVAR temperature (known G33B stale-input bug). Native must reuse existing common G17B4 `after_final_diagno_before_comp` (unchanged AVETMP physics) after source-owned G24, not create any alternative NOAA physics.

## Evidence

- Read-only scratch original source SHA-pin vendor Git blob `437f43bb7f0e51a1919e56664663e1a046986ed0` and exact original L4566/L4567 COMP condition/call. Append a write-only TEMP2D stream capture immediately after original L4567. Keep original compiled physical formulas and original P1–P5 surface, upper-air and GEO untouched.
- Independently re-execute six genuine original 2022-06-01 01:00–07:00 UTC model source hours; compare **all 45 MET fields across six hours as byte-identical** to uninstrumented pristine original. Record six 82×85 original COMP third temperature planes, pinned SHA, source hour, and per-hour count.
- The G51 native forensic executable accepts only original source P1–P5 file paths, **not any original numerical reference**, replays shared G48→G24 physical actor, uses same previously executed G17B4 first/second SURFVAR state to execute its third COMP callback once, writes first-hour REAL4 TEMP2D for **6,970 cells**.
- Separate numerical comparator verifies first original COMP third plane and native plane at frozen abs tolerance `2e-4 K`; records RMS/mean/max and bit differences; any exceedance is a scientific failure. Negative schema checks reject wrong original source clock/shape.
- CI includes all PR-run frozen C1/C2 physical regressions, original six-hour reference check, 6,970-cell science gate. Only small summaries and SHAs uploaded; do **not** publish original vendor sources, DEMs, NOAA raw forcing, or raw diagnostic matrices.

## Scope and vetoes

Expected scientific label (only after exact-head CI): `PASS_GENUINE_NOAA_ORIGINAL_NATIVE_COMP_THIRD_SCOPED_FIRSTHOUR`. This establishes only **third COMP surface temperature** for authentic real first hour, NOT any MIXHT/AVEMIX/WSTAR/TEMP3D or prior-hour COMP state nor G26 45 fields or P7. In particular **G26B all-LAND source gate remains fail-closed**, and no fake calm, prior-hour ZI/ZICONV/DPTT, or original temperature/oracle field may be injected to native. The next PR must bind source-authentic real-water COMP controls/MIXHT with original grid-level numerical proof before enabling a shared G26 actor. No Docker, wet deposition, S5, or P7 promotion.
