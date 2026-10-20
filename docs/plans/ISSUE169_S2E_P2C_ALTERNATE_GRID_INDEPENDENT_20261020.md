# Issue #169 S2-E — independent second-grid modern P2-C numerical audit

Date: 2026-10-20. Parent issue #169; source code baseline `main@4387c5899eab882adc7dec2c38d8e5fa19c9e6d2`.

## Problem being closed
P2-C **already computed** an alternate real-source Hefei UTM50N model grid: NX=90, NY=100, XREFKM=504.385, YREFKM=3524.769, DGRIDKM=0.100 km, 2022 GLC_FCS30D official 30 m raster SHA `ee5cefc27827d84f0aa42d0e014e211fcfef67f2bffc43185d17897d840d2e58`. In `.github/workflows/issue160-c4c5-hefei-20km-real-30m.yml` it had been honestly labelled `PRODUCED_UNVERIFIED`; only the historical 200×200 grid obtained an independent integer HITS/F6.3 comparison. The Python/NumPy independent 10×10 source point oracle hard-coded 200×200 and 20km, so no independent **new-grid numerical** conclusion was yet justified.

## Bounded change

Preserve the existing #160 independent raster/NumPy 10×10 sampling and point grid index mathematics, mapping policy, original-like R4 coordinates, source TIFF integrity, F6.3 formatting and Missing handling. Parameterize only **the independent reference's** declared origin, NX/NY, spacing, input coverage and row/header expected geometry. No native physical C++ kernel changes, no new reclassification, no P2-B area overlap, no GSHHG Full/coastline inference in this inland case.

- Frozen baseline: original 200×200 @100m with *no* CLI grid flags stays identical in method, source, output status string and 1,520,000×2 integer/F6.3 comparisons.
- Genuine alternate 90×100 at shifted origin: independently recompute **342,000 integer HITS** plus **342,000 F6.3 fractions** and 9,000 Missing flags, all with 0 mismatches; compare raw source SHA, native HITS/LU SHA and exact source accepted subpoint counts. A one-sided/wrong projected EPSG 32652 declaration must fail before any artifact is certified.
- Limit independent oracle to verified 2022 inland source EPSG:32650 and existing Wolsong original Full Coast BLN EPSG:32652. Limited grid budget 1..500 each, product <=250,000 cells, dx <=1km. Native producer retains its separate, existing resource/validity gate; **no size cap removed** (S5 deferred).
- Scientific statement if CI succeeds: `PASS_SCOPED_P2C_INDEPENDENT_SAME_SOURCE_90X100`, independent numerical reference with actual modern 30 m input **not independent original Fortran CTGPROC parity**. Original CTGPROC cannot use modern 2022 GLC product as its original historical GLCC GLAZAS input; don't mislabel native/reference 30 m comparisons as original Fortran physics.
- Existing old historical 200×200 authentic source, independent NumPy comparison and P3 format-only tests are retained in exactly the same workflow. This PR also keeps all original P1/P4/P5 regression gates, P3 original Wolsong scope and frozen policy SHA unchanged.

## Other S2-E exit items not closed here

P2-A **historical GLCC** dynamically produced a new Wolsong UTM52 20×20, but independent original CTGPROC with this same source+grid is still pending. That one can and should use the genuine Fortran CTGPROC GLAZAS (unlike the new 30m mapping). Other P4/P5 novel genuine source site/year/1-N station combinations are not proven merely because software supports them. The two configurations accepted under S2-E must remain source-by-source, physics-option-by-option scoped. #169 remains OPEN until all required original-science gaps are resolved or explicitly bounded, and #42 S3 combined five-product G19 also remains OPEN. Docker deferred.
