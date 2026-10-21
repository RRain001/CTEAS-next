# Issue #40 S4-R0 — selected water HEATFX source authority, not native DIAGNO science

Date: 2026-10-21. Base: `main@7428b726994bf7ceb00a45e15765534ce48d1490` (merged S4-Q PR #235). This is a **bounded prerequisite** for S4-R; it is not the completed S4-R native first-plane water-wind acceptance.

## Verified facts / invariants

- Original CALMET 6.5.0 source provenance: `CTEAS@dfad99a78ed84d655e21411c9d25eb0d2583bf13`, `calmet.for` blob `437f43bb7f0e51a1919e56664663e1a046986ed0`. S4-L PR #230 extracted original HEATFX and compared 960 original-vs-C++ QSW/QH scalars at zero exceedances; HEATFX **does not update QH over water**.
- S4-M PR #231 established the actual selected `NOWSTA=0, ITWPROG=0, ICOARE=10, IMIXH=1` input and original `WATER` (not `WATERP`) neutral fallback: water `WT=0`, hence post-WATER buoyancy QH = 0. Do not generalize this to overwater observations, COARE, or other options.
- S4-N/O/P/Q PR #232–#235 have separate original water 63 cells × six hours: 378 water-cell/hour scientific source records and standalone G35/G36/G37 *reference-only* C++ arithmetic. Original first-level U/V in S4-Q are **from Fortran**, not from a water-bearing native G24.
- Original `FCORIOL <= 998` uses literal scalar with minimum clamp; geographic GLOBE inversion requires a separately accepted branch. Original WATER's WS10 must derive from the **final native DIAGNO first level**, after G24, not station winds or intermediate FRADJ.

## Actual blockers and source-code ownership on base SHA

| Boundary | Current behavior | What S4-R must prove before any water enablement |
| --- | --- | --- |
| G19 original-file-backed strong admission | `g18d3_source_hflux_inputs` rejects every genuine GEO water cell | Distinct, **explicitly opted-in** type for selected real water source/clock and original default HFLUX; preserve normal G19 all-land path |
| G17C1 selected HEATFX | Refuses water before calling verified `p6e::heatfx` | Reuse the same original-verified P6E kernel on second SURFVAR **post-FRADJ** native temperature; keep water prior QH at selected neutral 0; independent original HEATFX water QSW/QH grid/hour trace |
| G17C2 selected ELUSTR | Explicit water rejection; existing ELUSTR kernels skip water | Preserve original water skip, make no fake water USTAR/EL. Those are assigned by original WATER in later COMP; verify land output and water untouched state from actual source |
| G22 SLOPE + G23 STHEOR/INTER2 + G24 WINDBC/SMOOTH/DIVCEL/W | Calls G17C1/G17C2 on same G14 frame | Use actual native WIND1 → FRADJ → HEATFX/AIRDEN/ELUSTR → SLOPE → STHEOR/INTER2 → G24; identify any first water-site mismatch by stage, not by injecting original final winds |
| G26B COMP | Explicit water rejection and no WATER integration | Only after native **63×6 first-layer U/V** vs separately instrumented original S4-Q pass, connect selected G35/G36 to source-driven COMP, then independent 6h×45 complete all-grid Fortran/C++ comparison |

## This PR's bounded implementation

New `g38_selected_noow_water_hflux_source_only` accepts *caller-supplied source controls*, actual water-category grid, and **explicit reference-only authority**. It requires the original selected `NOWSTA=0,ITWPROG=0,ICOARE=10,IMIXH=1,NOOBS=0,IAVET=1,ISURFT=-1`, literal historical water categories 50–55, a mixed water/land grid, and no overridden HFLUX coefficients. It reuses the existing `g18d3_original_block_data_hflux` constants and prepares selected prior-water QH=0 scratch. It refuses every other branch and returns permanent `native_final_wind_ready=false` and `g14_g26_production_ready=false`.

The previously accepted `g18d3_source_hflux_inputs`, `selected_iavet1_heat_after_fradj`, `selected_iavet1_elustr_after_heatfx`, G19/G22/G23/G24/G26/G26B, old C1/C2/Huoshan official science, and P6F remain **unchanged**. In particular, the existing strong G18D3 all-land water rejection is explicitly asserted in the new C++ negative CI.

### Explicit scientific status

- `S4R0_SELECTED_WATER_HFLUX_SOURCE_GUARDS`: software CI only; not an additional independent original-Fortran numeric test.
- `S4R_NATIVE_63_WATER_CELLS_X6H_FIRST_PLANE_UV`: **NOT_RUN**.
- `S4R_NATIVE_6H_X45_CALMET_FIELD_GROUPS`: **NOT_RUN**.
- `S4_P6_PRODUCTION_WATER_G14_G26`: **NOT_ACCEPTED**.
- `P7` #36: **BLOCKED**; wet deposition/Docker/S5 excluded.

## Ordered next changes (separate focused PRs)

1. **S4-R1**: source-bound test-only HEATFX/ELUSTR water-aware G22 branch with correct existing land formulas and original water skip. Real 2022 2SS Huoshan/Luogang + 1US Anqing, 82×85×9, 63 actual water cells, six chronological hours. Extract untouched original HEATFX **at same stage and source hour** in a scratch separate Fortran build and demand identical 45-field output as uninstrumented original. Check water QSW/QH, second SURFVAR TEMP2D and land ELUSTR individually. Do not relabel water as land.
2. **S4-R2**: independent actual native G24 end-of-DIAGNO first-plane U/V on all 63×6 original water cells. Compare with S4-Q pinned vendor 378 U/V pairs (plus WS10), within established stage-specific native/vendor tolerance and record exact errors and hashes. No copy of original final U/V into native code. Failure blocks downstream automatically.
3. **S4-R3**: only after R2 passes, add test-only original-selected G35/G36 WATER Z0/USTAR/EL/QH/ZI and state ownership to G26B COMP; compare every 6×45 field/hour and every actual grid cell with fresh, unchanged vendor CALMET at unchanged P6E tolerance, total exceedances 0. Recheck C1 143h real, C2 143h controlled and actual all-land Huoshan. Only a later explicit production decision could unlock the G26 default and then P7.

Never count software source-admission, original-only runs, standalone neutral WATER scalar, or first-plane input transport as `PASS_NEW_SITE_45FIELD_SCIENCE`.
