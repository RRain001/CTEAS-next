# Issue #40 — S4-R1c7b authentic sparse-station G17C3 STHEOR

Date: 2026-10-22. Base: main@ba9eca2d6325df5344fdf7dbdbe5deb952ad8ca6, merged PR #247 original station-only oracle.

## Scientific dependency

Real NOAA 2022 2SS+1US, 82x85x9, 63 WATER, six distinct hours. Pinned original CALMET 6.5.0 has exactly 8 ELUSTR2->SIMILT station invocations from 12 potential surface-station hours. Independently accepted G45 raw observed missing-surface-wind counts [1,0,1,1,0,1] sum to 4, matching 12-4=8. Original scratch-write-only and pristine 6h x45 MET.DAT are byte-identical. This is source-causal support for explicitly skipping invalid wind at STHEOR, never changing the P5 mask or turning missing into valid zero calm.

## Native work

- Extend the common G17C3 ELUSTR2/MIXHTST/SIMILT adapter only with an explicit test-only source-missing-wind skip. It preserves original StationSet/ordinal/upper PREPDI and never creates a synthetic observation. Old C1/C2 caller defaults are unchanged.
- Factor original READCF station controls out of G23 into ONE shared function used by both the all-land selected source and real mixed WATER source.
- G48 test-only consumes real G41/G43 and independently accepted G47 genuine first-hour WIND1/FRADJ/thermal/SLOPE C++ physical fields, reconstructs only source CALMET COMP model-internal nonwind MISSFC on a detached copy, replays original-ordered two-pass SURFVAR, then calls unchanged G17C3 station physics on the one valid station while skipping the genuinely missing wind station. No G14/P6F hour is committed.
- Native first-hour nine-level CSV contains source station ordinal and site cell, model UTC, genuine SIMILT U/V and original-physical selected station flux/mixing fields. An independent Python comparison consumes the pinned scratch-only original six-hour oracle after BOTH executables finish, and compares first-hour valid station U/V at the existing literal SIMILT tolerance 2e-4 m/s.
- Original real six-hour station reference and full first-hour G47 post-SLOPE numerical comparison are rerun on the same HEAD. C1/C2 143-hour physical equivalence workflow triggers now include changed shared G17C3 and G23 source-control files.

## Acceptance boundary

At most PASS_REAL_FIRSTHOUR_ORIGINAL_NATIVE_SPARSE_STHEOR_SIMILT, conditional on exact-head PASS with zero exceedances and all scientific regression checks. Scope is one real valid first-hour station, NOT full multistation six-hour G23/INTER2, G24 final 3D wind, WATER native six-hour causal ZI/ZICONV, G26 six-hour 45-field native-vs-original or P7. Issue #40 stays OPEN. No S5/Docker/wet deposition/vendor source redistribution. P5 primary/auxiliary missing/calm policy untouched.
