# Issue #40 — S4-E dynamic source-shape and production-readiness preflight

2026-10-21. Scientific baseline: [PR #215](https://github.com/RRain001/CTEAS-next/pull/215) merged `main@a00517280c3521c17251b05c52be2a4c5da2bc8a`. Independently freshly recompiled original CALMET 6.5.0 versus SAME selected-source G14 C++ 45 fields on original-format controlled synthetic inputs: **20SS/20US, 20SS/1US, 1SS/20US**, first 1h and six chronological hours, existing P6E frozen tolerance and zero cell exceedances. No genuine 20-station NOAA observation claim. **Do not test yet higher fixed numbers merely to advertise a capacity ceiling**; 20 is milestone coverage, not a hard limit.

## This bounded S4-E step

- Add **checked source-shape arithmetic** to existing S4-B1 G19 admission, without new physical formulas or hardcoded SS/US count: `station_columns=NSSTA+NUSTA`, `station_hour_slots=hours*(NSSTA+NUSTA)`, `wind_profile_scalars_per_component=NZ*(NSSTA+NUSTA)` (for selected 9-layer path). Every sum/product rejects `size_t` overflow before any future full physical-stage allocation. Keep `hours*45`, `nx*ny*nz` existing guards. These are *logical shapes*, **not a measurement or reliable upper bound of peak RSS**.
- Positive software-only cases: 20/20, 20/1, 1/20, 350/99 and 400/150. The latter are **arithmetic shape tests only**; 350/99 are original pinned Fortran reference compile capacities, not native physical max or science PASS. Overflow negative gates must run in Release builds.
- The G19 independent original source identities, SURF station-hour <=2,000,000 source reader contract, bounded UP sounding count, source clock and 17-stage causality remain unchanged. The selected CLI and production G26 normal `run()` remain fail-closed.
- New stand-alone PR gate only builds the source-admission tests and asserts the existing no-production execution policy. Physical G14 already merged and verified scientific baseline stays untouched.

## Remaining tasks before declaring S4 production complete

1. Inventory **actual peak memory and intermediate shape allocations** in G14 DIAGNO, COMP, SURFVAR, TEMP3D and P6F. Replace incomplete budget accounting only with measured/checked evidence, not an invented numeric RAM limit.
2. Validate changed station geometries, timestamps, independent measured weather inputs, missing/calm observations, and source registration, separately comparing original CALMET fields for each legal selected branch.
3. Design one normal G26 entry that composes the **same original-verified** G19/G14 kernels and only enables supported science options; reject unsupported options with exact explanatory errors. No branch mutation to make a test pass.
4. After independent original 45-field full-hour regression and negative-case audits, make production path the only regular deployment entry; retire test-only wrappers in their own unchanged-numeric behavior PR. P7 remains blocked from production until independently tested.

This PR is **S4E_SOFTWARE_SOURCE_SHAPE_PASS** only when its exact-head CI succeeds. It does NOT accept G26 production P6, new real multisite or arbitrarily large grid/CPU/memory use. P7 (#36), S5, wet deposition and Docker remain separate.
