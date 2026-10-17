# P1 / P2 Hefei 100 m minimal reconstruction — final scoped decision
Date: 2026-10-10. Decision owner: study user. Reference baseline `60b7b1d93866fff772926b6ac32dc0af7235552b`. P1/P2 remain separate independent Draft PRs #4 and #3, not merged. Original Fortran and control files remain read-only.

## Scientific scope and exit rules

Research application is the Hefei 5 km × 5 km, 50 × 50, 100 m grid; UTM zone 50N / WGS84; SRTM cropped north-up 90 × 77 geographic GeoTIFF, `GENERIC.LANDUSE 1.0` 57,600 samples, 38 categories with `DNZGEN=ESR-S`. The user explicitly **chooses minimal reconstruction**, not full cross-model and legacy-input-option coverage. Below unsupported options are tracked for transparency, **not required for this study**. Do not implement them without a changed scientific requirement. Real outputs must remain distinguishable from synthetic QA. Any unsupported control enabled in the minimal C++ path must be rejected, not silently ignored.

Definitions: `PASS_SCOPED_NUMERIC` is original Fortran vs independent C++ in-grid science fields. It is **not** equivalent to a byte-identical `TERREL.DAT`/`LU.DAT` writer, downstream P3 successful ingestion, or full-program parity.

## P1 TERREL 7.0.0 L141010

