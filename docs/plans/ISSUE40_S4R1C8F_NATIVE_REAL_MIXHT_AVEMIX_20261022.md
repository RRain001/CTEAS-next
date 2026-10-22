# Issue #40 — S4-R1c8f: native original-source MIXHT and AVEMIX

Date: 2026-10-22. Parent merged #257 main `613ef30487eb6c57122212dd7b74f49dbaa55e95`.

## Physical purpose

The genuine 2022-06-01 2SS/1US NOAA 82×85×9 mixed 6907 LAND + 63 WATER case now has accepted native full-grid G24 final U/V/W, native G17B4 COMP third SURFVAR, and native G53 original-selected neutral WATER. PR #257 pinned an independent six-hour *unmodified Fortran* source record at original CALMET COMP L4691 (WATER complete, before LAND MIXHT), L4701 (after LAND MIXHT), L4719 (after whole-domain AVEMIX), 6h ×3×6970×2 floats, with original 6h×45 `MET.DAT` byte identical. This PR performs the *first native actual-source* grid MIXHT and AVEMIX numerical integration, keeping #257 trace only in a separate external comparator.

## G54 candidate source provenance

The opt-in standalone G54 composes **existing** shared physics, not duplicated formulas or original result injection:
- G41 source with original P1–P5, G43 COMP non-wind MISSFC preserves missing observed WS/WD, 2SS/1US original ordinal;
- G48/G16 original sparse source WIND1→FRADJ→SLOPE→STHEOR/DIAGI/INTER2→shared G24 final 3-D fields, scientifically accepted by #253;
- G17B4 third COMP SURFVAR **after final G24 U/V** (validated #254), G17C1 source CALMET HEATFX/AIRDEN plus G17C2 ELUSTR with true *third* TEMP2D, not DIAGNO HEATFX/QH;
- G53 independently calculated 63 WATER neutral QH/USTAR/EL and ZI/ZICONV (validated #256); seed the WATER portion of the source live prior-COMP arrays before LAND MIXHT, and retain their category/ordinal in G52;
- G18D5 original READCF MIXHT scalars, G18B1 physical source AA/BB upper-sounding buffers, G18B3 original grid NEARU/IUPT (1 authentic upper station), G23 source FCORI/CMECH; previous-hour ZI/ZICONV/DPTT from source-owned G14 frame, **not Fortran intermediate fields**;
- Only the *one actual wind-valid original surface station* G48 STHEOR supplies current-hour station-cell DPTT. The missing SS does not produce a synthetic STHEOR/temperature jump. Call unchanged P6E `p6e::mixht_observed_mc` for all original LAND grid cells, preserving all native WATER values;
- Feed resulting full native 6970-cell ZI/ZICONV and same native G24 source-selected ILEVZI U/V into unchanged `g18c1_original_avemix_rebuild`; do not publish COMP state or claim G26 45-field acceptance.

## Numerical acceptance

Independent comparator loads only #257's SHA-pinned original COMP six-hour stage file **after native G54 is already executed**. Original source receipt must state pristine/scratch 6h×45 fields identical, 6907 LAND/63 WATER, no WATER changes from LAND MIXHT. Test native 6970 cell ZI/ZICONV vs original first-hour post-LAND MIXHT pre-AVEMIX (L4701), and native post-AVEMIX 6970 cell ZI/ZICONV vs original first-hour post-AVEMIX (L4719), for **27880 independently compared floats**. Frozen tolerance: `absolute 5e-3 m + relative 5e-5`. Store first 20 failures, worst i,j/field residual, SHA; any nonfinite, shifted grid shape, absence of full native provenance or threshold exceedance fails CI. No tolerances relaxed to make a failing source pass.

## Scientific non-acceptance

Even if all numerical checks pass this is **first-hour source-scoped MIXHT/AVEMIX**, not previous-hour causal six-hour transfer, P6F fields, G26 native MET.DAT 45-field comparison, WSTARR, TEMP3D, WATERP, other station counts, or #36 P7. Existing source all-land G26B and C1/C2 frozen paths are untouched. If CI disagrees, leave Draft and diagnose original COMP QH/DPTT/AA-BB and the 6970 point discrepancy; do not merge.
