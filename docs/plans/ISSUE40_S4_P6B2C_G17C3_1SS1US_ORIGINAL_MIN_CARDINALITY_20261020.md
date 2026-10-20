# Issue #40 / P6-B2C-0 — Restore CALMET's original 1SS/1US G17C3 source cardinality

Date: 2026-10-20. Scope: **minimum-station guard + software regression only**. No G23 activation on genuine Huoshan, no copied or generated PREPDI upper INTER2 observations and no 45-field P6 accepted claim.

## Literal original source

Pinned original repository `RRain001/CTEAS@dfad99a78ed84d655e21411c9d25eb0d2583bf13`, unmodified `engine/vendor/src/CALMET_v6.5.0_L150223/calmet.for` (whole original SHA256 `430381b4fb87f15127e20b13cc3e99be8a0e0fccf1d5821110af7f980558d134`):

- **READCF lines 26358–26373** rejects `NSSTA=0` when `NOOBS<2`; rejects `NUSTA=0` when `NOOBS=0`. It **does not** require two of either station for the selected `NOOBS=0` observation pathway. Original `DIAGI` L5099, L5125, L5137, L5163 loop `1..NUSTA` and `1..NSSTA` actual counts. Original `STHEOR` L31111–31155 processes the actual individual source station ordinal.
- Therefore C++ G17C3 `deck.surface.size()<2||deck.upper.size()<2` was an **additional adapter test-fixture restriction**, not an original CALMET physical control. Replace with `surface.empty()||upper.empty()`, leaving input grid, valid actual NOAA source, time bracket, source identity/UTM position, observed cloud/wind/pressure, selected 9-layer wind physics and previous-hour-memory validation unchanged.
- **Important independent issue**: original `PREPDI` L13990–14010 and L14091–14108 set `I1=2` if `IEXTRP<=0` (this project's actual `IEXTRP=-4`). For upper observations, PREPDI **does not fill upper layer 1** using the neutral WIND1 profile. Original code separately produces the extrapolated SURF profile in `STHEOR/DIAGI`; no inference from native 1SS G20 WIND1 fields to upper INTER2. In the existing G20 real 1SS1US test-only adapter, all upper INTER2 observations are deliberately missing `EDIT=999` and `present=false`. **Do not bypass this until original PREPDI complete upper k1..9 validity is explicitly checked against real NOAA UP.DAT, original time brackets and C++ selected VERTAV/PREPDI.**

## Regression / acceptance contracts

- The added isolated G17C3 test uses **one surface and one upper actual-cardinality fixture** from the already tested two-station construction. It exercises original selected C++ `SURFVAR` twice, `HEATFX`, `ELUSTR2`, `MIXHTST`, and source `DIAGI` all at the exact same hour, producing a finite one-surface-station profile without modifying the authoritative prior-hour `ZI/ZICONV/DPTT`.
- Negative tests must reject zero SS, zero US, invented upper ordinal, a future-only upper sounding, and missing source surface wind. The `merge_g17c3_surface_diagi` test must preserve neutral WIND1 input bytes and leave every **unverified upper** INTER2 wind `999 / present=false` (no synthetic meteorological second station).
- Retain all prior 2SS/2US current PR #53 selected-physics regression. A green CTest **only** proves first G17C3 single-cardinality software/physics-kernel compatibility on a deterministic fixture, **not** independent original Fortran STHEOR/MIXHTST/DIAGI numerical acceptance for the authentic NOAA Huoshan first hour.

## Scientific next gates

1. P6-B2C-1: independently extract and compile original selected PREPDI `IEXTRP=-4` *upper* `I1=2` and EDIT/EDITL validity, with actual NOAA IGRA `UP.DAT`, matching original `VERTAV`, 00/12 bracket and nine levels; do not invent k=1.
2. P6-B2C-2: genuine Huoshan `100×100×9` 1SS1US source-generated HEATFX/ELUSTR2/MIXHTST/DIAGI profile against independently compiled original CALMET station-level stages, including zero previous-hour `ZI/DPTT` first-hour source initialization and correct SS→US choice.
3. P6-B2C-3: only then activate explicitly opt-in genuine G23 INTER2 selected source hour, compare native vs original Fortran WIND1→SLOPE→STHEOR/DIAGI→INTER2 180k values and source-controlled `BIAS/WO`. Preserve original frozen Hefei 143h path separately.
4. P6-B3/C still requires real native original-format `MET.DAT` **45 fields/hour** and independent **full original CALMET** 1h/6h scientific runs.

**Verdict pending CI:** `G17C3_1SS1US_MIN_STATION_ADMISSION=PASS_SOFTWARE_SCOPED` only if the exact PR SHA CTest succeeds. `G23_REAL_NOAA_INTER2=NOT_RUN`, `PREPDI_1US_ORIGINAL_PARITY=NOT_RUN`, `P6_NEW_SITE_SCIENCE=NOT_ACCEPTED`. No P7, wet deposition, scaling or Docker.
