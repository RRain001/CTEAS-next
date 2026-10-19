# Issue #53 — P2-B native C++ GLC35→USGS38 via GSHHS Full L1 (2026-10-19)

## Source of truth and approval
- User-fixed non-water 34-class GLC mapping from [ISSUE53_GLC35_USGS38_USER_SELECTED_20261019.json](ISSUE53_GLC35_USGS38_USER_SELECTED_20261019.json), with 183/184 both USGS77.
- GLC210 **valid** pixels receive USGS52 if inside the GSHHS Full L1 land polygon, USGS55 if seaward. Sea includes bays and estuaries: no GLC210→54. On coastline overlap split original 30m pixel *area* using actual geometry intersection. Preserve 35-class raw diagnostics and all 38-class totals.
- The user excluded Antarctica. WDBII river/border lines not required. Full `f` is selected for scientific source; do not silently substitute high `h`, lower levels or 30m rasterized coastlines.

## New native producer (NOT yet science-qualified)
`native_cpp/src/p2_glc_lu_dat_cli.cpp` builds as `cteas_p2_glc_lu_dat`, separate from legacy P2-A `cteas_p2_glcc_lu_dat`. It invokes the already-merged same-UTM GDAL D2 **exact 30m pixel/model-cell rectangular area overlap** and adds GSHHS vector polygons; this does not alter P2-A 1km original GLAZAS point sampling or Issue #46 P3 code.

CLI:
```bash
cmake -S native_cpp -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --target cteas_p2_glc_lu_dat
build/cteas_p2_glc_lu_dat \
  data/landcover/glc_fcs30d/v1_2022/hefei/hefei_2022_30m.tif \
  340d224d961c88637363be9616302bdf6b955b4921144edc814b875ef9798473 \
  /EXTRACTED_GSHHS_F_SHAPEFILES/GSHHS_f_L1.shp \
  "$(sha256sum /EXTRACTED_GSHHS_F_SHAPEFILES/GSHHS_f_L1.shp | cut -d' ' -f1)" \
  docs/plans/ISSUE53_GLC35_USGS38_USER_SELECTED_20261019.json \
  "$(sha256sum docs/plans/ISSUE53_GLC35_USGS38_USER_SELECTED_20261019.json | cut -d' ' -f1)" \
  /NEW/OUTPUT/DIRECTORY 32650 510.885 3531.269 0.100 50 50
```

- Inputs: authenticated non-symlink TIFF, exact named `GSHHS_f_L1.shp` + adjacent `.shx`, `.dbf`, `.prj`, and frozen SHA-bound user mapping JSON.
- The standalone CLI hashes TIFF, `.shp`, policy bytes; **it does not itself prove the complete GSHHG release ZIP SHA** or its sidecars. Source-level trust requires the additional offline workflow that checks the official release ZIP SHA and extracts the four correlated sidecars.
- GSHHS L1 must be WGS84 *polygon* layer; case grid only WGS84 UTM N/S, same projected GeoTIFF (unrotated, 30m), region up to 50km in each side. The anti-meridian / polar edge cases and Antarctica fail closed; a larger curvilinear footprint needs a separately audited coastal region window rather than unvalidated corner-only bounding selection.
- For every cell: `Σ_{k∈GLC35}A_k = Σ_{j∈USGS38}A_j = A_cell`, and `A_GLC210=A_USGS52+A_USGS55`. Invalid source 0/250, incomplete raster, mismatched SHA, policy drift, CRS mismatch or invalid polygon fail closed. No fabricated seawater fill.
- Output `lu.dat` follows P2-A's original-compatible LU.DAT v2.1 header, fixed category order, south-up rows, 3-decimal class fractions; manifest `p2_b_d3_manifest.json` includes source/policy/L1 SHA and water area statistics, explicitly **`PRODUCED_UNVERIFIED`**, P3 `NOT_RUN` and original physics parity `NOT_RUN`.

## Executable acceptance evidence
- Lightweight PR workflow `.github/workflows/s2g1bb-issue53-p2b-native-gshhs-d3.yml` compiles strict C++ with GDAL/GEOS; synthetic WGS84 coastline tests include (i) one 100m cell and 30m source pixels with partial land/sea overlap, (ii) all land / all sea, (iii) both user 183/184→77 overrides, (iv) SHA and mapping tamper, (v) NoData fails closed. These are **software tests only** and do not download genuine GSHHG.
- **Manual-only** `.github/workflows/s2g1bb-issue53-p2b-gshhg-full-real-source.yml` downloads the authentic GMT 2.3.7 archive from `https://github.com/GenericMappingTools/gshhg-gmt/releases/download/2.3.7/gshhg-shp-2.3.7.zip` and verifies its published SHA256 `8dbbe7e071e77e9e75f2d639239099ebca8d5c16d6a07df8169729d49f15cf41` before extracting **GSHHS_shp/f/L1 only** and processing real 2022 Hefei GLC. The archive is ~142 MB according to available public mirror listings, so use artifact-backed cache if repetition is needed; it is **never checked into the repo**.
- The manual run produces a provenance/engineering acceptance report and 2500-cell LU.DAT artifact; it does **not** mark original MAKEGEO science PASS or coastal real-source validation COMPLETE.

## Remaining science blockers for #53
1. Genuine GSHHG v2.3.7 Full release ZIP SHA proof and actual Hefei 2022 land-side water output; latest manual Action run/attestation must be linked.
2. Genuine **coastal** 2022 GLC input with fully valid offshore source coverage, Full vs High difference audit, and at least one independent calculation of coastal pixel intersection and source metadata.
3. Original Fortran MAKEGEO 38→14 comparison against same new P2-B LU input, exact P3 surface fields, plus downstream selected CALMET water-category branch. This responsibility belongs to #46, not P2-B duplicate physics.
4. Cross-case generalization, automatic shoreline provider installer/source cache provenance and reproduction across Windows/Linux/macOS as needed; do not declare G5 generic acceptance from only Hefei.

The PR's software CI may be merged after code review with Issue #53 left OPEN and without upgrading science status. Full original science runs remain manual `workflow_dispatch` only.
