# P6C real 2022 COMP AA/BB buffers and GEO–SURF–UP joint observation audit

Date: 2026-10-11. Repository: RRain001/CTEAS; branch `codex/cteas-p6-calmet-hefei-100m`; draft PR #8. **This file records the earlier COMP-focused milestone. Latest independent RDSN/CGAMMA acceptance now advances the supported 2022 observation stage to P6C=PASS_SCOPED_HEFEI_2022_OBSERVATIONS**; P6D integrated remains NOT PASS, P6E–G NOT STARTED. See [P6C_RDSN_CGAMMA_2022_AUDIT.md](P6C_RDSN_CGAMMA_2022_AUDIT.md) and [complete CI #38113874913](https://github.com/RRain001/CTEAS/actions/runs/38113874913).

## Original source controls: reviewed independently

Pinned unmodified `engine/vendor/src/CALMET_v6.5.0_L150223/calmet.for` SHA256 `430381b4fb87f15127e20b13cc3e99be8a0e0fccf1d5821110af7f980558d134`. Independent original [read-only COMP/PREPDI inspection CI](https://github.com/RRain001/CTEAS/actions/runs/38112765903) shows:

- COMP L4150–4151 rejects nonzero sounding separation strictly below `NSECDT` (3600 s selected).
- Original Fortran `data maxsep/14/` at L3654; COMP L4236 rejects gaps greater than **14 h**. **MAXSEP is not a CALMET.INP control in this version**, and an initial 24 h candidate default was corrected to 14 h.
- Instantaneous upper soundings with `ISNAP != 0` and end time exactly at newest sounding trigger AA/BB renewal. COMP L4293 selects freshest BB (`JUSTA=+1`); L4366 selects freshest AA (`JUSTA=-1`). `UP.DAT v2.1` uses original `RDUPN` in both cases.
- PREPDI L13976–13985 has two distinct branches `JORDER +/-1`; comparing only chronological wind values with `JORDER=+1` is insufficient proof of correct physical-buffer ordering. Fortran source comparator now drives both physical AA/BB branches from real 6201 soundings.

## Real 2022 selected data: PASS only for source-backed independent joint values

[2022 original-source selected joint CI PASS](https://github.com/RRain001/CTEAS/actions/runs/38112477819). Model 50×50 at 100 m, 9 layers; 2022-01-01T00:00 through 2022-01-06T23:00 UTC: 144 timestamp labels, **143 valid one-hour intervals**. One virtual SURF station and one original P4 upper station 58424 (13 soundings/785 measured heights). Actual P4 `UP.DAT` SHA256 `058e8845d34aaaa5a6bedc60f512f5d24857a4534f4107d57bb97f5c3a8d9c99`.

- `GEO.DAT` 50×50/8 fields, original native Fortran read equivalence independently established (20,000 raw values); selected joint trace checks center grid elevation and roughness each hour.
- `SURF.DAT` 143 hours, 8 selected raw observation fields (original native Fortran formatted read), explicit validity masks; joint state verifies station/time/cloud/wind/temp and **143/143 missing IPCODE rain codes**.
- `UP.DAT` vertically integrated `VERTAV`, original PREPDI source U/V and original FACET+INTP face temperature; joint trace: 143×9=1,287 hourly-layer rows, 2,574 winds, 5,148 sampled AA/BB face temperatures. Max absolute error: U/V `5.0000004e-10 m/s`, face temperature `5.0e-10 K`, surface temperature `1.04e-7 K`, terrain/roughness 0. No mismatches.
- Explicit comparison windows: first 1 hour 18 U/V components; first 6 hours 108; full 143 hours 2,574. These source-backed scalar checks **PASS**.
- Candidate physical AA/BB switches 11 times in 143 hours, including exact 00/12 UTC boundaries. **This was a C++/chronological candidate conclusion, not original live COMP runtime evidence.**

## Both original PREPDI physical-slot JORDER branches — PASS

[Full latest P6B/P6C CI #38112918986](https://github.com/RRain001/CTEAS/actions/runs/38112918986) compiled the literal original PREPDI branch expressions against actual 13 sounding Fortran VERTAV outputs. The test explicitly feeds **71 hours JORDER=+1**, **72 hours JORDER=-1** with **11 physical AA/BB switchovers** rather than reusing only the `+1` branch. All **2,574 U/V hourly-layer components PASS**, max absolute U and V errors **5.0000004e-9 m/s**, zero mismatches, fixed `3e-4 m/s` tolerance. The same run reproduced the **143 original COMP live states** and source-backed triple-input joint comparison successfully.

## Further original runtime check introduced, separate from prior PASS

`reference/original_comp_runtime_trace.py` SHA-pins the original CALMET source; makes **only a temporary Fortran copy**; adds write-only `P6C_COMP_TRACE` at original COMP accepted-return path and recompiles under identical compiler settings. The integration workflow runs untouched original baseline, reruns write-only traced original and requires identical `MET.DAT` SHA256; it compares 143 original `nowtze,nsecze,ntzaa,ntzbb,justa,jusdt,jaasec,jbbsec` states to C++ joint buffer, including physical AA/BB time ordering, JORDER, interval gates. This is a required *independent result*; a successful source inspection or software test cannot substitute for execution.

**Original COMP runtime gate: PASS.** [Full 2022 source trace / joint input CI #38112842109](https://github.com/RRain001/CTEAS/actions/runs/38112842109) successfully ran original instrumented CALMET and checked: **143/143 original hourly COMP states**, **286 physical AA/BB timestamps**, **429 clock/seconds checks**, **11 original JUSTA/JORDER flips = 11 C++ transitions**, **0 mismatches**. Unmodified and write-only-instrumented `MET.DAT` SHA256 values were required identical by CI and passed. Traced original FORTRAN source SHA was pinned and untouched. Original COMP selected-case status is **PASS_ORIGINAL_COMP_RUNTIME_AA_BB**; whole P6C stage remains PARTIAL because complete original `RDSN` and `CGAMMA` execution state, full observation/mask arrays and P6D+ physics remain outside this independent trace.

## Precipitation and phase gates

Original `NPSTA=0`, `IPCODE=9999` for 143/143 hours. No validated wet removal/precipitation input exists: `P6_WET_FORCING_VALIDATED=FALSE`, `P7_WET_DEPOSITION_VALIDATED=FALSE`. Do not derive precipitation from absence codes or use dry reference CALMET as proof of HTO wet deposition readiness.

Official: `P6A=PASS`, `P6B=PASS`, `P6C=PARTIAL`, `P6D_INTEGRATED=HOLD`, `P6E–G=HOLD`, `P6_CALPUFF_READY=FALSE`. No vendor original files, P4/P5 branches or `main` were modified.
