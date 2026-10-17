# P6G G17C1: reuse the accepted P6E kernels, not a second CALMET implementation

Date: 2026-10-14. Development PR: #63 (Draft), stacked on accepted single-site physical authority PR #53 at `8d6642272d0abb77153880591e150f93e14d4479`.

## Architectural decision

- Keep the PR #53 verified real 143-hour P6D/P6E/P6F process-coordinator as an immutable **scientific regression**, not as a generic production application (it contains the pinned 50x50x9, 143-hour, selected-SS/US constraints).
- Keep PR #63 dynamic GEO, original SURF/UP, parsed met.inp, G14 hourly-state scheduler, and already validated multi-site source-selected WIND1, INTER2, FRADJ and SLOPE adapters.
- Reuse PR #53 physical kernels directly. Never fork CALMET's physical formulas merely because the number of stations changes. Only the data/parameter adapter, stage invocation and state transfer should become generic.
- Source-correct original order remains the shared `kHefeiOriginalStageOrder`. Last-hour committed ZI/ZICONV/DPTT may not be overwritten by a partially calculated current hour.

## This change: one previously missing stage handoff

Original CALMET with real `IAVET=1` executes `WIND1 -> SURFVAR/AVETMP #1 -> FRADJ -> SURFVAR/AVETMP #2 -> HEATFX/AIRDEN/ELUSTR -> SLOPE`.
G17B4 already obtained the two distinct temperature fields from the real stage-specific winds, but used a fixture heat flux in the subsequent selected source chain.

The new `p6g_g17c_iavet1_heat_handoff.hpp` accepts **only the verified second post-FRADJ SURFVAR temperature**. It computes the actual mid-hour solar field from original source UTM and UTC through PR #53 `surface_solar_grid/sinalpc_grid`, source-original `SETCOM NEARS`, observed station cloud and pressure, and invokes the **unchanged PR #53 P6E `heatfx` kernel** plus PR #63's separately original-Fortran-validated `source_airden_nears` AIRDEN implementation. No HEATFX, solar or AIRDEN equations are rewritten.

The G17B4 source object now retains the exact original GEO origin, extent, resolution, land classes, UTM zone, hemisphere and ordered station IDs/positions; HEATFX refuses a different grid, reordered sites, missing cloud, wrong hour, unsupported water, unmarked fixture or incomplete first/second SURFVAR. G17 returns the second temperature and computed QH to its existing SLOPE adapter. All previous-hour P6E state remains unchanged.

The extended existing G17B4 selected CTest directly compares QH/QSW against an independent invocation of the frozen PR #53 HEATFX header and density against `source_airden_nears`. It also rejects first-pass temperature, wrong station ordering, shifted GEO origin, wrong hour and missing cloud.

## What is *not* yet accepted

- This is an **all-land, 2SS+2US, 9-layer selected-stage test**. `G17CSelectedHeatInputs` deliberately requires `explicitly_test_only=true` because HA/HB/HC heat coefficients and the initial water-QH field are externally specified test controls rather than fully re-derived from the live original CALMET controls. Full real-world source attribution and the water-cell branch remain unverified.
- Neither the adapter nor its outputs can mark native `DiagnoHeatfx`, `DiagnoElustr`, `COMP`, or `P6F` complete; `G17SelectedTerrainFixturePhysics` continues to return `{Unknown,false}` for stages outside its validated scope.
- No single-site accepted physical source, PR #53 driver, numerical tolerance or branch-base topology is altered. A green selected test or 8784-hour input clock is **not** complete multi-station original Fortran 45-field parity.

## Next required integration, in priority order

1. Derive HEATFX coefficient/initial-condition and DAY/STABLE ELUSTR inputs from the same authentic original configuration and prior-hour COMP state. Replace the explicitly test-only controls only with independently verified source values.
2. Connect authentic PREPDI/DIAGI stability-capped observations, second WINDBC, SMOOTH/DIVCEL/W and complete P6E CGAMMA/MIXHT/AVEMIX/WSTARR/TEMP3D through G14's exact ordered callbacks, reusing the frozen physical kernels.
3. Generate native P6F hourly output with zero Fortran meteorological-field backfill. Require independent CALMET Fortran multi-station 45-field comparison for 1h, 6h, 143h and a full year. Preserve PR #53 143h 45-field zero-exceedance regression on every subsequent change.
4. Only then promote #63 beyond Draft and allow the copied G5 GUI to enable generic P6.

## CI attribution

The relevant scientific checks are `P6G multistation on accepted single-station baseline`, `P6G original-vendor G9 G10 G11 source parity`, and `P6 native causal DIAGNO COMP hourly integration`, all on **GitHub-hosted Ubuntu**. Always check results against the exact new commit SHA; this document does not claim any CI job succeeded before it has completed.
