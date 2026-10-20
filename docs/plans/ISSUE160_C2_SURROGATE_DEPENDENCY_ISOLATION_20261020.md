# Issue #160 C2 — separate test-only GEOS D2 surrogate isolation

Parent C1: [Draft PR #162](https://github.com/RRain001/CTEAS-next/pull/162), C1 authentic science run [39360612398](https://github.com/RRain001/CTEAS-next/actions/runs/39360612398), artifact [12237345901](https://github.com/RRain001/CTEAS-next/actions/runs/39360612398/artifacts/12237345901), branch head `cc5d120a718b8379898ac582d0eb91c1c45695f3`. Proven 40,000×38 integer HITS zero differences, 40,061 total HITS, 1,128 empty cells, 1,520,000 F6.3 fields zero differences, zero Missing mismatch; canonical GLCC 156MB SHA `4f2a1977d141e2040da4d36ec6a4826c5c960c84686eaf10f226f388cb3ab90a`; original source SHA `719abbd2327269bb0377208b3a7a0c74000b878efc756686023bbb2ef932f281`. Frozen Wolsong original GLCC prior D11 run [39344388008](https://github.com/RRain001/CTEAS-next/actions/runs/39344388008), [artifact 12229939690](https://github.com/RRain001/CTEAS-next/actions/runs/39344388008/artifacts/12229939690). Original master pinned to `dfad99a78ed84d655e21411c9d25eb0d2583bf13`.

**Separate stacked C2 PR:** no C2 changes to C1, P2-B `EXACT_AREA_V1`, historical 24→38 map, modern 34+1 JSON policy, P1, P3, P6, or P7.

## Search-based source and build reachability ruling

- `OriginalGshhsPointClassifier` / `recount_glcc_original_coast` **are still referenced by** `native_cpp/tests/p2_original_sampling_recount_tests.cpp`; `ctgproc_original_iptype.cpp` has its own `p2_original_iptype_tests.cpp` and its public header. They are **not safely deletable** as orphan code. Do not remove their implementation/API/tests.
- The D2 GEOS surrogate is not original Fortran point-in-polygon parity and must not become a transitive production dependency of the authentic original-BLN recount or inland no-coast CLI. The old CMake linked `cteas_p2_original_iptype` publicly from `cteas_p2_original_sampling_recount`; C2 moves D2-only overload symbol into an opt-in **test-only** `cteas_p2_original_sampling_d2_surrogate` target.
- The original production recount unit still emits the **identical core integer bookkeeping template and original-BLN overload/fraction** with no changed computation, source count category array, REAL*4 class labels, or writer. The synthetic D2 build emits the D2 GEOS adapter overload from the same source under a compile definition. The D2 target links back to the core and original IPTYPE library. Synthetic tests explicitly select D2; production CLIs link only the BLN/core library.
- This is dependency isolation and production link cleanup, **not** deletion of supported caller-reachable code. No assertion that the entire project is free of all dead code.

## Strict post-change gates — zero new science tolerance

1. Compile and run original recount + GEOS D2 / BLN synthetic contracts, Wolsong original-writer and Hefei 50N writer contracts (CMake/ctest); no compilation warnings.
2. Independently rerun actual historical Hefei C1 200×200×38 integer & F6.3 original Fortran comparison from exactly the pre-C2 GLCC and vendor SHA, require zero differences, identical **40,061 total HITS**, identical **1,128 Missing**.
3. Independently rerun genuine Wolsong source-pinned original D6–D11 GLCC/BLN comparison to protect pre-C2 observed **40,025 total HITS**, **37,035 nonempty**, **2,965 Missing** and all 1,520,000 fields. The prior Wolsong baseline alone **does not** prove this post-change run.
4. Run P2-B `EXACT_AREA_V1` original test gates and confirm source and 34+water modern mapping JSON untouched; never generalize area versus point sampling.

**Do not merge this cleanup/isolation PR until all actual post-change science gates are documented**. If source/CMake callers are discovered that require the D2 overload in the original production target, restore compatibility first; no deletion to force a test to pass. C4 30m samples and C5 P3 format remain NOT_RUN, #46 remains owner of P3 physics.
