# S2-2D — source-audited native P7 concentration CLI execution contract (2026-10-17)

Authority: [S2 roadmap](CTEAS_NEXT_FOUR_STAGE_PLAN_20261017.md), [issue #26](https://github.com/RRain001/CTEAS-next/issues/26), upstream [S2-2C issue #25](https://github.com/RRain001/CTEAS-next/issues/25). **Design-only initial Draft; no new native P7 concentration was executed or accepted by this document.**

## Discovered source and non-source distinctions
- `native_cpp/modules/p7_calpuff/src/native_met_hours_cli.cpp`: only validates/inspects MET; NOT CALPUFF solver.
- `src/case_ledger_main.cpp`: evaluates 2022 case identity, hashes and existing outputs; NOT a physics executor.
- Numerical reusable surface exists in `src/{original_comp_hourly.cpp,original_comp_neutral.cpp,original_motion_lifecycle.cpp,step.cpp,step_integration.cpp,hourly_conc.cpp,conc_file.cpp}` and adjacent source/transport/release/rise/writer components. The C++ source chain must be traced fully before selecting the production integration entrypoint; these names are **candidate areas to audit, not proof of finished production API**.
- `tests/original_hefei_firsthour_native_comp_tests.cpp`, `tests/original_hefei_sixhour_native_receptors_tests.cpp` and the established scoped 143h comparison runner demonstrate frozen test scenarios only.

## Strict implementation sequence
1. Derive source-authoritative call graph from actual P7 CMake targets + headers + existing 143h scientific comparison commands; document what owns puff state over all 143 hours, sampling and binary output.
2. Develop narrow no-GUI no-legacy native P7 CLI with `--met`, `--control`, `--work` or an equally explicit contract, accepting only the 2022 selected profile and **verified actual native P6-produced** full meteorology, not frozen original `MET.DAT` treated as fresh native.
3. Standalone startup/1h/6h tests; complete 143h including nonzero H-3 plume, receptor dimensions, unit, source release and timestamp continuity. Require deterministic `puff.con` writer and parse its actual records/fields.
4. Independent original CALPUFF physical comparison on identical meteorology: for 2022 selected profile A/B and C/D **357,500/357,500** REAL4 H-3 values bit-exact. Preserve separate A/C and B/D meteorology-induced statistics. Do not impose whole-file byte identity from a limited concentration comparison.
5. Negative/error path verification for wrong SHA, options, temporal gaps, stale workdirs, mismatched source location, all-zero results, child failure, partial publication and forbidden original-DGM/legacy fallback. Keep `IWET=0` and precipitation absent.
6. Expose bounded result manifest (source/toolchain SHA, controls, P6 MET actual SHA, output digest/bytes, hour count, concentration/real4 comparator denominators, honest `PASS_SCOPED`/`FAIL`/`BLOCKED` status) and an independently reviewable Draft PR. P7 status must not inherit an old C1/C2 PASS from a different executable HEAD.

## Dependency and completion
Implementation may begin before 2C merges, but **integration acceptance is blocked on 2C full fresh 143h native MET physical/source-provenance gates**. Existing `native_cpp.orchestration.plan` remains dry-run blocked; G5 `preprocess/upperair/met/puff/all` remain fail-closed. No changes to scientific tolerance, C1/C2 frozen oracles or Fortran vendor sources.

Status: `S2_2D=IN_PROGRESS_SOURCE_AUDIT_ONLY`, `P7_NATIVE_CONCENTRATION_EXECUTION=NOT_RUN`.

## Verified source-level blocker from the existing six-hour driver

Read-only inspection of `native_cpp/modules/p7_calpuff/tests/original_hefei_sixhour_native_receptors_tests.cpp` and its CMake targets establishes:

- The existing test can run **6 hours by default**, with an explicit `CTEAS_P7_PROBE_HOURS=7..143` extension, and separate C1/C2 integration environment selections. It is a test executable, not a clean solver command.
- That test **unconditionally reads original `puff.con`** with `read_conc_species_fields(argv[3],...)`, and may read an original DGM binary unless the special integration mode is chosen. Its post-solve comparator purpose is valid but **these inputs cannot be part of a new production P7 solver authority**. The new CLI must separate native advance/write from independent original comparison.
- The file supports `CTEAS_P7_NATIVE_PUFF_CON` to write original-compatible native WROUT1 output, and uses `create_original_hefei_2022_wrout1_writer(...)`. The writer and actual hour calculation are the viable reuse surfaces; the test driver's DGM/reference controls are not.
- `src/original_comp_hourly.cpp` implements `OriginalCompMultiPuffHours::advance_hour_pg`, which holds native puff state across hours and commits after complete current-hour success; caller remains responsible for correct source admission, retirement and sampling. This by itself is not the entire CALPUFF source-dependent production path.
- The `cteas_p7_receptors` CMake library builds `src/receptors.cpp`, `src/conc_file.cpp`, `src/hourly_conc.cpp`; P7 also has native step/cadence tests. **No reviewed, independently accepted general concentration CLI was found.**

**Next code boundary:** factor the scientific test-only reference reader/checker behind an independent comparator, while extracting the accepted native-only step/cadence/output path into a new constrained entrypoint. Preserve C1 test semantics and existing CTest; all original DGM/CON read logic stays comparator-only and must be impossible to trigger in `--execute` mode. An integration test that supplies only freshly produced native P6 MET + locked puff deck, with original `puff.con` and original DGM *physically absent*, is mandatory before any S2-2D execution PASS is claimed.
