# Issue #53 — D2 native C++ GLC raw area: scoped implementation

This PR implements **only D2**, the GLC_FCS30D 2022 30 m off-line input and raw category area fractions. It does not write crosswalk USGS-92 fractions, LU.DAT, P3 GEO.DAT, or any P6/P7 results. Issue #53 stays open for D1 and D3.

Native CLI:
```sh
cteas_p2_glc_raw TIFF NEW_OUT_DIR EXPECTED_SHA256 EPSG XREFKM YREFKM DGRIDKM NX NY
```
The authoritative case adapter in #42 must supply the validated, immutable grid and case identity. This CLI intentionally does **not** invent another shared case.yaml/grid.cmn parser. Its input is a single actual locally present GeoTIFF and a 64-digit SHA256 string; no API, GEE, credentials, or downloads are involved. It enforces exactly three decimal km digits for origin and a new output directory. The preexisting frozen Hefei P2 GEN CLI is unchanged.

GDAL source checks: exactly one UInt8 categorical band; a north-up and unrotated affine with 30 m resolution; CRS must equal the caller's EPSG:32601–32660 or 32701–32760 (WGS84 UTM); explicit mask/NoData and 35 legal source codes; and complete real raster coverage of every model grid cell. Unknown or missing pixels cause a hard error. Rotated/different CRS inputs are deliberately rejected pending separately reviewed projected-polygon support.

The kernel uses **exact axis-aligned rectangle intersections in the common UTM plane**, rather than counts of 30 m pixel centres or bilinear interpolation. It preserves raw GLC35 areas in square metres and fractions separately, including pixels along grid edges and mixed water/land cells. For each output cell: sum of 35 class areas = valid covered area = cell area, otherwise fail closed. GLC class 52 is never silently identified with USGS-92 class 52.

Output files: `p2_raw_fractions.csv`, `p2_raw_class_area_m2.csv`, and `p2_manifest.json`. Evidence is `PRODUCED_UNVERIFIED`, crosswalk state `P2_MAPPING_REVIEW_REQUIRED`, P3 `NOT_RUN`. The #42 upstream joint workflow must later bind case/config/grid/time/code and outputs with independent SHA evidence before G19 handoff. These raw output files are not substitute science approval.

The bounded GitHub Actions PR check compiles with -Werror, executes synthetic 30→100 m non-integer tests with known 400/9200/400 m² split, rejects masked/NoData, invalid category, wrong EPSG, rotated raster and missing coverage, reruns the existing GEN test, verifies the real 6168-byte 2022 Hefei GeoTIFF by SHA256 and processes all 2500 grid cells. No full-size 156 MB GLCC Git LFS or original CALMET/CTGPROC science is automatically executed. **Full scientific runs remain manual only**, by explicit `workflow_dispatch`.

Open blockers for this issue: D1 genuine Eurasia GLCC .img direct native reader and same-source original equivalence; complete GLC35→USGS38 class science review (especially codes 182, 183, 190, 210 and all uncertain classes); D3 approved LU.DAT serialization and independently verified #46 handoff. A green D2 Actions check cannot upgrade mapping or original-physics acceptance.
