# P1 / P2 first executable checkpoint (2026-10-10)

This checkpoint includes actual C++ source, independent compilation targets, unit tests and a read-only production crop ingestion smoke. No existing Python/GUI/Fortran source has been modified.

P1: GDAL-based reading of original 90x77 int16 GeoTIFF and its explicit NoData mask, geographic CRS, transform; strict .bbox parser. Raw raster is **not** TERREL's resampled model grid. No terrain fill/interpolation/projection yet.

P2: strict parsing of `GENERIC.LANDUSE 1.0` records including single-line 38-code class list, `LL`, `DEG`, `ESR-S`; rejects invalid categories, values and trailing data. Cropped file has 57,600 point records; no code converts 50m sampling into 100m cell fractions yet.

Validation: local CMake/CTest may be executed without Linux runner; GitHub Actions CI uses isolated GitHub-hosted ubuntu-latest to compile+read crop (not the private self-hosted runner). The reference original TERREL and CTGPROC execution remains BLOCKED until actual controls and outputs are frozen.

P4 (separate planned workstream): vendor `READ62_v5.661_L110225/READ62.FOR`, `read62.inp`, upper-air source/profile station/time+missing, and original upper-air outputs, with field/error and time-support denominator tests.

P5 (separate planned workstream): vendor `SMERGE_v5.7.0_L121203/SMERGE.FOR`, `smerge.inp`, ISD and surface-source validation, precipitation/time and QC decisions, and original SURF products; no arbitrary fill.

Branching rule: shared interface modifications only on the foundation branch. Implement module code on separate `codex/cteas-p1-...`, `codex/cteas-p2-...`, `codex/cteas-p4-...`, `codex/cteas-p5-...` branches created from one frozen foundation SHA; merge sequentially after independent review. Current P1 and P2 source-input commits are kept separate within the foundation line and are NOT complete program implementation.
