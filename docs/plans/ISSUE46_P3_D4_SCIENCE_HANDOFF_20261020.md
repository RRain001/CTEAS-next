# Issue #46 D4 — verified selected-physics P3 result → S3 / #42 evidence handoff

Date: 2026-10-20. Baseline `main@a60aa02ef2ef7ab8dbec7f872f427c8d7393eec3` (merged #177). **This D4 work only signs off the selected P3 supported MAKEGEO physics for the verified Wolsong 2022 case. It does not complete S3 P1–P5.**

## Valid accepted science reference

The independent original Fortran numerical validation from #177 is [Run #39386859987](https://github.com/RRain001/CTEAS-next/actions/runs/39386859987), [Artifact #12248275718](https://github.com/RRain001/CTEAS-next/actions/runs/39386859987/artifacts/12248275718): true same-source OpenTopography SRTMGL1 + 2022 GLC30m + genuine original Full BLN, grid EPSG32652/200×200@100m. Original SHA `8c4fb11db36d4b976b54f470b7a06ce4e38ab09e934951b0e2c613bddc34e347`. Original independent Fortran and C++ GEO 320,000 displayed numeric/category values: exactly equal, with 0 C++ float CSV fields outside predeclared fixed-format precision tolerances. Original/native full-file SHA differ due to file formatting/header; parsed field values have 0 mismatches.

## D4 artifact and bounds

`native_cpp/orchestration/p3_d4_science_handoff.py` is **only an attestation gate**, never another numerical model or another comparison threshold. It can promote a freshly produced `evidence/p3.json` **only after** independent original `p3-d3-wolsong-comparison.json` passes all 8 field-specific 40,000-cell counts with 0 displayed/precision failures and matches the *actual bytes* of the separately generated original GEO and native GEO/CSV.

Checks include:
- Wolsong scoped `case.yaml/grid.cmn/research_time` identity, UTM52N, 200×200@100m, same case and grid SHA from independent native P2-C/P3 producers.
- Real P1 source SRTMGL1 SHA; real 2022 P2-C GLC SHA; original Full COASTEXT BLN SHA; frozen mapping policy SHA and method ID.
- P2-C actual LU byte SHA and D2 P3 attestation/reference bindings; modified-format `LU.DAT` with legal original Fortran list-directed terminal marker after 38 fractional values; native GEO, native CSV, original GEO and D3 comparison report SHA.
- Independent source compiler, active original vs C++ GEO references (separate SHA). All 8 *predeclared* fields exactly matched after rendering, C++ high precision CSV within fixed tolerances.
- Fail-closed corruption/stale case/modified LU/modified original GEO/science-mismatch unit tests.

When and only when checks pass, write a **new** JSON `evidence/p3-d4-scoped-science.json` with `status=P3_WOLSONG_SELECTED_ORIGINAL_MAKEGEO_ACCEPTED_SCOPED`, original source/vendor references and immutable all-source SHA. Original P3 `evidence/p3.json` remains **unchanged** and honestly records `p3_original_makegeo_science=NOT_RUN` as its earlier native production context. Only D4 newly certifies externally reviewed original science. Do not alter P2/P3 provenance after the check.

## Reproducibility & handoff

The PR replays the *real* SRTMGL1/GLC30m/Full original BLN and independent original MAKEGEO in GitHub Actions, adds a software-negative separate job and uploads only bounded JSON evidence including the new D4 certificate. The source/vendor/DEM, coastline, raw LU/TERREL and GEO are intentionally **not** redistributed. File SHA and Run/Artifact provide an independently repeatable pointer; file bytes can be regenerated in authorized local scratch.

**For #42 S3** this is one successfully science-qualified Wolsong `GEO.DAT` entry, not an available combined five-product case. `UP.DAT`, `SURF.DAT`, P6 G19 parser, station identity and model hours are **NOT_RUN** and `S3_FIVE_PRODUCT_STACK=NOT_ACCEPTED`. Wolsong P2-C source-mapping provenance is user-approved for the selected modern dataset; original P2/TERREL source numerical equivalence outside existing scoped paths is **not claimed**. No additional MAKEGEO option (SNOW, LU2, NSPLIT or other 38→14 formula variation) is accepted.

Docker build/multiarchitecture packaging remains deferred until all other development issues close. D4 is eligible for merge/closure of #46 only after current-head genuine-source proof, fixed historical CTest and no-failure CI are reviewed. #169 S2-D and #42 S3 stay OPEN.
