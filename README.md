# CTEAS-next

CTEAS-next is a **partial, option-scoped C++20 reconstruction** of selected CALMET/CALPUFF physics pathways (P6/P7) and P1–P5 inputs. It is **not** a fully equivalent replacement for every original Fortran option.

## Entry points

| Area | Authoritative location | Current status |
| --- | --- | --- |
| C++ P1–P7 implementation and validation | `native_cpp/` | Selected branches only |
| Python legacy orchestration / GUI | `engine/` and `./calpuff-cli` | Legacy-compatible; **not a native P1–P7 driver** |
| Independent G5 native-only desktop and dispatch | `engine/gui_g5/` and `./cteas-g5gui` | Generic P6/P7/all **fail closed** |
| Native scientific reference and tests | `native_cpp/modules/{p4_read62,p5_smerge,p6_calmet,p7_calpuff}/` | Retain comparator and test source |
| Frozen reproducibility fixtures | `project/cases/` | Deliberately tracked exception; do not casually delete |
| Build, smoke checks, asset-restoration | `scripts/`, `scripts/migration/` | Current utilities only |
| Current CI and science reruns | `.github/workflows/` | Agent/CI-dispatchable and guarded automatic workflows |

For physics coverage and Fortran provenance, see `docs/physics/CALMET_CALPUFF_OPTION_MATRIX.md`, `docs/physics/CALMET_CALPUFF_OPTION_MATRIX.csv`, `docs/physics/VENDOR_SOURCE_LOCATOR.md` and `AGENTS.md`.

## Verified science (2026-10-17)

- **C1 (2022 1SS/1US, 143h)**: `PASS_SCOPED`. A/B and C/D H-3 REAL4 matching **357,500/357,500** each. The original CALMET MET input is frozen (original CALMET not freshly rerun).
- **C2 (2024 controlled 2SS/2US, 143h)**: `PASS_SCOPED`. Original/native CALMET: 143 × 45 field comparisons, zero frozen-tolerance exceedances. A/B and C/D H-3 REAL4 matching **20,592/20,592** each. This is controlled synthetic meteorology, not field-observed validation.
- Detailed audited evidence: [C1/C2 acceptance report](docs/science_acceptance/C1_C2_143H_RERUN_20261017.md), [C1](https://github.com/RRain001/CTEAS-next/actions/runs/39001955056), [C2](https://github.com/RRain001/CTEAS-next/actions/runs/39012460127). [Issue #6](https://github.com/RRain001/CTEAS-next/issues/6) was closed as **completed for the scoped cases**.
- **Whole-project scientific acceptance remains `NOT_READY`**. `MWET>0`/wet deposition and other untested plume rise, dispersion and terrain variants are **not accepted**.

## Build and tests

Use Python >= 3.11. For local setup, run `./bootstrap_venv.sh`. The nine portable CMake suites and Python/G5 regression selection are maintained by:

```sh
python3 scripts/migration/validate_ubuntu.py --portable --out /tmp/cteas-next-ubuntu
python3 scripts/migration/validate_python.py --portable --out /tmp/cteas-next-python
```

The Ubuntu command requires the documented GCC, GFortran and GDAL toolchain. See `docs/deployment/CONTAINER.md` for the portable Docker verification image. Runs marked `PASS_SOFTWARE` are **not** scientific acceptance. Large scientific workflows are not blindly run for every push or PR; authorized agents and CI may dispatch them without the owner clicking Run workflow. See [Science workflow trigger policy](docs/ci/SCIENCE_TRIGGER_POLICY.md).

Original CALMET/CALPUFF vendor sources and restricted terrain must not be distributed in this public tree. An authorized local source checkout may restore and hash-check them using `scripts/migration/configure_external_assets.py`. Follow `docs/migration/THIRD_PARTY_ASSETS.md`.

## Cleanup and recovery

The 2026-10-17 repository slimming removed archived `.yml.disabled` workflows, one-off P6 forensic scripts, obsolete host-sync tools and obsolete structure snapshots from **current `main` only**. Historical contents remain available from the last pre-cleanup commit `2f1747434e4217a99b9b9c6fed4d413e90006bd5`:

```sh
git show 2f1747434e4217a99b9b9c6fed4d413e90006bd5:scripts/p6d_compare_native_cgamma_grid_143h.py
git ls-tree -r --name-only 2f1747434e4217a99b9b9c6fed4d413e90006bd5 docs/migration/historical-workflows/
```

See `docs/maintenance/REPOSITORY_CLEANUP_20261017.md`. The frozen `docs/migration/SOURCE_MANIFEST.json` records the **old migration snapshot**, not an assertion that every old path still exists in the slim current tree. For whole-snapshot verification, check out its original frozen commit in a separate worktree.

## Frozen cases after result pruning

Both case configurations, grids, raw meteorological input and current science baseline files are kept. Generated `project/cases/*/deliverables/`, captured run logs and obsolete diagnostic outputs were deleted from **current** Git checkout. Exceptions deliberately retained as **read-only scientific inputs** include the frozen 2022 `run/met/met.dat`, `run/puff/puff.con`, `run/puff/puff.lst`, the 2023 `run/met/met.dat`, and the original model input decks; CMake and C1/C2 science jobs still require these bytes. They are not dispensable without an explicit, hash-checked fixture restoration redesign.

Old complete cases and documents can be inspected at pre-cleanup Git commit `2f1747434e4217a99b9b9c6fed4d413e90006bd5` (the same content is in the older CTEAS source archive). **Deleting a path in a new commit does not erase historical Git objects or guarantee a smaller cloned .git history.** For actual history size reduction, use a separate approved repository migration rather than rewriting the accepted main history.
