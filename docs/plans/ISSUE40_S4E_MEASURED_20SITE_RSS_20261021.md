# Issue #40 — S4-E measured 20-station P6 G14 resource baseline

Date 2026-10-21. This is a bounded **measurement** follow-up after scientific [PR #215](https://github.com/RRain001/CTEAS-next/pull/215) 20SS+20US / 20SS+1US / 1SS+20US original CALMET 45-field parity and merged PR #216/217 for source-shape and aggregate upper-air resource budgets.

## What this measures

Use the **same production-intended but still explicitly experimental** 17-stage G14 C++ executable `cteas_p6g_s4b2_unified_selected` against the identical original-format, source-backed synthetic 12×12×9 scenario, including the full selected-hour calendar. For each of three station configurations independently measure:
- `1h`: real process maximum resident-set size from `/usr/bin/time -f '%M'` (KiB), elapsed wall-clock seconds and user/system CPU time.
- `6h`: new process invocation completing the full six consecutive hours, with the same metrics.
- Source files and original C++ MET output SHA256, via exact repository SHA and uploaded JSON/text artifacts.

No invented threshold, no arbitrary 20-station limitation in C++, and no claim that a single Linux CI runner's process RSS predicts other grids, years, source files or hosts. Resource measurements exclude the prior compiler/linker process and original Fortran process, because these are *native C++ solver* measurements. They are **measured maximum process RSS, not an analytically derived peak-memory upper bound**.

## Preserve scientific acceptance in the same jobs

After measuring native candidate, independently check out pinned, unchanged original CALMET 6.5.0 source and execute it for the same source-files and first hour/full six hours, comparing 45 fields per hour against the native candidate using immutable existing P6E tolerances and `total_exceedances == 0`. This demonstrates instrumentation did not corrupt physical output, without changing a single C++ physics kernel. An RSS record exists even if original science later fails; that record is *not* a scientific pass.

## Next production stage

Use actual measured baseline to plan worst-case and stress tests with substantially longer valid simulations, then implement **explicit audited resource budget policy** for G19/G14, including memory exhaustion fail-closed and physically supported meteorological missing-data paths, before enabling normal G26. Continue using genuine independently observed multi-site station data as a separate science requirement. G26 normal `run()` remains unsupported here; P7, Docker and precipitation remain out of scope.

## Executed CI: measured native process RSS and fresh original science

[Actions run #39529868662](https://github.com/RRain001/CTEAS-next/actions/runs/39529868662) **3/3 jobs SUCCESS** from PR source `cc2bcbe5c395ec69055604c7d53354dbf18e580c`. These values are raw **Linux GNU time measured peak RSS** for the actual **small 12×12×9, six-hour selected executable**; they are not analytical memory upper bounds, not a measured year-long simulation and not general multi-site production metrics.

| Source sites | G14 1h RSS (MiB) | G14 1h wall (s) | G14 6h RSS (MiB) | G14 6h wall (s) |
|---|---:|---:|---:|---:|
| 20SS / 20US | 5.375 | 0.13 | 5.500 | 0.39 |
| 20SS / 1US | 5.250 | 0.15 | 5.625 | 0.55 |
| 1SS / 20US | 5.250 | 0.09 | 5.625 | 0.38 |

Evidence jobs: [20SS/20US #118993039589](https://github.com/RRain001/CTEAS-next/actions/runs/39529868662/job/118993039589), [20SS/1US #118993039715](https://github.com/RRain001/CTEAS-next/actions/runs/39529868662/job/118993039715), [1SS/20US #118993039731](https://github.com/RRain001/CTEAS-next/actions/runs/39529868662/job/118993039731). Each job uploads its machine-readable `s4e-measured-resource.json`, raw GNU time records, actual original source SHA256 and native MET output SHA256. The same CI job independently rebuilt and reran **unchanged original CALMET 6.5.0** and checked 45 fields for *each of 1 and 6 hours* with existing P6E thresholds, **PASS_SCOPED, zero exceedances**.

The standalone resource parser initially labels its value `PRODUCED_UNVERIFIED_until_original_comparison` because instrumentation is executed first. The separate independent original-CALMET comparison following it in the same successful job establishes the final scoped science result. These RSS numbers do **not** justify a production memory cap or an extrapolation to 100×100 grids, 143 h or 1 year.

**Final classification for this source/CI only:** `S4E_MEASURED_SOURCE_SELECTED_20_SITE_PROCESS_RSS=PASS_MEASURED`, `S4D_ORIGINAL_45_FIELD_1H_AND_6H=PASS_SCOPED`, `G26_PRODUCTION=NOT_ACCEPTED`.
