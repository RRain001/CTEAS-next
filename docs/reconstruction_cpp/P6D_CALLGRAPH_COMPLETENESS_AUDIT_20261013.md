# P6D CALMET C++ source-callgraph completeness audit (2026-10-13)

Scope: RRain001/CTEAS private; frozen Hefei 2022 50x50x9 grid, 143 hours. Scientific status: **P6D_FULL_UVW = NOT_PASS**. PR #51 remains Draft.

## Why local C++ parity is not full model parity

The original CALMET executable is a **stateful hour-by-hour call graph**, not merely a collection of independent subroutines. Source-faithful numerical kernels cannot substitute for: initial and shared COMMON memory, per-hour cross-module mutation, active branch selection, last-writer boundary updates, original float32 order and all independently generated output records.

### Source order established from pinned original calmet.for

1. COMP L4511 calls DIAGNO.
2. Within DIAGNO, WIND1 first-guess neutral SIMILT differs from the STHEOR -> ELUSTR2 -> MIXHTST -> SIMILT station-profile calculation. STHEOR calls (L5943–5952) update /TJMP/ DPTT in the station cell **before** COMP's grid-wide MIXHT.
3. DIAGNO: FRADJ L5643; HEATFX -> AIRDEN -> ELUSTR -> SLOPE (L5685–5732).
4. DIAGNO WINDBC(UG,VG) L5748, then INTER2 U/V L6055/L6059; on this case **HTFAC=1, so second WINDBC(U,V) L6092–6101 overwrites original boundary values**. Then SMOOTH L6119, DIVCEL and W L6124–6148.
5. COMP grid fluxes, MIXHT/MIXHT2 L4692–4699, AVEMIX L4715, WSTARR L4744, TEMP3D L4766.
6. Shared state persists to the next hour before following DIAGNO call.

## Confirmed implementation coverage and incompleteness

| Chain / feature | Current evidence | Classification |
|---|---|---|
| GEO/SURF/UP/PREPDI/WIND1 | dedicated original-source numeric tests, only selected modes/station counts | selected-case kernels, not generic |
| FRADJ/HEATFX/ELUSTR/SLOPE | source-scoped kernels, source-ordered production; 6 source-hour pre/post SLOPE parity | selected-case implementation, some strict QH driver errors |
| Station STHEOR/ELUSTR2/MIXHTST/SIMILT | independently verified physical kernels and 143h native previous-hour ZII/ZICONV/DPTT states | stage + staged recurrence PASS, NOT original one-pass COMP |
| INTER2 / double WINDBC / SMOOTH / DIVCEL / W | corrected HTFAC=1 second WINDBC, 6 source-hour U/V PASS | W strict FAIL, full-143h ULEV1/VLEV1/WFACE FAIL |
| Non-case switches: IKINE=1, IOBR=1, lake breeze, other diagnostic/prognostic input routes | isolated headers and synthetic tests exist; production realcase excludes/rejects paths | incomplete general CALMET |
| P6E grid flux, mixing, AVEMIX, WSTARR, TEMP3D | many selected kernels; selected 143h state fields DPTT, ZII, EL pass | incomplete independent CALMET.DAT field generation |
| Original one-pass time authority | scripts/run_p6_end_to_end.py: whole-period P6D -> P6F -> P6E COMP; then a second P6D using exported COMP state | **MISSING** original within-hour DIAGNO/COMP coupling |
| CALMET.DAT static and full meteorological fields | P6F write-from-p6d requires --statics-from and --met-fields-from original met.dat; P6E emits missing 9999 for unimplemented outputs | **MISSING** full independent original-equivalent output |
| General grid size/number of stations | realcase_wind_field_main.cpp explicitly limits 50x50x9 and selected station structure | case-scoped only |

### Measured source scientific status (2026-10-12 run 38281822600)

Six original DIAGNO sampled hours: final U maximum error 3.5763e-6 m/s, V 2.8610e-6 m/s, zero exceedances; W max 2.3925e-5 m/s, 687 exceedances against 1e-5 absolute diagnostic tolerance.

143h * 2500 * 27 selected wind fields: ULEV1 969 exceedances, max ~0.001711 m/s; VLEV1 824, max ~0.001319 m/s; ULEV2–9/VLEV2–9 all zero; WFACE1–9 total 352, max ~0.000268 m/s. Full U/V/W = FAIL (2145 exceedances). First low-layer exceedance: hour 12.

143h station DPTT/ZII/ZICONV/EL passes; 426 previous-hour state links checked. Do NOT confuse these with a source-original single-pass COMP acceptance.

## Execution priorities

1. Diagnose first layer at hour 12 from original write-only station US/VS and post-INTER2 grid U/V. Compare C++ station_inter2_layer1.csv and inter2_u/v fields. Fix first source divergence before changes to numerical tolerance.
2. Diagnose DIVCEL divergence and W vertical accumulation after SMOOTH separately, using source-instrumented point 10 and corresponding C++ divergence; then ensure six-sample and full-143h U/V/W scientific gates both PASS.
3. Architect actual sequential COMP State transition: for each hour DIAGNO/ELUSTR2/MIXHTST station DPTT mutation, then grid flux/MIXHT/AVEMIX/WSTARR/TEMP3D and commit state. No two-pass wind computation in final model.
4. Produce all meteorological fields independently from GEO/SURF/UP/clock. Original met.dat is a **read-only comparator**, not production data. Fail-closed when output is reference-backfilled or has missing fields.
5. Only then implement unselected switches/multiple stations/other grids. Per user instruction, precipitation and wet deposition are deferred as a separate track.

## Acceptance rules

G1 physical kernel equivalence; G2 original source-order coupled-hour equivalence; G3 independent native 1h/6h/143h all 27 U-LEV/V-LEV/WFACE fields numerical PASS; G4 all required CALMET.DAT source fields independently generated; G5 general branch/grid/station coverage.

16-runner regression matrix is only G1 software confidence: passing sixteen CTests does NOT imply G2/G3/G4/G5. Do not merge PR #51 or claim P6D_FULL_PASS until G3, and do not claim general CALMET until G5.
