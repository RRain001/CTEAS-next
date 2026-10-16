# P6C Phase 1–2 audit: Original GEO.DAT and SURF.DAT readers

Date: 2026-10-11. Current status: **P6C_GEO_READ_SELECTED_PATH_FORTRAN_FORMAT_PARITY_PASS; P6C_SURF_READ_SELECTED_PATH_NATIVE_FORTRAN_FORMAT_PARITY_PASS; P6C_UPPER_AIR_AND_OBSERVATION_TIME_INTERPOLATION_NOT_IMPLEMENTED; P6C_COMPLETE=FALSE**.

## Fixed scientific scope and source

- CTEAS P6 reconstructs original CALMET 6.5.0 (L150223), limited to user's new Hefei 50×50@100m UTM 50N WGS84 / 9-layer, 2022-01-01 00:00–Jan 06 23:00 UTC case. Original user-supplied 2023 smoke5d case is historical control reference, never the new meteorology golden.
- P6 workflow pinned original P3 `5b1013b`, P4 `dc4e3f0`, P5 `dd473ce`. Original `engine/vendor/src`, upstream branches and `main` are untouched.
- The original CALMET input environment has **143 one-hour output intervals from 144 endpoint labels**. Full `P6B` baseline produces original `MET.DAT` SHA256 `968b2dd24f0eb4ad428709b52a154d9022e8c7e37a4be3fb9498e3d7e756d04e`. File format-only equality and isolated input read equality do **not** qualify final C++ solver physics.

## 1. GEO.DAT v2.1 eight fields: PASS independently against native Fortran

CALMET source references: `READGE` `calmet.for` L27790–28392, `FILLGEO` L6983–7104; original selected path `IOPT(1)=1` (new 14 land-use categories), `HTFAC=1`, `IOPT(2...7)=2` (all six supplied gridded fields). The original `READGE` reads **rows j=NY down to 1**, and Fortran/C++ both store **i fastest, j south-to-north**. Check explicit coordinate origin, WGS-84 UTM50N, 0.1km 50×50 and land-use category membership instead of relying solely on dimensions (2023 case had same 50×50 but a 50km domain).

Modern code: `native_cpp/modules/p6_calmet/include/cteas/p6/read_geo.hpp`, `cteas_p6_read_geo`, `p6_read_geo_tests.cpp`. Its gridded input order is exactly `ILANDU, ELEV, Z0, ALBEDO, BOWEN, HCG, QF, XLAI`. Reject legacy default/category-table, second LU source, weather-projection mismatch, extra records and invalid finite numerics.

