# P3 MAKEGEO 3.2 L110401 — Hefei 100 m minimal C++20 reconstruction

Date: 2026-10-10. Frozen common parent: `60b7b1d93866fff772926b6ac32dc0af7235552b`. This document pertains solely to [Draft PR #5](https://github.com/RRain001/CTEAS/pull/5), which also carries the committed P1/P2 minimum feature/Fortran-option matrix. P4/P5 remain isolated in independent oh-my-pi agent branches. Original vendor tree untouched.

## Physics and I/O dependency

Original sources:
- `engine/vendor/src/MAKEGEO_V3.2_L110401/makegeo.for` SHA-256 `8c4fb11db36d4b976b54f470b7a06ce4e38ab09e934951b0e2c613bddc34e347`;
- original `makegeo.inp` SHA-256 `14f46700f232f5721d87aa489fda458ad68813cc0f8645c2bbce475872d3a6b7`.
- Input original `TERREL.DAT`: SHA-256 `d74a5a1045ea4cf25e120099196a3962ab012aaebdf37354ec8264fad0e27678`;
- Input original `LU.DAT`: SHA-256 `75720a211126ffc1d5dbd931cb1dfcc4b4c54f0f4b19b0bceeb26487ba75c0ea`.

Case: 50×50 @ 100 m UTM50N WGS84, no snowfall, all 2500 valid terrain and landuse cells, 38 input landuse classes mapped into 14 output categories.

Reference: `native_cpp/reference/capture_p1_p2.py` and `capture_p3_makegeo.py` rebuild and run **untouched** original TERREL 7.0.0, CTGPROC 7.0.0 and MAKEGEO 3.2 in isolated GitHub-hosted runner directories. P3 output `GEO.DAT` v2.1 SHA-256 `d1b8c2a079fcf6dd2f4f353f6fb4b115d34066719c7d384dbcf58dae0089c998`, bytes 161274.

## Scientific kernel

`native_cpp/src/p3_makegeo_cli.cpp` is standalone C++20 with `native_cpp/p3/CMakeLists.txt`, no shared ABI changes.

- Parse and strictly validate original control `! X !` table of **all 38** input categories: roughness `z0`, albedo, Bowen ratio, soil heat flux coefficient, anthropogenic heat flux, LAI and output category map.
- Parse and validate original `LU.DAT 2.1` 38 × 2500 fractions in south-to-north order and `TERREL.DAT 2.0` north-to-south elevations.
- `COMP` algorithm: water classes `IWAT`, `CFRACT=0.5` threshold with +0.0001 original tolerance, select highest eligible input-category fraction, remap via control table `mapcat`.
- `WT`: surface roughness `z0 = exp(sum(f_k * log(z0_k)) / sum(f_k))`; five other non-snow quantities by arithmetic weighted area average. For actual `GEO.DAT` outputs, the fields are: dominant category, elevation, z0, albedo, Bowen ratio, soil heat flux, anthropogenic heat flux and LAI.
- Fail-closed on unexpected CRS/zone/grids/categories, incomplete input rows/headers, `LSNOW`, `LLU2`, `NSPLIT`, uncovered cells and missing terrain. No silently invented physics or water/land corrections.
- Independently write a machine-readable numeric audit CSV and a `GEO.DAT v2.1` no-snow file with the original field order, category list, 10-values-per-record LU rows, north-to-south grids, `F7.2` and `F7.4` format widths; writer uses an identifying C++ provenance comment instead of imitating the original Fortran compiler/source, thus full file SHA differs legitimately.

## Audits and status

- [Original P3 source reference capture](https://github.com/RRain001/CTEAS/actions/runs/38046610229) **PASS** (original MAKEGEO compiled/executed on P1+P2 original reference files).
- [Initial independent P3 C++ science fields](https://github.com/RRain001/CTEAS/actions/runs/38046755786) **PASS**, original-vs-C++ 2,500 category fields + 17,500 float fields, **zero errors above predeclared per-field formatting tolerance**.
- [C++ GEO.DAT output parser and exact displayed-value validation](https://github.com/RRain001/CTEAS/actions/runs/38046904440) **PASS**, 20,000/20,000 formatted displayed values exactly agree with original.
- [Independent mixed-category/water-threshold/area-weighting reference](https://github.com/RRain001/CTEAS/actions/runs/38047003005) **PASS**: `native_cpp/reference/prepare_p3_mixed.py` produces 2,500 deterministic varied 38-category fractions, exercises majority/minority/equal-threshold water allocation, original `COMP` category mapping, original `WT` geometric z0 and arithmetic surface weighting. Original MAKEGEO binary and modern C++ each process the **identical synthetic LU.DAT**; 2,500 categorical and 17,500 numeric science fields are within predeclared Fortran text precisions with zero failures, and their independently written GEO.DAT displayed values have **zero mismatches in all 20,000 fields**. Synthetic `LU.DAT` SHA-256 `4adf1ca69d8337f8b172ff4269ea4866eb6d8c47e621a69d601dfbd7684bcf0d`; original synthetic `GEO.DAT` SHA-256 `015ee8745687d5528ca502542bfddd9f15d1d8e4feaaf8830200e63102790061`. This is numerical-method QA, not true measured Hefei land-cover classification.

## Option/routine exclusions

| Excluded from minimal scope | Original routines | Original control item |
|---|---|---|
| Daily dynamic snow cover and snow-age albedo/roughness | `RDSNHD`, `RDSN`, `WTSW`, `WTSWZ0`, `WTSWALB`, `FILLT`, `FILLS`, `ROLLBK` | `LSNOW`, `IFMTGEO`, `IDATEBEG`, `IDATEEND`, `MSRL`, `HSCL`, `MSAL`, `SDPMIN`, `XS`, `XF` |
| Second low-resolution landuse for missing primary cells | `COMP`, `READHD` | `LLU2`, `LU2DAT` |
| Splitting one category into several categories | `COMP` fractional redistribution block | `NSPLIT`, `CFRACT` is supported, split table only excluded |
| Partial/void LU coverage handling and IMISS fallback | `COMP` | `FLUMIN`, `IMISS` — the study requires all cells valid; these options are enforced as guards, fallback not used |
| Optional QA graphics, plot colors, Surfer specific spatial format | `COMP`, GRD output routines | `LUGRD`, `TEGRD`, `IXQA`, `IYQA` |
| Other geo projections, source LU resolutions and time-varying products | `READHD`, `WRTHEAD`, `COMP` | `PMAP`, `DATUM`, `IUTMZN`, `IFMTGEO` |
| Terrain-off simulation option | `COMP` | `LTERR=F` — the study intentionally requires real DEM elevations |

## Fortran routine and control-item traceability (reviewed for minimum scope)

The table above records deliberately **unimplemented** optional features. Below are the original `makegeo.for` source anchors so future maintainers can restore one only when the scientific case changes. Line numbers apply to `MAKEGEO_V3.2_L110401/makegeo.for` at its pinned SHA; source and controls are never edited.

| What the original does | Exact original code location | Exact input control / subsection | Minimal-rebuild decision |
|---|---|---|---|
| Parse/check input LU.DAT 2.1 and TERREL.DAT 2.0, source classes and georeference | `READHD` near L1433; `COMP` near L1994 | Group 0 `LUDAT`, `TERRDAT`; Group 2 `PMAP`, `IUTMZN`, `UTMHEM`, `DATUM`, `NX`, `NY`, `DGRIDKM` | **Implemented**: two original file formats, one exact CRS/grid |
| Determine dominant category, water threshold and map input→output category | `COMP` near L2153–2276 | Group 3 `NOUTCAT`, `OUTCAT`, `IWAT1`, `IWAT2`; Group 4 `NUMWAT`, `IWAT`, `CFRACT`, `X` category map | **Implemented**; genuine water-threshold cases separately tested |
| Weight six surface properties, with logarithmic weight only for z0 | `COMP` L2460–2481; `WT` L2703–2795 | Group 4b `X` (all 38 input category properties) | **Implemented**; real + 38-class synthetic field compare |
| Write no-snow GEO.DAT 2.1 | `WRTHEAD` L3794–3888; `COMP` L2514–2556; `WRRDAT` L3327–3386; `WREDAT` L3388–3449 | Group 0 `GEODAT`; Group 1 `LSNOW=F`, `LTERR=T` | **Implemented**, but only the supported study mode; 20,000 formatted field values exact |
| Dynamic daily snow mapping / time-varying GEO.DAT | `RDSNHD` L3978; `RDSN` L4091; `WTSW` L2799; `WTSWZ0` L2962; `WTSWALB` L3116; `FILLS` L4300; `FILLT` L4367; `ROLLBK` L4512 | `LSNOW`, `SNOWDAT`, `IFMTGEO`, `IDATEBEG`, `IDATEEND`, `MSRL`, `HSCL`, `MSAL`, `SDPMIN`; snow `XS`, `XF` input groups | **Omitted intentionally**: study control `LSNOW=F` |
| Secondary land use supplement when LU has empty cells | `READHD` L1433 and `COMP` L2011–2035 | `LLU2`, `LU2DAT` | **Omitted intentionally**: case has full LU coverage |
| Split-category area reallocation | `COMP` L2037–2054 | `NSPLIT`, Group 4f split instructions | **Omitted intentionally**: `NSPLIT=0` |
| Missing fractional LU replacement and sparse-coverage QA | `COMP` L2056–2065 and L2153–2173 and L2323–2340 | `FLUMIN`, `IMISS`; `LU2DAT` only when `LLU2=T` | **Omitted fallback**, enforcing full coverage instead |
| Surfer QA plot grids and extra output artefacts | `COMP` L2344–2460 and `OUT` L3451 | `LUGRD`, `TEGRD`, `IXQA`, `IYQA` | **Omitted intentionally**: no effect on CALMET physics |
| Terrain-free GEO output | `COMP` L1964–1980, L2531–2535 | `LTERR=F` | **Not supported**: case requires terrain |

### Submission and integration boundaries

1. The study-specific **P3 numerical reconstruction is accepted for submission/review**: no-snow, single original LU/TERR input pair, 50×50 @ 100 m, 38 input→14 output category mapping, all eight field types and legacy text GEO.DAT numeric representation.
2. `20,000/20,000` agreement means the **parsed, formatted science fields** coincide. It is **not** a claim of byte-identical complete files (the C++ provenance comment differs), cross-platform identity, or correctness of unselected original options.
3. The present P3 run deliberately consumes **original Fortran** `LU.DAT` and `TERREL.DAT`. P1/P2 C++ standalone legacy writers, end-to-end C++ P1→P2→P3 and original CALMET ingestion remain follow-on integration checks. They do **not** undermine the measured P3 kernel parity, but must not be represented as already complete.
4. `P3_SUBMISSION_STATUS = READY_FOR_INDEPENDENT_REVIEW`; `P3_SCIENCE_STATUS = PASS_REFERENCE_SCOPED`; `FULL_LEGACY_FEATURE_PARITY = NOT_TARGETED`; `CROSS_STAGE_MODERN_INTEGRATION = UNVERIFIED`. Submission here means code committed, pushed and opened for review. **It does not imply main-branch merge or final whole-chain validation.** Keep P4/P5 and shared baseline untouched.

Classification: **PASS_REFERENCE_SCOPED_P3_HEFEI_NO_SNOW_100M**, **READY_FOR_INDEPENDENT_REVIEW**. Neither full P3 options nor end-to-end modern P1/P2→P3 integration / original CALMET downstream ingestion is claimed.

