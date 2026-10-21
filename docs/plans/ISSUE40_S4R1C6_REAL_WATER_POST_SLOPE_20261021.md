# Issue #40 — S4-R1c6: genuine original-native first-hour post-SLOPE U/V

Baseline: main@7d646152460f607c4072f5ab0d4a914c90444bfc after merged native G14 six-hour COMP trace PR #245.

## Purpose and exact scope

Genuine NOAA 2022-06-01 02:00Z 2SS Huoshan/Luogang + 1US Anqing, 82x85x9 original CALMET case: 6907 land and 63 WATER cells. R1c4b previously verified first-hour WIND1/FRADJ/two SURFVAR; R1c3 verified original-source 6907-land HEATFX/AIRDEN/ELUSTR and water T/QSW/RHO. The G23/G24 final wind remains blocked. The present milestone extends genuine source-native stages through the original G22 SLOPE stage, prior to G23 interpolation and G24 completion.

Extract the existing G22 post-ELUSTR SLOPE arithmetic into ONE shared G22 helper, reused by unchanged all-land G22 and separately test-only G47 with authentic water source. Do not modify terrain physics, CALMET original, selected option, P5 wind missing/calm policy, C1/C2, or G14 scheduler.

G47 calls existing first-hour G44: model-internal G43 MISSFC -> G42 WIND1 -> G21 FRADJ -> G39 HEATFX/AIRDEN/ELUSTR. It preserves water QH=0 and uncomputed USTAR/EL, and uses the exact original P6D SLOPE kernel. All nine post-SLOPE U/V planes are emitted independently; original vendor numerical fields are NEVER fed to C++.

## Independent original-vs-native workflow

The existing R1c3 genuine NOAA workflow builds G47 and generates the same real site source files. Separately compile pinned pristine original Fortran blob 437f43bb7f0e51a1919e56664663e1a046986ed0 in a disposable write-only SLOPE-instrumented copy. Demand byte-identical six-hour x 45-field CALMET.DAT against a separate uninstrumented original.

Compare all 82x85x9 cells: 62,730 grid-layer records and 125,460 U/V components. Exact UTC/source/grid/categorical identity and previously frozen U/V tolerance 0.05 m/s. Record land/water-specific maxima, U/V maxima, exceedances, original/native binary and source SHA. Never loosen tolerance to pass.

C1 143h, C2 143h, previous all-land G22/G23/G24 and R1c3 original NOAA thermal science must remain green. Do not upload vendor Fortran, original raster or private raw station files.

## Acceptance boundary

At most PASS_SCOPED_REAL_FIRSTHOUR_POST_SLOPE, conditional on fresh exact-head Actions PASS. Not six-hour causal G21/G39, not G23/INTER2, not G24 final U/V, not WATER USTAR/EL/ZI, not G26 six-hour 45 fields, and not P7 production. Keep Issues #40/#36 OPEN.

Next R1c7: apply genuine validated post-SLOPE native wind to land STHEOR/DIAGI and original INTER2 on the same scheduler, then complete G24; only after that integrate selected WATER and true causal ZI/ZICONV. No new site-specific physics formula, S5, wet deposition or Docker.
