# G18D6 — original SETCOM REAL*4 NEARU and STHEOR SS→US binding

2026-10-14, PR #63 Draft stacked on PR #53 (accepted and frozen).

## Physical/algorithmic authority

Original CALMET 6.5.0 `calmet.for` **SETCOM** computes
`NEARU(I,J)` using the original nearest-upper station algorithm:

```fortran
      data rmax/1.e37/,ldate/.false./
      if(nusta.le.0)go to 121
      do 120 i=1,nx
      xgdpt=(float(i)-0.5)*dgrid
      do 120 j=1,ny
      ygdpt=(float(j)-0.5)*dgrid
      dmin2=rmax
      ksv=0
         do 112 k=1,nusta
         dist2=(xusta(k)-xgdpt)**2+(yusta(k)-ygdpt)**2
         if(dist2.lt.dmin2)then
            dmin2=dist2
            ksv=k
         endif
112      continue
      if(ksv.gt.0)then
         nearu(i,j)=ksv
      else
         write(io6,18)i,j,ksv,'NEARU'
         stop
      endif
120   continue
```

The earliest site in original source order wins equal-distance ties.
Distance is REAL*4 squared metres using original gridpoint center
coordinates. The exact `RMAX=1.e37` guard is from original BLOCK DATA.

Under `ITPROG=0`, original STHEOR uses the actual *station grid cell*:
`call mixhtST(...,is,js,nearu(is,js),iupt,...)`. The pinned
`IUPT=-1` therefore picks NEARU at each surface station's
`IST/JST`, not manually specified surface→UP pairs. Positive IUPT
and water/out-of-domain STHEOR are separate unaccepted branches.

## Implementation

- `p6g_g18d6_nearu_reference_main.cpp` executes the existing
  G18B3 original-deck native `g18b3_source_deck_upper_choice` path.
- `reference/compare_original_g18d6_nearu.py` extracts and compiles
  the **literal unchanged original CALMET Fortran SETCOM nearest-UP
  loops** and original DATA RMAX as a separate gfortran executable.
  It compares all gridpoint one-based upper-station ordinals exactly
  against real C++ output for **13 cases**, including 1/2/3/4/6/8 UP,
  station coincidence, equal-distance ties, near/far stations,
  5/10/20 km grids and up to 64×64 cells. Tolerance is **zero**;
  no independent *hand-coded* nearest-neighbor oracle is accepted.
- The new original-code CTest is
  `p6g_g18d6_literal_vendor_setcom_nearu_real4_parity`, compiled in
  GitHub-hosted Ubuntu Debug and Release alongside previous G18
  original source verification.
- New `p6g_g18d6_station_upper_assignment.hpp` derives every
  `G17C3StationControls.upper_ordinal_for_surface` directly from
  the original 1-based NEARU grid at that SS grid cell. It checks
  source station order, all-land valid GEO, inside-domain station
  coordinates, and original `IUPT=-1`. The existing selected
  2SS/2US stage test now uses this **source-calculated mapping**
  instead of manually supplied `{0,1}`; it also rejects incorrect
  outside-GEO station input.

## Remaining gates

Original SETCOM NEARU parity and STHEOR upper selection are bounded
components; they do not complete the original 17-stage G14 production
physics or independently verify original WIND1/INTER2/STHEOR/G17C3
thermal physical state. G18D4 COMP's native interface still correctly
refuses `{NativeCpp,true}` for full-hour promotion.

The remaining hard gates are source-complete first twelve PREPDI/
DIAGNO callbacks, real all-hour native P6F publication and restart,
and original multi-SS/UP per-value strict 45-field 1h/6h/143h/year
comparisons. Keep PR #63 Draft, hosted Ubuntu only, frozen PR #53
unchanged. CI PASS must be checked on the **exact current source SHA**.
