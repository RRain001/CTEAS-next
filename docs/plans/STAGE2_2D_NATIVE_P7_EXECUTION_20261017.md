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
