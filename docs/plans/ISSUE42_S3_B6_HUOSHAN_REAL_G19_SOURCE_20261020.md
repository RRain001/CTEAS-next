# Issue #42 S3-B6 — original CALMET `met.inp` and real-source G19 parser admission

Date 2026-10-20. Depends on merged [PR #189](https://github.com/RRain001/CTEAS-next/pull/189), `main@ce72f5a19ab758b8bb412c3cea4661ab4a156bcb`. Its actual [Actions #39404962297](https://github.com/RRain001/CTEAS-next/actions/runs/39404962297) completed both 2022 Jan and June real-terrain/GLCC/P3 original numerical jobs with success; June additionally genuinely produced P4 Anqing 2022 IGRA `UP.DAT`, P5 Luogang 2022 real full ISD + ISD-Lite `published SURF.DAT`, and the existing S3 five-source SHA join (not G19).

## This PR's one scientific gate

**Do not implement new CALMET physics or duplicate its native G19 input parser.** Reuse `engine.run_met.prepare_met.render_met_inp`'s original format / input group / station row generation by adding one explicit `source_paths/source_grid/source_times` scope for an isolated external B0. Its original legacy `case_name` behavior is unchanged if no override is supplied. Actual locations are the independently produced paths under the *same fresh* June `s3_huoshan_2022` case:

- Actual P3 native output `geo/makegeo/p3_case/geo.dat`, freshly **copied byte-for-byte with SHA verification into `geo/makegeo/geo.dat`** for the original CALMET consumer. The real P3 source receipt SHA must match both files; no external GEO or symlink.
- `met/upperair/final/up_58424.dat`, original independent P4 producer selected authentic Anqing `CHM00058424` (728 / 730 valid original 2022 profiles), physically outside the small grid, effective station at declared stack
- `met/surface/final/surf.dat`, produced from original NOAA 2022 Luogang `58321099999` data, single virtual station under actual >90% real annual full/Lite acceptance
- Original WGS84 UTM50N `grid.cmn`. Both January 48h and June 24h authentic source chains remain preserved, but real native G19 is attempted **only** for the authentic **2022-06-01 01:00→07:00 UTC six-hour window**. No historical Hefei `GEO/UP/SURF` fallback.

Add only the original selected `FROZEN_MET_CONTROLS`, `FROZEN_PUFF_CONTROLS` and the existing source-only nominal positive stack fixture to `case.yaml`, with source lat/lon equal to actual grid center. It is **metadata admission only**: emissions are not used by any P6/P7 numerical driver. The resulting new immutable case SHA is properly propagated by full rerunning the genuine P1–P5 producer chain and independent P3 original scientific comparator. No old `case.yaml` and new `met.inp` are mixed.

A fail-closed `native_cpp.orchestration.s3_huoshan_g19_source_only` orchestrator checks the already independent `s3_five_source_preflight` proof and exact B0 SHA, renders `run/met/met.inp` with the unchanged format mechanics, then calls the **existing** `native_cpp.orchestration.p6_g19_handoff.prepare_g19` and `execute_source_preflight`, compiled original-format native target `cteas_p6g_g19_source_case_preflight`. It validates actual file bytes, station identity/order, parser native stdout, NX/NY and source-only true status before emitting **bounded metadata JSON only**. No model fields/time stepping are computed.

## Verified original input-window blocker and unmodified workaround

The first real B6 [Actions #39405895222](https://github.com/RRain001/CTEAS-next/actions/runs/39405895222) failed closed because the P3 producer's output `geo/makegeo/p3_case/geo.dat` was not yet published at legacy G19's role `geo/makegeo/geo.dat`. Same-case SHA-preserving publication resolves only this interface.

After that fix, the 24-hour [Actions #39406213729](https://github.com/RRain001/CTEAS-next/actions/runs/39406213729) reached the genuine native parser, which rejected the actual source: `P6G model hour lacks bracketing upper sounding`. This is a **real scientific data admission failure**, not a path issue; the original Anqing profiles provide 728/730 annual observed slots but not necessarily the needed 00/12 brackets for every proposed 24h. No fabricated 00/12 observation or forced interpolation is allowed.

The existing scoped original READ62 short case had independently accepted authentic 2022-06-01 **01:00→07:00 UTC**, supported by observed original 00/12 profiles. Accordingly the test matrix is now:
- `jan_48h`: historical geographical selected original science regression only
- `jun_24h`: genuine 24h P1–P5 same-case **source production + SHA join only**, with native G19 explicitly **NOT_ACCEPTED** for this window
- `jun_6h`: independently fresh authentic six-hour P1–P5 production, its own immutable source/time SHA, P3 80,000-value parity, actual P4/P5 hour window and **the only proposed G19 native source parser acceptance**

Any real 6h native parser failure is a scientific blocker, not a reason to relax the original NOAA station-selection or P4 profile bracketing gates. All three matrix jobs must pass on the exact submitted head before merging.

## Strict verdict

Only a real workflow run with successful P1/P2/P3 original 80,000-field no-snow numerical comparator, genuine P4/P5 selected sources, five-SHA join, `met.inp` production and **native G19 actual-file parsing** can yield `S3_B6_HUOSHAN_GENUINE_FIVE_SOURCE_NATIVE_G19_PARSED_SCOPED`. Missing source, station, B0 SHA or parser failure remains a true blocker; never rename `P6_G19_DYNAMIC_FILE_INPUT_PARSED_NO_PHYSICS_EXECUTED` into a wind-field acceptance.

Still required before closing #42: S3-4 additional grid/station/time configuration positive and negative tests plus independent scope audit. **P6 45-field/hour numerical wind/P7 diffusion, wet deposition, S5 resource expansion, Docker remain NOT_RUN/DEFERRED.**
