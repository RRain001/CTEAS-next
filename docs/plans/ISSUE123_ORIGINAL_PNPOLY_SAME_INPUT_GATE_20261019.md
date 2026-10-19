# Issue #123 D4 — same-input ORIGINAL Fortran PNPOLY point oracle gate (2026-10-19)

## Purpose and strict scope
This follows #136 (`D4_PASS_SOFTWARE_COASTRD_BLN_PNPOLY_R4_SCOPED`), #131 (`D3_AUTHENTIC_GSHHG_FULL_L1_L4_SOURCE_VERIFIED`), and the permanently frozen #119 `EXACT_AREA_V1`. **GSHHG Full** is the selected production coastline; High will not be reintroduced as an acceptance criterion.

D4 requires more than a C++ port that looks like the original. This manual gate compiles **the original unmodified Fortran `PNPOLY` subroutine**, extracts it at runtime from the exact pinned original vendor `CTGPROC_v7.0.0_L150211/ctgproc.for`, and runs original and C++ on the **identical** synthetic REAL*4 coordinate stream. Only exact integer `-1/0/+1` codes are admissible. No epsilon/tolerance is permitted.

## Source provenance and software architecture
- Original public source: [CTEAS original Fortran @ dfad99a7](https://github.com/RRain001/CTEAS/blob/dfad99a78ed84d655e21411c9d25eb0d2583bf13/engine/vendor/src/CTGPROC_v7.0.0_L150211/ctgproc.for). Expected full file SHA256 `719abbd2327269bb0377208b3a7a0c74000b878efc756686023bbb2ef932f281` (pin confirmed in earlier project GLCC provenance; this gate will verify actual downloaded bytes anew). The original subroutine is **never modified and never redistributed** in this repository or the resulting artifact.
- New manual workflow [`issue123-original-pnpoly-manual.yml`](https://github.com/RRain001/CTEAS-next/actions/workflows/issue123-original-pnpoly-manual.yml) is `workflow_dispatch` **ONLY**. It downloads that exact public commit, fails if its SHA changes, extracts the original PNPOLY in an ephemeral runner, compiles with gfortran and creates a separately compiled native C++ batch reference.
- `scripts/s2g/issue123_original_pnpoly_oracle.py` prepares deterministic synthetic points: 3 separate model-km scales including Wolsong-like coordinates, inside/outside/edges/vertices and near-edge samples, and polygon winding reversal. Emits identical `float32` numeric text for both executables; compares every actual original/native integer result exactly and saves summary/first mismatches only.
- `cteas_p2_original_pnpoly_batch` is only the **non-production** stdin test driver for D4 C++ `original_pnpoly_r4`. It neither reads actual GLCC nor changes `LU.DAT`, P2-A original source mesh, D3 sampling recount, or P2-B EXACT_AREA.
- PR CI `issue123-original-pnpoly-batch-ci.yml` exercises the native CLI/input protocol and offline deterministic-case count; **does not download or execute the original vendor**. The actual original-versus-native Fortran comparison runs solely when the user manually dispatches the manual workflow.

## What a passing manual run establishes
`D4_PASS_UNMODIFIED_ORIGINAL_PNPOLY_SAME_INPUT_SYNTHETIC` means: the **unmodified actual original subroutine** and C++ produced exactly the same {-1,0,1} output on the listed synthetic floating-point samples under the pinned compiler flags/environment. Record exact source SHA, point count and any observed mismatches.

It does **NOT** establish:
1. Original `COASTEXT` native GSHHS binary processing/extraction and projected BLN vertex equality, including synthetic surrounding polygons and clipping.
2. Original `IPTYPE` whole hierarchical type 0–4 equality using a real original BLN and actual model sample coordinates; the original Fortran may treat boundary/near-boundary geometry differently.
3. The 38-category per-cell original `LFINAL=F` integer `HITS` or `LFINAL=T` `LU.DAT` scientific parity; the original CTGPROC `GENERIC + LCOAST` restriction persists.
4. Scientific evaluation for alternative GSHHG resolutions or real 2022 coast shoreline truth. Only Full is in scope.

## Next original parity gates
- Produce the authentic original `COASTEXT`/COASTRD BLN on a legal source and the same model grid, with source ID/coordinate/geometry provenance. Confirm the original source version and modern Full f L1–L4 lineage (same nominal release does not prove identical original binary polygon extraction).
- Use original unmodified `IPTYPE` and C++ `OriginalBlnIptypeR4` against **the exact same original extracted BLN** and the exact same original Fortran REAL*4 sample-point records; require **zero integer category mismatches**.
- Only then wire the D3 opt-in P2-A GLCC source-mesh recount to a separately named original-mode CLI and execute a manually triggered original `HITS/LU.DAT` original/native parity gate.
- #123 remains OPEN; original original/native parity cannot be inferred from the earlier GSHHG ZIP source PASS or the current synthetic CTest.

## Safety controls
Full scientific workflows are never PR-triggered, never auto-dispatched, and have a fail-closed SHA check. Source/code/actual coordinates are not uploaded in artifacts; only `provenance.json` and `oracle_report.json` are preserved for scientific audit.
