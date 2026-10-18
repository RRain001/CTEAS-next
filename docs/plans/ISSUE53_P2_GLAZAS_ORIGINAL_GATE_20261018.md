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
