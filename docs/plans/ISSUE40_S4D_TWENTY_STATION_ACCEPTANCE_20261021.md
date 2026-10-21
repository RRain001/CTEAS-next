# Issue #40 — S4-D twenty independent surface and upper stations, original numerical acceptance

2026-10-21, baseline `main@6fa3e59a4237a2f43867f86025270f8b3707d736`, following scientifically scoped [PR #214](https://github.com/RRain001/CTEAS-next/pull/214).

**User decision:** twenty stations are a sufficient bounded *scientific test coverage goal*. Do not impose a hardcoded maximum 20 in G19, G14, P6E, or production P6. The original CALMET 6.5.0 reference compiled limits remain `mxss=350,mxus=99`, which must not be adopted as arbitrary modern C++ capacities.

## Three new acceptance configurations

- `20SS+20US`: both independent station collections contain twenty observations and source metadata; this is a stronger check than twenty total stations.
- `20SS+1US`, `1SS+20US`: catch asymmetric nearest-neighbor and source-station indexing bugs.

Every case uses real original-format **controlled synthetic** 12×12×9, six-hour, UTM-50N land meteorology. Unique station IDs, independent original `met.inp` declarations, actual SURF station records and individually staged UP soundings, independently assigned per-source positions and station-specific winds are required. Do not present synthetic input as twenty historical NOAA observations. No original-output fields may be injected into native C++.

GitHub Actions compiles and runs **unchanged pinned original Fortran CALMET 6.5.0** separately from the SAME selected-source C++ G14 17-stage executor. For each case verify true original output and full source/provenance at (a) first model hour and (b) six consecutive model hours. Independently enforce original 45-field labels, timestamps, all grid cells and unchanged frozen P6E thresholds with `total_exceedances==0`, `status=="PASS"`. A C++ produced file or Fortran source admission alone is `PRODUCED_UNVERIFIED`, not a pass.

**Follow-up after PASS:** stop chasing 24/32/64 station artificial test counts. Start S4-E actual station-array shape/budget and source identity negative-case audit, real multi-observation-site source acquisition, and **separately gated** normal G26 production-entry design. All accepted C1/C2 and actual NOAA Huoshan original P6 numerical regressions must be protected. The new science validates the *selected* 9-layer all-land physics only; the normal production `run()` remains fail-closed until independent acceptance. P7 remains separate Issue #36; S5 large-grid and wet deposition/Docker are later tasks.

**Science result:** NOT_RUN until actual exact-head Actions matrix completes. If any of the three fails original science, leave the PR draft and document source-vs-formula root cause; never loosen tolerances merely to pass.
