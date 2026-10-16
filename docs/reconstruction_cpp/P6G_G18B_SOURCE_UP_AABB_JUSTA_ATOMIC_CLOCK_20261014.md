# P6G G18B — source-bound per-US AA/BB/JUSTA with transactional model-hour state (2026-10-14)

**Scope:** PR #63 (Draft), stacked on frozen validated single-site science PR #53. This is the G18B1/B2 **input/state integration slice**. It is not an independent complete vendor Fortran multi-site CALMET 45-field pass.

## Problem and original physics ownership

G18A used caller-supplied fixture `MIXHT` sounding buffers `AA`/`BB` and `JUSTA`. Merely using the chronological older/newer observations in that array is wrong after physical two-slot turnover: CALMET 6.5.0 uses two physical slots (AA and BB) whose chronological identity changes on each new sounding. The accepted PR #53 `p6::CompBufferedTimeline` establishes the original selected route: initial AA=observation 0, BB=1, then swap loaded slot on each bracket advance. For station (u), with chronological earlier sounding index `e` in the file, `JUSTA(u) = +1` when `e` is even, `-1` otherwise. Each US may turn over at a different hour. `G18BUpperBufferClock` only binds and validates **existing** G7b `UpperSeries` and G7c `InputHour::upper` chronological source records; it does not create or alter meteorological physics.

## Implemented

- New `p6g_g18b_upper_buffer_clock.hpp`: validates each original model-hour UTC timestamp and station identity, contiguous source sounding indices, actual vs G7c computed past/to-go/gap seconds, strict physical thermal heights and their valid flags. Projects chronological older/newer to **physical** AA/BB and JUSTA independently per US and retains station IDs, indices, turnovers and read counts for auditing.
- New `g18b_bind_physical_upper`: passes source-authenticated thermal profiles to the existing frozen `p6e::MixhtObservedMcInput`. The binding independently verifies **content** against original UP source temperature/height values, not only indices and time. It **does not infer or overwrite NEARU/IUPT or CGAMMA**. The G18A `selected_comp_mixht_with_observed_upper` wrapper replaces its previous fixture AA/BB/JUSTA for the selected verified path and continues to invoke the unchanged PR #53 MIXHT/WSTARR kernels.
- **G18B2 transaction correction:** `select(frame)` is a pure preparation and **does not advance** its internal committed two-slot clock. `commit_after_completed_g14_hour(frame, prepared, completed_g14_hours)` requires the G14 scheduler's actual completed-hour counter to equal `frame.hour_index+1`, revalidates the source payload and only then advances; a failed later COMP/TEMP3D/P6F stage leaves the cache unchanged so the **same hour is retryable**. This does not fake an earlier physical output or complete a G14 stage.

## Negative and integration tests

The existing `p6g_g17b4_original_iavet1_pre_and_post_fradj_surfvar` CTest now checks:

- A source-typed 2US hour is bound without inventing physical AA/BB, and G18A receives the exact same physical sounding/slot content.
- Rejects a forged JUSTA sign or a forged AA temperature with unchanged IDs/timestamps.
- Thirty consecutive 2US hours across **2024-12-31 → 2025-01-02**, with independent upper station sounding schedules, include nonuniform station turnover times, an actual `JUSTA=-1` period, and source slot parity after each turnover.
- Deliberate second-station input corruption rejects an hour **without advancing first-station state**. A later COMP failure simulation permits repeating the same prepared hour; premature, duplicated and stale commits all fail closed.
- Prior G17C1–G17D and G18A tests, the frozen 163-core-file guard, source original AVETMP and G9/G10/G11 Fortran selected tests remain mandatory. No physical equations or tolerances modified.

## Honest limitations and next G18B work

- This validates the source input/slot semantics, **not** general original CALMET multi-station COMP numerical parity, nor full year-long physical model output. The cross-year clock test is an **input/state test**, not a simulated 30-hour or 8784-hour native CALMET.
- The original CALMET **NEARU grid→upper station assignment**, `IUPT` override, upper-air AA/BB temperature interpolation to model faces, `CGAMMA` current/retained lapse branches, and general multi-site control parsing still require source-backed adaptation and direct original Fortran proof. NEARU remains explicitly fixture-scoped in G18A.
- G18A's `explicitly_test_only` remains mandatory. Full native G14 all-17-stage `COMP`, AVEMIX, TEMP3D, P6F and 45-field 1h/6h/143h/year original Fortran equivalence remain pending. Continue to keep PR #63 Draft and PR #53 frozen.

## Verification

Use GitHub-hosted Ubuntu `P6G multistation on accepted single-station baseline` (Debug/Release 17-test CTest and frozen-core guard), original G9/G10/G11 vendor parity, and the inherited PR #53 143-hour full science gate. Verify each conclusion on the **exact HEAD SHA**; this note is not an assertion of green CI before the run has finished.
