# P6G G18E5 — original-order SLOPE after staged ELUSTR (2026-10-15)

## Scientific boundary

This change is a **selected-fixture integration test**, not production CALMET and
not independent original-Fortran 45-field multistation parity. The single-site
PR #53 143h 45/45 comparison remains the scientific regression baseline.
G18E5 does not edit accepted P6D/P6E physical kernels, alter tolerances, or
introduce another scheduler.

## What changes

- Adds `p6g_g18e5_slope_stage_adapter.hpp`, a test-only adapter that accepts
  only frozen `kHefeiOriginalStageOrder[6] = DiagnoSlope`.
- It consumes `G18E2SelectedHeatfxStageAdapter::selected_heat_for(frame)` and
  `G18E3SelectedAirdenElustrStageAdapter::selected_elustr_for(frame)` for
  the **same live G14 frame and previous-hour memory**. It propagates the
  *post-ELUSTR* QH and *post-FRADJ* second-pass SURFVAR temperature to the
  existing G17 `provide_slope_heat` and `run(DiagnoSlope)`.
- G17's original accepted `compute_original_slope_scoped` kernel remains
  the only SLOPE calculation; G18E5 does not duplicate or approximate it.
- The test rejects wrong stage, fixture-to-production promotion, copied
  hour frame, changed previous-hour DPTT, duplicate execution and copied
  result retrieval. It checks resulting U/V fields are exactly those from
  G17's frozen kernel (not a loosened numerical comparison).
- The normal `MultiHourPhysics::run` explicitly returns
  `{Unknown,false}`; the full 17-stage scheduler **cannot** accept G18E5
  as an independently validated production stage.

## Source order and remaining acceptance

`PREPDI -> WIND1 -> FRADJ -> HEATFX -> AIRDEN -> ELUSTR -> SLOPE -> WINDBC -> ...`

The direct test's previous manual `provide_slope_heat` and `run(DiagnoSlope)`
calls are replaced with a provenance-checked stage adapter. This closes one
selected stage-routing gap. It does **not** prove:

1. All 17 G14 production callbacks operate on real 2SS+2US observations.
2. Real multistation original-vendor CALMET 45-field parity at 1/6/143/8784h.
3. Crash-safe P6F file publication/restart or all CALMET input branches.

CI evidence must be tied to the exact final source HEAD and both
Debug/Release CTests plus the frozen PR #53 science regression. PR #63
must remain Draft until all substantive acceptance gates pass.
