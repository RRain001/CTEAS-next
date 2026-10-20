# Issue #42 — S3-B1 genuine Huoshan P1 → P2-A → P3 geographic input production

Date: 2026-10-20. Depends on S2 #169 scoped close and S3-0 [PR #184](https://github.com/RRain001/CTEAS-next/pull/184). This is a **fresh Huoshan new-site source-data run**, not a simulated or old Hefei/Wolsong cached GEO replay.

## Single new site / B-0

- Site anchor 31.694°N, 116.655°E; WGS84 UTM50N. The authoritative actual grid is 100×100 at 0.100 km, 10×10 km, origin XREFKM=462.305 / YREFKM=3501.570 (exact to 1 m). Center longitude/latitude are **reprojected from the rounded authoritative grid centre**, and must pass the common B-0 `admit_case` geometry check.
- Research UTC [2022-01-01T00:00Z, 2022-01-03T00:00Z], 48 hours; 9 vertical layers and original `ZFACE` array 0,20,40,80,160,320,640,1200,2000,3000 m. This time/height authority is for eventual NOAA/G19 source admission, **not meteorological production in this PR**.
- The B-0 `case.yaml/grid.cmn/research_time` is generated **outside** repository and frozen by raw SHA prior to native P2-A or P3 invocation. Both must consume identical bytes; P3 independently checks P2 method, LU, case/time/grid input SHA.

## Genuine on-repo source bytes, not a license expansion

- P1 source: user-authorized preexisting tracked 90 m, 3 arcsec, 6000×6000 WGS84 GeoTIFF `calpuff_terrain_and_landuse_data/china_srtm/srtm_60_06.tif`. Its bounding box 115°–120°E, 30°–35°N includes Huoshan new-site grid. **Size 72,096,675 bytes, pinned SHA256 `913a082c79df74ff4189fec9d94b678618b395a6fb0a64ee94e14c532362eae4`**; source provenance scoped to the user's actual TIFF, **not independently verified SRTMGL3 NASA version**. Retains file's existing elevation vertical datum, without inferred transformation or forced NoData filling. Existing repository README notes unresolved general third-party redistribution rights.
- P2-A source: original 156,000,000-byte USGS GLCC Eurasia historical `eausgs2_0la.img`, SHA256 `4f2a1977d141e2040da4d36ec6a4826c5c960c84686eaf10f226f388cb3ab90a`. This is the exact supported original inland historical data class/mapping source, **not** modern 2022 GLC30m and not retired P2-B.
- Both Git LFS source binaries are hydrated with `actions/checkout lfs:true`, checked for **actual byte length, SHA and in-memory original geotiff CRS** before use. A 133-byte Git LFS pointer must **fail**, not masquerade as a GeoTIFF. Raw 72MB/156MB source files and vendor code are **not** uploaded in artifacts.

## Source-to-output provenance and explicit scope

The workflow compiles only existing selected C++ P1 (`cteas_p1_terrain_case`), P2-A (`cteas_p2_glcc_raw`, `cteas_p2_glcc_lu_dat`) and P3 (`cteas_p12_to_p3_dat`, `cteas_p3_makegeo`) executables. No physical formula or original field mappings change.

1. B-0 stage admission first; fail on wrong UTM/origin, source SHA, wrong product format or source coverage/NoData. Since the intact genuine 6000×6000 SRTM tile exceeds native P1's current **full-raster memory admission** (the first [Run #39398039862](https://github.com/RRain001/CTEAS-next/actions/runs/39398039862) failed strictly at `P1 native full-raster memory budget exceeded`), a separate, SHA-bound **integer source-pixel window crop** `scripts/s2g/issue42_s3_b1_true_srtm_window.py` reads a tightly buffered Huoshan subset without interpolation, reprojecting or missing-data filling. Parent TIFF full-byte SHA, child crop SHA, source window integer pixel bounds, original WGS84 lattice, parent/crop exact pixel+mask equality and B0 SHA are all verified and recorded before native P1. The derived TIFF, not the full parent, is provided to native P1 as a separately SHA-identified true-source window. This preserves P1's existing resource budget and does **not** implement S5 capacity removal.
2. P2-A `p2a_case_producer` on real historical GLCC: real 38-class `LU.DAT` and original-style INTEGER HITS; **existing previously proven original selected algorithm**, but this exact Huoshan geometry has not yet had independent true original GLAZAS run.
3. P3 `p3_case_handoff --p2-kind A`: direct run of P1 terrain on the exact-pixel no-resample window from the real SHA-pinned 90m TIFF, true TERREL.DAT generation, P3 no-snow 38→14 selected C++ physics against exactly the same P2-A LU and B-0. Real `GEO.DAT` and a separate fresh P3 producer attestation result.
4. Independent source-only SHA join validates on-disk P1/TERREL, P2 LU and native GEO SHA, original 90m TIFF and GLCC SHA, 100×100 grid/UTM50N, case/time/grid SHA and link P2 evidence into P3 before emitting a **new bounded JSON**. Only `S3_HUOSHAN_REAL_P1_P2A_P3_PRODUCED_UNVERIFIED` is admissible; no original newsite physics PASS claimed.

Expected bounded artifact: P2 and P3 JSON proof, genuine SHA lineage, source methods, valid row counts, no raster/GLCC/LU/TERREL/GEO raw data.

**DO NOT close #42 from this run.** True same-site P4 NOAA IGRA `UP.DAT` and P5 NOAA ISD `SURF.DAT`, original-science P3 parity at Huoshan, `met.inp` station/time metadata and native P6 G19 source-only reader are **NOT_RUN**. The next execution must freshly produce P4/P5 from actual Huoshan/Xinqiao selected stations for the same 48 h research period under the identical admitted B-0 (without copying unrelated frozen Hefei/Wolsong files). Scale #161 and Docker are deferred.
