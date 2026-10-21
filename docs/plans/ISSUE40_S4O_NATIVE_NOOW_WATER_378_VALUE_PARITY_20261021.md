# Issue #40 S4-O — native reference-only selected neutral WATER against all 378 genuine original records

Date 2026-10-21. Depends on merged [#232](https://github.com/RRain001/CTEAS-next/pull/232), exactly unchanged original CALMET 6.5.0 independent 2022 NOAA 2SS+1US 82×85 source with 63 genuine water cells × 6 chronological hours and source-instrumented 378 reference rows. Original reference-only instrumentation produced 45-field MET.DAT **byte-identical** to untouched uninstrumented original, and all 378 original water QH, USTAR, EL, ZI, WSTAR, Z0, WT, WS10 and PGT were independently checked. Do not repeat original Fortran subroutine physics inside selected G14/G26 code.

## Explicit native test-only scope

Add `p6g_g35_original_noow_water_neutral.hpp` as a separate reference candidate **not referenced by G19/G14/G26 production actors**. It computes only the original `WATER` neutral branch for `NOWSTA=0,ITWPROG=0,ICOARE=10,IMIXH=1` on real original water land-use categories **50–55** and only with an explicit test-only authority. This is the original source's no-overwater-observations fallback, not a generic all-site water/COARE or prognostic SST model.

Measured original source **WS10** is passed as input (not yet independently generated native after-FRADJ model wind). Native computes original Hosker water roughness `z0=max(2e-6*WS10**2.5,2e-6)`, neutral water friction `ustar=max(0.4*WS10/log(10/z0),1e-9)`, neutral `EL=9.9e9`, `WT=0`, water buoyancy `QH=WT*1195.2=0`, `WSTAR=0`, and PGT class D. The metric `QH` here is the original **water buoyancy flux**, not the heat-flux output of the land HEATFX routine. Floating-point operations use C++ float to reflect selected original REAL*4 behavior; numeric comparisons use explicit bounded original-derived absolute/relative tolerance and report maximum differences.

Missing from candidate BY DESIGN: mixed-layer height `ZI`, `ZICONV`, prior hour `ZICOLD` and `DPTT`, full source wind/FRADJ, CALMET multi-stage COMP state and any 45-field MET output. Both candidate result readiness flags are permanently false; a strict negative refuses running without `explicit_reference_only`, refuses `NOWSTA!=0`, `ITWPROG!=0`, unvalidated `ICOARE`/`IMIXH`, non-water land-use, invalid WS10. The actual 378 numeric original rows must pass 63 identical cell coordinates × six independent hours, zero missing/duplicate identities and the C++ **seven scalar fields** QH/WT/USTAR/Z0/EL/WSTAR/PGT.

## Real CI scientific hierarchy

The S4-O workflow rebuilds actual 2022 original NOAA 2SS+1US same case from immutable original inputs, reproduces S4-N **both** untouched and exactly instrumented original CALMET full six hours, requires byte-identical original MET output and actual original water 378-row physical state, *then* builds a dedicated C++ reference binary and compares each recorded original scalar. Existing accepted land HEATFX, ELUSTR and G14/G26 code is untouched.

Strict pass is `S4O_ORIGINAL_TRUE_63_WATER_CELLS_SIX_HOURS_NATIVE_NEUTRAL_QH_USTAR_Z0_EL_WSTAR_PGT_PASS_SCOPED`; this admits only the separate test candidate, **not** the complete WATER or model G14 physics. Actual post-FRADJ native WS10, full original WATER mixing-height / previous ZICOLD state and all 270 native/original field-hour group comparisons are NOT RUN. Preserve water category, sparse real NOAA station observations and all production refusals.

Next S4-P should independently source-check and implement water-specific original `ZI/ZICONV/ZICOLD/ILAPSE/IMIXH=1` hourly state and eventually integrate into a new explicit certified complete hour authorizer; only then prove all 6×45 original CALMET field groups with zero exceedance. Keep #40 and #36 OPEN, production NOT_ACCEPTED, no wet deposition/Docker/S5.
