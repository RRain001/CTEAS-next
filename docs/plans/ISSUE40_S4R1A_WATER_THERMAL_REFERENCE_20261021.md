# Issue #40 — S4-R1a selected WATER SURFVAR/HEATFX/ELUSTR test-only bridge

Date 2026-10-21. Base `main@564dc48e5df9779e9a8025f4a9f4970f28268ad1` after **merged S4-R0 #236**, source-only input gate with original WATER neutral controls.

## Why R1a is separate from R1's scientific claim

Reading actual post-S4-Q source shows a FIFTH water fail-closed barrier beyond the G19/G17C1/G17C2/G26B four identified in S4-Q: `G17B4TwoPassSurfvar` also refuses water before the original first- and second-pass IAVET=1 calculations. Simply changing G18D3 or G17C1 would be neither executable nor physically correct.

S4-R1a *does not change the accepted all-land default behavior*. It adds individually opted-in **test-only** water acceptance at G17B4, G17C1, G17C2; all existing call sites retain their default false. A separate `g39_original_noow_water_postfradj_thermal_reference` requires the S4-R0 G38 original-deck selected-control contract, actually completed first and second SURFVAR passes, source station and grid identity, identical second-pass post-FRADJ wind, a valid model hour, and an explicitly supplied original ZM source height.

- SURFVAR uses existing P6E original `surfvar_multistation` plus AVETMP first-level wind; neither initial wind nor post-FRADJ wind is generated here.
- HEATFX uses frozen `p6e::heatfx` for **all cells'** shortwave QSW; original water QH is passed as zero (no-OW-selected neutral WATER), and original HEATFX skips writing it. Explicitly refuse nonzero injected water prior QH.
- ELUSTR uses frozen `p6e::stable_elustr` and `p6e::elustr_daytime` for land cells only; on genuine water cells it SKIPS writing USTAR/EL, and keeps QH=0. Its water USTAR/EL **zero placeholders are not physical WIND/COMP outputs**. `water_state_pending_original_WATER=true` documents this missing stage.
- Both standard G17C1/G17C2 and G17B4 **continue to reject any water** when the additional test-only parameter is absent. G18D3's existing all-land physical admission and G19/G21/G22/G23/G24/G26/G26B main paths remain unchanged.
- The new G39 return type has `water_ustar_el_zi_ready=false`, `g22_g24_wind_ready=false`, `g14_g26_production_ready=false`.

Negative controls: missing explicit authority, invalid READCF water tuple, original HFLUX override, detached wind, unknown water GEO, default all-land G17B4/G17C1/G17C2 still deny, incomplete SURFVAR, and water ELUSTR stage cannot synthesize neutral WATER turbulence state.

## Acceptance truth table

| Requirement | Current R1a evidence |
|---|---|
| C++ software kernel builds and fail-closed opt-in controls | Await exact-head Actions; `PASS_SOFTWARE` only if complete |
| Original HEATFX independently compiled Fortran 24 cases and 960 QSW/QH reference scalars | Previously S4-L #230 `PASS_SCOPED`, not newly rerun by R1a |
| Real 2022 2SS/1US 82×85×9, 63 WATER×6h post-FRADJ C++ thermal fields vs scratch original | `NOT_RUN` in R1a |
| True native G24 63×6 water U/V/WS10 vs S4-Q vendor trace | `NOT_RUN` |
| G26B WATER COMP, full 6×45 45-field original-vs-native numerical science | `NOT_RUN` |
| G26 default production / P7 #36 | `NOT_ACCEPTED` / `BLOCKED` |

## Next acceptance-required stage

S4-R1b must rebuild the actual NOAA source-owned `G19SourceClockCase` 2SS/1US water case (82×85 @1km) and preserve real post-FRADJ source geometry. Derive source G17B4 SURFVAR1/SURFVAR2 and G39 HEATFX/ELUSTR from real independently native G20/G21 stage data, then compare each genuine water QSW/QH and all land ELUSTR scalar field-hours against original Fortran scratch-only instrumented trace, keeping byte-identical whole original MET.DAT. A new structurally typed native water-only wind-DIAGNO path (with original land station mapping) may be added only when science permits, and must still prohibit default G26 and P7. Then compare actual native G24 first-plane 378 water U/V pairs against S4-Q original, followed by selected COMP/WATER 6h×45 all-grid independent original and native.

Do not label this PR `PASS_NEW_SITE_45FIELD_SCIENCE` or claim S4-R1 complete from the scoped software tests.
