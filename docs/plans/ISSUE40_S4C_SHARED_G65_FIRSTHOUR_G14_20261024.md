# Issue #40 S4-C — same unified S4B2 executable runs genuine WATER first-hour G14 17 stages

Date: 2026-10-24. This **does not** accept production P6, multiple real-water hours, P7, nor independent scientific review. PR #308 remains Draft.

## Physics reuse, no new formulas

Original G65 first-hour `G65RealNoaaFirstHourActor` was moved without editing its numerical stages into `p6g_g65_shared_noaa_firsthour_actor.hpp`, now included by the original G65 research executor and the **same S4B2 parameterized executable** used by the accepted C1/C2 land-source research baseline. Both instantiate the exact G26A 12-stage and G26B 5-stage native actor with one G14 scheduler and atomic state/clock transaction; no original `MET.DAT` or vendor intermediate array enters the solver.

S4B2 adds an explicitly scoped `--selected-experimental --water-firsthour-g14-trial-only` research mode, requiring a full genuine six-hour source (`--hours 6`), a **one-hour-only** causal execution (`--probe-prefix-hours 1`), unoccupied `--out`, and rejecting simultaneous source-only preflight, `--g26-normal-entry-trial` and state trace. The actor only admits studied 82×85×9, 2SS/1US, 63 WATER, 6h source geometry; other source shapes fail closed. The existing all-land path and production rejection are unchanged.

G41 reads authentic original NOAA station/GEO/UP clocks and HFLUX source. G43 recreates CALMET COMP's **five non-wind missing-value fields** for the first hour in a detached G14 source copy; original P5 wind and precipitation values are checked to be identical and are **never** filled. Before the program emits any MET output, the shared G65 17-stage actor must produce a complete native P6F dataset, pass internal state and station-clock precommit, and commit the G14 transaction; output is written to a fresh path. This is a scope-specific *trial*, not an unconditional native G26 production path.

## Fixed local original/native independent comparison

Inputs from private Ubuntu `local-science/s4h_huoshan_xinqiao_true_2ss_2022/` were held fixed. Their SHA256 values are recorded in `ISSUE40_S4C_WATER_SOURCE_PREFLIGHT_20261024.md` and remain unchanged. The original Fortran six-hour `run/met/met.dat` is a previously frozen read-only result, SHA256:

`a7004fbf780212d58536be3957306c2aecc53abe2e58bfec870571b12d8b8e14`.

The current fresh GCC12 S4B2 trial binary generated a *separate* first-hour native `MET.DAT`, SHA256:

`d8e6065e2d26bc517f72619bd1822c6832d04ec7c42c4b93d12d32910a3c984c`.

The independent `scripts/s4/s4c_compare_noaa_unified_firsthour.py` reads original six-hour Fortran sequential unformatted 2.1 records and the one-hour native result **after solver execution**; it enforces the known expected field labels, 82×85×9 / 2SS/1US original headers, hour timestamps, and original/native SHA identity. Frozen field-specific tolerances from the existing independent R1c8i/R1c9ah comparators are unmodified.

| Scoped criterion | Outcome |
| --- | --- |
| Original Fortran fixed comparison interval | 2022-06-01 01:00–02:00 UTC (hour 1 of original 6h file) |
| Native G14 actor runs all 17 stages / commits state and clock | YES, same shared G65 first-hour actor, fresh S4B2 CLI |
| Independent grid REAL4/INTEGER4 values compared | **313,650 / 313,650** (45 fields × 6,970 cells) |
| Bitwise-equal REAL4/INTEGER4 words | **298,578** |
| Frozen-tolerance/INTEGER4 exceedances | **0** |
| Standalone native P6F candidate | `PRODUCED_UNVERIFIED` before independent comparison; then `PASS_SCOPED_S4C_UNIFIED_FIRSTHOUR_FORTRAN_45` |
| Generic CALMET P6, NOAA hours 2–6 in unified executable | **NOT_ACCEPTED / NOT_RUN** |
| P7, second independent site configuration, external independent reviewer | **NOT_RUN** |

Private result files and report: `/home/lhy/dev/reports/cteas-s4c-unified-20261024/s4c-shared-firsthour-native.met.dat`, `s4c-shared-firsthour-vs-original.json`, and S4B2 stdout/stderr. They MUST NOT be committed or uploaded to the public repository. The original Fortran CALMET was **not rerun in this batch**; it is the prior fixed-sha six-hour original output.

## Fail-closed negative/software checks

- Rebuilt the original G65 research target and S4B2 target with GCC12 in the independent P6 CMake build; both compile successfully using the same extracted class.
- `p6g_s4c_water_shared_firsthour_no_implicit_production` verifies research opt-in, no production default, exact declared six hours / one-hour prefix, no normal-trial mixing or tracing, no duplicate flags, and no output on absent actual inputs. `p6g_s4c_water_source_cli_fail_closed` and `p6g_s4b2_no_implicit_production` remain.
- Python `test_s4c_compare_noaa_unified_firsthour.py` verifies independent audit refuses reference=candidate and wrong SHA or occupied audit path.
- All scientific pass statements here remain scoped to the original NOAA **hour 1 only**. Validated physical code does not imply unconstrained production support or unchanged C1/C2 full 143h at the newly modified SHA until those regressions are rerun.

## Next milestones

1. Refactor G65's hour-two native actor and G66 prior WATER P6F handoff into the shared G14, keeping the UTC/ZI/ZICONV/DPTT boundary guards and G43 per-hour model-internal MISSFC (raw wind unchanged).
2. Independently validate hour 2 45 fields with original same-source Fortran, including failure rollback, before hours 3–6. Prevent the current firsthour flag from being used for more than one hour.
3. Complete all six hours and selected C1/C2 143h plus additional site / station configuration on the same candidate binary, then request scientific review by a separate real human. Do not enable `science-validated`, `merge-verified`, merging or P7 before the applicable gates pass.

Formal multi-architecture Docker release verification remains post-S5.
