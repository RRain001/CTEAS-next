# Issue #42 S3-B6 — original CALMET `met.inp` and real-source G19 parser admission

Date 2026-10-20. Depends on merged [PR #189](https://github.com/RRain001/CTEAS-next/pull/189), `main@ce72f5a19ab758b8bb412c3cea4661ab4a156bcb`. Its actual [Actions #39404962297](https://github.com/RRain001/CTEAS-next/actions/runs/39404962297) completed both 2022 Jan and June real-terrain/GLCC/P3 original numerical jobs with success; June additionally genuinely produced P4 Anqing 2022 IGRA `UP.DAT`, P5 Luogang 2022 real full ISD + ISD-Lite `published SURF.DAT`, and the existing S3 five-source SHA join (not G19).

## This PR's one scientific gate

**Do not implement new CALMET physics or duplicate its native G19 input parser.** Reuse `engine.run_met.prepare_met.render_met_inp`'s original format / input group / station row generation by adding one explicit `source_paths/source_grid/source_times` scope for an isolated external B0. Its original legacy `case_name` behavior is unchanged if no override is supplied. Actual locations are the independently produced paths under the *same fresh* June `s3_huoshan_2022` case:

- `geo/makegeo/p3_case/geo.dat`
- `met/upperair/final/up_58424.dat`, original independent P4 producer selected authentic Anqing `CHM00058424` (728 / 730 valid original 2022 profiles), physically outside the small grid, effective station at declared stack
- `met/surface/final/surf.dat`, produced from original NOAA 2022 Luogang `58321099999` data, single virtual station under actual >90% real annual full/Lite acceptance
- Original WGS84 UTM50N `grid.cmn` and June 1–2 24-hour UTC `research_time`, no historical Hefei `GEO/UP/SURF` fallback.

Add only the original selected `FROZEN_MET_CONTROLS`, `FROZEN_PUFF_CONTROLS` and the existing source-only nominal positive stack fixture to `case.yaml`, with source lat/lon equal to actual grid center. It is **metadata admission only**: emissions are not used by any P6/P7 numerical driver. The resulting new immutable case SHA is properly propagated by full rerunning the genuine P1–P5 producer chain and independent P3 original scientific comparator. No old `case.yaml` and new `met.inp` are mixed.

A fail-closed `native_cpp.orchestration.s3_huoshan_g19_source_only` orchestrator checks the already independent `s3_five_source_preflight` proof and exact B0 SHA, renders `run/met/met.inp` with the unchanged format mechanics, then calls the **existing** `native_cpp.orchestration.p6_g19_handoff.prepare_g19` and `execute_source_preflight`, compiled original-format native target `cteas_p6g_g19_source_case_preflight`. It validates actual file bytes, station identity/order, parser native stdout, NX/NY and source-only true status before emitting **bounded metadata JSON only**. No model fields/time stepping are computed.

## Strict verdict

Only a real workflow run with successful P1/P2/P3 original 80,000-field no-snow numerical comparator, genuine P4/P5 selected sources, five-SHA join, `met.inp` production and **native G19 actual-file parsing** can yield `S3_B6_HUOSHAN_GENUINE_FIVE_SOURCE_NATIVE_G19_PARSED_SCOPED`. Missing source, station, B0 SHA or parser failure remains a true blocker; never rename `P6_G19_DYNAMIC_FILE_INPUT_PARSED_NO_PHYSICS_EXECUTED` into a wind-field acceptance.

Still required before closing #42: S3-4 additional grid/station/time configuration positive and negative tests plus independent scope audit. **P6 45-field/hour numerical wind/P7 diffusion, wet deposition, S5 resource expansion, Docker remain NOT_RUN/DEFERRED.**
