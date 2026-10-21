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

## Actual NOAA first-hour failure and source-owned remediation

The first full genuine-source Actions attempt `39570627483` stopped at `G20 unsupported missing/calm original surface wind`. This is a real observed data condition, not a compiler problem or an allowable opportunity to invent a wind. Pinned original CALMET WIND1 lines 36114–36126 explicitly skip similarity extrapolation on EDITL-missing SS and create physically zero profiles for valid calm; lines 36239–36242 suppress missing surface station bulk weight, then preserve source BIAS/ICALM and valid upper station weight logic. Existing frozen G9 C++ `multi_station_wind1_firstguess` already implements masked-zero bulk weights and calm reweighting, but G20/G16 default adapters refused such stations before reaching it.

Follow-up adds `g41_original_noow_water_source_profiles` as a typed test-only G20 source-map wrapper; missing original SS gets `present=0` on every layer, calm valid SS keeps `present=1` with exact zero wind. The separate G42 source type invokes the **unchanged** G9 numerical kernel, uses a zero *inactive storage carrier* only for `present=0`, and verifies no missing station is advertised as valid. The existing G20 original signature retains its former missing/calm refusal, and G16 remains unchanged. Its output feeds G41 G21 FRADJ. No weakening of G19FileBackedCase/G26 and no synthetic meteorological observation. This remains scientifically `NOT_ACCEPTED` until a successful real-original comparison across all 63 water cells for first-hour WIND1/FRADJ.

## Second genuine science run and strict air-density separation

Actions `39571732687` proves that selected real 2SS+1US G42 preserved the first-hour observation: `S4R1C1_SOURCE_NOAA_MISSING_SURFACE_COUNT=1 CALM_COUNT=0`. It then stopped at `G17B AIRDEN missing RDSN pressure/TEMP2D` in G39. This is a **separate** P5 sparse auxiliary *nonwind* missing-data condition, not a return of the G20 wind defect. Original vendor AIRDEN calmet.for L2094–2098 blindly performs `rho=0.3484321*PRES(NEARS)/TEMP2D` with no source missing-data guard, potentially creating an unphysical density if PRES is an original missing sentinel; the native G17B guard correctly fails closed. P5 must retain its approved primary fill + sparse auxiliary policy, including missing original pressure. Never silently fill from primary or treat `9999` as measured pressure, and do not disable all-land physical AIRDEN protections.

**R1c1 scientific stage reduced strictly to source-native first-hour G42 WIND1 + G21 FRADJ + genuine 2×SURFVAR**. These three kernels run *before* original AIRDEN and consume no station pressure. The selected first-hour executable exports only six physical per-cell values (U/V before and after FRADJ; TEMP2D before and after FRADJ), not fabricated QH/QSW/rho/USTAR/EL. G40 original/native 63×6 water QSW has already been scientifically accepted separately in #238, and is not revoked. G39 heat+air density remains `NOT_RUN_ON_REAL_SPARSE_AUX_PRESSURE`, not PASS. The scratch original independent first/second DIAGNO diagnostic remains full 6h reference, and first-hour 63-water pairing is required to claim G42/G21 parity.
