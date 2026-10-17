# Hefei 2022: first real numerical reference case

Status: CASE_SPEC_LOCKED / FORTRAN_CONTROLS_CAPTURED / REFERENCE_CAPTURED — artifact register with per-artifact, per-deck and per-vendor-source SHA-256: `docs/reconstruction_cpp/HEFEI_2022_REFERENCE_CAPTURE.md`, reproduced by `scripts/capture_hefei_2022_reference_case.py` (known caveats are listed in that register).
Source of user requirements: `testcase.md` @ `66e30ffb1ff4638a97af8a060748ce30b7578350`; crop provenance: `calpuff_terrain_and_landuse_data_crop/hefei_5km/crop_info.json`.

| Property | Intent, not assumed legacy control |
|---|---|
| Stack | 31.939774444°N, 117.141610855°E, physical height 70.8 m, diameter 1.6 m, exit 25°C and 17.26 m/s |
| Emissions | HTO 2.63e13 Bq/year; HT 0 Bq/year; release window/hourly rate TBD |
| Domain | 5,000 m x 5,000 m centered on stack, 100 m nominal cell side, 50x50 **geometrical cells** |
| Crop | EPSG:32650 UTM50N centered at (513.3846439571, 3533.7689269678) km; ±3.5 km extent (1 km margin) |
| Vertical | NZ=9, ZFACE=[0,20,40,80,160,320,640,1200,2000,3000] m; datum and original height representation TBD |
| Time labels | 2022-01-01 00:00:00 through 2022-01-06 23:00:00; hourly label count=144, local/UTC and interval semantics TBD |
| Terrain | WGS84 GeoTIFF 90x77, 3 arcseconds, NoData=-32768 (raw DEM); independent original output mask TBD |
| Landuse | GEN point format with 57600 samples at 50 m; 38 USGS-92 categories, ESR-S datum; GEN mode, not GLAZAS |

Absolute case geometry in candidate projected metres (NOT asserted as legacy control): x lower face=(513384.6439571 - 2500) m, y lower face=(3533768.9269678 - 2500) m. Fortran control/coordinate rounding and cell-center convention can differ. The stack at exact square center lies on the boundary between the four central cells for even NX/NY, not at a unique cell center.

Required reference evidence per P: `engine/vendor/src/{TERREL...,CTGPROC...,MAKEGEO...,READ62...,SMERGE...,CALMET...,CALPUFF...}`; record versioned source blob hashes, control-file hashes, input-data identities, stdout+stderr, exact output artifacts, field decoding and comparison data. Missing original Fortran run or real-case data = BLOCKED, not PASS.

Every comparison must report data CRS/datum, nx/ny/nz, origin, coordinate conventions, time semantics, missing/value numerators and denominators, error norms (MAE/RMSE/max), matching fields and options, compiler flags and platform. Prior 50m crop/full-data findings may guide tests but do not certify 100m.
