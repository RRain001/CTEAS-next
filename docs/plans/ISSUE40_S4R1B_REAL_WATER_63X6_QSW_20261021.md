# Issue #40 — S4-R1b genuine 2022 NOAA WATER QSW native-vs-original six-hour comparison

Date: 2026-10-21. Base: `main@cff4baa0c8e73783d38fa4769751a658e5c2d450` (R1a PR #237 merged after 17/17 successful exact-head workflows).

## Science being tested

The original source WATER path is 2 observed NOAA surface meteorological stations 583140/583210, one independently sourced Anqing upper station 58424, six hours 2022-06-01 01:00–07:00 UTC, original-sized 82×85×9 1 km UTM50N GEO, with exactly 63 actual original water-category cells (378 water-cell hour records). The 45-field original six-hour CALMET.DAT must be independently rerun from the same SHA-verified GEO, SURF, UP, and met.inp, and remain **byte-identical** when scratch CALMET is independently instrumented. Vendor source: RRain001/CTEAS@dfad99a78ed84d655e21411c9d25eb0d2583bf13 CALMET Fortran Git blob 437f43bb7f0e51a1919e56664663e1a046986ed0. Do not copy/re-publish vendor source into the public CTEAS-next repository.

### Genuine numerical C++ path

- G19 `g19_load_source_clock_only`: read real original met.inp/GEO.DAT/SURF.DAT/ordered UP.DAT, exact station order/hour clock. **Not** G19 physics-ready type.
- G38: enforce exactly `NOWSTA=0 ITWPROG=0 ICOARE=10 IMIXH=1 NOOBS=0 IAVET=1 ISURFT=-1` original branch with genuine 50–55 water GEO; reject HFLUX overrides.
- G40: on every real hour, reuse frozen P6E WGS84-UTM inverse + SOLAR time midpoint, source SETCOM nearest observed surface station, observed cloud/temperature SURFVAR, and selected unmodified P6E HEATFX. Extract ONLY water `(i,j,h,category,NEARS,ICC,SINALPC,QSW,QH)` plus temperature carrier and assert G26 flags remain false.
- The temperature carrier is original-source observed SURFVAR, NOT actual post-FRADJ second IAVET=1 temperature. That distinction is safe **only for water QSW**, whose immutable Fortran HEATFX calculation does not depend on TEMP2D at all. It does **not** validate land sensible QH or ELUSTR, and must not be reported as such.
- The original Fortran trace inserts WRITE after genuine original DIAGNO second SURFVAR/HEATFX/ELUSTR, before alternate ISFCMET branch. The native C++ command has no original trace/original MET input. Strictly verify water cell order/real identifiers/nearest station and cloud category, compare all 378 source QSW and SINALPC values. Require finite original QH and test this specifically (neutral prior-water QH may not be safely assumed absent original observation).
- Publish original vs scratch CALMET full 45-field SHA equality, exact native binary SHA, original input SHA, strict residual upper bounds, date/hour/cell evidence.
- Original full 45-field parity and physical completion are **NOT** achieved from this interface.

### Evidence and acceptance gates

| Claim | Required evidence |
|---|---|
| Authentic observed water case | True NOAA 2SS 1US data and original P1/P2/P3 GEO input SHA and same 82×85×9 63 water cells |
| Genuine C++-computed solar water QSW | Independent G19/G38/G40 C++ run using source met.inp, GEO, SURF, UP without original MET.DAT as input |
| Genuine original WATER HEATFX QSW | Exact pinned scratch Fortran trace from same source, six independently executed hours, unchanged 45-field MET.DAT bytes |
| Numerical source parity | 378 paired actual water cell/hour records with matching GEO category/NEARS/ICC and `max|ΔQSW|<=0.05 W/m²`, `max|ΔSINALPC|<=1e-3`; no fake synthetic station/scenario |
| R1a unchanged | Re-run negative source-only G39 test; no production route |
| Full real land thermal G22 | `NOT_RUN`; post-FRADJ surface temperature, land QH/ELUSTR parity unresolved |
| Native G24 water final U/V & G26 6h×45 | `NOT_RUN`; blocked separately |
| P7 #36 | `BLOCKED` |

Stage can be marked `PASS_SCOPED_ORIGINAL_VS_NATIVE_WATER_QSW` **only if exact-head GitHub Actions finishes SUCCESS**. This is an intermediate scientific acceptance, not full S4 P6.
