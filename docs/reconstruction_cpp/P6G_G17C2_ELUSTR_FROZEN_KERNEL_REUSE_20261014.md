# P6G G17C2 — frozen P6E ELUSTR source-kernel reuse (2026-10-14)

PR: #63 (Draft), stacked on source-accepted #53. This is one additional **selected-stage** compatibility and safety increment, not a native all-hour, multi-station CALMET acceptance claim.

## Why this change

The existing G17C1 bridge already uses true `IAVET=1` **second SURFVAR after FRADJ**, and source-verifiable SOLAR/HEATFX plus NEARS/AIRDEN. Original CALMET orders **FRADJ → second SURFVAR → HEATFX/AIRDEN/ELUSTR → SLOPE → first WINDBC → INTER2**. Stable ELUSTR **modifies QH in place**, so passing the earlier HEATFX QH directly to SLOPE incorrectly skips a physical state transition.

## What is implemented without new physics formulas

- `p6g_g17b4_iavet_two_pass.hpp`: retains the exact second SURFVAR's *FRADJ-adjusted* first-layer U/V snapshot; the next stage must demonstrate that its complete post-FRADJ wind field matches this actual source snapshot.
- `p6g_g17c2_elustr_handoff.hpp`: delegates to the **unchanged #53** `p6e::stable_elustr` and `p6e::elustr_daytime` headers. Per-cell QH<0 and QH>=0 branch selection mirrors the accepted single-site P6E source arrangement. Inactive cells are masked as water only for the independent immutable branch-specific kernel calls, then merged. No stability formula, PSIU correction, heat flux, friction velocity or Monin-Obukhov equation is rewritten.
- All valid land-cell roughness is read from genuine GEO `z0_m`; density, final temperature, QH, station cloud and nearest-site mapping come from the same selected source hour. The test fixture explicitly supplies `zm_m=0.5*(ZFACE(1)+ZFACE(2))` and `ipsifcn`, which must be tied to original met.inp for production.
- `G17C2SelectedElustrResult::selected_slope_fixture()` transfers the **ELUSTR-updated QH** to subsequent G17 SLOPE with exactly the second SURFVAR temperature; it cannot declare a production native stage complete.
- Extend existing G17B4 CTest to cover daytime and nighttime source cases; per-cell QH, USTAR and EL equal independent direct invocations of the two immutable source kernels. Reject stage-wind replacement, stale temperature, shifted GEO/station reorder, invalid roughness and unmarked fixtures. Ensure previous-hour ZICONV remains untouched.

## Explicit remaining blockers

1. External experimental HEATFX coefficients and original parameter authority are still not fully bound to original input and control state. `explicitly_test_only=true` is mandatory; full `DiagnoHeatfx`, `DiagnoElustr` still fail closed.
2. This increment is **all-land**, original-selected 2SS+2US, 9 layers and does not validate water, arbitrary pressure or additional meteorological control branches.
3. Real multi-station PREPDI/DIAGI stability-dependent SIMILT, STHEOR/ELUSTR2/MIXHTST, previous-hour CGAMMA/DPTT, second WINDBC, SMOOTH/DIVCEL/W, COMP, full P6F and source-parity 45-field 1h/6h/143h/year remain incomplete.
4. #53 163-file immutable guard and independently repeated source-accepted single-site 143h regression must stay passing. This development must not alter the numerical tolerances or merge until the complete multi-station Fortran scientific oracle passes.

## CI evidence

Check the **exact commit SHA** for PR #63 and its GitHub-hosted Ubuntu `P6G multistation on accepted single-station baseline`, source-vendor G9-G11 and inherited 143-hour scientific workflows. A successful G17C2 selected CTest does not certify full 45-field P6G multi-station production equivalence.
