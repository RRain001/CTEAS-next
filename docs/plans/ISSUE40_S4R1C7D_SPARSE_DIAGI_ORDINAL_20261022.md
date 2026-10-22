# Issue #40 — S4-R1c7d sparse original station ordinal bridge

Date: 2026-10-22. Parent original-reference oracle #249 was independently checked against exact HEAD and merged at `main@3b4b7cdcd517a2734f50306a432f687a4747fec3`.

## This scoped change

The shared `merge_g17c3_surface_diagi` previously asserted `selected.size()==NSSTA` and indexed each `selected[i]` against `SS[i]`, although the authentic 2022 2SS+1US NOAA first hour has only one valid observed surface wind. Source-only #249 independently recorded the real six-hour pre-INTER2 three station columns and post-INTER2 all 82×85×9 original U/V without changing the pristine original 45-field output.

This change adds an **explicit source validity vector**, one binary flag per **original surface station ordinal**, to the existing shared G17C3 merge helper. It does not create a separate physics implementation.

- Omitted mask retains the old dense behavior and exact existing C1/C2 source ordering.
- Supplied mask must be binary and have exactly `NSSTA` entries, with number of ones exactly the number of native valid DIAGI station results.
- For a source-absent SS, the original station ID and all WIND1 and PREPDI columns remain in place; the DIAGI column remains marked not-present. If upstream incorrectly marked a missing SS as an observed INTER2 station, reject instead of silently reinterpreting its values.
- For a source-valid SS, require exact source station ID and UTC hour before writing only that SS ordinal's native STHEOR/SIMILT output and level-valid bits. All original US columns remain immutable; no fake zero/calm is introduced.
- Unit regression denies mask omission, invalid mask size/count/values, shuffled/wrong/duplicated surface stations, contradictory original observation presence, and stale model hour.

The existing CALMET G16 WIND1 still fails closed for a missing source SURF wind and `g23_source_stheor_diagi_inter2` does **not** opt in to this new sparse path. Therefore this is a **structural adapter unit acceptance only**, not a native real-source INTER2 run. The original source trace itself is not imported as C++ wind forcing.

## Validation

GitHub Actions authentic NOAA G48 workflow builds `cteas_p6g_g17c3_sparse_ordinal_merge_tests`, executes the positive and negative tests, and checks:

- `S4R1C7D_G17C3_REAL_SPARSE_ORDINAL_MERGE_UNIT=PASS`
- `S4R1C7D_NEUTRAL_WIND1_UPPER_PREPDI_AND_MISSING_WIND_UNCHANGED=PASS`
- `S4R1C7D_NATIVE_G16_WIND1_G23_INTER2_G26_P7=NOT_ACCEPTED`

Do not upgrade status unless Actions for this exact PR head succeed. C1/C2 frozen 143h regressions must remain green.

## Next scoped gate

Source-proven missing wind at the upstream **WIND1** G16/G20 admission stage without removing stations, no fake calm, and with original six-hour per-station validity; then connect the existing shared G17C3/G16/G23 to the real G47 land+WATER post-SLOPE state and independent original #249 full-grid INTER2 reference. Compare U/V for nine levels with frozen numerical tolerance. Subsequently solve G24 tail, causal COMP/ZICONV and native G26 45 fields before #36/P7. No wet deposition or Docker/S5 work in this PR.
