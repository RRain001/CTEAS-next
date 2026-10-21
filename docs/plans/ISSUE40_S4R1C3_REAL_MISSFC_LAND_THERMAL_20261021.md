# Issue #40 S4-R1c3 — real NOAA first-hour native MISSFC → G39 land thermal

Date: 2026-10-21. Exact starting production main `005502d308e1f9eef20531c7f17d8eef063105d4` after merged #239 first-hour G42+G21 and merged #240 original 2SS×6h G43 COMP MISSFC. Original vendor CALMET v6.5.0 source blob `437f43bb7f0e51a1919e56664663e1a046986ed0`.

## Frozen physical boundaries

- Original NOAA real 2SS 583140/583210, 1US 58424, 2022-06-01 01:00–07:00 UTC, 82×85×9 original GEO with 63 water cells and 6907 land.
- **P5 user policy invariant:** primary complete filled and original calm converted under the approved v2 rule; auxiliary remains sparse with wind and nonwind missing. Never mutate P5 SURF.DAT, forge a calm or pressure observation, or reassign station roles.
- **P6 original source order:** original CALMET COMP calls MISSFC before DIAGNO; G43 independently verified real source model-internal, nearest originally valid donor station, five nonwind fields. Original missing winds are never replaced by MISSFC; G42 source WIND1 uses a validity mask and the frozen genuine W1 BIAS/ICALM algorithm.
- G44 is a **new standalone reference type**. It holds the original raw first-hour source and creates a *detached* model-internal G43 resolved source copy. Only that copy feeds the G41/G42 source clock, G21 true WIND1/FRADJ/two IAVET1 SURFVAR, then G39 existing frozen HEATFX/AIRDEN/ELUSTR kernels. No original wind/U/V/temperature/CALMET.DAT field may become a native input. All 6h×45 original outputs and the default all-land G19/G26 physical guard remain untouched.
- Land computed QH, RHO, USTAR and EL are experimental **original-compare candidates**. At the WATER cells original ELUSTR skips USTAR and EL, so *they must remain zero/pending* before original WATER. No water friction or mixing-height physics is claimed by this PR.

## Verification

The S4-R1c3 workflow starts from the accepted genuine NOAA P1–P5 chain and pristine Fortran original 6h×45 fields used in #240. It builds the native G44 in Release with `-Werror`, outputs 6970 rows (one model hour; land and water), then compiles a **scratch-only** instrumented original CALMET that adds write-only original DIAGNO output **after AIRDEN and ELUSTR** for the same 6970 cells (Fortran anchor 5697). It must preserve the original complete 6h `MET.DAT` SHA and source blob unchanged.

Independent comparator checks each GEO original land category and UTC hour. For land it compares original-versus-C++ TEMP2D, QSW, post-ELUSTR QH, AIRDEN RHO, USTAR and EL. For water only TEMP2D/QSW/RHO are comparable at that stage, and both C++ QH before/after ELUSTR and USTAR/EL must be zero. Pre-registered tolerances (before seeing numeric results): temp 0.001 K; QSW 0.005 W/m²; QH 0.25 W/m²; RHO 0.0001 kg/m³; USTAR 0.005 m/s; EL max(0.5 m, 1% of reference). All errors remain reported; thresholds cannot be loosened to declare success without an independent scientific justification and new review.

The only acceptable stage label after exact-head true numerical pass is `PASS_SCOPED_REAL_FIRSTHOUR_LAND_HEAT_AIRDEN_ELUSTR`. A compile-only PASS is software evidence, not physical acceptance. If science fails, report the specific first cell, stage and residual and keep the PR Draft. Source G43 six hours PASS stands independently. Native actual G24 WATER final U/V, source WATER USTAR/EL/ZI, six-hour stateful G26 45-field, and P7 #36 are explicitly **NOT_RUN/BLOCKED** until separately measured.
