# Issue #119 — P2-B EXACT_AREA_V1 Wolsong freeze gate (2026-10-19)

## Frozen numerical acceptance already established
Manual [Actions #39236968133](https://github.com/RRain001/CTEAS-next/actions/runs/39236968133), main@487c2e68: verified GSHHG v2.3.7 Full L1, real GLC_FCS30D 2022 b23, 200×200@100m, EPSG:32652 and 40,000-cell LU.DAT. The source GLC210 201,504,180 m² is conserved into USGS52 1,512,532.7412982835 m² + USGS55 199,991,647.2587017 m²; raw fraction sum error <1e-9. 222 cells have BOTH printed f52 and f55 positive.

Status: PASS_SCOPED_REAL_COASTAL_ENGINEERING, not proof that historic GSHHG shoreline is the observed 2022 physical shoreline. The production area method, source TIFF and mapping are frozen; audit code is read-only.

## Remaining exact-area acceptance/freeze gates
1. Independent lightweight PR synthetic tests must pass (no real shoreline science on PR).
2. After merging, only the **user manually dispatches** [Wolsong Issue119 workflow](https://github.com/RRain001/CTEAS-next/actions/workflows/issue119-wolsong-p2b-real-coast.yml) with validation_scope = full_p2b. Do not auto-dispatch science tests.
3. The workflow obtains the SHA-verified official GSHHG ZIP, extracts matching High h L1 sidecars, and independently rechecks **each of the 222 mixed 52/55 cells** by intersecting the actual GLC210 source pixels with Full and High land polygons. Fail closed on source hash, grid/row order, or Full-vs-produced LU.DAT fractions differing by >0.000501 (the LU.DAT three-decimal printing tolerance).
4. Evidence: mixed_52_55_cells.csv with 222 UTM cells and Full/High independent 52/55 areas; mixed_52_55_audit.json with full/high SHA, total land area on the entire 20×20 km domain, and the *within-222-cells-only* 52/55 Full/High sensitivity. Do not label the within-222 comparison as whole-domain sensitivity.
5. 2017-era GSHHG/2022 GLC shoreline age and mapping inconsistency remain an explicit **NOT_INDEPENDENTLY_VERIFIED_2022_SHORELINE** limitation. A 52-labelled landward water sliver may reflect an outdated vector coastline, not a confirmed freshwater lake. Independently observed 2022 coastline reference and predefined tolerance are required before claiming real-world shoreline positional truth.
6. When quantitative results are reviewed, freeze as EXACT_AREA_V1_FROZEN_PASS_SCOPED only with documented conditions and limitations. If Full/High changes are material, extend the quantitative audit before freezing. Do not infer accuracy from conservation.

## Next module (deferred)
[Issue #123](https://github.com/RRain001/CTEAS-next/issues/123): ORIGINAL_SAMPLING faithful CTGPROC native Fortran comparison and coast options. Reuse current P2-A native implementation rather than creating a parallel duplicate. P3 Wolsong original-vs-C++ parity remains #46. Nothing in this PR modifies P2-A, the area kernel, P1, P3, P6 or P7.
