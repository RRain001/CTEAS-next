# P6G G17B: source-computed solar and multistation observed temperature through HEATFX and G17 terrain

Date: 2026-10-14; source authority: #53 `8d6642272d0abb77153880591e150f93e14d4479`, under Draft PR #63. The 163 accepted physical source files and scheduler remain byte-identical.

## Scope added

New `native_cpp/modules/p6_calmet/include/cteas/p6/p6g_g17b_observed_solar_heat.hpp` and `tests/p6g_g17b_observed_solar_heat_tests.cpp`.

Inputs: one strict G6 original GEO.DAT dynamic grid, G7 original SURF.DAT multi-station hourly observed temperature/RH/cloud (same station ordering as original `met.inp`), source-selected calendar hour, plus **explicit experimental ancillaries** (see below). C++ calls the existing source-validated #53 P6E algorithms:

1. `surfvar_multistation`: actually interpolate the supplied observed multi-station temperature and humidity into `TEMP2D`. Do not invent missing observations or reorder stations.
2. `surface_solar_grid`: source CALMET COORDLIB UTM/WGS-84 inverse at each model-grid cell, retaining original intermediate REAL*4 grid-center evaluation.
3. `sinalpc_grid`: actual original SOLAR from the beginning of the UTC model hour, selecting the original hourly mid-interval `SINALP(NHRB+2)` value. The G7 SURF parser is UTC+0000 only; zone conversion/sub-hour time zones not inferred.
4. `heatfx`: source native MCLOUD=1 branch, driven by real computed `TEMP2D` and `SINALPC`, actual station RDSN cloud, and **explicit ancillary parameters**. Outputs `QSW`, `QH`; water-cell `QH` remains the supplied initial value, preserving original HEATFX semantics.
5. G17B2: take exact G17B TEMP2D into G17 native FRADJ, the matching computed QH and TEMP2D into source SLOPE, snapshot first WINDBC before INTER2, and run G16 native INTER2. Assert the complete corrected U/V field is element-for-element identical to the pre-existing G11 combined FRADJ+SLOPE source kernel run on the same input fields.

## Not yet original CALMET fully validated / no production claim

The following **are still explicitly supplied by fixture**, not constructed and independently verified through a complete original met.inp + P6E control chain: `NEARS` (nearest 1-based site), heat coefficient inputs `HA*/HB*/HC*`, `IRAD/NUMTS/TRAD` selection, initial water QH, `CGAMMA` lapse rate, source `CRITFN`/domain reference temperature, and original P6E AIRDEN/ELUSTR state.

As a hard safety boundary, the fixture requires `explicitly_test_only=true`. The returned G17 terrain and slope fields carry `SyntheticReferenceFixture` provenance **even though the solar and actual observed TEMP2D are now physically computed**. There is no possibility of accidental acceptance as a fully native CALMET P6E result. `G17SelectedTerrainFixturePhysics` still returns `{Unknown,false}` for unimplemented HEATFX/AIRDEN/ELUSTR callbacks: the full accepted-order G14 scheduler thus rejects an attempted full multi-site hour.

The case thus closes the old **synthetic sunshine field** gap and proves real native numerical forwarding from observed SURFVAR → SOLAR → HEATFX → FRADJ/SLOPE → first WINDBC → INTER2 **in a fixture-controlled selected chain**. It does **not** close CGAMMA or full P6E, and does not meet original full multi-station 45-field hourly numerical equivalence.

## Validation

- Pinned original single-station #53 science: `163` pre-existing production source files unchanged by #63, frozen Hefei 143-hour 45-field strict gate must remain PASS.
- G17B CTest: source-valid UTM north WGS-84 12×12 10km 2SS grid; compares P6E SURFVAR station fields, source SOLAR UTC Jan 1 beginning-hour and original source HEATFX QSW/QH **exactly**, tests real daytime/nighttime solar sensitivity, station temperature and cloud influence, water QH preservation, unsupported hemisphere/identity/missing cloud/ancillary rejection.
- G17B2 CTest: pinned `met.inp` wind controls; computed TEMP2D/QH enters source FRADJ and SLOPE, then source first WINDBC and INTER2. G17 staged field is checked against native G11 combined original source algorithm **without tolerance changes**, with prior thermal state unchanged.
- Initial G17B1 [Actions #38515874684](https://github.com/RRain001/CTEAS/actions/runs/38515874684) Debug/Release 14 CTests and accepted baseline protection PASS after correcting P6E header include path.
- Latest G17B2 [Actions #38516104609](https://github.com/RRain001/CTEAS/actions/runs/38516104609): CI underway when this report was authored; do not claim new staged integration PASS before this run completes.
- Original selected Fortran [Actions #38516104746](https://github.com/RRain001/CTEAS/actions/runs/38516104746) and latest Hefei 143h strict scientific [Actions #38516104631](https://github.com/RRain001/CTEAS/actions/runs/38516104631) are independent required gates.

## Mandatory next phases

1. G17B3: source-validate `NEARS`, `IRAD/NUMTS/TRAD`, complete radiation/heat parameters and real initial water QH against original CALMET in multiple real station layouts; avoid simply claiming an arbitrary explicit fixture is authentic.
2. G17C: source-native grid AIRDEN + DAY/STABLE ELUSTR paths, actual CGAMMA from immutable previous-hour ZICONV, mixing-height-dependent DIAGI SIMILT, then second WINDBC, SMOOTH/DIVCEL/W in original sequence.
3. G18: unite native PREPDI/COMP state, P6F records, dynamic output; independently require original Fortran multisite full 45-field 1h→6h→143h→year parity before marking #63 ready or enabling G5 GUI.

PR #63 remains Draft, original #53 stays unchanged, only GitHub-hosted Ubuntu used.
