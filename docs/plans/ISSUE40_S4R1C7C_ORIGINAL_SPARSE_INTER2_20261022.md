# Issue #40 — S4-R1c7c real NOAA sparse DIAGI → INTER2 source oracle

Date: 2026-10-22. Baseline: \`main@030b65978c29be553a856140df4c313151b785c8\` after merged #248.

## Motivation

The genuine observed 2SS+1US 2022-06-01 01–07 UTC site (82×85×9, 63 WATER) has 4 actually missing surface-station winds in 12 station-hours. Merged #248 independently proved only the first real valid station G17C3 ELUSTR2/MIXHTST/SIMILT U/V at 2e-4 m/s. It does **not** establish original \`US/VS\` arrays for missing station columns or what \`INTER2\` did at every model grid cell. G17C3 can skip source-invalid SS only with an explicit test opt-in, whereas \`merge_g17c3_surface_diagi\` expects \`selected.size()==NSSTA\`; G16's full \`do_wind1\` also rejects missing wind. Removing the site/reindexing it or converting to observed calm would change scientific inputs.

## This PR

Source-only SHA-pinned, write-only instrumentation on **independently freshly executed original CALMET 6.5.0**, reusing the existing #248 authentic P1–P5 true NOAA workflow.

- Just before original DIAGNO's two \`INTER2\` calls, capture original fixed-order \`US/VS\` arrays (SS1, SS2, US1; all 9 layers), with native source \`NDATHRB/NSECB\` per each of six chronological hours.
- Immediately after both original \`INTER2\` calls and before subsequent wind-tail processing, capture all original \`U/V\` on the 82×85×9 grid. The physical formula, source input decks, station count, WIND1, STHEOR and output writer are unchanged.
- The original blob \`437f43bb7f0e51a1919e56664663e1a046986ed0\` and original DIAGNO anchor lines 6055, 6059, 6072 are checked before instrumentation; scratch CALMET compiles separately. The untouched-pristine and instrumented-original **six-hour × 45-field MET.DAT must be byte identical**.
- Decode independent binary stream records with strict expected hour keys, six distinct times, 9 original layers and all 3 station ordinals. Cross-check the first actual valid original station's pre-INTER2 U/V against the separately obtained #247/#248 original SIMILT station reference.
- Publish **only** a bounded JSON containing SHA provenance, station column statistics and full-grid U/V counts; no raw Fortran source, original observation, private terrain or raw wind trace in GitHub artifacts.
- Negative self-test for corrupt original stream headers.

## Validation and next gate

Expected current maximum status: \`PASS_ORIGINAL_REAL_SPARSE_INTER2_PRE_POST_REFERENCE_ONLY\` **only after CI genuinely passes**. This is an original reference/oracle, not original-versus-native INTER2 and not a new CALMET physics branch. It cannot be used to inject original station profiles or U/V into C++.

After numerical evidence, fix **existing shared** G17C3→G16/G23 station-column representation to keep exact SS1..SSn and US1..USm even when a SURF wind is missing, and use explicit presence/sentinel semantics demonstrated by original. Verify first-hour native full-grid 9-level INTER2 against the new independent original (no relaxation of frozen tolerance), then proceed G24 wind tail and causal WATER COMP. No claim of six-hour native G14 WATER 45 fields or P7.

No P1–P5 source policy changes, no Docker, S5, wet deposition or licence changes. \`#40\` remains OPEN.
