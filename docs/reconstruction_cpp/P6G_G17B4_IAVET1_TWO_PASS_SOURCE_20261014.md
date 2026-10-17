# P6G G17B4 — original two-pass IAVET=1 SURFVAR/AVETMP with real G17 WIND1/FRADJ stage provenance

Date: 2026-10-14. Development PR: #63 (Draft), based on the accepted single-site PR #53 source authority. All 163 accepted P6 physics and scheduler files remain bit-identical to #53; this is new multistation code only.

## Original CALMET 6.5.0 causal sequence

The pinned `engine/vendor/src/CALMET_v6.5.0_L150223/calmet.for` demonstrates two distinct SURFVAR calls during DIAGNO:

- Lines **5607–5611**, conditional `ISURFT<0`: first `SURFVAR(UG(1,1,1),VG(1,1,1),...,IALL=0)` before topographic FRADJ.
- Lines **5643–5644**: native `FRADJ` adjusts `UG/VG` based on terrain/temperature.
- Lines **5667–5670**, conditional `ISFCMET=0`: second `SURFVAR(UG(1,1,1),VG(1,1,1),...,IALL=0)` after FRADJ, before HEATFX, AIRDEN, ELUSTR and SLOPE.
- Lines **12879–12880**: each SURFVAR with `IAVET=1` (and `IALL!=2`) calls `AVETMP` with the then-current **first-layer** U/V, so the first and second `TEMP2D` are not guaranteed equal.

The actual Hefei input deck demands `IAVET=1`, `MNMDAV=1`, `HAFANG=30°`, `IRAD=1`, `TRADKM=500 km`, `NUMTS=5`, with observed `ITPROG=0`, `IRHPROG=0`, `NPSTA=0`. Thus the older G17B2 single-pass `IAVET=0` source-selected tests cannot be used for full Hefei physical acceptance.

## Implemented

- New `p6g_g17b4_iavet_two_pass.hpp`: parses mandatory original met.inp surface controls, computes independently audited P6E `surfvar_multistation` raw observed 2D temperature, and implements two **strictly ordered** P6E `avetmp` calls from distinct original 3D wind snapshots.
- Modified `p6g_g17_staged_terrain.hpp`: `prepare_original_iavet1_before_fradj()` consumes the G16 WIND1 field actually produced by that stage. `finish_original_iavet1_after_fradj()` verifies source WIND1 first-layer identity, verifies first `TEMP2D` equals the FRADJ forcing, then computes the second `TEMP2D` from the **same stage's native FRADJ-adjusted 3D U/V**. Source AIRDEN and SLOPE subsequently require the **second** `TEMP2D`, while FRADJ uses the **first**. Old IAVET=0 scoped tests remain unchanged.
- Selected CTest `p6g_g17b4_original_iavet1_pre_and_post_fradj_surfvar` checks both direct source AVETMP numeric fields, the full G16 WIND1 → first SURFVAR → native FRADJ → second SURFVAR → source SETCOM/AIRDEN → selected SLOPE → first WINDBC → G16 INTER2 chain, the distinct two temperatures, and rejection of wrong-hour, missing, repeated, reordered, water, or stale first-temperature inputs. Requires pinned original Hefei `met.inp`; tested 2SS+2US 12×12 at 10 km. Stage QH remains controlled and explicitly fixture-provenance.
- Added independent **literal vendor AVETMP** comparison CTest: `p6g_g17b4_original_vendor_avetmp_40_case_source_parity`, reusing unchanged source-selected P6E `compare_original_avetmp.py` and building the source C++ reference executable. Compares native C++ AVETMP against unmodified CALMET Fortran (40 zero-wind/rotated/upwind cases) at original published abs/rel acceptance thresholds, independent of internal C++-to-C++ comparisons.
- CI runs both Debug and Release on hosted Ubuntu. PR #53 accepted 163-file invariant enforced mechanically on each push.

## Explicit acceptance limits and next mandatory work

1. Stage test wind input and QH are controlled fixtures. Real multi-station WIND1→FRADJ source-equality is only demonstrated at the selected-kernel test level; **not** yet independently accepted against full original **multi-station** CALMET 45-field hourly science.
2. Current G17B4 selected SURFVAR requires **all-land** model grid and refuses original water interpolation branches until validated. Its `IRAD/NUMTS/TRADKM` station weighting is only source-validated in the prior 72-case G13 oracle; full multi-station moisture/water and prognostic branches remain outside scope.
3. Genuine second-pass TEMP2D must next feed **source-calculated** native SOLAR/HEATFX and real AIRDEN+day/stable ELUSTR, rather than fixture QH. Full original `CGAMMA`/thermal cross-hour state, SMOOTH/DIVCEL/W and P6F then need integration in the #53 unified scheduler.
4. Only after independent original vendor multi-site 1h→6h→143h→year **45-field** verification can #63 be marked production-ready. Until then PR #63 stays Draft and G5 GUI fails closed.

CI notes: [G17B4 selected stages #38522939034](https://github.com/RRain001/CTEAS/actions/runs/38522939034) all 3 jobs passed, including Debug/Release selected-stage tests. Latest literal Fortran AVETMP oracle added at [#38523102036](https://github.com/RRain001/CTEAS/actions/runs/38523102036); its final results must be checked before claiming original AVETMP G17B4 CI PASS.
