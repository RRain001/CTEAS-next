# P6G G17B3: real source NEARS + AIRDEN, and the newly isolated IAVET=1 acceptance gap

Date: 2026-10-14. Branch: `codex/p6g-multistation-on-accepted-p6a-p6f-20261014` (PR #63 Draft, parent #53). #53's 163 accepted C++ physics/scheduler source files are unchanged.

## Verified literal CALMET 6.5.0 source

Original `engine/vendor/src/CALMET_v6.5.0_L150223/calmet.for`:

- **SETCOM L29762 / L29784–29811:** in the original `do 20 i=1,nx; do 20 j=1,ny; do 12 k=1,nssta` loop, the source computes cell center `(FLOAT(i)-0.5)*DGRID` and `(FLOAT(j)-0.5)*DGRID`, then `DIST2=(XSSTA(k)-XGDPT)**2+(YSSTA(k)-YGDPT)**2`. With initial `DMIN2=1.e37`, the strictly-less-than condition preserves the first station at exact distance ties. NEARS is **1-based station ordinal**, in met.inp SS order. No external NEARS array should be needed for live physics.
- **AIRDEN L2090–2098:** `RHO(i,j)=0.3484321*PRES(NEARS(i,j))/TEMP2D(i,j)`. `PRES` is the actual SURF.DAT station pressure (mb), `TEMP2D` is the grid's current source SURFVAR temperature (K). No invented default air density.
- **SURFVAR L12878–12881:** if `IAVET=1` and `IALL!=2`, CALMET calls `AVETMP(NX,NY,MNMDAV,HAFANG,DGRID,U,V,TEMP2D)`.
- **DIAGNO L5607–5611 and L5667–5671:** original code may call SURFVAR **twice**, once with preliminary WIND1 `UG/VG` before FRADJ, and again with **FRADJ-modified** wind just before HEATFX/AIRDEN/ELUSTR. Their temperature fields can differ when `IAVET=1`; assuming one common TEMP2D through both steps is incorrect for this case.
- **Real pinned Hefei met.inp:** `IRAD=1`, `TRADKM=500`, `NUMTS=5`, `IAVET=1`, `ITPROG=0`, `IRHPROG=0`, `NPSTA=0`, `MNMDAV=1`, `HAFANG=30`. Existing `surfvar_multistation.hpp` is explicitly a **source-selected IAVET=0** routine and cannot stand in for the full Hefei route.

## Implemented and gated on #63

- `p6g_g17b_setcom_airden.hpp`: REAL*4 source SETCOM and AIRDEN kernels, with source station-order/tie semantics and explicit pressure/TEMP2D validation.
- `p6g_g17b_observed_solar_heat.hpp`: source-derived NEARS and native AIRDEN gridded density join actual selected SURFVAR+SOLAR+HEATFX. An externally offered NEARS vector is **only a rejection/comparison oracle**; never a physical override.
- `p6g_g17_staged_terrain.hpp`: selected source AIRDEN stage can complete **only after** an explicit source-observed TEMP2D handoff matching the FRADJ input and model hour; still returns `Unknown,false` when no such source was supplied. Full HEATFX/ELUSTR/COMP remain incomplete. This phase remains fixture-scoped, not fully validated source P6E.
- `p6g_original_surfvar_controls.hpp`: strict parser for IRAD/TRADKM/NUMTS/IAVET/ITPROG/IRHPROG/NPSTA; requests for non-implemented `IAVET=1` branch fail closed. The source-scoped IAVET=0 case must match all three influence parameters and exact grid-scaled TRADKM.
- `p6g_g17b_observed_solar_heat_tests.cpp`: source density compared cell by cell; missing pressure, spoofed NEARS, wrong source temperature and unsupported IAVET=1 inputs are rejected. Explicit test-only switched IAVET=0 path is checked against source controls.

## Independent literal vendor numerical verification

- `p6g_g17b_setcom_airden_reference_main.cpp`: native C++ reference executable.
- `compare_original_g17b_setcom_airden.py`: extracts the **literal original Fortran statements** from `calmet.for`, compiles them under gfortran on hosted Ubuntu, and compares 8 independent station/grid scenarios including ties and reordered stations, **exact** NEARS ordinal and **bitwise REAL*4** RHO. The script does not invent independent Fortran physics formulas.
- [Actions #38517494040](https://github.com/RRain001/CTEAS/actions/runs/38517494040): **15/15 Debug and 15/15 Release PASS** including the new literal Fortran SETCOM/AIRDEN test, plus #53 163-file ownership guard PASS.
- Subsequent IAVET=1 fail-closed and staged source-AIRDEN integration revision: [Actions #38517975631](https://github.com/RRain001/CTEAS/actions/runs/38517975631) queued/running when documented. Must pass separately; no extrapolation from earlier green tests.

## Next integration/acceptance

1. Model authentic `IAVET=1` using already accepted P6E `avetmp.hpp`, `MNMDAV/HAFANG` from real met.inp and **two different original wind snapshots**: pre-FRADJ WIND1 and post-FRADJ before HEATFX, exactly where original SURFVAR is called. Do not force these two temperatures equal. Validate selected original Fortran AVETMP, then full two-pass source order.
2. After the final `TEMP2D`, compute authentic SETCOM NEARS → AIRDEN RHO and full day/stable ELUSTR with actual P6E source inputs, no fabricated `QH` or roughness.
3. Complete original CGAMMA and prior-hour mixing history, DIAGI/SMOOTH/DIVCEL/W/COMP/P6F, then strict independent multi-site **45-field** Fortran 1h→6h→143h→year validation.

**Acceptance:** G17B3 source NEARS and AIRDEN selected kernels PASS with literal Fortran source; full original Hefei IAVET=1 multi-station SURFVAR, AIRDEN coupled within production hourly loop, HEATFX/ELUSTR and full 45-field scientific parity remain NOT ACCEPTED. PR #63 Draft; do not enable G5 production GUI.
