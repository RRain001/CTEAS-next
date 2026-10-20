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

**Current science status:** NOT_RUN until GitHub jobs and exact source SHA are verified.
