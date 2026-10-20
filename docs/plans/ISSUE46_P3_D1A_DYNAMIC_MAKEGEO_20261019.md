# Issue #46 — P3 MAKEGEO D1-A dynamic grid calculation (2026-10-19)

## Purpose

Issue #46 was reopened because its original acceptance target was broader than the historical scoped Hefei-only parity. This PR is the **first software-only native P3 parameterization slice**, not an original scientific acceptance and not a complete new-site P1–P5 handoff.

## In-scope changes

- Preserve the selected legacy MAKEGEO control branch: LTERR=T, LLU2=F, LSNOW=F, NSPLIT=0, WGS-84 UTM, fixed 38 input classes → approved 14 output classes and existing unmodified selected physical formulas.
- Parse valid UTM zone 1–60, hemisphere N/S, NX/NY up to 500 cells each, DGRIDKM to 0.001 km representation, and XREFKM/YREFKM as literal **exactly three decimals in kilometres**.
- Reject UTM parameter mismatches in input LU.DAT and TERREL.DAT headers: zone, hemisphere, dimensions, origin and resolution must match the MAKEGEO control file. Preserve row orientation (TERREL north–south, LU/CSV south–north).
- Produce dynamically sized CSV and GEO.DAT while keeping original Hefei 50×50 @ 0.1 km, 50N, XREFKM=510.885/YREFKM=3531.269 regression.
- Small synthetic 4×3/52N test confirms P3 output shape, index order, MAKEGEO USGS52→output51 mapping, dynamic GEO headers. Negative tests cover bad source-grid origins, truncated LU, invalid zone, spacing precision and non-three-decimal origins.
- Retain strict original control table and bounded cell allocations; no additional unsupported MAKEGEO switches, snow, supplemental LU2, source category choices or scientific tolerance changes.

## Explicit gaps and next phases

- **D1-B:** adapt existing `native_cpp/p3/p12_native_dat_adapter.cpp` from fixed Hefei 50×50/UTM50N to the same approved dynamic B-0 grid control without rewriting P1/P2 numerical kernels. The source CSV and manifests must be admission-checked against the same case/grid and data hashes.
- **D2:** connect authentic upstream P1 [#54] `terrain.csv` plus P2 [#53/#123] 38-category fractional output; generate newly created original-format TERREL.DAT + LU.DAT and dynamic GEO.DAT in isolated scratch. Not allowed to use old Hefei GEO/TERR disguised as new site.
- **D3:** manually dispatch unchanged, independently compiled original MAKEGEO and C++ on **same** non-Hefei authenticated inputs and unchanged supported physical options. Compare original/C++ 8 fields per cell and formatted GEO bytes/values, preserving scalar precision, land–water semantics, category tie-breaking and missing coverage boundaries.
- **D4:** hand accepted GEO with exact source/product/version/grid/case SHAs to [#42]. New 30m land cover mapping and coastline original option equivalence must respect ongoing [#123] acceptance and its limitations. Keep #40 P6 45-field physical science separate.
- Full 143h/annual/real original scientific workflow runs **only via explicit `workflow_dispatch`**; normal PR CI is a small isolated synthetic/fixture software regression.

## Review gate

`P3_DYNAMIC_CONTROL_AND_GEO_SOFTWARE=REVIEW_REQUIRED`; `P3_GENERIC_P1_P2_INPUT_HANDOFF=NOT_RUN`; `P3_ORIGINAL_NON_HEFEI_PARITY=NOT_RUN`; `G1B_B_P1_P5_REAL_INPUT_STACK=BLOCKED`. Do not close #46 based on this PR alone.
