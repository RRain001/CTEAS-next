# Issue40 S4-R1c2 — original COMP MISSFC station-level repair science

Date 2026-10-21. Based on S4-R1c1 accepted authentic 63-water first-hour numerical science PR #239 (branch commit 9c190cc2; not a full G14 production approval). Preserve primary/auxiliary P5 policy `P5_ISD_LITE_WIND_V2_WHOLE_VECTOR_HOLD_CALM_REPLACE`: P5 SURF files remain immutable, the sparse 583140 AUX may contain original missing WS/WD, TEMP, PRES. The selected NOAA June 2022 real 2SS (583140+583210) / 1US 58424 case uses source-generated 82×85×9 UTM50N GEO with 63 actual water cells.

## Source truth and exact native boundary

Unmodified CALMET 6.5.0 Fortran pinned blob `437f43bb7f0e51a1919e56664663e1a046986ed0`: COMP line 3986 calls MISSFC *before* DIAGNO at L4511. MISSFC L9762–10000 repairs ICEIL, ICC (when MCLOUD<3), TEMPK (when ITPROG !=2), IRH, PRES. Wind WS/WD and precipitation IPCODE must never be modified by MISSFC. Missing original TEMPK is preserved as OTEMPK. If an entire variable is missing across all stations, original MISSFC stops.

CMPD2 L3427–3456 computes REAL*4 squared distances from source-station UTM-relative X/Y, and RREPLAC L29477–29537 / IREPLAC L9216–9279 choose the nearest **original valid** source station with strict `<` tie behavior (earlier met.inp station wins). Source candidate values are saved before the outer replacement loop to avoid recursive replacement. No spatially interpolated fictitious station and no P5 file rewrite is accepted.

`G43OriginalMissfcHour` is a new standalone model-internal, source-gated detached source-hour record; its output contains the unchanged original `SurfaceHour`, a distinct resolved copy, original OTEMPK trace and independently derived 1-based donor-station identity for each of five meteorological quantities. G43 is not convertible to physics-ready G19 and does not publish any G14/G26 state.

## Independent science

Workflow `.github/workflows/issue40-s4r1c2-comp-missfc-parity.yml` performs:

1. Build P1/P2/P3 original real GEO and NOAA P4/P5 source in the same exact case and compile unmodified original CALMET six hours.
2. Original scratch source adds write-only trace **before and after COMP L3986 MISSFC**, yielding exactly 2SS ×6 hours ×2 phases = 24 station-hour snapshots. It must retain byte-for-byte original six-hour 45-field `MET.DAT`.
3. Independently build and execute G43 native source-only C++ from original met.inp/GEO/SURF/UP without original trace or MET values as inputs.
4. Compare all 24 snapshots for source station/year/julian/hour identity and ceiling, cloud, RH, IPCODE, TEMP, PRES, WS and WD against independent original. Require exact integer values and real scalar tolerance no greater than 0.001 in native units. Enforce that 583140 genuine first hour raw TEMPK/PRES/WIND are missing; original and native COMP MISSFC repair only TEMP/PRES and never WS/WD.
5. Verify P5 source SURF SHA unchanged and unmodified vs scratch original CALMET six-hour MET.DAT byte-identical. Fail closed on missing or mismatched stations, missing all-site candidate, wrong source branch or duplicate source hours.

Science stage acceptance only `PASS_SCOPED_ORIGINAL_MISSFC_2SSX6H` after exact-head Actions SUCCESS. G39 AIRDEN/HEATFX/ELUSTR real-source numerical parity, native G24 water final wind, full G14/G26 45-field, P7 remain `NOT_RUN/BLOCKED`. Do not generalize from this 2SS case to arbitrary fields or control branches without independent source verification.
