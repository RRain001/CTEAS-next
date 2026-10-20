# Issue #168 S1-A/S1-B: retire the P2-B native area producer

Baseline: `main@abc4cbf80ab7a16a9551bd5a0ac1f65e3b64e434` (2026-10-20). The baseline is **pre-retirement**.
This is the independent S1 retirement candidate, **not a scientific PASS**.

## Production decisions and protected references

- Keep **P2-A**: original GLCC 1 km, historical 24-to-USGS38 mapping, direct-LAEA/source GLAZAS/LUGRID, original coastal point/BLN checks and F6.3 serializer.
- Keep **P2-C**: genuine 2022 GLC_FCS30D 30 m, source-pixel 10x10 POINT HITS, inland water 210 -> 52, seaward Full L1 original BLN point test -> 55, 34 fixed mappings, LU.DAT v2.1. Method **not** EXACT_AREA_V1.
- Retire **P2-B**: grid/source-pixel area intersection kernel, executable entry points and production runtime copy. No automatic fallback to it.
- **Protect SHA256 `a5fa157f57feb1aa160dd96d920a22d267fea78c5828c6040fa95e86536544ed`** of `docs/plans/ISSUE53_GLC35_USGS38_USER_SELECTED_20261019.json`. The literal `cteas.p2b...` schema string is consumed by the frozen P2-C core: do **not** rename/mutate.
- Preserve all real input TIFF/GLCC/BLN, metadata, data licenses and archived acceptance reports. `scripts/s2g/p2b_wolsong_case.py` is retained as an existing historical source-acquisition/verification utility consumed by Wolsong real-source tests; it is **not** an approved 30 m LU producer. Archived model-grid-area review scripts remain audit-only, not production routes.

## Reachability inventory and action

| Node | Baseline dependency / reachability | S1 action |
| --- | --- | --- |
| `cteas_p2_glc_area` / `glc_area_fractions.{cpp,hpp}` | P2-B-only raw-area fraction kernel; consumed by B raw & LU CLIs and dedicated CTest | Delete CMake target and exclusive source/header |
| `cteas_p2_glc_raw` / `p2_glc_area_cli.cpp` | P2-B-only raw-area producer; Docker runtime + obsolete Issue53 workflow and migration portable label | Delete CLI and all active build/runtime references |
| `cteas_p2_glc_lu_dat` / `p2_glc_lu_dat_cli.cpp` | P2-B-only GEOS/GSHHG area + policy crosswalk to LU.DAT | Delete CLI/target, historical science reports retained |
| `p2_glc_area_tests.cpp`, `test_p2b_native_gshhg_lu_dat.py` | Only test deleted area kernel and native B CLI | Delete obsolete tests, keep prior Git evidence |
| Historical Issue119/Issue46/P2-B-only Issue53 Actions | Invoke deleted B executables or validate their manual workflow; now invalid | Remove these ten obsolete active workflow files |
| Issue160 C1/C2/C4 software CI | Shared P2-A/C software checks but previously compiled obsolete B targets | Remove B target/CTest selections, **keep** all A/C tests |
| Docker runtime | Copied `cteas_p2_glc_raw`, not modern point sampler | Drop B raw CLI, include `cteas_p2c_glc30m_sampling` |
| `cteas_p2_glcc_source`, `cteas_p2_original_sampling_recount`, BLN/PNPOLY/original writer | P2-A, P2-C live shared infrastructure | **KEEP**, no physical or mapping edits |
| Modern mapping JSON, GLC2022 inputs, `test_p2b_user_mapping_20261019.py` | Used to pin/guard modern P2-C policy despite B-derived naming | **KEEP** exactly, including original policy-status fields |
| `scripts/s2g/p2b_wolsong_case.py`, source verification tests | Authentic frozen 2022 TIFF provenance and valid source coverage | **KEEP** historic source-only code; remove stale test asserting retired workflow exists |
| Original GLCC source+metadata+testing | P2-A 24-to-USGS38 and real original comparison | **KEEP**, frozen output contract |
| P3 MAKEGEO, P6/P7 | No changes permitted under S1 | **KEEP** |

## Independent baseline evidence to rerun on this candidate

Previously passed on `main@abc4cbf80ab7a16a9551bd5a0ac1f65e3b64e434` (historical, not proof of new candidate):

