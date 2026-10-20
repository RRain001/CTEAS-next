# Issue #42 S3-B3 — real Huoshan P1–P3 original-science time alignment for NOAA integration

Date: 2026-10-20. Depends on merged [PR #186](https://github.com/RRain001/CTEAS-next/pull/186) original 80,000-value Huoshan MAKEGEO verification. This change **does not** produce P4, P5, G19 or a five-product S3 PASS.

## Reason and scientific boundary

Existing genuine Huoshan P1/P2-A/P3 [PR #185](https://github.com/RRain001/CTEAS-next/pull/185) was admitted with 2022-01-01 00:00 → 2022-01-03 00:00 UTC. Separately, archived authentic NOAA 2022 Huoshan/Xinqiao P5 test data and P4 Anqing IGRA replay use 2022-06-01 → 2022-06-02 windows. Reusing already-generated January evidence against June weather would mix B-0 `research_time` SHA and is scientifically invalid.

The existing true-source workflow now executes *two independent complete jobs*, each in an isolated GitHub runner scratch: `jan_48h` preserves the previously passed January source and physical reference; `jun_24h` rebuilds the exact same **genuine** UTM50N Huoshan 100×100 @100m terrain/GLCC/P3 configuration for 2022-06-01 00:00 → 2022-06-02 00:00 UTC. Both read the same individually SHA-verified original SRTM90 and historical GLCC and recompile the same pinned unmodified original Fortran MAKEGEO. Both must pass the predeclared original/C++ 10,000 × 8 = 80,000 zero-mismatch printed-field check, with no tolerance changes.

Only the **research clock and resulting exact B-0 SHA** differ between matrix periods; source geographical footprint and physical controls stay frozen. Upload separate artifact names to avoid conflating their independent certificates. Do not merge unrelated prior NOAA standalone staged cases or carry over source-file bytes: future P4/P5 must be freshly produced under the June B-0 `case.yaml/grid.cmn/research_time` and actual station selection. The earlier P5 NOAA fixture was generated from a *different larger geographic grid* covering two stations; do not assume that identical `1US/2SS` membership will remain on the 10-km Huoshan grid. Confirm the native selector's real 1/N station results and original hour-ending/00/12 brackets, or fail closed.

## Subsequent gate, not included in this PR

1. In the June case, stage authenticated NOAA IGRA Anqing and real ISD/ISD-Lite source archives with immutable provenance.
2. Invoke **existing** scoped P4 `run_cpp_pipeline` and P5 `p5_case_producer` on that exact June B-0 in fresh independent scratch; require `UP.DAT`, published `SURF.DAT`, station tables and both producer manifests.
3. Run `native_cpp.orchestration.s3_five_source_preflight` over the original five generated output roles. Missing or foreign source must fail, not be replaced with the other site/year's hashes.
4. Generate a real matching `run/met/met.inp`; invoke existing `p6_g19_handoff` and native G19 **source-only** parser; preserve 9-layer original/source station order and native parser proof. P6 wind fields and P7 remain out of scope.
5. Run at least one alternate-grid/time positive/negative regression before considering #42 closure. Only then assert `S3_P1_P5_NEW_SITE_STACK=PASS_SCOPED`.

Current status: `HUOSHAN_REAL_GEO_P3_ORIGINAL_80K=PASS_SCOPED_JAN`; `HUOSHAN_JUNE_ORIGINAL_80K=AWAIT_CI`; `REAL_NOAA_P4/P5_SAME_CASE=NOT_RUN`; `G19=NOT_RUN`; `S3=NOT_ACCEPTED`. Docker stays deferred.
