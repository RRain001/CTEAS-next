# P6 CALMET 6.5.0 — first real source-backed physics and 2022 baseline audit

Date: 2026-10-11. Research study: 2022-01-01T00:00Z to 2022-01-06T23:00Z endpoint labels, 50×50 at 100 m in 5 km × 5 km stack-centered Hefei area, 9 layers, UTM 50N/WGS84.

**Status: P6B_ORIGINAL_CALMET_REFERENCE_PASS; P6C_TERSET_ORIGINAL_FORTRAN_PARITY_PASS; P6D_FRADJ_ORIGINAL_FORTRAN_PARITY_PASS; P6_FULL_DIAGNOSTIC_WIND_NOT_IMPLEMENTED; P6_CALPUFF_READY=FALSE.**

## Source and upstream locking

- Original `engine/vendor/src/CALMET_v6.5.0_L150223/calmet.for`, Git blob `437f43bb7f0e51a1919e56664663e1a046986ed0`; original unmodified compiler flags `gfortran -O0 -std=legacy -fno-automatic -fno-align-commons -fallow-argument-mismatch -ffixed-line-length-none` (reference workflow).
- P3 candidate input via captured original `GEO.DAT 2.1`, P3 scripts pinned `5b1013baea10c0b3c3946e62ab77428dff05455e` (P3 independent C++ field parity previously verified).
- P4 via pinned `dc4e3f042e5668358fc43f2f2ae98d7a554ecfd3` (original byte parity of full 2022 `UP.DAT` from current P4 scope); P4 P6B integration exports `up_58424.dat`, verified 2022 IGRA data. Effective station is virtual/proxy relocated to stack, NOT measured on site.
- P5 via pinned `dd473cede495bb04b312dc31d6bdef8afabe26c2` (new real 2022 ISD + Lite wind-cleaning script, original SMERGE called to publish `SURF.DAT`, **not a fully Fortran-equivalent C++ P5 SURF writer**). The latest P5 data process still needs independent meteorological QA and precipitation review.
- Historical 2023 case control source pinned `2908293f061af93e754bc9fe1f00d857d1d6a0d8` **only** as `case.yaml` configuration scaffold; no historical 2023 meteorological file, `MET.DAT` or `PUFF.CON` is used as golden data.
- All source cross-branch reads are `git fetch` with exact commit identifiers into isolated GitHub-hosted reference CI; **no branch merge, no original vendor source edits and no write to P3/P4/P5 worktrees**. The P6 branch base remains the frozen common foundation `60b7b1d`.

## P6B: reference execution and CALMET.DAT field decoder — PASS

