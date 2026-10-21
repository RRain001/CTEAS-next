# Issue #40 / S4-L — original CALMET water HEATFX source law versus unresolved QH lifetime

Date 2026-10-21. Follows merged PR #228 independent original Fortran CALMET 6 h real 82×85 water-bearing 2SS + 1US site, and merged PR #229 source/clock structural separation. The strong G19/default G14/G26 selected physical path correctly remains all-land only.

## Precisely what the original code already proves

The unchanged CALMET 6.5.0 source `calmet.for` pinned to Git blob `437f43bb7f0e51a1919e56664663e1a046986ed0` implements original `HEATFX` on all cells, including water. **Original shortwave QSW is computed at water points**, while the original `HEATFX` branch **does not overwrite QH in water points**. Hence before even invoking `HEATFX` on a water-bearing grid, the water QH vector must be an **original state with a proven initialization/ownership**, rather than the all-land fixture `initial_water_qh_wm2.assign(nx*ny,0.f)`. Choosing zero just because the previous all-land code never used this array would silently invent real-site science.

The accepted `p6e::heatfx` kernel already takes a separately supplied prior QH vector and leaves water entries untouched; do NOT duplicate or change this accepted formula.

## New independent test and source custody

The S4-L action independently checks out untouched original Fortran CALMET 6.5.0 and the previously developed original source-extraction comparator from the frozen `RRain001/CTEAS@dfad99a78ed84d655e21411c9d25eb0d2583bf13`, SHA checks the vendor Fortran and dynamically extracts the unmodified literal `HEATFX` subroutine. A *fresh* gfortran compiled reference runs **24 reference cases** over a 5×4 grid containing actual original water codes and different preloaded water QH sentinel values, land, cloud and night combinations; an independent existing native C++ HEATFX target runs the identical source-format input. All **960 QSW/QH scalar values** must pass the frozen absolute/relative tolerance with **0 exceedances**, and water-QH sentinels must be preserved exactly (already enforced by the pinned original comparator). No C++ constants are mistaken for original source without source validation.

A second source-audit script records exact original calmet.for SHA, HEATFX and ELUSTR call-site/source line references plus candidate water/QH references; uploads **only hashes/line indices**, not source text or redistribution of third-party code.

## Explicit remaining science blocker

This **does not** determine who originally initializes QH on water and how QH is propagated across HEATFX→ELUSTR, MIXHT/COMP or hour boundaries in the authentic 2022 water-bearing observed 2SS+1US site. Real QH state is not interchangeable with the synthetic sentinel in a stand-alone routine fixture. This test must be reported as `PASS_SCOPED` **only for the literal independent original HEATFX routine**. The original full CALMET six-hour 45-field benchmark in PR #228 is a separate scientific reference, not a claim of C++ field parity.

Next S4-M: instrument/reference the pinned unchanged original 82×85 CALMET water grid at hour 1–6 *before HEATFX* and *after HEATFX*, *after ELUSTR*, and *after COMP* (reference-only instrumentation isolated and fully hashed; never modify the original source in a shipping C++ path) to identify exact water QH provenance and downstream use. Verify source call order, station gaps, QH, USTAR/EL, ZI, and CALMET.DAT 45 fields using same authentic NOAA GEO/UP/SURF/met.inp, then independently implement a separately gated water state adapter reusing `p6e::heatfx`. Only after zero-exceedance 270-group original-vs-native 45-field science is G26 trial candidate permitted; production and P7 remain denied.
