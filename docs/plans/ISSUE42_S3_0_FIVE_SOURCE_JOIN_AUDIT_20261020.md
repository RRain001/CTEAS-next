# Issue #42 S3-0: fail-closed five-producer source lineage on ONE new B-0 case

2026-10-20. The S2 module-level exit issue #169 is now closed **PASS_SCOPED** on selected paths; this is *not* S3 acceptance. P1–P5 numeric algorithms and NOAA selection policies remain owned by their completed module-specific issues.

## Genuine integration gap now being addressed

An independently real Wolsong P1/P2-C/P3 run and original MAKEGEO D4 certificate exist, while genuine NOAA upper-air/surface integration evidence in PR #44/#47 comes from the **different** Huoshan/Xinqiao domain. Combining these previously captured files into one report would fabricate a same-site weather/terrain proof. Existing G19 source-only logic already audits meteorological station count, native source parser and `met.inp`, but it cannot by itself prove that *all five producer files* came from one immutable B-0 case, because the underlying producers maintain distinct science/status manifest schemas.

## S3-0 producer manifest join

`native_cpp/orchestration/s3_five_source_preflight.py` is a small **read-only orchestration validator**, not a sixth numerical kernel. It calls existing `admit_case()` on staged `case.yaml/grid.cmn/research_time` and checks the actual source files, strictly relative to the same independent case root:

| Role | Unique existing producer output | Byte/identity gate |
| --- | --- | --- |
| P1 & TERREL | P1 real GeoTIFF and native `terrain.csv` already recorded within P3 D2 `evidence/p3.json`; native `geo/makegeo/p3_case/terrel.dat` | P3 case SHA must equal B0; P1 TIFF/CSV and TERREL SHA declared; TERREL actual bytes SHA verified |
| P2-A or retained P2-C | `evidence/p2.json` and `geo/ctgproc/p2a_case/lu/lu.dat` or `geo/ctgproc/p2c_case/lu.dat` | P2 method B0/source/grid matched; P3 must point to **same** P2 proof SHA and same actual LU SHA. Retired P2-B is always rejected |
| P3 MAKEGEO | `evidence/p3.json` and `geo/makegeo/p3_case/geo.dat` | Dynamic UTM/grid sizes, P3 native input status and actual GEO SHA must agree with P1/P2 and B0 |
| P4 READ62 | `met/upperair/p4_d1a_annual_manifest.json` plus `met/upperair/final/up_WMO.dat`, `stations.csv` | Original source/stack case B0 raw SHA, exact case scratch path, JDAT=2/IFMT=1/PSTOP=500, 00/12 writer bracket covers requested UTC, per-WMO genuine candidate files and station CSV SHA |
| P5 SMERGE | `evidence/p5.json`, `met/surface/final/surf.dat`, `stations.csv` | Same B0/source case SHA, published SURF bytes, stable true IFSTN station IDs and exactly `(END-BEGIN)/hour` emitted hour-ending records, no global file fallback |

Outputs are not copied and producer evidence is not rewritten. Only a fresh separate `evidence/s3-b0-five-source-preflight.json` is written on **ALL exact path, case/grid/time SHA, real file bytes, source role and station-clock** gates passing. Symlink/missing/foreign site/past-case and unsupported physical option admission fail closed. This file's explicit status `S3_B0_SAME_CASE_FIVE_PRODUCERS_SOURCE_LINEAGE_PASS_NOT_G19` means only provenance and source consistency checked, **not independent original physics or native G19 input science**.

## Tests and scientific safeguards

The PR exercises positive/negative **synthetic manifest software** tests: foreign P2/P3 B0 case, retired P2-B, P3 LU stale SHA, mismatched real P4 UP proof, P5 SURF SHA/time window drift, missing AA/BB brackets and duplicate IFSTN source aliases. Separate existing B0 original precision/duplicate-key tests are rerun. No authentic new meteorological or terrain data are introduced in this PR, so `S3_REAL_STACK_NOT_RUN` remains true and #42 must stay **OPEN**.

## Next genuine-source path, not a fallback

Candidate priority remains independent **Huoshan/Xinqiao** ~31.694°N,116.655°E, WGS84 UTM50N; prior original IGRA Anqing source (30.6167°N,116.9667°E) relocates to a documented effective virtual station under the existing >80% rule, 2022 728/730 genuine 00/12 profiles and 2023 730/730. Previously verified genuine 2 surface ISD/ISD-Lite stations `58314099999` / `58321099999` from PR #47 can inform year/source selection, but must be **regenerated against the same newly staged B0 case**, not copied from another scratch/test.

The repository has pinned modern 30m GLC TIFF only for Hefei 20 km and Wolsong; no independently verified Huoshan 2022 modern TIFF is established by this repo scan. Either run the already accepted original historic GLCC P2-A source explicitly for the new domain or obtain/authenticate modern 2022 30m land-use source before choosing P2-C. A genuine raster SRTM route must separately be selected and SHA admitted for the new Huoshan footprint. The project contains historic archived NOAA subsets, but does not yet have a single independently verified, fresh **Huoshan same-hour P1/P2/P3/P4/P5** set. A partial source must report `BLOCKED_REAL_ASSETS`, never fill from Wolsong/Hefei/captured older site artifacts.

**S3 next phases:** B1 fresh scratch/source staging → B2 run selected P1/P2/P3 from true authorized DEM/GLCC/GLC and genuine P4 IGRA/P5 NOAA→ B3 immutable `met.inp` identity mapping, native source-only G19 parser with original geographic/temporal reference → B4 independent science and at least a second configuration negative → B5 proof artifact and scoped handoff to #40. P6/P7 full physics (#40/#36), scale (#161) and Docker after other Issues closed remain outside this PR.