[GitHub Actions P6B source-pinned original CALMET 2022 reference and field decoder](https://github.com/RRain001/CTEAS/actions/runs/38106767619).

- Original unchanged TERREL/CTGPROC/MAKEGEO → new P4 `UP.DAT` and P5 `SURF.DAT` with original SMERGE → unchanged original CALMET 6.5.0 successfully ran to termination on the new 2022 Hefei 100 m case.
- Original `MET.DAT`: **64,762,556 bytes**, SHA256 `968b2dd24f0eb4ad428709b52a154d9022e8c7e37a4be3fb9498e3d7e756d04e`.
- Original sequential unformatted record framing is **little-endian 4-byte length prefix + trailing length**; exactly **7,562** total records: 1 dataset declaration (96 bytes), 1 count (4 bytes), **1,114** Fortran 132-byte comment/control records, 1 run-control header (176 bytes), ZFACE and station metadata, five gridded static 2D records plus 6,435 hourly records.
- Independent decoder `native_cpp/modules/p6_calmet/reference/decode_calmet_hourly.py` derives expected record labels from original `OUTH D`/ `OUTHR` and `WRTR2D`/`WRTI2D`; **time first 2022-01-01T00:00Z, last 2022-01-06T23:00Z, 143 contiguous one-hour time intervals, 45 2D fields each = 6,435 hourly 2D fields**, no field sequence/record length/time gaps. **144 endpoint labels are not 144 output intervals.** Fortran source `OUTH D` actual routine name `OUTHD`.
- Output includes 9 levels of each `U-LEV` and `V-LEV`, 9 `WFACE` values at top layer interfaces, 9 `T-LEV` fields, plus `IPGT, USTAR, ZI, EL, WSTAR, TEMPK, RHO, QSW, IRH`; under `NPSTA=0`, **no RMM or IPCODE precipitation output**. `IRTYPE=1`, `LCALGRD=T`; this is the original required full meteorological content for CALPUFF, not merely wind-only.
- Reference run and decoding **do not** prove modern C++ wind/temperature equivalence, meteorological representativeness or complete rainfall data.

## P6C source-backed TERSET numerical comparison — PASS

Original `TERSET` is CALMET's local terrain-maximum/minimum height and distance calculation, source `calmet.for` **L31805–31902**, controlled by `TERRAD` from Group 5. The actual old operational selection was `TERRAD=15 km`; the new case studies a **5 km wide** box. Thus the 15 km radius encompasses the *entire grid*, with out-of-domain terrain unavailable. Numerical fidelity and scientific representativeness must not be confused.

Modern C++ `native_cpp/modules/p6_calmet/include/cteas/p6/terrain_envelope.hpp`; `cteas_p6_terset`; independent audit `compare_original_terset.py` compiles the literal original TERSET source extracted without modification and uses untouched `params.met` / `grid.met` common blocks. Independent tests: actual P3 terrain, flat terrain, isolated extremum, local radius 0.12 km and 15 km, spatially heterogeneous terrain. [TERSET original numerical parity CI](https://github.com/RRain001/CTEAS/actions/runs/38106630752): **six × (2,500 cells × four real quantities) = 60,000 fields**, no differences above frozen per-field tolerances. On actual terrain HMAX/HMIN difference zero, max distance error **5.0×10⁻⁷ m** (text-precision effect). Fortran's zero-initialized distance arrays and strict-extremum tie behavior are explicitly reproduced.

## P6D source-backed FRADJ Froude blocking numerical comparison — PASS

Original `FRADJ`, CALMET source **L7289–7455**, enabled by Group 5 `IFRADJ=1`; physics uses original `CRITFN=1`, `TAU=-0.01`, single-precision constants `RPD=0.017453` and `DPR=57.296`, terrain gradients, `TERSET` HMAX, lapse rate, surface temperature, height of all model layers, local wind speed and direction. This is an **obstacle blocking adjustment**; it is not the complete initial-guess wind, slope flow or convergence minimization.

C++ `native_cpp/modules/p6_calmet/include/cteas/p6/froude_adjust.hpp`; `cteas_p6_fradj`. Independent `compare_original_fradj.py` compiles *literal source-extracted* original TERSET + FRADJ, uses exact common-block geometry, and compares 50×50×9 U/V winds for seven synthetic and real-DEM settings: flat calm, realistic hill/ridge under stable weak flow, hill under unstable flow, high-speed flow, representative vs spatial surface temperature, and actual P3 terrain. [Fortran parity CI](https://github.com/RRain001/CTEAS/actions/runs/38107015476): **7 × 45,000 = 315,000 wind components PASS**; stable hill case showed **5,657 original wind components actually adjusted**, largest difference U **1.172966×10⁻⁷ m/s**, V **1.147894×10⁻⁷ m/s** in that test. The actual real DEM test may leave wind unchanged for the *analytic forced wind and strong vertical clearance*; its presence does **not** substitute for original CALMET hourly wind extraction.

## Precipitation and unsupported-mode distinction

Original new 2022 P6 reference runs with `NPSTA=0`. This is valid for **diagnostic winds + other micrometeorological outputs**, but **does not qualify rainfall inputs for downstream HTO wet deposition**. The `ForcingInventory` code was corrected to differentiate `can_attempt_full_reference_run()` from `can_claim_wet_deposition_forcing()`: an explicit `NPSTA=0` may pass the original runnable path while wet forcing remains blocked. No fabricated precipitation, no silent replacement of missing rain by zero.

## Remaining blockers and next physical work

- **P6D incomplete despite FRADJ unit PASS:** implement original `SLOPE` (Group 5 `ISLOPE=1`), observation-based `WIND1` and `SIMILT` vertical extrapolation (`IEXTRP=-4`), `DIAGI`/`DIAGNO`, terrain-following `TOP OF2`/ `TOPOF2` if selected, smoothing, and `MINIM/DIVCEL` divergence. Each gets a captured original Fortran subroutine/unit golden data before whole-hour parity.
- **P6E incomplete:** meteorological `ELUSTR`, `HEATFX`, `MIXHT`, `TEMP3D`, `SURFVAR`, `SOLAR` and related stability/mixing physics, with day/night/calm/stable/convective reference checks.
- **P6F incomplete:** source-equivalent `CALMET.DAT` writer and original P7 CALPUFF reader acceptance. Current decoder **only reads original** and does not write a modern met file.
- **P6G incomplete:** modern complete 143-interval source-equal u/v/w + meteorology per field, then independent scientific observation validation. Don't label P6 complete or production ready from two isolated physical units.
- Practical met QA: P5 ISD/Lite station coverage and hourly wind repair remains distinguishable from quality of CALMET itself; any station outside domain is a proxy not physical local measurements.
- Domain concern: original `TERRAD=15 km`, `RMAX1=100 km`, `RMAX2=200 km`, `R1=50 km`, `R2=100 km` substantially exceed the 5 km simulation box. Numerical matching of original CALMET settings on a small box does not establish the physical appropriateness of that domain.

**Release state: P6B_REFERENCE_CAPTURE=PASS; P6C_TERSET=PASS_REFERENCE_ISOLATED; P6D_FRADJ=PASS_REFERENCE_ISOLATED; P6_FULL_SOLVER=NOT_READY; P6_METEO_FIELD_PARITY=NOT_YET_TESTED; P6_WET_FORCING=NOT_YET_VALIDATED; P6_MAIN_MERGE=NO.**
