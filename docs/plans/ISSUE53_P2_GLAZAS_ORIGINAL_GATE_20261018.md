# Issue #53 — Original CTGPROC GLAZAS scientific parity gate

**Date**: 2026-10-18. This is a true **independent original executable** numerical gate. It does not substitute a native C++ GEN replay or prior captured GEN `LU.DAT` for the real Fortran GLAZAS pathway.

## Evidence already available

The real [D1→D3 manual Actions run #39117936870](https://github.com/RRain001/CTEAS-next/actions/runs/39117936870) checked official GLCC Eurasia `eausgs2_0la.img` (156 MB, exact SHA256 `4f2a1977d141e2040da4d36ec6a4826c5c960c84686eaf10f226f388cb3ab90a`) then independently replayed C++ native GLCC window versus Python GEN + legacy C++ GEN. All 2500 cells × 38 classes compared, 10011 included, 29989 excluded, max fraction discrepancy 0.0; D3 emitted preliminary 2500-row `LU.DAT` with SHA-bound source/manifest and `PRODUCED_UNVERIFIED` status.

The later [run #39120524332](https://github.com/RRain001/CTEAS-next/actions/runs/39120524332), launched from commit `19992f70196d0515d03f2093e1ae2ef38ccc7d50`, also completed both real and synthetic jobs successfully.

**Neither result claims original GLAZAS numeric identity**. Current status is `P2_A_GLCC_REAL_SOURCE_AND_GEN_SCOPED=PASS`, `P2_A_GLCC_D1_D3_REAL=PASS_SOFTWARE_SCOPED`, and `P2_A_ORIGINAL_GLAZAS_PARITY=NOT_RUN`.

## Original GLAZAS standalone comparator

`native_cpp/reference/validate_p2_glazas_original.py` takes:
- Original official 156000000-byte `eausgs2_0la.img`, SHA-locked; never a Git LFS pointer.
- External *genuine* original CTGPROC executable and its independently verified SHA256. The original program must be installed on the authorized Ubuntu self-hosted runner; no vendor source or binary is copied into this public GitHub repository or artifacts.
- The frozen Hefei 2022 `ctgproc.inp` and `grid.cmn` as a control authority, and the actual on-the-fly D1→D3 `lu.dat` + SHA-bound manifest (not a historical reference fixture).
- A fresh isolated output directory.

The script builds a separate copy of the input deck and changes the single active `1 !GEN=...` line to **`1 !GLAZAS = glcc.img !`**, sets `MESHGLAZ=20`, `LFINAL=T`, `LPREV=F`, `LCOAST=F`, `LQACELL=F`, `LSNOW=F`, `DUSGSLA=ESR-S`, WGS84 UTM50N / 50×50×100 m and exactly three-decimal origin (510.885/3531.269). This intentionally does not test other CTGPROC shoreline/polar/land-cover options. Original `ctgproc.x` runs with relative `glcc.img` path in its own short-name scratch cwd, reading the verified official 156MB source.

The independent original outputs `lu.dat` and `ctgproc.lst` are read only after **returncode zero**. Compare:
1. Exact LU.DAT version 2.1/header, `FRACTION`, WGS84 UTM50N, 50×50, southwest origin, spacing, 38 *specific* USGS-92 category IDs and 2500 j-major/i-minor rows.
2. All **95,000 displayed values** at original three-decimal source precision, predeclared absolute tolerance ≤0.0005. Preserve the first 20 **exceedances** and maximum/mean discrepancy; fail if any exceeds.
3. Independent original CTGPROC `ctgproc.lst` text's `Number of data points used to update grid:` vs D1/D3-native recorded `total_samples` (expected 10011 in the frozen real-source case). Absent or ambiguous LST counter fails. Equal displayed ratios alone are insufficient.
4. Separate SHA256 fields for original binary, original input deck, original output LU, original LST, native LU and source, with execution status and runtime.

The comparator fails closed if original executable is absent, not executable, symlink, has wrong pinned SHA, if the raw IMG fails its official size/hash, or if original outputs/point counts/headers are malformed. Never invent an original process or fall back to GEN. The outside-repository GLCC dataset and original executable remain separate.

## How to run

Use manual-only [`Issue53 genuine original CTGPROC GLAZAS parity`](https://github.com/RRain001/CTEAS-next/actions/workflows/s2g1bb-issue53-glazas-original.yml) after this workflow is merged to `main`.

Choose `Run workflow` on **main** and supply:

- `original_binary_absolute_path`: an **existing absolute path on an online self-hosted runner labeled `cteas-managed`** containing an authentic vendor CTGPROC executable.
- `original_binary_sha256`: **64 lowercase hex SHA256 from independently vetted binary provenance**.

The self-hosted runner must already have Git LFS, CMake 3.20+, C++20 compiler, GDAL development headers/libraries, OpenSSL development files and Python 3. The GLAZAS raw image is obtained by checkout `lfs:true` from the committed root GLCC object. No unapproved redistribution or generic internet download of vendor code is performed.

If these native preconditions are absent, the job remains `BLOCKED_ORIGINAL_BINARY`, not `PASS`. **Do not substitute earlier GEN-path `LU.DAT`**. The job executes original code in isolated temporary directories and publishes only manifests and numeric-difference summaries, not the original code or raw source.

The PR software gate `python3 -m unittest -v native_cpp.reference.tests.test_glazas_original_gate` uses historical `LU.DAT` **solely as a file format fixture**. It does not run or accept a fake binary as scientific evidence.

## Release and scope constraints

The #53 selected original GLCC / 24→38 history can only be marked `PASS_ORIGINAL_GLAZAS_SAME_SOURCE` after the full manual original program run passes all above requirements. GLCC `LU.DAT` is interim until the original scientific gate and #42 B-1 source/case/grid/time hashes are accepted; #46 independently owns P3/MAKEGEO/GEO.DAT.

The modern 2022 `GLC_FCS30D` 35→USGS-92 crosswalk is **not yet approved**: especially 182 herbaceous wetland, 183 floodplain, 190 impervious, 210 open water. Its historical-style LU may not be generated as science-pass without explicit reviewed mapping and physical impacts. `P2_MAPPING_REVIEW_REQUIRED` and #53 `OPEN` remain.

**No long CALMET/CALPUFF test, vendor re-publication or P3 algorithm was introduced here.**


## 2026-10-18 updated CTEAS original source workflow (without preinstalled binaries)

The original **CTEAS** repository `RRain001/CTEAS` is publicly readable. Its pinned `main` commit is `dfad99a78ed84d655e21411c9d25eb0d2583bf13`, source path `engine/vendor/src/CTGPROC_v7.0.0_L150211/ctgproc.for`, 269543 bytes, independently recorded source SHA256 `719abbd2327269bb0377208b3a7a0c74000b878efc756686023bbb2ef932f281`. This is the historical Exponent CTGPROC Version 7.0.0 Level 150211, not a native reimplementation. Its compilation options come from CTEAS `scripts/build_native_linux_x86_64.sh` and existing `native_cpp/reference/capture_p1_p2.py`: `gfortran -std=legacy -ffixed-line-length-72 -fno-automatic -fno-align-commons -fallow-argument-mismatch -O0` with an isolated lower-case INCLUDE alias directory for legacy case-sensitive names.

**No user-supplied binary path or hash is necessary now**. On automatic PR only, a *build-only* Actions job performs sparse checkout of this exact original SHA in a separate temporary directory, checks original file SHA and actually compiles `ctgproc.for`. It **does not run original science**, fetch real 156MB LFS, or upload third-party code/executable. A second automatic job runs comparator-only synthetic/previous format fixture tests.

On user-approved manual `workflow_dispatch`, hosted Ubuntu 22.04 pulls the exact same CTEAS original commit (sparse no-LFS checkout) and **CTEAS-next** original 156MB GLCC Git LFS (strict original SHA). It compiles authentic CTGPROC from original source and independently hashes the executable, then runs C++ native D1→D3 and actual CTGPROC `GLAZAS` in the same-source frozen 50×50 domain. `validate_p2_glazas_original.py` now also requires the original Fortran `ctgproc.for` file and checks its SHA; if the original returns no `LU.DAT`/LST or any of the 95,000 values/point-count gates fail, the scientific job fails and preserves only metadata/difference report.

This does **not** authorize redistribution of CTGPROC vendor source or compiled binary in CTEAS-next; separate checkout is transient and outputs deliberately exclude original code, binary, and raw IMG. Original source has third-party Exponent copyright; original CTEAS GitHub availability is **not** itself a grant of new redistribution rights.

[Manual original-source GLAZAS science workflow](https://github.com/RRain001/CTEAS-next/actions/workflows/s2g1bb-issue53-glazas-original.yml) → select main → Run workflow (no inputs). The run's actual result, *not successful source compilation*, determines `P2_A_ORIGINAL_GLAZAS_PARITY`. Until the science run completes on the current code, this status remains `NOT_RUN`.



## 2026-10-18 actual first original science run and improved integer oracle

Manual [`Run #39128466718`](https://github.com/RRain001/CTEAS-next/actions/runs/39128466718) **actually executed the authentic pinned CTGPROC GLAZAS** on the real official 156MB GLCC and wrote its independent LU.DAT. The original 2500×38=95000 **three-decimal fraction values all matched native D1→D3 exactly (max absolute difference 0.0, exceedances 0)**. The job was marked failure because the original `ctgproc.lst` printed `ncount=56` while the comparison improperly equated it to the native **10011 sub-grid mesh hits**.

**Original Fortran source audit**: `ctgproc.for` lines ~2480–2506 calls `LUGRID(ngtmp,xmesh,ymesh,lucat,ncount2)` for each successful sub-grid point; `ncount2` is the mesh-level hits counter. But the original `ncount` printed by `Number of data points used to update grid` at ~3595 is incremented only once per *GLCC source pixel* touching the grid, not once for each of its successful MESHGLAZ subpoints (line ~2505). Thus **56 and 10011 are different units and must NOT be compared**, and their numeric inequality is **not evidence of C++ physics disagreement**.

The stronger scientifically valid original-reference contract requires two **independently executed original Fortran runs with identical source, grid and MESHGLAZ=20**:
1. `LFINAL=T`: original three-decimal **FRACTION** LU.DAT, compare all 95,000 original categories against native D3 ratios (absolute tolerance ≤0.0005).
2. `LFINAL=F`: original **integer HITS** LU.DAT (genuine original sub-grid counts per output cell × class, not the original log `ncount`). Compare all 95,000 exact integers with the new native C++ D1 `p2_glcc_usgs92_hits.csv`, saved directly from its in-memory integer count array and pinned by `hits_csv_sha256` in D1 `p2_manifest.json`. Verify for every grid cell: sum of original integer hits equals native cell_samples, exact per-class hits, consistency of original HITS vs original fractions, and original `ncount` remains unchanged between the two original control runs. **Scientific success requires both original runs to execute successfully and all numerical gates to pass.**
3. Preserve in the artifact: original source commit/SHA and binary SHA, both original control SHA, both original LU SHA, native integer CSV SHA, max and first 20 integer field differences, original 56-type **GLCC parent pixel** count (report only, not as sub-grid sample comparator), total sub-grid hits for both original and native, provenance and numeric scope.

The updated manual [same workflow](https://github.com/RRain001/CTEAS-next/actions/workflows/s2g1bb-issue53-glazas-original.yml) now invokes `native_cpp.reference.validate_p2_glazas_hits`. The PR CI tests the parser and comparator **with synthetic integer data and format fixtures only**; it may never replace the manual 156MB original science run.

Original HITS is an independent source-specific reference. This change does not alter historical `ctgproc.for`, P3/MAKEGEO, the 2022 GLC mappings, the raw source products, or any upstream long-time P6/P7 validation.

