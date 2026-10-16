# P6G G18B6–G18B7 — literal-vendor NEARU and previous-hour CGAMMA ZICONV

Date: 2026-10-14. PR #63 remains Draft, stacked on frozen #53. This is a bounded multi-US source-stage verification, **not** a claim of full native CALMET multi-station scientific equivalence.

## G18B6 original SETCOM NEARU

Original source authority: `engine/vendor/src/CALMET_v6.5.0_L150223/calmet.for`, routine `SETCOM`, loop `DO 120 I=1,NX / J=1,NY`, inner loop `DO 112 K=1,NUSTA`:

- `XGDPT=(FLOAT(I)-0.5)*DGRID`, `YGDPT=(FLOAT(J)-0.5)*DGRID`;
- `DIST2=(XUSTA(K)-XGDPT)**2+(YUSTA(K)-YGDPT)**2`;
- strict `DIST2.LT.DMIN2`, initialized `RMAX=1.E37`; tie retains first source-ordered station;
- `NEARU(I,J)=KSV` one-based, with a fatal input-error branch when no valid site.

The accepted G18B3 candidate maps grid cells using equivalent REAL*4 ordered geometry, but previous tests compared only C++ fixture expectations. G18B6 now adds `p6g_g18b6_setcom_nearu_reference_main.cpp` and `compare_original_g18b6_setcom_nearu.py`, whose Fortran oracle extracts **the literal source loop** from the unmodified vendor file, asserts its sentinel expressions have not changed, compiles the extracted Fortran with `gfortran -O0` and compares every one-based ordinal with the actual G18B3 C++ production adapter. Independent 10 fixture cases cover 1/2/3/4/6 upper stations, coincident and equidistant source sites, 2x2–50x50 grid sizes, and 5/10km cells. This is an exact integer comparison with no tolerance or nearest-station interpolation.

The GitHub-hosted Ubuntu `P6G multistation on accepted single-station baseline` workflow now builds the added C++ reference binary explicitly before running `ctest -R '^p6g_'`. The initial CI failure was purely a missing explicit binary build target; it was fixed in the existing workflow without changing physics. **[Code gate #38543870652](https://github.com/RRain001/CTEAS/actions/runs/38543870652) PASS: Debug 18/18, Release 18/18, PR #53 frozen 163-file guard PASS**, including the new literal-vendor NEARU CTest.

This validates `SETCOM NEARU` for the selected 1–6 upper-station REAL*4 geometry, **not** `IUPT` and complete multi-UP COMP/TEMP3D; IUPT parsing remains source-selected as previously recorded. G18B3 still fails closed on unmarked fixture controls, intentionally keeping the unverified whole-model acceptance flag off.

## G18B7 previous-ZICONV origin for CGAMMA

Original source authority: `calmet.for` CGAMMA caller:
- `IUPT>0`: `CGAMMA(..., IUPT, ZUPT, ZICONV(IIUPT,JJUPT), GAMUP(IUPT))`.
- `IUPT<=0`: for each `IU`, `CGAMMA(..., IU, ZUPT, ZICONV(IIUP(IU),JJUP(IU)), GAMUP(IU))`.

**These are source upper-reference cells**, independent of nearest-US `NEARU(I,J)`. PR #53 already source-audited `p6::upper_reference_cell`: Fortran INTEGER-truncated `X/DGRID+1.5` / `Y/DGRID+1.5`, clamped to [1,NX/NY]. G18B7 now reads `frame.previous.ziconv_m` strictly at each upper station's mapped reference cell; it does not use the current hour's tentative `frame.next` or a manually provided per-US convective state vector. The established G18B4 frozen `p6::CGammaState` numerical kernel and transactional candidate/commit authority are unchanged. Invalid source IDs, grid size, nonfinite state and swapped station order fail closed.

Existing 30-hour asynchronous 2US cross-year **input/state** fixture now verifies two distinct upper reference cells, a single-station previous ZICONV convective branch, independent retained-convective history and direct equality to the old immutable PR #53 per-US CGAMMA kernels. This is **not** 30 hours of native CALMET P6D/E/F physical parity.

## Remaining work

1. Bind the physical G18B4 `ZUPT` and prior-ZICONV to real G14 hourly production inputs/commit paths with explicit source `CGAMMA` control and station time trace; selected fixture no longer invents ZICONV, but does still supply `ZUPT` test-only.
2. Implement/verify original per-cell `GAMMA(I,J)` inverse-distance-squared synthesis from independent per-US `GAMUP` in the authentic original source `IUPT<=0` branch, and complete gridded PREPDI/DIAGNO CGAMMA consumption with a separate Fortran oracle.
3. Complete G18C AVEMIX/TEMP3D/P6F source-order callbacks and atomic state transfer within a **single G14 production scheduler**, not an independent reimplementation. Full multi-site 45-field original CALMET 1h, 6h, 143h and full-year strict tests remain blocking. PR #63 stays Draft; PR #53 frozen source is unchanged.

CI results must always be reported against their **exact code SHA**; this document cannot confer PASS to a newer uncompleted run.
