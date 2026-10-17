# P2 CTGPROC GEN path: real and heterogeneous 100 m reference audit

Scope: **only** original CTGPROC 7.0.0 Level 150211 `GENERIC.LANDUSE` (LL, DEG, ESR-S), 38 USGS classes, 50 x 50 UTM zone 50N WGS84 grid at 100 m, with `LFINAL=T`, no coastline, snow or continuation. User-owned reference Fortran in `engine/vendor/src` and original 57,600-point cropped file were read-only; no P4/P5 shared interface or code changes.

Source control basis: `RRain001/CTEAS@60b7b1d93866fff772926b6ac32dc0af7235552b`. Real source input SHA-256: `bd937d99fb13b49ac6185c080359bef050afe76fc63945ac53b7d676547d43dc`. Original real-case LU.DAT SHA-256 `75720a211126ffc1d5dbd931cb1dfcc4b4c54f0f4b19b0bceeb26487ba75c0ea`.

## Reference comparison gates

| Criterion | Real Hefei original GEN | Deterministic heterogeneous GEN |
|---|---|---|
| Original source-point count | 57,600 | 57,600 |
| Input coordinate strings | Unchanged source | Identical to real source |
| Input category IDs | Original GLCC-derived | Deterministic code remap, 56,455 changed records |
| Original/C++ in-grid input points | 10,011 / 10,011 | 10,011 / 10,011 |
| Processed grid cells | 2,500 | 2,500 |
| Cells with 2+ categories | 0 | 2,500 |
| Distinct nonzero categories | 1 (21) | 38 |
| Independently compared float fractions | 95,000 | 95,000 |
| Maximum abs fraction error | 0.0 | 0.00033333333300000767 |
| MAE | 0.0 | 0.000002357894734484265 |
| RMSE | 0.0 | 0.000028035065733984077 |
| Declared `LU.DAT` text precision tolerance | 0.0005 (3 decimal places) | 0.0005 |
| Exact accepted-point count match | PASS | PASS |
| Printed fraction comparison gate | PASS | PASS |

Reference Actions: [real-case and mixed GEN pass](https://github.com/RRain001/CTEAS/actions/runs/38044378424), all scoped C++ unit tests PASS; original CTGPROC binary ran successfully twice, once on unchanged real inputs and once on synthetic copy. Heterogeneous original `LU.DAT` SHA-256: `cdf222ebc6c8359b1235d3d2558a07f36f975aa4750d9accf4c18daeef9c9d25`; generated synthetic input SHA-256 `6e9c0b7eeb185ae4445928ab510cd43697c49201821722c49f62b25015b50070`. Deterministic generation code: `native_cpp/reference/prepare_p2_heterogeneous.py`. Independently audited comparison: `native_cpp/reference/compare_p2_gen.py`. Evidence archives are Actions artifacts (temporary, seven-day retention) and must be preserved in a long-term reference store if needed.

## Preserved failure and source-based correction

An initial homogeneous benchmark passed but was insufficient: all fractions were category 21. Initial heterogeneous comparison [FAILED](https://github.com/RRain001/CTEAS/actions/runs/38044152113) even though both accepted 10,011 points: 34 cells had category-share discrepancies; max absolute error 0.25. The C++ implementation had previously converted PROJ UTM metres into kilometres by exact `x / 1000.0`, causing several near-boundary points to fall into neighbouring cells. The original coordinate library `COORDLIB/COORDS` declares `XMULTO=0.001` as implicit `REAL*4`; in double precision that value is `0.0010000000474974513`. Its conversion is equivalent to `float32(projected_m * double(float32(0.001)))`, then `LUGRID` uses original REAL*4 index/truncation logic.

The new source path reproduces this multiplier and retains original REAL*4 latitude/longitude input. All 34 mismatching cells then agree within the predeclared `F8.3` output tolerance; **no reference artifact, grid definition, or tolerance was modified**. A fixed test input near the eastern cell 38 boundary is also in `native_cpp/tests/p2_gen_fraction_tests.cpp` to prevent regression. Note: the benchmark does not directly prove the complete proprietary projection library's behavior for arbitrary source datums.

## Gate boundaries

Status: **PASS_REFERENCE_SCOPED_P2_GEN_ESR_S_HEFEI_100M_AND_HETEROGENEOUS**, **NOT P2_FULL_PROGRAM_PASS**. Remaining: alternate landuse database formats, variable datums, source coordinate systems, coast/snow/continuation, multiple-file state aggregation, full CTGPROC input-output option coverage and format details, cross-platform repeatability. Submitted for independent review as a **Hefei-scoped minimal reconstruction**, per user scope decision 2026-10-10 (see consolidated P1/P2 feature matrix in P3 PR #5). Full CTGPROC historical-option coverage is not an acceptance requirement. Main-branch merge remains a separate action. Independent code review and final downstream modern P1/P2→P3 compatibility remain open. No original/independent observations outside the original Fortran comparison have yet been evaluated.
