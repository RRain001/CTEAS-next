# S4-R1c9v — third-hour G14 transaction retry contract (synthetic, test-only)

## Scope / actual provenance

- Parent: stacked Draft PR #308 at `415bcbf03297e45bf2e0a0ed77058615b49c5c11`.
- Worktree: `worktrees/s4-r1c9v-hour3-g14-retry-contract` (isolated new branch).
- Related uncommitted G64 research work: `s4-r1c9u-hour3-native-p6f45-trial`. **Do not modify or commit that worktree.** Its unpublished candidate is not an exact-SHA science admission.
- This change adds only an in-memory **synthetic** source-clock/scheduler regression in `native_cpp/modules/p6_calmet/tests/p6g_g14_unified_hourly_tests.cpp`; it does **not** enable genuine NOAA hour3 G22/G23/G26B/G63/G64 and does not produce an original-comparable `MET.DAT`.

## Enforced transition contract

Starting with two committed synthetic hours, the same `UnifiedMultistationHourlyScheduler` attempts its third hour four times, each with a **fresh G14 physics executor**:

1. Fail at COMP/MIXHT: no P6F precommit, no station-clock preflight, no physical state or clock publication.
2. Fail at P6F precommit **after all 17 native stages**: no station-clock preflight or publication.
3. Fail during source-clock publication preflight: P6F checked, but still no G14 memory or AA/BB/CGAMMA publication.
4. Positive retry: publish the complete `ZI/ZICONV/DPTT` state once, and then publish clocks only after physical commit; hour4 inherits hour3 state.

Proceed through hours4–6 without creating a second clock/memory authority. Test asserts exact hour index and UTC clock, prior-state reference identity, all three history field values, rollback bit-for-bit equality for all history vectors, lifecycle allocation/destruction counts, 17-stage dispatch, hook call counts and one-way clock publication. None of the synthetic numeric values are Fortran scientific reference values.

## Development evidence / acceptance labels

- Ubuntu Docker entry: `/home/lhy/dev/bin/cteas-s4-verify dev`, existing verification image, read-only source and isolated reusable build cache.
- Initial smoke: `dev-20261023T235402-9e89908d`, `DEV_PASS`, native CMake executable compiled and ran, exit 0.
- Strengthened source history checks: `dev-20261023T235502-892a9a20`, `DEV_PASS`, exit 0.
- Formal exact-SHA Docker build/full: **NOT_RUN** (deliberately deferred to frozen continuous P6 physics batch).
- Genuine NOAA hour3 G14 atomic commit with native hour3 G64 candidate: **NOT_RUN**.
- Original Fortran same-input six-hour 45-field equivalence and independent scientific review: **NOT_ACCEPTED / NOT_RUN**.
- Draft PRs #296–#308 remain unmerged; no change to source physics/guard thresholds.

## Next integration

1. Preserve and separately stabilize G64 third-hour P6F candidate from the existing `r1c9u` worktree, including explicit hour2 native state inheritance, input hashes, source-original 313,650-field comparator and failures.
2. In a **reviewed isolated** worktree, wire a fresh real third-hour actor through G14's same 17-stage scheduler and G64 precommit; repeat this rollback/positive retry contract with genuine NOAA, verify staged AA/BB/CGAMMA publication, prior `ZI/ZICONV/DPTT` and hour4 preview. Do not claim the present synthetic test proves this.
3. Run local targeted tests during the continuous hours3–6 implementation, then one frozen exact-SHA Ubuntu Docker full and formal independent scientific review. Do not unlock production `hour_index>1` guards based on synthetic pass.

Any quantitative claim about the real third-hour P6F remains limited to the unpublished read-only comparator evidence in the pre-existing local-science directory; the current change does not reinterpret it.
