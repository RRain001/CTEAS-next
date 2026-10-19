# Issue #123 — ORIGINAL_SAMPLING faithful CTGPROC v7.0.0 phase D0/D1
Status: D1_SOFTWARE_CONTRACT_CANDIDATE; ORIGINAL_FORTRAN_POINT_COAST_PARITY=NOT_RUN.

## Frozen predecessor, not to be changed
Wolsong EXACT_AREA_V1 is **FROZEN_PASS_SCOPED** by user decision and Issue #119 closed. Select official **GSHHG v2.3.7 Full f L1** for area-method models. Original historical coastline controls are a distinct mode and must not overwrite GLC2022, 52/55 geometric area split, original LU.DAT or acceptance metadata.

Frozen Wolsong output SHA256: `3bccf3af99681dce1f31bf25c2085f19bef2e0c2b750c451f6fcf36cd11301b7`. Source GLC2022 SHA256: `2a1a208c5386735692d788066f730c7391e87f0981e7b9ad099442af2e217711`. User waived Full-vs-High as a blocking comparison.

## Checked original reference (READ-ONLY, no vendor redistribution)
- Original code: [CTEAS@dfad99a / CTGPROC_v7.0.0_L150211/ctgproc.for](https://github.com/RRain001/CTEAS/blob/dfad99a78ed84d655e21411c9d25eb0d2583bf13/engine/vendor/src/CTGPROC_v7.0.0_L150211/ctgproc.for).
- LUGRID: mapped 38-class indices, Fortran REAL*4 grid coordinates and `NGRID(land,i,j)=NGRID(land,i,j)+1`. Original marine option only when `LCOAST .AND. LMARSWAP .AND. (LUCATTYPE.EQ.1)`:
  * `IPTYPE(x,y)==0` (sea): `if(ilu.ne.54) ilul=iocean`; original 54 bay/estuary preserved.
  * `IPTYPE(x,y)!=0` (landward including GSHHS nested lake types): `if(ilu.ge.54.and.ilu.le.55) return`; discard 54/55 landward points, keep 52.
  * Then map through `LUMAP`, increment *integer* hit count for mapped class. Never split a sample's fractional area.
- SVGRID: `LFINAL=T` with `ISUM!=0` writes 38 distinct `NGRID(k,i,j)/FLOAT(ISUM)` fractions (F6.3). When `ISUM==0` AND `LCOAST` AND `LMARFILL` AND USGS38, assess **centre** `IPTYPE`: ocean gets `IOCEAN=1`, landward remains missing. Partially sampled cells are **not** automatically padded.
- READCF rejects `GENERIC` source + `LCOAST` or `LSNOW`; coastal must have LMARSWAP and/or LMARFILL; IOCEAN must be a mapped valid 1..92 category.
- IPTYPE uses hierarchical GSHHS polygons, 0 ocean, 1 mainland/island, 2 lake, 3 island in lake, 4 pond in lake-island. **Only using Full L1 to classify lake hierarchy is not original IPTYPE parity**. No claim of porting original COASTEXT/COASTRD/IPTYPE yet.
- Pre-existing native implementation **already has counting/projection**: `native_cpp/src/geo/landuse_fraction.cpp` (`GEN`), `native_cpp/src/geo/glcc_raw_fractions.cpp` (raw GLCC/GLAZAS), `native_cpp/src/p2_glcc_raw_cli.cpp` (HITS), `native_cpp/src/p2_glcc_lu_dat_cli.cpp` (38-class LU.DAT). These must be reused. No duplicate full hit-count implementation is authorized.

## This PR (D1, software only)
Only introduces `native_cpp/include/cteas/geo/ctgproc_original_coast_policy.hpp` and a CTest for the above original **policy branch**. No caller integration, no standalone working original coastal processor, no real original Fortran comparison. The pure helper accepts a future independently-validated `IPTYPE` value: it does *not* compute it from GSHHG. Test checks point suppression, original 54 exception, ocean `IOCEAN`, empty-only `LMARFILL`, invalid GEN+coast/snow, presence of both 52 and 55 in NGRID/ISUM. Test must show `ORIGINAL_FORTRAN_POINT_COAST_PARITY=NOT_RUN`.

## Next gates
1. Define original-compatible shoreline source format/loader and hierarchical `IPTYPE`; user preference Full geometry remains fixed, but original Fortran source support/representation must be checked independently.
2. Wire the *existing* P2-A point-count pipeline through guarded original optional coast policy, instead of duplicating base GLAZAS or GEN implementations.
3. Use a legal original CTGPROC input route (NOT `GENERIC+LCOAST`) and original source/controls, compile original Fortran without modifying vendor code; same-source C++ vs Fortran `LFINAL=F` exact 38 integer HITS and `LFINAL=T` 3-decimal LU.DAT fractions, with 54, empty sea, missing and mixed 52/55 paths.
4. Full real science acceptance only **manual workflow_dispatch** as authorized previously. PR synthetic CI is allowed. Do not auto-trigger real original science.
5. P3 Wolsong original/native GEO.DAT remains #46, not part of this adapter gate.

Acceptance label this PR only: `PASS_SOFTWARE_ORIGINAL_COAST_POLICY_SCOPED` after CI. Do not use `PASS_ORIGINAL_FULL_CTGPROC_PARITY`.