Original reference: `engine/vendor/src/TERREL_v7.0.0_L141010/terrel.for`, `terrel.inp` and `COORDLIB.FOR`.
Modern implementation: Draft [PR #4](https://github.com/RRain001/CTEAS/pull/4) head `6bcfc6024be2d010cd025491853b0bcb292e6127`, scoped standalone C++20 `native_cpp/src/geo/terrain_grid.cpp`. Evidence [CI PASS](https://github.com/RRain001/CTEAS/actions/runs/38044005756) and `P1_TERREL_100M_SCOPED_AUDIT.md` in P1 PR. Verified raw Terra output SHA-256 `d74a5a1045ea4cf25e120099196a3962ab012aaebdf37354ec8264fad0e27678`.

Supported study path: WGS84 GeoTIFF, real*4-aware latlon→UTM50N, `LOADTIFF → SAVEELEV → CELLIND → CELLDAT → HEIGHTS` averaging, 2,500 cell hits and mean elevations, explicit missing-mask, fail-closed source NoData. Original and C++ accepted exactly 3,456 pixels; 2,500 / 2,500 cell hit counts exactly matched, all 2,500 formatted heights matched; raw unformatted `TERREL.SAV` unrounded means maximum absolute difference `1.271333339047942e-6 m` (strict threshold `1e-5 m`).

| Original optional feature excluded | Original routine / relevant control | Why outside the Hefei minimal path |
|---|---|---|
| Fill void model cells from surrounding DEM | `CELLFILL`, `INTERP2D`; `! LVOIDFIL !`, `! CELLRADKM !` in `terrel.inp` | Input coverage 2,500 / 2,500; no gaps to fill. |
| Replace terrain data void/noise values by land/sea type | `SAVEELEV`, `HEIGHTS`; `! INOISEREP !`, `! ZNOISE !`, `! ITERREP !`, `! TERDEF !` | No source NoData, source-fail-closed; water/land filters off in tested case. |
| Shoreline classification and BLN/GSHHS polygons | `COASTEXT`, `COASTRD`, `IPTYPE`; `! LCOAST !`, `! LBLNREAD !` | Inland Hefei selected model grid, no sea/shore process required. |
| Peak-elevation receptor / maximum-gridded heights | `SAVEELEV`, `CELLIND`, `CELLDAT`, `HEIGHTS`; `! IMODEL !` (ISC Cartesian/Polar alternatives), `LPEAK` internal; `! LXY !`, `! LINTXY !`, `! XYRADKM !`, `! NXYCOL !` | CALMET Cartesian grid is cell-mean height; no ISC peak-grid or discrete receptor terrain queries. |
| Polar grid and gap interpolation | `CELLIND`, `FILLANG`; `! IGRID !`, `! IPROC !`, `! NRING !`, `! NRAYS !` | `IGRID=1`, rectangular Cartesian only. |
| Legacy and alternative source DEM databases / coordinate sheet approximation | `LOADOTHER`, `LOADGNR`, `LOADSRTM`, `SETGLOB`, `LOADDMDF`; `! MSHEET !`, database-type tags in input Group 0 | Only user-supplied WGS84 GeoTIFF is needed. |
| Multi-source continuations / extended cross-model output modes | `CELLIN`, `CELLOUT`, `MODOUT`; previous .SAV continuation controls, `! IMODEL !` | Single input tile / CALMET model format sufficient. |
| Standalone byte-compatible `TERREL.DAT` writer and P3 ingestion | `MODOUT`, `WRTHEAD`, `! IMODEL !` | **Integration work still required**, not a feature intentionally discarded. This is a remaining P3-dependent exit gate. |

## P2 CTGPROC 7.0.0 L150211

Original reference: `engine/vendor/src/CTGPROC_v7.0.0_L150211/ctgproc.for`, `ctgproc.inp`, `COORDLIB.FOR`.
Modern implementation: Draft [PR #3](https://github.com/RRain001/CTEAS/pull/3) head `c35edb88ce7182382f4467f21feac135864943e5`; `native_cpp/src/geo/landuse_fraction.cpp`; evidence [CI PASS](https://github.com/RRain001/CTEAS/actions/runs/38044445479), `P2_HETEROGENEOUS_100M_AUDIT.md` in P2 PR.

Supported study path: input parser for `GENERIC.LANDUSE 1.0`, `ESR-S` datum, original implicit `REAL*4` input lat/lon and `COORDLIB::XMULTO=0.001` unit conversion, 50×50 category fraction computation, 38 categories, explicit missing handling. Original/C++ accepted 10,011 samples. Real Hefei 95,000 fraction fields exactly matched; independent synthetic heterogeneous GEN reference (2,500 mixed-class cells with all 38 categories) passed all 95,000 fields at the predeclared LU.DAT F8.3 precision tolerance 0.0005, max error 0.000333333333; no missing-cell differences.

| Original optional feature excluded | Original routine / control in `ctgproc.inp` | Why outside the Hefei minimal path |
|---|---|---|
| Other input LULC databases/datum conventions | data-type records Group 0; `! DCTG !`, `! DUSGSLA !`, `! DNLCD !`, `! DGLC2K !`, `! DUMDGLC !`, `! DMODIS !` | `GEN` + `DNZGEN=ESR-S` source is pinned; no alternate landuse supplied. |
| Coastal reassignment and marsh filling | `COASTEXT`, `COASTRD`; `! LCOAST !`, `! LBLNREAD !`, `! LMARSWAP !`, `! LMARFILL !`, `! IOCEAN !` | Inland model grid, no coastline data processing needed. |
| Snow-related land-use alterations | snow processing; `! LSNOW !` | Frozen user case has no snow landuse processing path. |
| Alternative grid mesh selection / categorical diagnostic | `! MESHCTG !`, `! MESHGLAZ !`, `! LQACELL !`, `! ITHRESH !` | Single prescribed 100 m grid; original control-specific tuning not necessary. |
| Multi-file staged aggregation and finalization | `! LFINAL !`, `! LPREV !` and saved intermediate files | Single complete GEN input, no continuation. |
| Other datum/projections/zones and entire original binary LU output option matrix | `! DATUM !`, `! IUTMZN !`, `! NX !`, `! NY !`, `! DGRIDKM !` | Only scoped UTM50N/WGS84 50×50 0.1 km. |
| Standalone byte-compatible `LU.DAT` writer and P3 ingestion | Original `LU.DAT` writer / Group 0 `! LUDAT !` | **Integration work still required**, not optional science functionality. |

## Engineering decisions and next gate

- The P1 and P2 original Fortran files `terrel.dat` and `lu.dat` are already reproducibly captured by `native_cpp/reference/capture_p1_p2.py` using original controls on GitHub-hosted Ubuntu; reference artifacts expire after 7 days unless exported. A permanent evidence ZIP was created for the user earlier in the conversation.
- Do not require unsupported feature parity as a blocker to P3. P3 minimal path can initially ingest **original** `TERREL.DAT` and `LU.DAT` and compare independently against original MAKEGEO, avoiding fabricated P1/P2 integration claims.
- To declare a **fully modern P1→P2→P3** pipeline, implement or adapt the checked, documented, full legacy output contracts and rerun downstream reference comparisons. Never claim this gate from field-only parity.
- No edits to common foundation `60b7b1d`, original `engine/vendor/src`, or independent P4/P5 worktrees / branches. No main merge or force-push.
