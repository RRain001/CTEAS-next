# Issue #40 S4-P — original water ZI/ZIMECH/FCORI plus native selected neutral 378-row comparison

Date 2026-10-21. Depends on independently accepted real original NOAA 2022 2SS Huoshan 583140 + Luogang 583210, real Anqing 58424 1US, exactly 82×85@1km with 63 genuine water cells and six modeled hours from merged #232 and #233. No synthetic alternative or zero-filled NOAA observations.

## Original source and numerical proof

Original unmodified CALMET 6.5.0 source Git blob `437f43bb7f0e51a1919e56664663e1a046986ed0`. Actual original `WATER` for this no-overwater-station original READCF `NOWSTA=0,ITWPROG=0,ICOARE=10,IMIXH=1` executes neutral friction and original `MIXHMC`. Literal source:
- `HEATFX` computes water QSW but not water QH, subsequent `WATER` uses `WT=0`, `EL=9.9e9`, `Z0` Hosker and neutral `USTAR` in the accepted selected G35 test-only comparison (#233).
- Original `WATER` sets mechanical water height `ZIMECH=CONSTW×USTAR/FCORI` (L32964); original gridded coriolis factor `FCORI=max(abs(f(lat)),2.5e-5)` is sourced from the original UTM grid map, not guessed constant across the site.
- `MIXHMC` IMIXH=1 checks original `WT`; because the selected neutral `WT=0`, the actual pinned Fortran source returns with `ZICONV=0` for either convective relaxation setting. Subsequent `ZICOLD=ZICONV` (L33019), and the actual original `ZI=min(ZIMAXW,max(ZIMINW,max(ZIMECH,ZICONV)))` (L33027–29). `DPTT` might carry state and is recorded but **not** generically validated outside WT=0.
- This source-scoped collapse is **not** true for observed water temperature differences, nonzero surface buoyancy, `WATERP`, or alternative `IMIXH`. Do not weaken any physics or option guard based on this special case.

**Independent GitHub Actions** regenerates all original source GEO/SURF/UP/met.inp, native accepted P1–P5, independently computes pristine original Fortran CALMET six hours with all 45 output groups and 270 original field-hour inventory, and regenerates S4-N original per-water cell-hour `QH,USTAR,ZI` reference with unchanged original MET bytes. It then creates a **new, separate exact-hash-pinned scratch-only Fortran source instrument** adding water records at the original `WATER` exit of `ZI,FCORI,CONSTW,ZIMINW,ZIMAXW,ZICOLD,DPTT,ZICONV,ZIMECH`, compiles it separately with the accepted Fortran compiler flags and reruns the exact same real NOAA 2022 source. Require **full original MET.DAT byte equality** and 63×6=378 independent water site-hour identities matching S4-N `ZI`; require original ranges/branch numerical consistency.

## Strict native candidate boundary

Add completely separate `G36OriginalWaterZiInputs/Result`, test-only C++ reference candidate, with inherited original G35 selected-no-OW neutral subroutine but accepts immutable **original** per-cell/hour `WS10,FCORI,CONSTW,ZIMINW,ZIMAXW` as inputs. Compute `ZIMECH`, neutral `ZICONV/ZICOLD` and bounded `ZI` using selected original float step sequence. Native compares all 378 original reference rows and rejects missing/duplicate station/cell/hour, changed source control tuples, out-of-domain GEO, invalid coriolis/bounds, and any implicit or new physical option authority. Existing G19/G14/G26 actors **do not call G36**.

Only `S4P_ACTUAL_WATER_63x6_NATIVE_ZI_ZIMECH_MIXHMC_ZERO_SOURCE_PARITY_PASS_SCOPED` qualifies as S4-P PASS: narrow, source-injected scalar original physics reference. It does not yet calculate native 82×85 post-FRADJ `WS10`, original `FCORI` from independent cartographic projections, or full-model 45-field numerical parity, and does not admit the water branch into G14 or G26. Original `DPTT` is recorded but not validated as a production state.

Next scope, only after final strict CI: independently generate native post-WIND1/FRADJ water WS10, grid FCORI, constant/water bounds and compare real six-hour full WIND/COMP state, then compare 6×45=270 original CALMET field-hour groups. A 20-station test was not a capacity ceiling. Keep default physics fail-closed, P6 #40 and P7 #36 OPEN; avoid unrelated wet deposition, Docker, S5 changes.
