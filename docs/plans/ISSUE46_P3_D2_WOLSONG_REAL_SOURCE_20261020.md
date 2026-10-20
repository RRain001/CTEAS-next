# Issue #46 D2 — Genuine-source Wolsong P1 SRTMGL1 + P2-C 2022 GLC30m → GEO

2026-10-20. Parent: issue #46; depends on merged [#174](https://github.com/RRain001/CTEAS-next/pull/174) and [#175](https://github.com/RRain001/CTEAS-next/pull/175). **Real-source native chain is a scoped D2 acceptance; numerical equivalence with independently compiled original Fortran MAKEGEO is separate D3 and is NOT_RUN in this PR.**

## Locked inputs and selected Wolsong geometry

- P1 real DEM: OpenTopography SRTMGL1 WGS84 1″ `N35E129.tif`, <https://opentopography.s3.sdsc.edu/raster/SRTM_GL1/SRTM_GL1_srtm/N35E129.tif>, exactly 6,456,645 bytes, SHA256 `b9b44e6936d45a738ead91429804048e6fa095abbee98e1792b7c42dbecf0769`, as already audited by `docs/data_audits/wolsong_srtm_20261019/summary.json`. Real Int16 pixel data and nodata metadata; ocean zero heights are not turned into invalid pixels or fabricated elevations. Source not checked into repo and excluded from artifacts.
- P2 real land use: Wolsong 2022 GLC_FCS30D 30 m SHA256 `2a1a208c5386735692d788066f730c7391e87f0981e7b9ad099442af2e217711`, [frozen mapping](https://github.com/RRain001/CTEAS-next/blob/main/docs/plans/ISSUE53_GLC35_USGS38_USER_SELECTED_20261019.json) SHA256 `a5fa157f57feb1aa160dd96d920a22d267fea78c5828c6040fa95e86536544ed`. Uses only **P2-C GLAZAS/LUGRID 10×10 source-point sampling**, 34+210 policy and USGS 52/55 original-style coastal distinction; **not retired P2-B area intersection**.
- Original coast: independently stage authentic original CTGPROC vendor source `RRain001/CTEAS@dfad99a7…` and source SHA `719abbd2…`, official GSHHG v2.3.7 **Full** via `scripts.s2g.issue123_gshhg_binary_full`; run original COASTEXT under the previously accepted GNU I/O-only adapters and SHA-check actual `coast.bln` = `67da93d441e7defe3eb46627ed9ce896c0a91ffd89fd5e4363d834d8108e11f9`. No synthetic substitute or coastal inference from UTM52.
- **One grid**: EPSG:32652, 200×200 @100 m, `XREFKM=533.215`, `YREFKM=3942.629`. B-0 `case.yaml/grid.cmn/research_time` staged independently for Wolsong 2022 UTC. All products have exactly one shared numeric authority and SHA-attested producer methods.

## Native execution and integrity gates

1. Build unchanged P1 native `cteas_p1_terrain_case` from `native_cpp/p1`, P2-C native `cteas_p2c_glc30m_sampling` from root `native_cpp`, and dynamic P1→TERREL plus P3 binaries from `native_cpp/p3`.
2. Use official 2022 Wolsong 30m P2-C plus verified original BLN to produce genuine 38-class coastal `LU.DAT` under `geo/ctgproc/p2c_case`. Ensure same B-0 case origin/CRS/extent and immutable data policy.
3. Run genuine SRTMGL1 P1 via `native_cpp.orchestration.p3_case_handoff`, convert native `terrain.csv` into north-to-south `TERREL.DAT`, and feed **the original native P2-C LU.DAT directly** into selected 38→14 P3 MAKEGEO physical option branch. Do not synthesize missing cells, copy legacy Hefei TERREL, or replace 2022 GLC by 1990s GLCC.
4. Gate case/source/method/zone/dimensions, all input and output SHA, finite/covered GEO scalars, expected 40,000 rows and coastal BLN SHA. Publish only small `P3_D2_REAL_WOLSONG_SOURCE_PRODUCED_UNVERIFIED` reports; keep original P3 science `NOT_RUN` and do **not** treat valid output as original equivalence.

## Explicit D3 follow-up

- Compile original standalone MAKEGEO from the unmodified pinned original source in a new independent validation job. Feed **the same newly produced Wolsong `TERREL.DAT`, `LU.DAT`, and supported selected physical control** to original and native P3; compare land/sea category, elevation, roughness log-weight, albedo, Bowen, soil heat, anthropogenic heat and LAI in each of 40,000 cells; inspect 320,000 displayed fields, F7 format, missing rules, original Fortran REAL*4 and water-threshold ties. Qualify any code-level parser and scientifically reviewed tolerances separately. **This D2 PR does not contain an original MAKEGEO run.**
- Cross-module P1–P5 same-site + P6/P7 remains #42/#40/#36. Scale expansion remains #161. Docker remains deferred until all other development Issues close.

The 2026-10-19 audit `docs/data_audits/wolsong_srtm_20261019` is only source-integrity and terrain diagnostic provenance; it cannot be re-labeled original P3 science. This workflow is the first genuine Wolsong three-module proof only after exact-source CI succeeds.
