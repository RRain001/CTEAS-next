# #160 C0 — frozen baseline, input contracts and C++ reachability (before cleanup)

Date: 2026-10-20. Freeze revision: `RRain001/CTEAS-next@8e0936dc7a248e1d3992b58bba5908a760f3e9dc`. This is the **pre-#160 code** baseline, not a newly executed scientific run. The PR for C0/C1 is additive; it is not authority to close #160.

## Contract / authoritative decisions

- Historical USGS GLCC (`eausgs2_0la.img`) uses **the existing** `glcc_raw_fractions.cpp` 24-entry mapping and direct-LAEA original P2-A sample trace. Neither its mapping, ingest, nor historical source metadata may be edited as part of #160.
- The *only* modern mapping authority is `docs/plans/ISSUE53_GLC35_USGS38_USER_SELECTED_20261019.json` (Git blob SHA `07b73c6f2adfc993a68eb4fe5033150ec97b9691`; Git blob SHA is **not** the policy's SHA256). Thirty-four fixed classes and valid GLC210 → inland USGS52 / Full L1 seaward USGS55. GLC52 → USGS42; GLC183/184 → USGS77. Keep the policy's `production_authorized=false` untouched. P2-C mapping policy is `P2C_MAPPING_POLICY_USER_APPROVED_FROZEN`, **not** a claim of globally accepted application.
- P2-C 30m methodology is original CTGPROC GLAZAS/LUGRID **point HITS and SVGRID REAL*4 F6.3**, not P2-B `EXACT_AREA_V1` pixel-area intersection. Freeze `MESHGLAZ=10`, source-centered evenly spaced 10×10 subpoints (implementation and independent reference still to be proved on real 30m inputs); input 0/250/NoData must be excluded, never filled with USGS55.
- Exactly two 20×20km 200×200@100m domains. Wolsong: EPSG:32652, xref=533.215km, yref=3942.629km, Full L1, no missing-cell marine fill. Hefei: EPSG:32650, WGS84 (117.141610855°E,31.939774444°N), central coordinate by WGS84/UTM50N, model origin nearest meter after subtracting 10km: **503.385km,3523.769km**; nominal center (513.385km,3533.769km), true projected center approx (513384.644m,3533768.927m): +0.356m/+0.073m grid-center rounding offset. Hefei LCOAST=F, LMARSWAP=F, LMARFILL=F; authentic source water 210 becomes 52, never 55.

## Existing authentic scientific evidence frozen (not rerun in this PR)

| Scope | Original code/input lineage | Existing evidence | Prior accepted result; #160 status |
|---|---|---|---|
| Wolsong historical GLCC, original Fortran vs C++ | original `CTEAS@dfad99a78ed84d655e21411c9d25eb0d2583bf13`, `ctgproc.for` SHA256 `719abbd2327269bb0377208b3a7a0c74000b878efc756686023bbb2ef932f281`; GLCC IMG canonical SHA256 `4f2a1977d141e2040da4d36ec6a4826c5c960c84686eaf10f226f388cb3ab90a`; original coast BLN SHA256 `67da93d441e7defe3eb46627ed9ce896c0a91ffd89fd5e4363d834d8108e11f9` | [original run 39344388008](https://github.com/RRain001/CTEAS-next/actions/runs/39344388008) and [artifact 12229939690](https://github.com/RRain001/CTEAS-next/actions/runs/39344388008/artifacts/12229939690), source as recorded in `ISSUE123_D11_ORIGINAL_SAMPLING_NATIVE_LU_20261020.md`. Also later [run 39346661759](https://github.com/RRain001/CTEAS-next/actions/runs/39346661759) (successful D6B regression at baseline HEAD, **not** proof of new #160 functions) | 1,520,000 integers and F6.3 fields independently zero difference; 40,025 hits, 37,035 nonempty cells, 2,965 Missing: accepted **only** for Wolsong historical source; #160 new code NOT_RUN |
| Wolsong modern 30m `EXACT_AREA_V1` | 2022 GLC_FCS30D TIFF SHA256 `2a1a208c5386735692d788066f730c7391e87f0981e7b9ad099442af2e217711`; GSHHG Full L1 SHP SHA256 `121435427911ea80624802e0f352d777eaf6ba6966ca5f07e687650e95329fd9` | [run 39236968133](https://github.com/RRain001/CTEAS-next/actions/runs/39236968133); [run 39241482533](https://github.com/RRain001/CTEAS-next/actions/runs/39241482533); `ISSUE119_WOLSONG_EXACT_AREA_V1_FREEZE_GATE_20261019.md` | `P2B_EXACT_AREA_V1_FROZEN_PASS_SCOPED_WOLSONG_2022`. Not a #160 30m sampling oracle |
| Hefei historical GLCC 20km LCOAST=F | same canonical original GLCC and Fortran source; new model origin above | Original same-input 40,000-cell integer/F6.3/Missing original-vs-C++ reference | **NOT_RUN at C0** |
| Hefei modern 30m 20km | existing `data/landcover/glc_fcs30d/v1_2022/hefei/hefei_2022_30m.tif` SHA256 `340d224d961c88637363be9616302bdf6b955b4921144edc814b875ef9798473` has only a **5km** case footprint (metadata width=height=172) | `data/landcover/glc_fcs30d/v1_2022/hefei/metadata.json` | **BLOCKED_FULL_20KM_SOURCE_MISSING**. Do not use as full 20km ground truth |
| Wolsong modern 30m 20km sampling | same 2022 TIFF as area path, Full L1 | New per-sample HIT independent oracle and F6.3 still required | **NOT_RUN** |
| Both #160 30m → P3 format-only | `LU.DAT` v2.1/UTM WGS84/38 fixed ordered IDs/200×200/F6.3/Missing | Independent consumer/parser + real outputs | **NOT_RUN**; P3 numerical physics belongs solely to #46 |

**SHA hygiene:** Git blob IDs in this document denote repository object identities. SHA256 values above are copied from the frozen acceptance artifacts and must be independently verified when real-source jobs run. SHA pin is never sufficient by itself to claim actual comparison has run.

## Production + test + public header reachability / cleanup precheck

| Node | Callers / build edge at frozen HEAD | C0 decision |
|---|---|---|
| `src/geo/glcc_raw_fractions.cpp`; `glcc_raw_fractions.hpp` | `cteas_p2_glcc_source` → raw CLI / GEN driver / historical LU writer / original recount → D9/D11 CLIs and tests | **KEEP** historical GLCC ingest+mapping; no P2-C cleanup |
| `src/geo/ctgproc_original_sampling_recount.cpp`; public `ctgproc_original_sampling_recount.hpp` | `cteas_p2_original_sampling_recount` → synthetic recount tests, `cteas_p2_original_coast_hits_wolsong`, `cteas_p2_original_sampling_wolsong` | **KEEP** exact point-classification recount |
| `src/geo/ctgproc_original_bln_pnpoly.cpp`; public header | `cteas_p2_original_bln_pnpoly` → original recount & original IPTYPE/PnPoly CLI / synthetic tests | **KEEP** REAL*4 boundary semantics |
| `src/geo/ctgproc_original_iptype.cpp`; public header | `cteas_p2_original_iptype` → original recount (including `recount_glcc_original_coast`); synthetic original-IPTYPE tests | **ISOLATE candidate** D2 GEOS L1–L4 surrogate; **not deletion-ready** as it remains a live CMake/test/API dependency |
| `ctgproc_original_coast_policy.hpp` | original recount and coast-policy tests | **KEEP** legacy contract; do not remove original non-target options from reference |
| `ctgproc_original_sampling_lu_writer.hpp` | Wolsong D11 producer + LU writer tests | **KEEP** REAL*4 F6.3; any generic extension must preserve Wolsong bytes/format semantics |
| `p2_glc_lu_dat_cli.cpp`, `glc_area_fractions.cpp`, mapping policy JSON | `cteas_p2_glc_lu_dat` `cteas_p2_glc_area`; P2-B source/area tests and GSHHG Full real workflows | **KEEP/PROTECT** all P2-B source and `EXACT_AREA_V1` |
| CMake + Python case/workflow test clients | `native_cpp/CMakeLists.txt`, `native_cpp/tests/p2_original_sampling_*tests.cpp`, `scripts/s2g/tests/test_p2b_user_mapping_20261019.py`, `test_p2b_native_gshhg_lu_dat.py`, Issue119/123 workflow families | **KEEP/REGRESSION**; no code deletion without mapping every caller and rerunning equal-input checks |

This is a **conservative source/CMake/header reachability audit**, not proof that a test never dynamically loads a symbol. For C2 deletion, enumerate all references with a fresh repository-wide symbol search and preserve any external API/compatibility use. **No C2 deletion in the C0/C1 PR.**

## Required next gates (no premature PASS)

1. C1: compile the new inland CLI, run synthetic header/coast-off tests, independently execute authentic original Fortran and C++ same-GLCC same-grid full 40,000-cell HIT + F6.3 + Missing comparison, pin Run and artifact.
2. C2: separate deletion-only PR **after** C1 authentic baseline, with pre/post Wolsong + Hefei GLCC per-cell equalities **and** existing P2-B area regression; no GLCC mapping changes.
3. C3: rerun Wolsong original (D6–D11) with any new dual-mode entry, verifying exact frozen values.
4. C4: build 30m point-sampling producer with exact 34+water user mapping and source coverage, sample position/REAL*4 binning/NoData, independent calculator on ALL 40,000 × 38 integer fields at both sites. Output `P2_C_GLC30M_SAMPLING` distinct from `EXACT_AREA_V1`. Wolsong use Full L1 boundary handling; inland do not load any shore geometry.
5. C5: independent LU.DAT v2.1 parser for header/zone/3dp grid/38 class order/south-up rows/F6.3/Missing (format only), issue #46 handoff. P3 MAKEGEO, its parameter model and `GEO.DAT` intentionally out of scope.

**C0 status:** source/files/known historical run audit completed; **new compilation, CTest, pytest and new scientific runs NOT_RUN** until the PR CI or site workflows have actual results. The earlier `main@8e0936dc7` is the immutable before-cleanup numerical comparison anchor.