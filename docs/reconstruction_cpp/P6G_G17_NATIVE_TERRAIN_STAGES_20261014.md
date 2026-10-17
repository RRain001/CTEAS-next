# P6G G17: native stage-ordered terrain chain, explicit acceptance boundary

Audit date: 2026-10-14. Active work: PR #63, based only on accepted PR #53 (`8d6642272d0abb77153880591e150f93e14d4479`), no old source merges, no edits to the 163 accepted C++ P6 physics or scheduler files.

## Goal and source position

Preserve the original CALMET 6.5.0 DIAGNO execution order from PR #53:

```text
PREPDI previous ZICONV       [NOT IMPLEMENTED in P6G full scheduler]
WIND1                        [G16 real C++ selected kernel]
FRADJ                        [G17 new stage callback, PR #53 native froude_adjust]
HEATFX -> AIRDEN -> ELUSTR  [NOT IMPLEMENTED; must supply real P6E fields]
SLOPE                        [G17 new stage callback, PR #53 native source SLOPE]
first WINDBC                 [G17 new stage callback, snapshot PRE-INTER2 U/V]
STHEOR/ELUSTR2/MIXHTST       [NOT IMPLEMENTED; DIAGI source physics required]
INTER2                       [G16 real C++ selected kernel, two distinct station profiles]
post-INTER2 WINDBC           [NOT IMPLEMENTED]
SMOOTH -> DIVCEL -> W        [NOT IMPLEMENTED]
COMP MIXHT/AVEMIX/WSTARR/TEMP3D, P6F [NOT IMPLEMENTED]
```

Source markers: `engine/vendor/src/CALMET_v6.5.0_L150223/calmet.for`, `FRADJ` call at ~5643, `SLOPE` ~5722, SLOPE-add ~5738, first `WINDBC` boundary snapshot ~5748, `INTER2` ~6055–6059. Existing `p6g_terrain_hour.hpp` G11 combined helper is retained for independent comparison, **not** used as a single callback at an incorrect stage.

New adapter: `native_cpp/modules/p6_calmet/include/cteas/p6/p6g_g17_staged_terrain.hpp`.

- `DiagnoWind1`: delegates G16, using a source-effective `met.inp` wind configuration.
- `DiagnoFradj`: calls immutable `p6::froude_adjust` with exact original `ZFACE`, terrain envelope, explicit lapse rate / temperature and `CRITFN`; rejects wrong hour and stale `GEO` / `TERSET`.
- `DiagnoHeatfx`, `DiagnoAirden`, `DiagnoElustr`: explicitly return `{Unknown,false}`. The stage adapter does **not** claim P6E physical output.
- `DiagnoSlope`: only after FRADJ and explicit source-typed QH; calls immutable `p6::compute_original_slope_scoped` and adds original slope winds to FRADJ-adjusted U/V. Rejects wrong-hour, missing, unverified and inconsistent SURFVAR temperature/QH sources.
- `DiagnoWindbcFirstGuess`: snapshots UB/VB directly from the corrected wind **before INTER2**, with exact 9 × 2 × NY and 9 × 2 × NX layouts. Passes it to G16's separate state authority.
- `DiagnoInter2`: runs G16 original-selected C++ two-component interpolation only after the corrected wind/boundary handoff. It retains source pre-INTER2 UB/VB without recomputing them after observation blending.
- All unsupported downstream physical stages return `{Unknown,false}`, and therefore a full G14 hourly simulation cannot falsely complete.

**G17 fixture is not an accepted native P6E state.** Test fixture `TerrainHourProvenance::SyntheticReferenceFixture` is intentional; real `HEATFX`, `SUN`, `CGAMMA`, `AIRDEN/ELUSTR` and thermal history must be introduced separately and source-validated before production.

## Independent checks

New strict CTest: `p6g_g17_fradj_slope_first_windbc_native_stage_source_parity`:

1. 12×12×9, 10 km, 2 surface + 2 upper stations with source-bounded wind state and explicit controlled QH/temperature.
2. FRADJ stage U/V equals direct immutable `froude_adjust` U/V (without tolerances).
3. FRADJ→SLOPE separate stage output equals the previously tested G11 combined source subchain at all 1296 U and 1296 V nodes (no tolerance widening).
4. First WINDBC produces the exact 216-element U / 216-element V lateral boundary snapshots from the pre-INTER2 corrected field.
5. WIND1/FRADJ/SLOPE/WINDBC/INTER2 cannot be reordered, silently duplicated, or run with missing QH, wrong hour, wrong original GEO / TERSET or inconsistent source TEMP2D.
6. PREPDI, thermal P6E, SMOOTH/DIVCEL/W and COMP must report incomplete; original preceding-hour thermal state must not be mutated by selected stages.

[Actions #38514388051](https://github.com/RRain001/CTEAS/actions/runs/38514388051): Debug and Release each **13/13 CTest PASS** (G6–G17) and accepted P6 `163`-file frozen-source ownership **PASS**. [Original Fortran G9/G10/G11 #38514388152](https://github.com/RRain001/CTEAS/actions/runs/38514388152): Debug/Release source-selected numerical comparisons PASS.

Latest explicit extra guards: commits `577da956`, `c183f23d`; [#38514694657](https://github.com/RRain001/CTEAS/actions/runs/38514694657) started afterward and requires its own PASS before claiming those new checks are accepted.

## Next real physics acceptance work

- G17B: connect **real per-hour multi-station SURFVAR** to FRADJ and **native solar/SUN, HEATFX, AIRDEN, ELUSTR** to SLOPE. Reuse the frozen P6E kernels from #53, not synthetic rays/coefficients, not old G5–G13 physics merges. Preserve source order and REAL*4 rounding.
- G17C: integrate **STHEOR/ELUSTR2/MIXHTST**, real DIAGI capped SIMILT, first/second WINDBC, SMOOTH/DIVCEL/W with original source boundary state. The `p6g_selected_hour_bridge.hpp` remains validation-only until this closed.
- G18: join real previous-hour ZICONV/CGAMMA to native COMP MIXHT/AVEMIX/WSTARR/TEMP3D, then independent P6F. Compare original Fortran **multi-site** U/V/W, TEMP, QH and the complete 45-field record for 1h, 6h, 143h, and year. Strict original Fortran parity is a separate gate; G17A selected-kernel PASS alone proves neither multi-site full solver nor production acceptability.

Merge policy: #63 stays Draft; #53 remains immutable. Use only GitHub-hosted Ubuntu.
