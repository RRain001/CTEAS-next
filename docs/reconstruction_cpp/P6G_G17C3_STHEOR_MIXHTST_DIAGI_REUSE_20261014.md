# P6G G17C3 — Reuse #53 STHEOR, MIXHTST and DIAGI for multi-SURF selected stage

Date: 2026-10-14; owner PR: #63 (Draft), stacked on #53 at `8d6642272d0abb77153880591e150f93e14d4479`.

## Architecture and scope

The accepted PR #53 143-hour scientific producer is **not** being rewritten or generalized in place. PR #63 retains its dynamic GEO/SURF/UP inputs, station identity and G14 `kHefeiOriginalStageOrder` single authoritative hour scheduler. The new G17C3 adapter is **selected/test-scoped** and is not promoted into the full G14 production callback.

The selected station-specific path is:
1. From exactly the current original SURF.DAT hour, use each SS station's **raw anemometer** wind, opaque cloud and pressure. The station's own absolute WGS84 UTM coordinates provide the SIMILT latitude; GEO maps each site to its own grid cell, without domain-edge clamping.
2. Use the already source-selected G17C1 solar and second post-FRADJ SURFVAR temperature. Source-backed landuse, GEO Z0, albedo, Bowen ratio, HCG and QF are required; no single-station constant `Z0` or surrogate pressure/cloud is allowed.
3. Invoke **unchanged PR #53** `p6::station_elustr2_flux` for STHEOR station QH/USTAR/EL. Station ELUSTR2 has different wind-floor/log rules than gridded ELUSTR and must not be replaced by gridded output.
4. Use the explicit caller-provided **SS→US ordinal** to select that upper station's most recent sounding whose timestamp is <= the current hour's **start**, never a future sounding. Build original `MixdtSounding` directly from the observed thermal levels.
5. Invoke **unchanged PR #53** `p6::station_mixhtst` with the station cell's original **previous committed COMP ZI/ZICONV/DPTT**, not the current hour's temporary field. Record its ZI cap, convective height and /TJMP/ DPTT mutation; do not commit any current-hour state in the selected bridge.
6. Invoke **unchanged PR #53** `p6::original_similt_profile` using station EL, MIXHTST ZII, original ZFACE/ZIMIN. The resulting per-level DIAGI surface profile has an explicit validity mask above the cutoff.
7. Merge those surface columns into `G16ObservedProfiles.inter2_*` only. Neutral WIND1 columns and each independently PREPDI-generated upper-air profile remain unchanged. Only after the already accepted FRADJ/SLOPE/first WINDBC is this replacement accepted by G16 and consumed by INTER2. Duplicate/stale stage handoffs fail closed.

## Tests and scientific guards

The dedicated extended `p6g_g17b4_original_iavet1_pre_and_post_fradj_surfvar` CTest now exercises selected 2SS/2US daytime and nighttime hours, reads the pinned real met.inp numerical wind controls, and checks:
- Source station identities 58321/58322 and distinct upper-station identities 58424/58425.
- **Elementwise/exact** comparison of station QH/USTAR/EL, MIXHTST ZII/ZICONV/DPTT and SIMILT U/V against separate direct calls of the immutable #53 source kernels.
- Station-specific observed wind **direction and speed**, original latitude, independent older UP soundings and separate 2SS station-cell GEO indices.
- Rejection of missing wind direction, invalid SS→US ordinal, missing valid older sounding, unmarked test fixture, reordered stations, changed upper-air profile, duplicate profile refresh and stale model-hour values.
- No change to the `frame.previous` committed prior-hour buffer and no false `NativeCpp,true` claim for unimplemented DIAGNO/COMP stages.

## What is explicitly NOT complete

The original CALMET multi-SS **station-to-UP correspondence**, original source-dependent STHEOR/ELUSTR2 numerical controls (HA/HB/HC, FCORI/CONSTB, MIXHTST parameters, IPSIFCN), and water/calm branches still require an independently verified general original-input route. The current SS→US association and thermodynamic controls are **explicitly test-only**. PREPDI/CGAMMA and CGAMMA historical branch dependence, actual complete G17C3 in every real model hour, generic second WINDBC→SMOOTH→DIVCEL→W, full COMP and P6F remain outside scope. No full real-case 45-field multi-SS/US parity is claimed for 1h, 6h, 143h or year.

Do **not** remove fixture checks or convert selected stage PASS into production PASS; continue to require original vendor CALMET numerical comparison and the independent frozen PR #53 143-hour strict regression. PR #63 must remain Draft until that evidence exists.

## CI

Run on GitHub-hosted Ubuntu, verify **exact HEAD**. The relevant checks are `P6G multistation on accepted single-station baseline` (Debug and Release `^p6g_` CTest, frozen 163-file guard), `P6G original-vendor G9 G10 G11 source parity` and the inherited `P6 native causal DIAGNO COMP hourly integration`. Document the actual GitHub run ID and conclusion separately; the existence of this note does not imply CI PASS.
