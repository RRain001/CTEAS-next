# Issue #40 S4-C — Remove arbitrary eight-station test bound; source-calibrated original Fortran scientific capacity

Date 2026-10-21. Base `main@b301038b05cf0a155877645731655875a077b38e`. This phase addresses the explicit requirement that station count can exceed six, eight, or twelve. The **selected C++ G14 physics** already uses the actual G19 source-backed SS/US cardinalities, not a `<=6` station limit (PR #213). Do not mistake the old `1..8` **test fixture** ceiling for a production capacity limit.

## Grounded original-vendor constraints — separate from new C++

Unmodified original CALMET 6.5.0 pinned `CTEAS@dfad99a78ed84d655e21411c9d25eb0d2583bf13`, `engine/vendor/src/CALMET_v6.5.0_L150223/params.met` includes **`parameter(mxss=350,mxus=99,mxps=700,mxows=30)`**. Those are actual compiled original maximum surface and upper-air station *capacities*, not proof that all combinations can be run within ordinary CPU/memory or with valid observations. The C++ physical path must use input-dependent allocations and independent memory budgets, not inherit that Fortran's compile-time fixed storage cap.

This PR changes the controlled original-format test source producer's arbitrary 1..8 count to the **source-pinned original 350 surface / 99 upper reference limit**, solely because scientific head-to-head requires running that original executable. The independently run original evidence script reads `params.met` itself and refuses counts above compiled `mxss` or `mxus` (and stores its SHA), avoiding a second hardcoded acceptance oracle. Production C++ G19/G14 input authority and formula do not change. More source-station diversity: station #9 onward gets distinct actual-format UTM coordinates remaining in the bounded 12×12 controlled grid and SS/US wind values remain finite and within physically legal bounds. Existing 1–8 source fixtures and their scientific baselines are preserved.

## New strictly-scoped original-vs-native science

Actual original 6.5.0 and the SAME G14 C++ selected physical 17-stage actor freshly process cases (NSSTA,NUSTA): **(7,7), (8,2), (2,8), (9,9), (12,3), (3,12), (1,9), (9,1)**, source-backed controlled 12×12×9 original-format data, legal six-hour cross-year clock. Every candidate must independently pass *first* 1h and full consecutive 6h with **45 matching original fields/hour**, all 144 cells per field per hour, using the frozen P6E numeric tolerances; require zero exceedances, zero missing, correct header/source IDs. Output producing alone is **PRODUCED_UNVERIFIED**, not science. The original CALMET source and compiler SHA plus actual source files/relative station IDs remain separately identified. No original MET values used by native C++.

The actual C1/C2 accepted 143h path, the accepted 1..6 original science jobs, accepted shifted-ID tests and actual NOAA Huoshan 100×100 real P1–P6 6h original comparison remain required **at the exact head SHA**, including failure if previous baseline changes.

## Scientific exclusions

Passing this matrix proves a **tested** subset of independent 7–12 station combinations within one controlled 12×12×9 synthetic setup, not full arbitrary N/M, unrestricted data validity, all grid sizes, or production G26 admission. Original static limits 350/99 do not constrain C++ conceptually; eventual C++ maximum should arise from checked array indexing, station-hour budgets and available memory/resources. Original 350/99 must not be promoted as the target C++ hard limit. Field-observed independent multisite cases and non-selected CALMET options require their own fresh Fortran science; P7, precipitation/wet deposition, S5 big domains and Docker remain separate.

## Actual first accepted original-vendor evidence (2026-10-21)

The first science attempt was a correctly blocked engineering probe, NOT a numeric comparison: G19 original sources with 7–12 stations generated valid data, but selected C++ G17B4 rejected `stations.surface.size()>6`; after removing that fixture guard, P6E original SURFVAR weighting likewise rejected `stations.size()>6`; a third identical fixture-only cap in G17C selected IAVET=1 heat handoff was then removed. **None of these three changes alters P6E original pairwise station sorting, interpolation weights, temperature, heat flux formulas, meteorological fields, or scientific tolerances.** They keep actual per-source station IDs, geometry, observations, input clock and array-extent checks. The normal production G26 stage remains disabled.

[Exact physical-source gate Actions #39518781475](https://github.com/RRain001/CTEAS-next/actions/runs/39518781475): all **8/8 independent jobs SUCCESS** for 7/7, 8/2, 2/8, 9/9, 12/3, 3/12, 1/9, 9/1. Each job independently compiled unchanged original Fortran CALMET 6.5.0, reran true original-source-file science for 1h and consecutive 6h, and ran the SAME native G14 selected C++ actor; separate frozen P6E 45-field comparison requires `intervals=1/6`, 45 fields/hour, `status=PASS`, `total_exceedances=0`. Proven result is **`PASS_SCOPED_CONTROLLED_7_TO_12_STATIONS`**, with synthetic original-format source only; not independent observed multi-station NOAA or all CALMET branches.

Because the three count-gate fixes touch accepted C1/C2 and real Huoshan physics adapters, the PR now adds explicit pull-request triggers for the G17B4, G17C and P6E SURFVAR source files to existing C1 first-hour, C2 6h old/new byte parity and full NOAA Huoshan P1–P6 original 45-field regression workflows. Final merge requires **all these exact-head regressions SUCCESS**.

The true original Fortran compiler's `params.met` controls `mxss=350,mxus=99`; this is evidence/reference capacity **not** the C++ numerical transport/physical admission policy. Scientific tests for a station count above 12, arbitrary field observations, broad grids and production resource behavior are not yet certified.