- P2-A authentic Hefei GLCC: [run 39367015109](https://github.com/RRain001/CTEAS-next/actions/runs/39367015109), [artifact 12240206528](https://github.com/RRain001/CTEAS-next/actions/runs/39367015109/artifacts/12240206528). Original vendor `ctgproc.for` SHA256 `719abbd2327269bb0377208b3a7a0c74000b878efc756686023bbb2ef932f281`; canonical GLCC SHA256 `4f2a1977d141e2040da4d36ec6a4826c5c960c84686eaf10f226f388cb3ab90a`.
- P2-C authentic Wolsong: [run 39367027413](https://github.com/RRain001/CTEAS-next/actions/runs/39367027413), [artifact 12239309934](https://github.com/RRain001/CTEAS-next/actions/runs/39367027413/artifacts/12239309934), 1,520,000 integer HITS and 1,520,000 F6.3 fields, all zero mismatch; real 2022 TIFF SHA256 `2a1a208c5386735692d788066f730c7391e87f0981e7b9ad099442af2e217711`, original BLN SHA256 `67da93d441e7defe3eb46627ed9ce896c0a91ffd89fd5e4363d834d8108e11f9`.
- P2-C authentic Hefei 20 km: [run 39367022974](https://github.com/RRain001/CTEAS-next/actions/runs/39367022974), [artifact 12239309694](https://github.com/RRain001/CTEAS-next/actions/runs/39367022974/artifacts/12239309694), 1,520,000 integer HITS and 1,520,000 F6.3 fields, all zero mismatch; actual GLC2022 20 km TIFF SHA256 `ee5cefc27827d84f0aa42d0e014e211fcfef67f2bffc43185d17897d840d2e58`.

The previous runs do **not** establish the post-delete comparison. P3 v2.1 input structure was checked, but 38-to-14 numerical original MAKEGEO comparison remains Issue #46.

## S1 acceptance states — 2026-10-20 updated after authorized Docker deferral

**User scope decision:** postpone Docker **build, image verification, and the unrelated gitless P7 provenance repair** until all other development Issues have been closed. These are **explicitly NOT conditions for closing #168**. This change does not assert any Docker PASS, modify P7 scientific physics, or waive native/P2-A/P2-C scientific gates.

- **S1-A PASS_SCOPED:** independent target/caller diff reviewed for B-only deletions. Original GLCC, BLN original point classification, P2-C modern 34+210 immutable mapping, original validation source data, and input/source SHA remain present. Obsolete issue119/46/53 P2-B entrypoints/workflows removed; no supported fallback to B.
- **S1-B IMPLEMENTED:** native `EXACT_AREA_V1` B-only CMake targets, kernel, CLIs and obsolete tests removed. Dockerfile **static references** have been minimally updated to stop copying deleted B and name retained C, but actual container build/runtime portability verification is **DEFERRED**.
- **S1-C PASS_SCOPED:** [post-retirement native build/CTest Run #39372805241](https://github.com/RRain001/CTEAS-next/actions/runs/39372805241), all 59 build steps and 10/10 CTest PASS; preserved frozen modern policy SHA and linker symbols. [P2-A Hefei original-vs-C++ Run #39372805129](https://github.com/RRain001/CTEAS-next/actions/runs/39372805129), [Artifact 12241334070](https://github.com/RRain001/CTEAS-next/actions/runs/39372805129/artifacts/12241334070): integer and F6.3 zero mismatch. [P2-C Wolsong Run #39372805046](https://github.com/RRain001/CTEAS-next/actions/runs/39372805046), [Artifact 12241818575](https://github.com/RRain001/CTEAS-next/actions/runs/39372805046/artifacts/12241818575): 1,520,000 HITS and 1,520,000 F6.3 zero mismatch, Missing 0 difference; P3 input format-only PASS. [P2-C Hefei Run #39372805031](https://github.com/RRain001/CTEAS-next/actions/runs/39372805031), [Artifact 12241808664](https://github.com/RRain001/CTEAS-next/actions/runs/39372805031/artifacts/12241808664): same exact zero-mismatch counts and P3 format-only PASS. Last pre-deferral PR head `996dd60f5a6ca867f1e4a9467661531685e5762c` repeated 18 non-Docker checks successfully; one unrelated original GEN manual job skipped by its established control.
- **S1-D ACCEPTANCE SCOPE:** merge PR #170 and close #168 when native and true-source science remain PASS. Final production Docker build/entry/runtime, and corresponding platform QA, are explicitly **NOT_RUN / FAILED_PREVIOUS_GITLESS_P7**, not PASS. Do not claim P3 MAKEGEO 38→14 physics parity (#46 scope), full P6/P7 physical completeness, or identical post-delete `LU.DAT` byte SHA without a fresh bytewise comparator.

**Deferred Docker blocker provenance:** [two-platform attempt #39373264635](https://github.com/RRain001/CTEAS-next/actions/runs/39373264635) failed at P7 CMake configure after P1/P2/P3/P4/P5/P6/P6E/P6F packages compiled. The existing `native_cpp/modules/p7_calpuff/CMakeLists.txt` checks `git rev-parse HEAD` while `.dockerignore` excludes `.git`; the build cannot obtain a valid source commit. A standalone P7 configure with Git present passed on both platform runners in [Run #39373745832](https://github.com/RRain001/CTEAS-next/actions/runs/39373745832). This is the reason to defer container validation, **not** a P2 numerical failure. The automatic `issue168-p2-docker-runtime-smoke.yml` PR check has been removed to avoid scheduling further Docker work prematurely.

Backlog and restart criteria are recorded in `docs/plans/DOCKER_FINAL_SWEEP_AFTER_ISSUES_20261020.md`. Do not create a new Docker work Issue before remaining development Issues are closed; this is a post-Issue consolidation task, not an additional #168 blocker.

No modifications to historical original Fortran, GLCC classification, P2-C 34+210 JSON, native P2-C point/BLN physics, P3, P6 or P7 are authorized by this patch.
