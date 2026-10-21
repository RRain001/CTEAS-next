# Issue40 S4-R1c1 – authentic water 2SS/1US first-hour native WIND1/FRADJ/HEATFX

Date 2026-10-21, baseline main@c2e381ceb6c279a58d8c702cb8da067276c612c7. Follow accepted R1b original-vs-native 63 water cells×6-hour QSW parity PR #238.

## Source architecture decision
The existing `G19FileBackedCase` is a physics-ready all-land-only type, and the selected G21 source kernel accepted that type. Explicit opt-ins added in S4-R1a at G17B4/G17C1/G17C2 were never connected to real mixed GEO. Never remove `g18d3_source_hflux_inputs` water refusal, never cast `G19SourceClockCase` into `G19FileBackedCase`, never bypass accepted source checks with fabricated winds.

Create `G41SelectedNoowWaterFirstHourSource` separately from `G19FileBackedCase`: real original source and observed hourly station clock from G19 source-only; unchanged G18D6 nearest upper station and land-observation validation; unchanged exact G38 selected `NOWSTA=0 ITWPROG=0 ICOARE=10 IMIXH=1 NOOBS=0 IAVET=1 ISURFT=-1` and no original HFLUX coefficient override; original G17B4 two-pass SURFVAR controls.

G21 source kernel is extracted once with an explicit `selected_water_reference_only` argument. Its public accepted G19FileBackedCase signature wraps with *false*, preserving the exact old all-land behavior. Only the typed G41 first-hour wrapper may call with *true*, which again checks G38 original water controls. G41 real CLI accepts source-owned NOAA `met.inp/GEO.DAT/SURF.DAT/UP.DAT`, constructs original scheduler and prepared PREPDI/CGAMMA, computes native G20 first WIND1 and native G21 FRADJ / two SURFVAR passes, then calls source-gated G39 to execute HEATFX/land ELUSTR, leaving WATER USTAR/EL/ZI pending. It emits source-water-only first-hour per-cell U/V and thermal diagnostic CSV without any CALMET.DAT or vendor trace as a native input.

## Verification gates

- Compile existing G19 and new G41 with `-Werror`; retain source-denial test.
- Run genuine NOAA 2022-06-01 01–07 UTC 2SS (583140,583210) +1US (58424), 82×85×9 UTM50N, 63 mixed WATER cells. Source hashes are already checked in the same S4-R1b artifact-generation pipeline.
- Independently run original Fortran CALMET 6h from identical inputs. The scratch-only original R1b DIAGNO HEATFX trace provides first-hour water `QSW` and second SURFVAR `TEMP2D` for actual scientific comparison. Never replay original U/V as native input.
- Require genuine native G41 first-hour 63 WATER rows, unchanged original source hour, source-control and station mapping, preserved native no-OW water QH zero. Report per-cell numerical residual of source QSW and post-FRADJ TEMP2D. If original vs native post-FRADJ temperatures disagree, this is an explicit scientific failure requiring diagnosis; **do not** mark original full G21 as verified from QSW alone.
- No prior-hour G14 memory or station clock commit; output only the **first hour** and retain all full six-hour wind and 45-field science as NOT_RUN. Full independent native G24 63×6 first-plane U/V remains the next stronger stage; water MIXHT/WATER/COMP/G26/P7 not accepted.

## Scope truth

`G41_FIRST_REAL_HOUR_NATIVE_G20_G21_G39` may be marked `PASS_SCOPED` **only if** all exact-head workflow software/scientific checks pass. A software-only compile success is `PASS_SOFTWARE` and must not become full P6 acceptance. The authoritative P6 Issue #40 remains open and P7 #36 blocked.
