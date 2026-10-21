# S4-E: measure actual selected G14 process RSS on real NOAA Huoshan 100×100

Date 2026-10-21; refs [#40](https://github.com/RRain001/CTEAS-next/issues/40), follows merged scientific #215 and resource #216–#219. Scope: **only evidence instrumentation**; no source weather fabrication, no selected physical kernel change, no new production G26 authority.

## Controlled evidence design

The existing [S3 real Huoshan original-source workflow](../../.github/workflows/issue42-s3b1-huoshan-real-geo.yml) reconstructs the **same** authentic 2022 Huoshan 100×100×9 @100m original-format GEO/SURF/UP and 1SS/1US selected G14 P6 run, then separately compiles and reruns unchanged original CALMET 6.5.0 and enforces all 6×45 original fields with zero P6E exceedances. On the legally supported **2022-06-01 genuine NOAA six-hour** matrix branch only, GNU `/usr/bin/time` now measures the existing selected native executable's actual process max resident set size and CPU/wall time for:

- Original selected-source one-hour *prefix*: the real G19 source deck declares 6 hours and G14 actually executes only 1 hour.
- The matching full continuous 6 hours with cumulative physical history and identical executable.

The binary, NOAA/GEO inputs and native MET output files are SHA256 recorded in the machine-readable `s4e-huoshan-measured-resource.json`, along with raw GNU time `%M %e %U %S` (max RSS KiB, elapsed seconds, user CPU seconds, system CPU seconds) and candidate output size/SHA. The receipt is emitted **only after the independent unmodified original CALMET full 6h field comparison returns PASS with zero exceedances** and it is retained alongside the original Fortran science artifacts.

The original G14 stdout and candidate file output semantics are unchanged, as is the frozen field comparator and source chronology. A genuine 100×100 raw retained 45-field hourly lower bound is `100×100×45×4×hours`, giving 1,800,000 bytes for 1h and 10,800,000 bytes for 6h, excluding all temporaries and a second serialized file copy.

## Strict limits

This is a **Linux runner process RSS measurement**, not a mathematical peak RAM upper bound or resource budget policy. It excludes input acquisition, compilation, original Fortran process, staging and P1–P5 runs, and cannot be extrapolated to a year, arbitrary grid sizes or real 20-site observations. It does not remove S5 capacity limits or unlock G26 production/P7. No year-long or independent 20-site NOAA science is claimed.

## Merge gate

Exact final PR SHA must pass Huoshan authentic four-job workflow (including first/full six-hour original science), existing relevant P6 CI regressions, and produce a parseable JSON receipt with strictly positive observed peak RSS, matching SHA and `total_exceedances=0`; if the runner cannot measure, fail closed. Only then update measured figures and sign `S4E_HUOSHAN_REAL_100X100_RSS=PASS_MEASURED_SCOPED`.
