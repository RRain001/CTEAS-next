# Issue #46 — D1-C B-0 same-case native P1/P2 → MAKEGEO handoff

Date: 2026-10-20. Baseline `main@ee5dff43fe47545b3728054999a20358e0e7c99d`; follows merged PR #174 (P3 D1-B dynamic DAT format software).

## Unambiguous source/interface intent

- Accepts an immutable independent B-0 `case.yaml` + `grid/grid.cmn` + `grid/research_time`; it does not infer a case from a path or copy any frozen reference output.
- **P1 is really executed**: run the existing compiled `cteas_p1_terrain_case` directly on a caller-supplied and SHA-verified genuine WGS84 geographic DEM TIFF. The native P1 emitter writes `terrain.csv` for precisely the admitted projection, 3-decimal origin, dimensions and resolution; no alternate terrain interpolation or fabricated uncovered cells.
- **P2 is not reinvented**: consume the existing `LU.DAT` written by either `native_cpp.orchestration.p2a_case_producer` (GLCC historical) or `p2c_case_producer` (30 m modern original-style subpoint). Verify exact attestation case/grid/time SHA, P2 method ID, UTM, dimensions and actual LU bytes against its hash. P2-B EXACT_AREA is unsupported.
- Keep only original selected MAKEGEO 38→14 physical control template. Replace its seven spatial fields, leaving all other options, class mapping, thresholds and scalar formulas unchanged. Bind template SHA in evidence. Feed genuinely generated P1 `terrain.csv` through PR #174's dynamic original-format `TERREL.DAT` writer; P2's existing `LU.DAT` is passed through unchanged. Execute the existing compiled `cteas_p3_makegeo` (not another kernel).
- The native P3 parser validates identical CRS, origins, NX/NY, spacing, original LU class order, north-to-south TERREL, south-to-north LU, valid numeric cells and 38→14 controls. Stage only fresh `geo/makegeo/p3_case` and `evidence/p3.json`. Lock output `terrain.csv/terrel.dat/makegeo.inp/p3.csv/geo.dat` SHA, source TIFF, producer binaries, upstream P2 proof and all three case authority SHA. **No overwrites or `project/current` fallback.**

## Exact operator interface

```sh
# Requires an already produced and attested P2-A or P2-C LU.DAT
python3 -m native_cpp.orchestration.p3_case_handoff \
  --case-yaml /independent/my_site/case.yaml \
  --p1-tif /authorized/my_srtm_data.tif \
  --p1-tif-sha256 <actual_sha256> \
  --p1-bin /native/cteas_p1_terrain_case \
  --dat-bin /p3/cteas_p12_to_p3_dat \
  --p3-bin /p3/cteas_p3_makegeo \
  --p2-kind C
```

For P2-A, set `--p2-kind A`. Selected original physical control template is fixed by the source code to `project/cases/hefei5km_2022_reference_case_20261011/geo/makegeo/makegeo.inp`, no operator-selected alternate 38→14 physics.

## Test and scientific boundary

Dedicated CI compiles actual P1, P2-C, CSV→DAT adapter and P3 C++ binaries, generates a fresh synthetic **geographic WGS84 DEM raster** and a separate synthetic **native-UTM 30 m land-cover raster** over the *same* distinct 4×3 case, runs P2-C and P1/P3 through both real C++ executables, checks source/output hashes, GEO shape and actual P3 category, refuses mutated raster SHA, edited time contract and tampered P2 LU bytes. This is much stronger than a mock-only handoff but **all source pixels are synthetic**; it is intentionally `D1C_SAME_CASE_SOFTWARE_PASS`, not real DEM/30m GLC scientific acceptance.

**D2 still open:** stage genuinely sourced and provenance-attested non-Hefei DEM + P2-A/C GLCC/GLC input for the *same* new site; run real native production and preserve source products, projection, time, land/sea, cell coverage, 38 classes, SHA and original type across the chain. Availability of a real DEM/selected site must be separately verified; do not use frozen Hefei 5km original TERREL as a stand-in.

**D3 still open:** independently run original Fortran MAKEGEO under identical non-Hefei input and unchanged physical controls, verify original/native GEO 8 values per cell, water/mixed surface rules, precision, missing thresholds and category ties, with scientific artifact. Only then can D4 admit new-site GEO into #42 S3. No original CALMET/CALPUFF P6/P7 inference.

**Scope limitations:** P1 NoData handling requires fully valid geographic TIFF; P3 bounded 500×500 and supported selected physical branch only. Larger domains are S5 #161. P2-A and P2-C may have distinct source years; science does not treat them as interchangeable. Docker AMD64/ARM64 packaging is postponed until all other development Issues close, per user instruction.

**Status before CI:** `D1C_NATIVE_B0_SOFTWARE=CANDIDATE`, `D2_REAL_SITE_SCIENCE=NOT_RUN`, `D3_ORIGINAL_NON_HEFEI=NOT_RUN`, `DOCKER=DEFERRED`.
