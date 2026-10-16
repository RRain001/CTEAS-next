# CTEAS: seven-program C++20 reconstruction

Status: IMPLEMENTATION_IN_PROGRESS / SCIENTIFIC_REFERENCE_BLOCKED (2026-10-10)
Baseline: RRain001/CTEAS main `66e30ffb1ff4638a97af8a060748ce30b7578350`.
Previous draft: PR #1, branch `codex/cpp-fullchain-reference-reconstruction` (ahead 2, behind 3 from main); documents reviewed and selectively replaced, no old branch merge or force-push.

## Mission and authoritative references
Maintain the existing Python GUI, scripts, Fortran executables and untouched `engine/vendor/src`. Implement in `native_cpp/`:
P1 TERREL 7.0.0 L141010; P2 CTGPROC 7.0.0 L150211; P3 MAKEGEO 3.2 L110401; P4 READ62 5.661 L110225; P5 SMERGE 5.7.0 L121203; P6 CALMET 6.5.0 L150223; P7 CALPUFF 7.2.1 L150618.
No standalone preliminary or final-numbered programs. **Every P stage is responsible for its own** reference capture, SHA/provenance inventory, numerical comparison, and full-case acceptance. A software unit test cannot count as a Fortran equivalence test. Independent observations are a distinct scientific gate.

## Frozen study intent, unresolved original-program controls
The first real case is `testcase.md`: latitude 31.939774444, longitude 117.141610855; 5 km by 5 km centered square, nominal 50 by 50 horizontal cells at 100 m; 9 layers and ZFACE 0,20,40,80,160,320,640,1200,2000,3000 m; 2022-01-01 00 through 2022-01-06 23 (144 hourly labels, NOT automatically 144 Fortran records); physical stack height 70.8 m, bore 1.6 m, 25 C outlet, 17.26 m/s; annual HTO 2.63e13 Bq, HT=0.
EPSG:32650 is verified **for the crop construction**. This is not proof that all seven original control files are configured to the same CRS, grid origin or timestamp policy. Do not freeze the actual Fortran grid geometry, projection or interval conventions until captured and checked. Do not infer hourly activity solely from annual emissions.

Input crop is `calpuff_terrain_and_landuse_data_crop/hefei_5km/`; terrain is uncompressed 90x77 WGS84 SRTM GeoTIFF + bbox, land use uses `GENERIC.LANDUSE 1.0` 57,600 point lines, 50 m sampling, 38-category header, `--lulc-type GEN`, `DNZGEN = ESR-S`. Never read its compact raster as the original fixed-size GLAZAS image, fill NoData, or equate 50 m point sampling with 100 m modeling cells. Prior crop/full data equivalence was demonstrated at 50 m only and must be rerun at 100 m.

## Implementation order, dependencies, ownership
Preferred workstreams: P1 / P2 / P4 / P5 independently with **one authority for common contracts**. Serial order if no safe isolated agents: P1 → P2 → P4 → P5 → P3 → P6 → P7.
P1 `geo/terrain`: DEM georeferencing/coverage, TERREL terrain allocation, missing-mask, original data version 2.0.
P2 `geo/landuse`: GEN header/points, datum-aware transformations, exact class fractions, original CTG output version 2.1.
P4 `met_input/read62`: raw upper-air station/UTC/profile/time/QA contract and READ62 output.
P5 `met_input/smerge`: raw surface station/UTC/QA/precip/merge and SMERGE output.
P3 requires P1+P2; P6 requires P3+P4+P5; P7 can validate against frozen original CALMET data before P6 is complete, but final integrated replacement depends on P6. End-to-end comparison is a **P7 exit gate**, not a separate numbered program.

## Contracts and scope
`native_cpp/` is a stand-alone CMake C++20 project (CTest). Public library boundaries: shared core; P1/P2 geo; P4/P5 meteorological input; then P3 geo merge; P6/P7 physics. `cteas_atmos/core` utility headers are copied intact from user-owned CTEAS-Atmos at SHA 449c17b733d0874151be5f6a14811eaa61da9bed (see `REUSE_PROVENANCE.md`), with no Atmos physics imported. Explicit mask distinct from numeric values; SI units and CRS/datum explicit in every field; time labels not implicitly UTC; array layout i-fastest. Never make a field valid merely because a value is finite. No silent interpolation, projection approximation or untrusted tolerance widening.

## Stage-local acceptance gates
For every P: (1) source/control tree hashes and option/routine inventory, (2) clean original Fortran execution with immutable reference inputs and outputs + run/compiler provenance, (3) C++ build + unit/synthetic tests, (4) parser/field/record/mask/units checks, (5) same-input stage-level and real-case Fortran-vs-C++ field comparisons with declared tolerances, exact finite/valid denominators and mismatch breakdown, (6) independent audit, (7) unsupported options and gaps.
Statuses: IMPLEMENTED_SCOPED, PASS_SOFTWARE, PASS_REFERENCE, PASS_REAL_CASE, BLOCKED, FAIL. Do not claim PASS_REFERENCE until a raw reference exists and is actually compared. Do not retune tolerances from C++ output.

## Runner and data safety
No workflow currently exists on main; the GitHub connector does not currently expose an authorized self-hosted runner inventory. Treat runner online/labels/data access as UNVERIFIED and do not claim server execution. Use local isolated CMake for small tests; require runner preflight, trusted dispatch workflow and isolated reference result directories before any original Fortran run. Never overwrite `engine/vendor/src`, `project/`, original data, or reference outputs. No main merge/force-push.
