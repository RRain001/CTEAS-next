# Issue #40 S4 P6-B1 — authentic Huoshan 1SS/1US first-hour WIND1 diagnostic, not an accepted CALMET wind field

2026-10-20. Prerequisite [#42](https://github.com/RRain001/CTEAS-next/issues/42) genuine same-site 1SS/1US P1–P5, G19 source-only numeric input SHA accepted on 2022-06-01 **01:00→07:00 UTC**. [#40 P6-A](https://github.com/RRain001/CTEAS-next/issues/40) actual audit [PR #193](https://github.com/RRain001/CTEAS-next/pull/193) verified G20's current 2SS/2US and synthetic ID 58424/58425 policy, source SHA and P6D 50×50/frozen 143h incompatibility.

## Narrow implemented experiment

This PR modifies **only the already existing G20 test-only WIND1 source-profile function and its CLI**, not P6D/E/F or scientific option values:

- For genuine 1SS/1US first-hour *test only*, reuse existing original selected SURF SIMILT neutral profiles, actual P4 NOAA UP bracket VERTAV/PREPDI wind and G16 native WIND1 first guess on the authorized actual original G19 geometry. Preserve exact source-window, source station identity and producer B0 SHA checks.
- The existing **2SS/2US synthetic G32E upper-first-layer** original-source representation remains unchanged, including source test IDs 58424/58425 and existing G20/G26 synthetic tests. One-SS/one-US new-site WIND1 **does not** pretend to know the original Fortran DIAGI/INTER2 first upper layer missing policy: all separate INTER2 inputs are marked unavailable/999. G16 requires post-SLOPE physics before INTER2; never execute G26, FRADJ, SLOPE, COMP, P6E or P6F as a result of this input-only experiment.
- A new explicit opt-in `--real-one-ss-one-us-test-only` is mandatory for the single-station configuration. Calling the CLI without that flag must reject and produce **no candidate CSV**. Supplied 2SS/2US with that flag also rejects. The code emits distinct `PASS_P6G_G20_REAL_1SS1US_TEST_ONLY_NATIVE_WIND1` and **`ORIGINAL_WIND1_PARITY=NOT_EVALUATED`** status.
- Reuses the accepted S3 genuine Huoshan 100×100×9 @100m case by **one additional guarded step in the existing true NOAA workflow**, on `jun_6h` only. The unchanged native G19 source-only stage must pass beforehand. Compiles the same existing `cteas_p6g_g20_source_wind1_probe` target and executes the exact first hour from `2022-06-01T01:00Z` to `02:00Z` against genuine `met.inp/GEO/SURF/UP`.
- Checks returned first-hour source coordinate/time/role SHA, parses all **90,000 layer/grid records**, requires all U/V finite and at least one actual nonzero model-grid U/V, records component min/max and exact CSV/real source/core binary SHA. Uploads **bounded JSON only**, not 90k rows or raw NOAA data. A negative CLI no-opt-in invocation must explicitly reject.

### Explicitly not accepted

The WIND1 selected **first guess** is not an independently original-FORTRAN-validated 3D wind field: no original CALMET WIND1 first-hour station and grid oracle, no FRADJ/SLOPE/INTER2 or final 45-field `MET.DAT`. Even if all source and native tests succeed, status is only `P6B1_REAL_HUOSHAN_ONE_ONE_WIND1=PRODUCED_UNVERIFIED`, and `P6_NEW_SITE_SCIENCE=NOT_ACCEPTED`.

A real fail-closed source hour because of missing/calm P5 observation, invalid original PREPDI profile or unsupported original control is a science blocker, **not** a license to fabricate wind, fill original upper observations, change threshold, or use the frozen Hefei 50×50 geometry. The independent original CALMET physics comparison, missing k=1 policy and full 45-field/hour belong to subsequent P6-B1/2/3/C. S5 capacity work, P7, precipitation and Docker remain deferred.
