# Issue #53: genuine multi-region original GLAZAS science gate

The pinned original [Hefei GLCC original Run #39191914836](https://github.com/RRain001/CTEAS-next/actions/runs/39191914836) on `main@e4e62514` passed: 95,000 integer HITS exact, 95,000 displayed class fractions exact, original/native 10,013 submesh hits. This is not evidence for other geographic regions, hemispheres, grids or UTM zones.

This new independent **manual-only** workflow runs fresh authentic original CTGPROC/GLAZAS on exactly the same official source bytes as native P2, at two substantially different regions:

| Case | Approximate location | WGS84 UTM | Southwest origin (km) | Cells | Grid spacing | Mesh |
|---|---|---|---|---|---|---|
| `japan_utm54n` | Tokyo inland, 139.7E 35.7N | EPSG:32654 | (378.389, 3945.454) | 40×60 | 0.200 km | 10 |
| `sumatra_utm47s` | Central Sumatra, 101.3E 1.8S | EPSG:32747 | (753.626, 9797.884) | 30×40 | 0.150 km | 20 |

Both are checked for validity and source coverage when executed; any unsupported vintage Fortran UTM configuration or missing raw 1km GLCC pixel coverage is a **FAIL** with the corresponding reason, not an implied pass.

## Evidence and criteria

1. Use frozen CTEAS original source `dfad99a78ed84d655e21411c9d25eb0d2583bf13` (ctgproc.for SHA256 `719abbd2327269bb0377208b3a7a0c74000b878efc756686023bbb2ef932f281`) and original Eurasia 156,000,000-byte `eausgs2_0la.img` (SHA256 `4f2a1977d141e2040da4d36ec6a4826c5c960c84686eaf10f226f388cb3ab90a`). Never use historical canned `LU.DAT` as an oracle, synthetic GLCC as science evidence, or change source vendor code.
2. Build original Fortran and native production D1/D3 independently, on a `main` workflow dispatch only. Native GLCC direct-LAEA method SHA, EPSG, numeric origins, spacing, dimensions, `MESHGLAZ` and D1→D3 linkage are verified.
3. Generate isolated original `!GLAZAS = glcc.img !` cards per regional geometry. Original *fraction* and *integer* executions run separately (`LFINAL=T/F`). Verify each output version, UTM zone and hemisphere, grid origin, grid spacing, row count/order, 38-class order and value format. Fail closed if unsupported or cells lack source samples.
4. Compare **all** `nx×ny×38` original versus C++ production HITS **with zero integer tolerance**. Require exact per-cell counts, source GLCC 1km pixels converted to identical input category mapping, original fraction-HITS self-consistency, plus displayed fractions within the existing fixed `0.0005` threshold. Never use the diagnostic candidate CSV as production.
5. JSON artifact contains independent case verdicts, total hits, integer/fraction differences, first disagreements, input/control/source hashes. Both regions must independently report `PASS_SCOPED_ORIGINAL_GLAZAS_REGIONAL` before the overall `PASS_SCOPED_ALL_TESTED_REGIONS`. Even this would NOT prove arbitrary UTM zones, grids, input products, or P2-B GLC_FCS30D mapping.

### Run

The [Issue53 GLCC cross-region original GLAZAS workflow](https://github.com/RRain001/CTEAS-next/actions/workflows/s2g1bb-issue53-glazas-cross-region.yml) is **manual-only for full science**; PR-triggered jobs only test the comparator with synthetic LU formats and compile Python code. After merge select **main → Run workflow**. Follow up with a separate manual original validation for other WGS84 UTM zones or grids only if these two cases reveal no new issues. Do not close #53 while P2-B 30m crosswalk remains `P2_MAPPING_REVIEW_REQUIRED`.

The program `native_cpp.reference.validate_p2_glazas_regions` and the manual workflow are purposely separate from frozen Hefei validation to preserve its independently audited exact-grid comparison and result.
