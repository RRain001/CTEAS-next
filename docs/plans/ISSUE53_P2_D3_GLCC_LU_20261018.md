# Issue #53 D3: Historical GLCC P2 fractions → LU.DAT v2.1 scoped contract

Date: 2026-10-18. This extends the completed, real-source D1 **GEN-equivalence** test without claiming original GLAZAS equivalence, approved modern crosswalk, or P3 physics.

## Accepted D1 real-source evidence

User-authorized [Actions #39115417375](https://github.com/RRain001/CTEAS-next/actions/runs/39115417375) completed **SUCCESS** on `main@e5fb4e45231c8e4c68ec4a52fa66a43553b820be`. Verified the original 156,000,000-byte Git LFS GLCC `eausgs2_0la.img`, SHA256 `4f2a1977d141e2040da4d36ec6a4826c5c960c84686eaf10f226f388cb3ab90a`. Two independent paths, native C++ direct byte-window D1 vs Python original-size source GEN points read by the previous native P2 GEN implementation, produced 2,500 grid cells and 38 USGS-92 classes with identical 10,011 **included**, 29,989 outside samples, `max_fraction_delta=0.0`. Workflow artifact `issue53-d1-actual-glcc-source-and-gen-evidence`, artifact ID `12132535537`.

**Evidence level:** `P2_A_GLCC_REAL_SOURCE_AND_GEN_SCOPED=PASS`, not `P2_A_ORIGINAL_GLAZAS_PARITY=PASS`. Neither path is original Fortran GLAZAS. A full independent original `CTGPROC GLAZAS` same-source `LU.DAT` and point-count equivalence remains mandatory.

## D3 historical-only formatter design

New P2-owned executable:

```text
cteas_p2_glcc_lu_dat D1_P2_MANIFEST_JSON D1_P2_GLCC_USGS92_GEN_REPLAY_CSV NEW_OUTPUT_DIR
```

Before accepting any data it requires exact `producer=cteas_p2_glcc_raw`, authentic GLCC 156MB official SHA, expected source method, `PRODUCED_UNVERIFIED`, no upstream false GLAZAS/P3 claims, WGS84 UTM EPSG 32601–32660 or 32701–32760, exactly three-decimal kilometer origins and representable 1-meter-quantized grid spacing. The D1 producer now adds `fractions_csv_sha256` to its manifest **after closing the emitted CSV**; the D3 consumer verifies exact input CSV bytes against it. Existing pre-D3 D1 manifest does not have this additional field and must not be silently promoted.

All rows require `i,j,samples,cat11,...,cat92`, exact 38-class order, j-major/i-minor, exactly NX×NY consecutive rows, nonempty samples, finite [0,1] fractions with sum=1 to `1e-8`, and no extra/truncated records. Original legacy `LU.DAT` v2.1 text header is serialized with dynamic NX/NY, EPSG zone/hemisphere, case origin and DGRIDKM; USGS-92 38 classes and `F5.3` style displayed proportions, trailing `.`. New `lu.dat` is **provisional**, and sibling `p2_d3_manifest.json` explicitly says `PRODUCED_UNVERIFIED`, original GLAZAS `NOT_RUN`, #42 B-1 joint SHA `NOT_RUN`, downstream P3 `NOT_RUN`, modern crosswalk `P2_MAPPING_REVIEW_REQUIRED`.

D3 does not generate a source from bare `MISSING` cells; it **fails closed**. GLCC categories are only the frozen historical 24→USGS92 38 mapping. This writer **rejects** `cteas_p2_glc_raw` and any other producer: modern GLC_FCS30D 35→38 requires explicit scientific acceptance and a separately reviewed mapping ID/SHA before using this v2.1 output path.

### PR scoped checks (not scientific)

Synthetic 50×50 source manifest/CSV with 38 categories is compared **data-line exactly** to the existing frozen `native_cpp/p3/p12_native_dat_adapter.cpp` legacy writer; the fixed historical adapter is left untouched. A separate 3×2 EPSG:32748 southern-UTM case checks dynamic indexing and 38-class order. Negative tests reject wrong producer, wrong official SHA, mutated CSV hash, fractions not summing to one, missing sample cell, 3dp origin violation, destination collision. PR CI **does not download genuine GLCC** and does not run P3.

The data-to-manifest binding is a software integrity contract, not sufficient scientific provenance for the new case: #42 must still bind immutable `case.yaml`/`grid.cmn`/`research_time`, the complete source and result hash ledger, and independently staged P1–P5 inputs; #46 owns P3/MAKEGEO validation and final GEO.DAT.

## Remaining acceptance gates

1. On **new D3 commit**, manually run official LFS GLCC 156MB D1 + Python GEN plus new D3 produced LU.DAT check, with SHA-bound manifests and field-level format check. Prior #39115417375 predates the CSV SHA and D3 implementation.
2. Separately run **original Fortran GLAZAS** with exact GLCC source, MESHGLAZ/control/datum/shoreline behavior, compare original 38×2500 displayed fractions at abs tolerance ≤0.0005, independent per-cell point counts, explain first differences. Python GEN replay is not an original GLAZAS oracle.
3. Scientific mapping review of all GLC_FCS30D 35 classes and 12 locally present classes, especially 182/183/190/210. `P2_MAPPING_REVIEW_REQUIRED` remains; no accepted modern `LU.DAT`.
4. After D3 and cross-module contracts accepted, #46 can consume P2 fields for P3 new-site validations; neither this PR nor #53 duplicates a generalized P3.

Do **not** close issue #53 based solely on software or GLCC real-source GEN equivalence.
