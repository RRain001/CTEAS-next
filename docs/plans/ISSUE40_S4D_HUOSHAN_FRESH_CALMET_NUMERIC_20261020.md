# S4-D fresh unchanged original CALMET 6.5.0 on true Huoshan NOAA source — independent 45-field science

Refs #40, #36. This builds upon S4-C [PR #207](https://github.com/RRain001/CTEAS-next/pull/207), merged `main@5a6502e`: the **same C1/C2 accepted unified G14 executable** has genuinely executed C1/C2 and a true S3-produced Huoshan 100×100×9, 1SS+1US, 01–07Z 2022 June 1 first-hour + continuous six hours from independently generated NOAA input. S4-C only certified `PRODUCED_UNVERIFIED`; file creation alone is no original science.

This PR is a **strict, independent original Fortran** comparison, reusing the existing original S3 matrix `jun_6h` and **not creating any replacement site-specific C++ physical solver**. Following already successful P1 SRTM90, historical GLCC P2-A, unchanged original P3, real NOAA READ62/SMERGE source, SHA joined G19 and native 6h, it independently:

1. Reads original `original_cteas` checkout pinned `dfad99a78ed84d655e21411c9d25eb0d2583bf13`, verifies unmodified `calmet.for` git blob `437f43bb7f0e51a1919e56664663e1a046986ed0`, compiles a NEW vendor executable with gfortran and original include dependencies.
2. In an isolated temp directory copies **only** the same S3 published genuine `met.inp`, `GEO.DAT`, `SURF.DAT`, `UP.DAT`; copies preserve all source SHA and physical bytes. Edits file-path tokens in a staged *copy* of the met deck (`GEODAT/SRFDAT/UPDAT/METLST/METDAT`), **and verifies** original numerical READCF, grid, station count, control and UTC fields unchanged.
3. Executes untouched original CALMET independently for the same six genuine hours. A forbidden or missing original input, original process failure, incomplete binary output, or Fortran stop is a hard failure with source and compiler/listing evidence.
4. The separate frozen P6E reader compares ORIGINAL 45 fields × six hours at 100×100 original cells with the already produced *new shared C++* G14 six-hour CALMET.DAT, existing frozen tolerances. Requires **all 270 field-hour groups and zero exceeding field-cell values**. No backfill from original MET, no reduced tolerances.
5. Preserves original binary/source hash, true S3 observation-source SHA, native SHA and actual failure diagnosis. No secret or large raw source files attached.

**Current science status: NOT_RUN until the actual independent workflow result is checked.** No merging it as proof of successful original parity on a failure; report first differing field/time/cell and repair only validated original control or physics. Source context: virtual station effective positions reflect already accepted NOAA fallback and original READCF, *not a fabricated extra station*. No 24-hour run because the real S3 source lacks legal complete 00/12 upper brackets in that window. P7, asymmetric station combinations, other grids/years and S5 memory limit remain separate.

## Actual scientific acceptance evidence — 2026-10-20

[Actions #39446678843](https://github.com/RRain001/CTEAS-next/actions/runs/39446678843), exact PR head `08a17ff8ec162de09dfbb3c450a9dc604e0fdfed`, all 4 S3 jobs completed **SUCCESS**. New `jun_6h` steps independently compiled/reran unchanged CALMET 6.5.0 and completed a separate frozen-tolerance comparison against the same newly shared C1/C2 native G14 executable on genuinely regenerated Huoshan 2022 1SS/1US, 100×100×9, 01–07 UTC 2022-06-01.

- Actual vendor execution: `S4D_HUOSHAN_6H_FRESH_UNMODIFIED_VENDOR_CALMET=PRODUCED_UNVERIFIED`, compile and six-hour execution success, original listing and source SHA artifacts preserved, no native output used as vendor input.
- Actual strict numerical conclusion: `S4D_TRUE_HUOSHAN_6H_270_FIELDS_FRESH_ORIGINAL_NUMERIC=PASS_SCOPED`. Independent `p6e_calmet_dat21 compare` JSON: `intervals=6`, `fields_per_hour=45`, `status=PASS`, `total_exceedances=0`.
- The independent job log contains all **45 fields**, each **denominator 60,000** (6×100×100), `missing_reference=0` and `missing_candidate=0`: exactly **2,700,000 nonmissing field-cell checks**, zero exceeding frozen tolerances. Largest of the 45 per-field absolute differences is **0.00006866455078125**, on `EL`; this is *not* a changed scientific tolerance or a claim of byte-for-byte identical files.
- The same original pipeline generated S3 P1–P5 and actual source SHA, original grid geometry/stations and controls; `jun_6h_alt` is **source-only** with different UTC window, not claimed P6 45-field science.
- The result is real **new-site** P6 original-vs-C++ selected branch science beyond Hefei C1/C2, but **not** all options, 1SS2US/2SS1US asymmetrical site cases, larger actual domains, P7 newsite or full production G26 admission. `#40` still OPEN, `#36` still OPEN.

Verdict: `S4D_TRUE_HUOSHAN_1SS1US_100X100_20220601_6H_CALMET45=PASS_SCOPED`. Reviewer must validate SHA and actual job result prior to merge.