Reference [P6C native Fortran eight-field data-read CI — PASS](https://github.com/RRain001/CTEAS/actions/runs/38109436038): regenerates new real **2022** `GEO.DAT` using **unchanged original TERREL+CTGPROC+MAKEGEO** from pinned P3 sources, then independently compiles a **native Fortran selected-format reader following original READGE/FILLGEO list-directed source statements**, and compares 2,500×8 = **20,000 numbers** to the C++20 reader. No comparison over preset absolute tolerance `1e-5`; maximum observed printed difference: terrain `6.1000094e-11 m`, albedo and soil heat parameter `3.9539982e-11`, others zero. Real 100m study grid SW origin from P3 manifest `x0=510.8846439571007 km`, `y0=3531.2689269678035 km`; GEO file stores coordinates to 0.001km. Both programs read the same original GEO.DAT text. This independently written Fortran reader is **not** a claim that all of original `READGE`'s QA scratch, land-use fallback or alternate projection paths have been ported.

## 2. SURF.DAT v2.1 one virtual station: raw formatted read PASS

CALMET selected path `RDHD` L14862–14927, `RDSN` L23437–23660; `IFORMS=2` **formatted** `SURF.DAT 2.1`, `PMAP=NONE`, `UTC+0000`, `NSSTA=1`, `ISPACK=0`; original P5 produces `SURF.DAT` through **unchanged Fortran SMERGE** from newly cleaned current 2022 ISD/Lite data. `RDSN` accepts explicit hourly beginning and ending times with seconds, eight surface fields `WS, WD, ICEIL, ICC, TEMPK, IRH, PRES, IPCODE`; Fortran `9999` signals missing.

Modern code: `native_cpp/modules/p6_calmet/include/cteas/p6/read_surface.hpp`, CLI `cteas_p6_read_surface`, test `p6_read_surface_tests.cpp`; reads exactly 143 original one-hour record intervals, checks station ID and UTC continuity, exposes original raw values and separate **validity masks**:
- Exact calm pair `WS=0, WD=0` is an observed, valid wind and **not missing**; newer P5 may already choose to replace it according to its documented independent wind-policy before SMERGE.
- `WS=9999` or `WD=9999` means unavailable wind and cannot be assumed calm.
- `IPCODE=9999` means missing precipitation *code*, never observed zero precipitation. In any event original P6 reference `NPSTA=0` omits gridded rainfall and **does not prove HTO wet-deposition readiness**.
- Fortran raw output comparator faithfully preserves 143×8 original printed meteorological scalar values and 143 station/time keys; original stable UTM case does not apply LCC/PS wind rotation.

The source-independent comparator `compare_fortran_surface.py` compiles a native Fortran `SURF.DAT` input-format reader following original `RDHD/RDSN` formatted-branch list-directed read order; its QA is limited to the **raw 2022 SMERGE output**, not original RDSN's full state machine, source-data quality, interpolation or weather modeling. It runs as a new mandatory P6B workflow gate **after** original SMERGE and **before** original CALMET. Real 2022 CI [P6B integration + P6C SURF native Fortran selected-path check](https://github.com/RRain001/CTEAS/actions/runs/38109730617) **PASS end-to-end**, including original SMERGE, P6C SURF original Fortran field parity, and unchanged original CALMET reference run. P6C SURF 143 intervals: **1,144 raw meteorological scalar values and 429 station/time fields**, all PASS at predeclared raw-real tolerance `2e-4`, no errors. Max observed error WS `1.9000000e-7 m/s`, WD `0`, TEMPK `0`, PRES `3.99999999e-6 mb` (float output text). 2022 `SURF.DAT` SHA256 **`082202c9d4e87dca35869b5ab4dccde115f243ba129341e2301f123cb2672cff`**. Missing-value tallies from P6C explicit masks: **wind missing 0/143, cloud missing 0/143, precipitation code missing 143/143**. These indicate data *in this generated SURF run*, not meteorological truth: raw precipitation codes contain **no usable rain data** and C++ P6 must not equate them to zero rain. The unchanged original CALMET run after this additional gate again reproduced `MET.DAT` 64,762,556 bytes and the 143×45 record/time schema.

## 3. P6C UP.DAT now has separate PASS; remaining stage blockers

**Superseding 2026-10-11 update:** The formerly missing selected UP.DAT reader and transform are now implemented and independently verified. See [P6C_UPDAT_RDUPN_2022_AUDIT.md](P6C_UPDAT_RDUPN_2022_AUDIT.md) and [2022 original native Fortran parity PASS](https://github.com/RRain001/CTEAS/actions/runs/38110557735). Original `UP.DAT 2.1` uses **`RDHDU→RDUPN`**, not the legacy `RDUP`; 13 actual 2022 in-case upper soundings, 785 levels, 6,280 numerical fields pass. Original P4 standalone full-year byte-parity is a separate upstream proof; the 13 case soundings, not all annual 730, were compared during this P6C case integration.

1. **C-HEIGHT-TIME still pending:** original `COMP` AA/BB 00/12 UTC sounding bracket selection, time interpolation, missing-data and terrain-following model-layer vertical interpolation. Current P6C proves original **file format and per-sounding conversion only**.
2. **C-INTEGRATION still pending:** actual 2022 `GEO.DAT+SURF.DAT+UP.DAT` original per-hour true station values/masks/vertical interpolated fields against C++, for 1h→6h→143 one-hour intervals. Original reference outputs cannot be replaced with inferred interpolation results.
3. **Original full reader state pending:** supported selected paths of `READGE/RDSN/RDUPN` passed raw-format comparison, but optional branches and full reader-to-`COMP` time state were not yet independently audited.
4. **P6D–G remain HOLD:** `FRADJ` isolated PASS does not imply P6D complete; 143/143 original surface rain codes are absent, not zero rain.

Status: `P6A_PASS`; `P6B_ORIGINAL_REFERENCE_PASS`; `P6C_GEO_PASS`; `P6C_SURF_RAW_FORTRAN_FORMAT_PASS`; `P6C_UP_RDUPN_FORMAT_AND_UV_PASS`; `P6C_COMP_TIME_INTERPOLATION_PENDING`; `P6C_COMPLETE_FALSE`; `P6D_FRADJ_ISOLATED_PASS_BUT_FULL_D_HOLD`; `P6_CALPUFF_READY_FALSE`.
