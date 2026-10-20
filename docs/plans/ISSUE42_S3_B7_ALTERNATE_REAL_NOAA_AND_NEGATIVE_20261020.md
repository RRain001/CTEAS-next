# Issue #42 / S3-B7 — alternate genuine NOAA UTC and fail-closed source integration gates

2026-10-20. This is the final **S3-4** scoped acceptance candidate after [PR #190](https://github.com/RRain001/CTEAS-next/pull/190) merged as `main@bc7e03bba29162ce6148c913380bbe469c1f8363`. PR #190 already proved the true Huoshan 100×100@100 m UTM50N 2022-06-01 **01:00–07:00 UTC** P1–P5 original-source production and native G19 actual input parsing. 2022-06-01 00:00→2022-06-02 00:00 UTC authentic same-case P1–P5 products were produced and SHA-joined but **native G19 properly rejected the absence of required 00/12 brackets for some hours**. This remains an input science limitation rather than a new time-series kernel defect.

## New, independent alternate positive scenario

In the existing genuine-source workflow, add a **fourth** isolated period `jun_6h_alt`, research interval `2022-06-01 02:00→08:00 UTC`. This is deliberately a **different real case time configuration**, not a recycled six-hour file. It retains the same *independently verified real Huoshan geographic grid* (100×100, 0.100 km, EPSG32650, origin XREFKM=462.305 km/YREFKM=3501.570 km) to distinguish a **temporal configuration regression** from unverified spatial expansion. No claim of validating a second horizontal grid is made.

The fourth job, isolated by GitHub Actions matrix runner and fresh scratch, performs all of the following with the *real same-site source bytes and its own case/grid/time SHA*:

1. Real parent SRTM 90m full SHA, no-resample source-pixel window crop, C++ native P1 terrain, real historical GLCC selected P2-A and C++ native P3.
2. Independently compiles unchanged SHA-pinned original Fortran MAKEGEO (CTEAS `dfad99a7`) and compares **10,000 grid cells × 8 selected fields = 80,000**, original vs C++ numeric and printed values with fixed unchanged tolerances.
3. Independently checks actual NOAA IGRA/ISD catalog candidates under the authoritative grid, the originally selected real Anqing 2022 728/730 profiles with actual 00/12 UTC brackets, and Luogang 2022 original full ISD+ISD-Lite (>90% *both* annually).
4. Runs existing native READ62 and SMERGE modules on this genuinely different time configuration in a clean 2022-06-01 02:00–08:00 case, giving separate `UP.DAT` and **published** `SURF.DAT`; invokes canonical S3 five-source same-case SHA join, original-format `met.inp` renderer and unmodified native G19 file-backed parser. **Never** reuses previously generated `UP.DAT` or `SURF.DAT`.
5. Exports separate bounded artifact and actual code, source, time and input-role SHA evidence. 24h/Jan/01–07 UTC jobs continue running unchanged with their own isolated evidence, so the four jobs are not conflated.

## Actual negative tests, run only after successful alternate native G19

The new `native_cpp.orchestration.s3_huoshan_g19_negative_gates` executes three **real byte-level tamper tests on those very same independently produced files**. Each changes only scratch data in a `try/finally` scope and restores original bytes and SHA afterward:

- **Station cardinality negative:** change the actual single NOAA `NSSTA=1` in the genuine original-format `met.inp` to 2. The existing `p6_g19_handoff.prepare_g19` must reject because the real station selection and deck disagree. Never claim two authentic surface stations.
- **Actual published SURF SHA negative:** mutate one byte in the *already produced real NOAA-derived* `SURF.DAT`, without touching any NOAA archived raw or simulator. Existing `execute_source_preflight` must reject the SHA mismatch *before* running the binary.
- **B0 UTC mismatch negative:** temporarily change only actual `grid/research_time` END from 08:00 to 09:00 while `case.yaml` still authorizes 08:00. Canonical `admit_case` must reject rather than reusing another time window's source SHA.

Finally it re-calls real `prepare_g19` and the native G19 source reader on **restored original files**, verifies equality of exact input-role SHA/identity/order and writes separate evidence. No synthetic weather is introduced or used in any positive verdict; negatives are deliberate metadata/byte corruption tests.

## Scope and closeout

Only if all four actual CI matrix jobs succeed, every independent original comparison passes, the new second-clock positive G19 parses real source, all 3 negatives truly fail closed, the restoration re-parses, and SHA artifacts/real logs are reviewed, can #42 be considered for **`S3_P1_P5_NEW_SITE_STACK=PASS_SCOPED`** under its selected original paths and valid observed six-hour brackets.

Not accepted under S3: arbitrary year/season NOAA availability, the rejected 24h G19 input, P1 general-scale memory limits, all original CALMET/CALPUFF physics choices, P6 hourly 45-field winds, P7 concentrations, wet deposition and Docker. Those belong to S4/S5 or separate later steps. Historical GLCC mapping is unchanged. P2-B stays retired.

**Scientific declaration:** second independent **UTC configuration** regression only, not second distinct horizontal grid, 1US/2SS production, or proof for all other NOAA site geometries. If such a different-grid test is later required, it is a separate scientific deliverable.
