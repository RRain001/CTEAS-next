# S4-A | Issue #40 | C1/C2 P6 execution architecture inventory

Date: 2026-10-20. Scientific scope: SOURCE-LEVEL AUDIT ONLY. No physics kernel, CALMET control, numerical tolerance, or frozen runner is changed by this PR.

## Decision

Preserve accepted C1 (2022 Hefei, 1SS/1US, 50x50x9, 143 h, compared against FROZEN original CALMET meteorology) and C2 (2024 controlled-synthetic 2SS/2US, 12x12x9 at 10 km, 143 h, independently FRESH-RUN unchanged original CALMET and C++ P6). Both passed their existing selected 143 x 45 field-level comparison without exceedances; these are separate accepted scenario-specific numerical baselines, NOT proof of one production P6 implementation.

Work toward ONE native G14 / DIAGNO / COMP / P6F production runner based on the C2 17-stage causal architecture, reusing only physically verified low-level original-option kernels from the C1/C2 implementations. Preserve old binaries only for frozen reference and audit. Do not create a third Huoshan-specific production flow out of the previously merged source-only PR #193–#200 probes.

## Observed actual binary and source paths

| Property | C1 actual route | C2 actual route | Unification action |
|---|---|---|---|
| GitHub workflow | .github/workflows/science-c1-143h.yml | .github/workflows/science-c2-143h.yml | Keep as independent regression baselines |
| P6 executable | cteas_p6_native_hourly_driver | cteas_p6g_g34b_six_hour_selected_gate | Create a new common production driver |
| Orchestrator source | native_cpp/modules/p6_calmet/src/native_hourly_driver_main.cpp invokes P6D and P6E separate stage binaries | native_cpp/modules/p6_calmet/src/p6g_g34b_six_hour_selected_gate_main.cpp owns G34BSelectedOnlyHour::run: 17 ordered stages | Use G14 coherent live-hour frame, prev-state and output as the only authority |
| DIAGNO | realcase_wind_field_main.cpp calls selected stage kernels and file-backed sources | G26 A via run_selected on source-backed frame, prepdi/g20/g21/g22/g23/g24 | Audit each adapter and exact input/option semantics |
| COMP | process-run P6E + NativeCompHistory files | G26B via G18D4 selected COMP, same frame | One cumulative causal COMP history, no original-MET backfill |
| P6F | P6E joined MET and independent serialized header | G34B g18c5 + g18c6 45-field selected P6F | Identical original field order and dynamic NX x NY x 45 REAL4 |
| Frozen restrictive conditions | C1 P6D nx=50 ny=50 nz=9, NSSTA=1/NUSTA=1; upper up_58424.dat and max143h | C2 G34B 2SS/2US, 12x12, 6 or 143h, explicit test-only mode; G26 production run() returns Unknown,false | Never silently relax fixed gates without matching science |

## Low-level selected-physics function and adapter audit

| Stage | Evidence of actual C1 call or include | Evidence of actual C2 dependency | Current scientific conclusion |
|---|---|---|---|
| Original input, PREPDI, VERTAV, CGAMMA | read_upper.hpp, frozen surface/upper bridge, c1 hourly gamma input | G19 + G18E4 + G20 from same live original G14 hour | Data processing and state ownership differ; compare exact selected options and missing first upper layer |
| WIND1 | wind1_selected_firstguess.hpp and upper_hourly_wind.hpp | G20 / G16 selected stations and observed profiles | Some lower functions overlap but full station/clock pathway not proven cross-runner equivalent |
| FRADJ and TERSET | realcase_wind_field_main.cpp includes froude_adjust.hpp and calls froude_adjust | G26 -> G21 -> p6g_terrain_hour.hpp includes SAME froude_adjust.hpp | Shared low-level file, but full input CGAMMA/TERRAD/CRITFN and state must be compared |
| SLOPE | C1 includes slope_flow.hpp | G21 terrain adapter and G22 share slope_flow.hpp | Shared kernel, source QH/TEMP and stage order still need audit |
| SURFVAR/HEATFX/AIRDEN/ELUSTR | C1 surfvar_observed, p6e/heatfx, elustr_stable/daytime | G21 twice SURFVAR, G22 selected thermal branch | Separate wrappers; source time/option and REAL4 must be proven |
| STHEOR/ELUSTR2 | C1 calls station_elustr2_flux from station_elustr2.hpp | G23->G17C3 includes station_elustr2.hpp | Shared low-level kernel; station/previous-COMP state may differ |
| MIXHTST / DIAGI / SIMILT | C1 calls station_mixhtst and original_similt_profile | G17C3 includes station_mixhtst.hpp and similt_profile.hpp | Shared headers do not establish identical full station profile; original NOAA STHEOR parity pending |
| INTER2 and post-wind tail | C1 inter2_selected.hpp and P6D diagnostic segments | C2 G23 INTER2, G24 WINDBC/SMOOTH/DIVCEL/W | Input flags, weights, missing upper k=1 and boundaries need explicit parity |
| COMP history | NativeCompHistory in C1 process coordination | G26B / G18D4 G14 state and first-hour init | DISTINCT orchestration and state ownership, highest risk |
| P6F | File-backed 45 field merger | g18c5/g18c6 original binary dataset | Distinct output builders; prove full original 45 fields with same new binary |

Do NOT equate shared low-level header files to an already proven identical full numerical execution. Audit classifications are SHARED_LOW_LEVEL_FILE, DISTINCT_ADAPTER, DISTINCT_STATE_OWNER, and UNSUPPORTED_OPTION. The script scripts/s4/p6s4a_execution_route_audit.py pins 37 unique source-based facts and emits all SHA256 without running science; a deliberately changed C2 station cardinality guard must fail closed.

## Subsequent bounded PR sequence

- S4-B1: new independent native G14 runner contract and state/data ownership. Keep C1 and C2 frozen binaries functional. Do not prematurely remove G26 run() Unknown,false gate or copy selected output into production.
- S4-B2/B3: connect the same verified original selected kernels, COMP history, original-format 45 fields in a real unified actor. Numerical original CALMET 1-hour and 6-hour stage gates before broader claims.
- S4-C: dynamic independent 1..N ground station and 1..M upper station, 1/1 1/2 2/1 2/2 positive and negative cases, selectable valid NX/NY/DGRID, original source positions, UTC windows, cross-year and provenance. Never fabricate a station or upper missing layer. S5 #161 owns all-static-capacity-limit removal.
- S4-D: on ONE binary rerun accepted C1 143h 45-field and fresh-original C2 143h 45-field, then same genuine Huoshan S3 original GEO+SURF+UP 1h/6h (and legally available longer) original Fortran versus native CALMET with all 45 original fields per hour. Failing any cannot be labeled unified science PASS.
- S4-E #36 follows S4-D scientific acceptance: actual newsite P7, original CALPUFF, cross-site unified P1–P7. No Docker or rain/wet deposition until separately scheduled.

Scope verdict: C1_PASS_SCOPED / C2_PASS_SCOPED / S3_REAL_INPUT_PASS_SCOPED retained. S4A_ROUTE_SOURCE_AUDIT awaits CI. C1_C2_UNIFIED_PRODUCTION=NOT_IMPLEMENTED; NEW_SITE_P6_45FIELD=NOT_ACCEPTED.
