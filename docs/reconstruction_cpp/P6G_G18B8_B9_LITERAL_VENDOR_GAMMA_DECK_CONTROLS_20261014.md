# P6G G18B8–G18B9 — source-correct multi-UP CGAMMA to 2D GAMMA with original ZUPT/IUPT

2026-10-14; PR #63 (Draft) on accepted #53. **This is a selected-stage, Fortran-vendor verified CGAMMA grid increment, not full multi-station CALMET scientific acceptance.** No #53 frozen original scientific sources or numerical tolerances were changed.

## Original CALMET DIAGNO source authority

The unmodified vendor file `engine/vendor/src/CALMET_v6.5.0_L150223/calmet.for` has two distinct `IUPT` branches when `NOOBS=0` and `IDIOPT2=0`:

- **IUPT>0:** `CGAMMA(...,IUPT,ZUPT,ZICONV(IIUPT,JJUPT),GAMUP(IUPT))`, then `GAMMA(I,J)=GAMUP(IUPT)` for every grid cell. No grid-distance weighting is applied.
- **IUPT<=0 (original pinned deck IUPT=-1):** compute `GAMUP(IU)` independently for each upper station, sampling its **previous committed** `ZICONV(IIUP(IU),JJUP(IU))` via PR #53's original `upper_reference_cell`, then evaluate the original `CMPD2` squared distance to each station at `(FLOAT(I)-0.5)*DGRID, (FLOAT(J)-0.5)*DGRID`. At each grid cell, in source station order, `DIS2SAF=AMAX1(DIS2(K),0.01)`, `TOP=TOP+GAMUP(K)/DIS2SAF`, `BOT=BOT+1.0/DIS2SAF`, `GAMMA(I,J)=TOP/BOT`.

The nested Fortran order is I outer, J inner, K innermost; the output array layout is J-major / I-fastest. In particular, the source lower-bound is **0.01 m² of squared distance**, not 0.01 m distance or an arbitrary CALPUFF interpolation weight. Original `CMPD2` and the two GAMMA fill branches are source-backed, not reconstructed by assuming NEARU is equivalent.

## New source implementation

- `p6g_g18b8_gamma_grid.hpp`: combines original G18B3 source-ordered upper station geometry/IUPT with G18B4–B7 each-station `CGammaState` candidate results and previous-ZICONV. It implements the two **original source accumulation branches in REAL*4 order**. Exact UTC hour, upper station identities, finite fields, original ordinal bounds and test-only scope are checked. The resulting source-stamped GAMMA grid is a candidate for PREPDI/DIAGNO; the full G14 `NativeHourStageResult` remains not completed.
- `p6g_g18b8_gamma_grid_reference_main.cpp` uses that actual production-slice header (not a duplicate). `compare_original_g18b8_gamma_grid.py` extracts and compiles the **literal vendor Fortran** IUPT>0 domain fill, IUPT<=0 1/R² GAMMA, and source `CMPD2` subroutine; assertions validate the vendor expressions before compiling. Full REAL*4 bits, not a relative tolerance, are compared across 14 configurations / **6432 grid cells**: 1/2/3/4/6 upper sites, coincident and equal-distance US, station exactly at the grid cell center (0.01 m² source floor), 5/10km and 2×2–50×50, both IUPT=-1 and positive IUPT=1/2/3/6. No physically fictitious Fortran oracle formula is written.
- Existing `.github/workflows/p6g-accepted-baseline-multistation.yml` and CMake now explicitly build the G18B8 native CLI and register `p6g_g18b8_literal_vendor_diagno_gamma_cmpd2_real4_parity` in both GitHub-hosted Ubuntu Debug/Release CTests. No self-hosted runners.
- Extended the existing selected G17/G18 CTest with actual independent 2US, 30-hour **cross-year input/history scenario**, G18B7 original previous-hour station reference-cell ZICONV, original IUPT=-1 inverse-distance gamma and IUPT=2 constant gamma, UTC/source station-order guards and refusal to treat a selected fixture as full production physics.

**G18B8 code gate:** [GitHub Actions #38551884001](https://github.com/RRain001/CTEAS/actions/runs/38551884001) on code SHA `aa389948f949aa06b57b6461be18310e5276a021`: Debug **19/19 PASS**, Release **19/19 PASS**, frozen PR #53 163-core-file guard PASS. The literal original Fortran GAMMA test passed in the Debug and Release CTest runs.

## G18B9 original gamma controls

The pinned case original `met.inp` includes `! IDIOPT2 = 0 !`, `! IUPT = -1 !`, `! ZUPT = 200. !`. Previously the selected G18B4/G18B7 CGAMMA bridge accepted test-provided `ZUPT=200.f`. The new `p6g_g18b9_original_gamma_controls.hpp` reads **all three** source controls from one actual original `met.inp`, validates a finite positive ZUPT and original IUPT index, and rejects diagnostic-file lapse mode `IDIOPT2 !=0` pending its own numerical certification. The selected source bridge now passes the exact parsed source ZUPT into the already frozen PR #53 `CGammaState` kernel and the matching IUPT into the source-verified G18B8 grid field, preserving a single source authority. Tests reject duplicate/missing/malformed ZUPT, invalid positive IUPT values, and unsupported IDIOPT2.

**G18B9 still requires `explicitly_test_only=true`** because G14 production has not bound these source controls and the complete DIAGNO/COMP/P6F hour execution. Source `ZUPT` authenticity at this selected stage does not itself establish a full multi-station 45-field result.

## Next blocking G18C / final acceptance

1. Feed G18B9's source-correct GAMMA field, through one authoritative PREPDI→DIAGNO wind stage using the existing PR #53 wind and stability kernels; do not add a duplicate execution controller. Preserve the hourly atomic snapshot/commit for upper AA/BB and previous-ZICONV histories.
2. Reuse accepted #53 AVEMIX, native TEMP3D, full P6E and dynamic P6F under G14 stage-order control, including all stage-specific source outputs; no partial candidates marked as `{NativeCpp,true}`.
3. Verify actual **multi-SS/US original Fortran 45-field** numerical equality and physical state on 1h, 6h, 143h, full year/cross-year, then only consider advancing PR #63 out of Draft. Keep the independent unchanged #53 accepted Hefei one-site 143-hour strict science regression green.

Documentation and selected Fortran parity only establish the bounded component gates described above. Check the **exact final HEAD** GitHub-hosted CI for the G18B9 new source-control tests separately.
