# Issue #40 — S4-R1b actual original-vs-native WATER shortwave on NOAA 82×85

Date: 2026-10-21. Base `main@cff4baa0c8e73783d38fa4769751a658e5c2d450` after #237 merged 17/17 Actions.

## New science (not an alternative synthetic case)

Reuse the entire S4-N **actual original six-hour** 2022-06-01 01:00–07:00 UTC two physically observed surface station source 583140 / 583210 plus Anqing 58424 upper-air, a genuinely generated 82×85×9 GEO containing 63 original water cells and 6907 land cells. Reproduce SHA-pinned SRTM, original GLCC P2A LU, native P1/P3 and independent original MAKEGEO, NOAA P4/5 actual files, original met.inp/SURF/UP and fresh full unmodified six-hour original Fortran. This is not a preexisting fixture or re-imported CALMET.DAT.

In a *separate scratch copy only* of original `calmet.for` blob `437f43bb7f0e51a1919e56664663e1a046986ed0`, log original DIAGNO at L5697, after ISFCMET=0 HEATFX, AIRDEN, ELUSTR. Record each true water i,j,h, original land category, SETCOM NEARS, RDSN opaque cloud, original SINALPC, **QSW** and original **QH** and post-FRADJ TEMP2D. Independently execute untouched full original CALMET on byte-identical inputs and require exact full **45-field × 6h MET.DAT byte equality** after trace instrumentation. Do not commit original source or upload original compiled binaries/DEM.

**Native C++ is genuinely input-owned, not an oracle replay**: `g19_load_source_clock_only` consumes the same independently generated actual met.inp, original GEO.DAT, RDSN SURF.DAT, and genuine archived UP.DAT; G38 validates original `NOWSTA=0, ITWPROG=0, ICOARE=10, IMIXH=1, IAVET=1`, no HFLUX override and true mixed-water GEO. For every actual source hour, frozen P6E `surface_solar_grid`, `sinalpc_grid`, SETCOM nearest-SS and `p6e::heatfx` compute **QSW** based on original observed cloud and source solar only. The HEATFX temperature carrier is actual measured station SURFVAR interpolation, which affects unused **land** QH but **not QSW**. The submitted C++ process never receives or reads original trace or original CALMET.DAT.

Test matches all 378 actual water cell-hours, authentic cell-hour and category identities, nearest original station/its cloud, independent solar sine and W/m² QSW with explicit tolerances (0.001 sine, 0.05 W/m² radiation), exactly zero original-vs-native selected prior-water QH, positive daytime shortwave, original full-output byte parity. All evidence must show numeric residual statistics and SHA chains; any failure is scientific **FAIL**, not pass by synthetic receipt.

## Scope exclusions are not implicit successes

- The original HEATFX QH for water is **preserved**, not recomputed: zero follows the selected previously traced original neutral branch. Not generic COARE/WATERP.
- Original first/second IAVET=1 temperature from native G20/G21 real post-FRADJ wind **not yet source-numerically validated**; this check does **not** validate land QH or either ELUSTR branch in actual NOAA case.
- Native G24 final U/V at 63×6 actual water cells: `NOT_RUN`. Prior S4-Q only supplied original vendor U/V as replayed arithmetic inputs; it is not native wind acceptance.
- Original-vs-native complete G14/G26 all 45 fields × six hours: `NOT_RUN`, no admission of P7.
- The original G19 physics-ready type, all-land G22, G26B water restrictions remain unchanged.

## Staging

1. S4-R1b independent water **QSW/QH-preserve** source-scoped actual original/native case (this PR).
2. S4-R1c source-owned real **G20→G21 two-pass actual post-FRADJ native wind and thermal** with exact original per-stage TEMP2D/QH/ELUSTR parity; must not silently inject original winds.
3. S4-R2 integrate verified WATER-capable G22/G23/G24 into scoped G14 and compare actual native final 378 wind pairs against original.
4. S4-R3 complete G26B/WATER mixed-case 6h×45 original/native field scientific parity before lifting default G26 and P7 #36 block.

Do not call this S4 final or G26 production acceptance from a subset QSW pass.
