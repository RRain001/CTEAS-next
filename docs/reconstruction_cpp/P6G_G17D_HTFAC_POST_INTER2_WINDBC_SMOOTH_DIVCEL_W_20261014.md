# P6G G17D — dynamic multi-SS/US DIAGNO final 3D U/V/W through the frozen #53 source kernel

Date: 2026-10-14. PR #63 stacked on #53. The scientific authority is accepted #53; its 163 core files remain byte-identical and no physics equations are rewritten here.

## Why the tail is different from merely calling a generic W solver

Original CALMET 6.5.0 DIAGNO `HTFAC>0` source route, `calmet.for L6092–L6148`:

1. The **first** WINDBC is captured after FRADJ/HEATFX/ELUSTR/SLOPE but **before** INTER2. The G16 stage deliberately preserves those pre-INTER2 boundary snapshots.
2. Source-selected station profiles and INTER2 update the full U and V fields.
3. The **second** WINDBC runs with the **post-INTER2** U and V fields for `HTFAC>0`, replacing the first boundary for the tail physical calculation. Skipping this step silently changes SMOOTH/DIVCEL and W.
4. The unchanged, independently source-audited #53 `p6::original_smooth_divcel_w` receives exactly `NSMTH(K)` from the original parsed met.inp, original `ZFACE(K+1)-ZFACE(K)` thicknesses, grid `DGRIDKM*1000`, and the proper post-INTER2 boundary U/V. It performs SMOOTH → all-layer DIVCEL with W=0 → per-layer W integration + WINDBC refresh in the original sequence. `IOBR=0` and no lake-breeze are the **selected** route; other branches fail closed.

## New implementation

- Extended `p6g_g17_staged_terrain.hpp` with `DiagnoWindbcPostInter2Htfac1` and `DiagnoSmoothDivcelW` callbacks and captured intermediate and final fields. It reuses #53 `diagno_segment.hpp`; no new smooth/divergence/continuity formula is introduced.
- Selected source `GEO.DAT` reader accepts `HTFAC=1` only. Since G17D also serves constructed test grids, the adapter demands an *explicitly test-only* source HTFAC=1 assertion before WIND1, rather than silently treating all possible dynamic grids as HTFAC=1.
- State guards reject second WINDBC before genuine native INTER2, final W before second WINDBC, duplicate second boundary, duplicate final mass segment, wrong UTC hour, any non-source ZFACE/NSMTH, and unsupported IOBR. The saved *first* WINDBC remains immutable for audit.
- Exact computed final 3D U/V and 10-face W are assigned into the current hour `frame.fields` for later COMP/P6F integration, but `frame.previous` remains immutable; the unimplemented COMP stage continues returning `{Unknown,false}`.
- Extended the G17B4/G17C1–C3 selected CTest to check post-INTER2 boundary faces, source NSMTH, direct immutable-kernel exact equality for U/V/W/divergence and boundary results, zero initial W bottom face, finite W, prior boundary preservation, no previous-COMP mutation and out-of-order/duplicate rejects.

## Evidence versus unverified scope

The G17D test uses a controlled 12×12, nominal 10 km, 9-layer, 2SS/2US selected stage, original source-parsed met.inp, and the same frozen physical kernel used in PR #53. This is **not independent complete multi-SS original Fortran 45-field parity** and not a production CALMET solver. The generic multi-station water/lake, IOBR=1, other HTFAC and arbitrary vertical-level branches are not accepted.

The source-derived general SS→US station correspondence, fully real HEATFX/ELUSTR inputs, true multi-hour PREPDI→COMP states (including station DPTT in /TJMP/ and gridded CGAMMA ZICONV), physical mixing height/TEMP3D, and full P6F output remain pending. Multiple-station full 1h→6h→143h→year 45-field original vendor parity is the final promotion gate. PR #53 frozen Hefei 143h 45-field regression remains mandatory.

Relevant CI workflow: `P6G multistation on accepted single-station baseline` on GitHub-hosted Ubuntu; check exact commit SHA's Debug/Release selected CTests and frozen-ownership guard. The G9/G10/G11 original Fortran source workflow and #53 143h science workflow are independent gates.
