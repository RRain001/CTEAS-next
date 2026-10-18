# #54 D4 evidence review and scoped P1 handoff to #46

Date: 2026-10-19. This report is a **review record**, not proof that all
provenance fields or all original TERREL branches have been authenticated.
Numerical evidence and independent source authorization are separate gates.

## 1. Authentic original-vs-native numerical replays

Immutable native fix: [PR #96](https://github.com/RRain001/CTEAS-next/pull/96),
`main@d9d695f618668f9783ee5d75c6e7e509c74bebe9`.
Original: `RRain001/CTEAS@dfad99a78ed84d655e21411c9d25eb0d2583bf13`,
untouched TERREL 7.0.0 L141010.

| Independent real route | Owner-triggered actual original Actions | Original/native accepted | Wrong model-cell hits | Bad raw means | Bad F8.1 heights |
|---|---|---:|---:|---:|---:|
| A user two-tile 3 arc-second SRTM | [#39175533425](https://github.com/RRain001/CTEAS-next/actions/runs/39175533425) SUCCESS | 3429 / 3429 | 0 | 0 | 0 |
| B OpenTopography SRTMGL1 1 arc-second | [#39175533591](https://github.com/RRain001/CTEAS-next/actions/runs/39175533591) SUCCESS | 30893 / 30893 | 0 | 0 | 0 |

Maximum absolute unrounded Fortran-REAL4 vs native mean errors:
A `2.542666678e-6 m`; B `3.560333340e-6 m`, both below
the **unchanged** `1.0e-5 m` threshold.
Output DAT F8.1 bound: `0.0500001 m`. Exact per-cell integer hits and
empty masks; no terrain source, sampling method, reference control,
CELLIND or tolerance change.

Losslessly re-encoded **identical selected TIFF used for BOTH genuine
original and native** in each replay:
- A: `2120a3be8591384b34c298f3466a3afd21d037e9cd794e507c0bea701e6baa4b`
- B: `41e628cc6ab49cf37a1d8886942d9aa5b7ba0231055d18d67b0185ac32284ad4`

These prove **scoped numerical equivalence for those exact two rasters
and selected original options**, not replacement of all TERREL modes.

## 2. Historic frozen Hefei regression

Original historical 90 x 77 (6,930 source pixels), 50 x 50 @ 100m
UTM50N, frozen source SHA:
`c4211914fce527d2ad41ecac1e668d7faa2904bbbfd9135868ee83ef0d32123f`.
Original TERREL DAT SHA:
`d74a5a1045ea4cf25e120099196a3962ab012aaebdf37354ec8264fad0e27678`;
SAV SHA:
`5b09c27974eb5e77e3a0fc2126836e0c46f57a3558da5e1083930bcb6267cd74`.
Historical acceptance: exactly 3,456 accepted pixels; all 2,500 grid
cells match; source CTEAS original audited
[report](https://github.com/RRain001/CTEAS/blob/dfad99a78ed84d655e21411c9d25eb0d2583bf13/docs/reconstruction_cpp/P1_TERREL_100M_SCOPED_AUDIT.md).

The new independent manual-only
`.github/workflows/issue54-hefei-frozen-manual.yml` reruns the
original TERREL reference capture on the exact old cropped TIFF and
verifies original DAT/SAV SHA. **Important grid-definition distinction**:
the 2026-10-10 generator uses center-derived unrounded origins
`510.8846439571 / 3531.2689269678 km`, whereas the current approved
#42 B-0 case contract requires **three-decimal origins**
`510.885 / 3531.269 km`. Directly comparing old raw-origin original
cell bins to canonical-origin C++ is invalid (genuine initial history
Run #39177414771 found 20 mismatches, despite identical 3,456 total
hits). After independently attesting the true historical original
DAT/SAV hashes, rerun **the original TERREL executable** with the same
canonical three-decimal grid as current native and compare strict
integer/REAL4/F8.1 tolerances. **Mark PASS only after an actual
main Actions result; do not re-label old-source SHA as the new-grid
reference SHA or infer a numerical pass from D2/D3.**

## 3. Source product / datum / rights audit

| Route | What is actually evidenced | What is not proved by TIFF pixels or filename |
|---|---|---|
| A owner-provided 3-arcsec | User's actual 90m TIFF bytes, geographic WGS84 Int16 transform, 2-tile source adaptation and real same-TIFF parity | `CGIAR-CSI-SRTM-v4.1` **is a declared identity**, not verified chain-of-custody of this user's particular TIFF; no documented proof of redistribution permission |
| B OpenTopography 1-arcsec | Official provider's actual SRTMGL1 route, real downloaded file, selected bytes, WGS84 spatial coverage and numeric parity | The TIFF CRS tag alone does not authenticate the specific **vertical** reference; provider product claims require identity trail; does not demonstrate unrestricted redistribution |

**Provider-level sources, not pixel-level proof**:
- [CGIAR SRTM 90m V4.1](https://csidotinfo.wordpress.com/data/srtm-90m-digital-elevation-database-v4-1/):
  version 4 is void-filled with auxiliary data, 3 arc-second,
  horizontal WGS84. Terms prohibit commercial resale or redistribution
  without explicit permission and request acknowledgment. Do not call a
  filename-based user copy independently authenticated or publish tiles.
- [CGIAR data terms](https://bigdata.cgiar.org/srtm-90m-digital-elevation-database/):
  original NASA raster was postprocessed by CGIAR to fill voids.
- [OpenTopography ordinary SRTM GL1 product](https://portal.opentopography.org/raster?jobId=rt1785519752511):
  horizontal WGS84, nominal 30m, vertical tied to EGM1996 / EPSG:5773.
  The **separately named ellipsoidal SRTM GL1 product** is a different
  vertical option and is NOT the requested `demtype=SRTMGL1`.
  Product documentation supports an **expected** EGM96 orthometric
  elevation reference; it is not an independent per-file vertical datum
  authentication of this delivered TIFF.

The real run metadata truthfully reports
`source_product_version_authenticated=false` and
`height_vertical_datum_authenticated=false`. Until independently
attested, retain `SOURCE_PROVENANCE_REVIEW_REQUIRED` for
cross-product absolute-height interpretations and production P3
admission. **No false pass or conversion to WGS84 ellipsoidal heights.**
Never upload original TIFFs, original vendor sources, binaries, DAT/SAV,
API credentials, private filesystem locations or original controls.

## 4. Actual P1 -> #46 handoff contract (scoped)

Producer: #54, **only** these two source adapters feeding the **same**
`cteas_p1_terrain_case` / `grid_geotiff_terrain_utm` native kernel.

Inputs, checked fail-closed:
- B-0 admitted `case.yaml`, authoritative `grid/grid.cmn`,
  `grid/research_time`, immutable SHA, `IMAP=UTM`,
  `DATUM=WGS-84`, zone 1–60, hemisphere N/S, positive NX/NY/DGRIDKM,
  mandatory 3-decimal `XREFKM/YREFKM` in km.
- #49 `p1_source_manifest.json` with selected raster and SHA, source
  raw metadata, one route; route A user local aligned 3-arcsec mosaic,
  B only cached/downloaded official SRTMGL1 1-arcsec. Neither mixes
  DEM products. Any source NoData or incomplete model cell rejects P1.
- Explicit `source_product` declaration is **NOT** external provenance
  authentication. P1 uses geometry only; release, source and research
  time do not change P1 terrain values.

Outputs under scratch `geo/terrel/p1_native/`:
1. `terrain.csv`: exactly NX*NY rows, header
   `i,j,hits,elevation_m`; 1-based `i,j`; `i` west->east
   fastest, `j` south->north; counts nonnegative and model cells
   must have hits >0 before downstream input; heights metres,
   9-decimal scientific-audit representation of REAL*4 averaging.
2. `p1_native_manifest.json`, existing
   `p1-native-preliminary-v1` schema, includes `route`,
   `product_declaration`, case/grid/time/source TIFF+manifest SHA,
   native binary SHA, zone/hemisphere/grid origin as strings,
   row order, model row count, selected source hit count and CSV SHA.
   **Existing native status is `PRODUCED_UNVERIFIED`**; it does
   not transform itself into `SCIENCE_ACCEPTED` after a separate
   original parity Actions run.
3. Independent evidence in original-science CI (not in producer CSV):
   exact source SHA, original DAT/SAV hashes, original control/exe
   identities and `NUMERIC_PASS_PROVISIONAL` comparison. Record
   distinct A/B evidence and frozen Hefei regression run reference.

#46 owns generic original-compatible `TERREL.DAT` serialization
(`F8.1`, projection/header, north->south, maximum ten elevations per
physical line) and P3 MAKEGEO; **#54 never creates a parallel P3
writer**. It must join P1 native and science evidence by exact
`grid_sha256`, `selected_tif_sha256`, case/route and CSV SHA,
refusing mismatched or missing provenance. #46 additionally needs
#53 accepted P2 provenance; neither #54 nor this report declares
P3 `GEO.DAT` or P1-P7 end-to-end PASS.

## 5. Decision rule

- D2 & D3 `NUMERIC_PASS_PROVISIONAL`: established.
- Historical frozen Hefei PASS: only after actual manual rerun.
- D4 **independent review**: evidence exists for selected numeric
  physics and source-licensing limits; product-specific attribution
  for user-owned 90m files and absolute vertical datum still require
  explicit per-asset attestation for production acceptance.
- Until that source provenance is independently resolved, avoid
  unconditional `SCIENCE_ACCEPTED` and record `D4_SCOPED_NUMERIC_PASS /
  SOURCE_PROVENANCE_REVIEW_REQUIRED`. #46 remains OPEN.
