# Issue #42 S3-B5 — genuine original NOAA P4/P5 production on exactly the June Huoshan case

Date: 2026-10-20. Depends on B4 real station-geometry [PR #188](https://github.com/RRain001/CTEAS-next/pull/188) `main@77e221402cf192c907da48b2e3ee49aa316807dd`, including [actual run #39404280433](https://github.com/RRain001/CTEAS-next/actions/runs/39404280433).

## Actual selection geometry

For the **same** P1–P3 actual 100×100@100m UTM50N June 2022 grid, official full-station catalogs report **zero** physical IGRA stations and **zero** physical ISD stations inside. The closest IGRA is Anqing `CHM00058424` 123.407 km away. The closest ISD candidate is Luogang/Xinqiao `58321099999` 44.653 km away, with Huoshan `58314099999` second at 44.719 km. These are station catalog *candidates*, not a preapproved result. Never reuse the physically different larger-grid 1US/2SS previous NOAA result.

## Implementation

June-only workflow steps use the **same scratch root and immutable B0** which has just produced authentic SRTM90, genuine historical GLCC, P3 `GEO.DAT`, and passed unmodified original MAKEGEO/C++ 80,000-field zero-difference comparison.

- The original case definition now carries a source/stack lon/lat and a physical `grid/center_location` matching the exact B0 grid centre. Both January and June P1–P3 physical regressions rerun because this intentionally changes `case.yaml` SHA, not the grid or source.
- Stage pinned **actual retained original NOAA** Anqing IGRA POR from the existing repository, and Luogang full ISD + ISD-Lite for 2022, independently copying bytes to new scratch and SHA-checking originals. Independently recount yearly full/Lite 2022 authentic source hours; both must be strictly >90% to qualify as an external ISD proxy. No live NOAA, synthetic source or unrelated prior `UP/SURF` is copied.
- Build existing native READ62 and SMERGE kernels without physics edits, use their established **offline original annual selectors** on the exact June B0. They must verify actual 00/12 real IGRA, real original hourly P5 sources, and publish newly computed candidate `UP.DAT` and `SURF.DAT`. P5 final `published SURF` remains explicitly distinct from original raw SMERGE parity.
- Run existing #184 `s3_five_source_preflight` to independently check true produced on-disk `TERREL/LU/GEO/UP/SURF`, their station manifests, single B0 SHA and actual hours. This is **only source provenance join** and must not be called G19 PASS.
- Upload only bounded JSON reports. Keep original NOAA raw bytes, vendor sources, geographic rasters and model binary files off GitHub Actions artifact release.

## Strict exit and blockers

CI on this exact PR head must complete all authentic January/June P1–P3 original comparators plus **actual** June raw NOAA source check, P4/P5 producers and five-source SHA join. If a 2022 archived original source is unavailable or the real P4/P5 selectors reject candidates/inputs, **report precise true blocker and keep Draft**; do not weaken thresholds or substitute other stations.

Expected success label is `S3_B5_SAME_SITE_REAL_FIVE_PRODUCT_SOURCE_JOIN_PASS_SCOPED_NOT_G19`. Even with success, #42 S3 remains OPEN: still needs `met.inp` from exact selected stations and real G19 source-only parser plus second-configuration verification. Original P4/P5 numerical equivalence under this grid is separately scoped; P6 45-field numerical wind, P7, precipitation, capacity, Docker remain deferred.
