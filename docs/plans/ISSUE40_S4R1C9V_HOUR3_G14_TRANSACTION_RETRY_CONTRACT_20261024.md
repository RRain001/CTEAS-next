# S4-R1c9v: real NOAA third-hour G14 atomic retry; fourth-hour preflight

## Provenance and limitations

- Stacked parent: Draft PR #308, `415bcbf03297e45bf2e0a0ed77058615b49c5c11`.
- Isolated branch: `codex/s4-r1c9v-hour3-g14-retry-contract`.
- Existing dirty `s4-r1c9u-hour3-native-p6f45-trial` remains unmodified and uncommitted. Its four-file test-only code diff was read-only applied into this isolated worktree, without copying private binary or Fortran assets.
- Exact-SHA Ubuntu Docker **full**: **NOT_RUN**, deferred until continuous P6 research batch freeze. Independent scientific review: **NOT_RUN**. Real NOAA hours 4–6 full-stage physics: **NOT_ACCEPTED**.
- Original Fortran reference is never an input into native G14. The existing original `MET.DAT` was read only by a separate comparator. Default production hour_index>1 physics guards remain in force; all new routes require explicit test-only opt-in.

## In-memory synthetic scheduler regression

`native_cpp/modules/p6_calmet/tests/p6g_g14_unified_hourly_tests.cpp` covers fresh 17-stage G14 executors and separate failure injections at hour-three COMP, G64 P6F precommit, and prepared station clocks. Failure preserves exact `ZI/ZICONV/DPTT`, model time and external publication; retries use new actor identity. Positive commit and continued synthetic hours 4–6 are checked. This is **not original/native science**.

- Ubuntu Docker DEV_ONLY run `dev-20261023T235603-335c47dc`: compiled/reran synthetic G14 regression, exit 0, including `S4R1C9V_HOUR3_SYNTHETIC_G14_RETRY_PASS`.
- Initial synthetic-only local commit `54331d92e913d097086cabb00a2c18cbefd6ec94`.

## Authentic source-native third hour: 82x85x9 NOAA, 2SS/1US

- Native G26A stages0–11 and G26B stages12–16 execute in **one fresh test-only `G65RealNoaaThirdHourTrialActor`** on the actual G14 scheduler frame with native hour-two history and committed AA/BB/CGAMMA. Stage16 G64 candidate must match the independent unpublished trial byte-for-byte.
- A first complete 17-stage attempt is intentionally rejected *after P6F candidate validation*. The scheduler remains at hour two, without altered hidden memory or station clocks.
- A new actor then repeats all 17 stages, checks the same P6F candidate, preflights clock publication, commits native `ZI/ZICONV/DPTT` atomically, and publishes AA/BB/CGAMMA after the physical commit. Fourth-hour preview carries the same committed history.
- Source input SHA256: met.inp `c5e6b02ac623a3f7d11b464deca657cd26285605753ef185bcc215257dee9744`; GEO.DAT `5feaa58e5835576b3ae2c03a51e955114d620a7aeb710ded58a9f999695f602a`; SURF.DAT `6a3f45eebdba8c7b783b5b89d5e1b3a7eecf2ce71f7fdaa814e7a54f04a9f655`; UP.DAT `a4e99dabe6ed246643bb298c3d883c8cde8a5dd07aaa346952f7e096d325ad00`.
- First real hour3 trial `/home/lhy/dev/CTEAS-next/local-science/s4-r1c9v-hour3-g14-trial-20261024`: native process exit code 0, test-only stdout G14 rollback/commit/clocks/hour4-preview `PASS_SCOPED_TRANSACTION_ONLY`; output third-hour P6F SHA256 `58d65642a1fae53fd3bce41225a0fe31ea4c08a9b0255f387e49079253769301`, identical to independently generated prior candidate.
- The separate original-vs-native comparator is only for the candidate's 45 hourly fields. Read-only original Fortran `MET.DAT` SHA256 `a7004fbf780212d58536be3957306c2aecc53abe2e58bfec870571b12d8b8e14`; comparison `313650/313650` values within **unchanged** frozen tolerances, `0` exceedances and `231976` REAL4/INT32 bitwise equal. Comparator originally labeled the input an unpublished precommit; this model-state flag is **not** an audit of G14 transaction. Separate scoped G14 test process validates transaction, not formal science.

## Authentic fourth-hour source preflight

- New test-only flag `--fourth-hour-g26a-preflight-only` runs previous two committed hours and hour-three G14 trial, then G26A fourth-hour PREPDI/WIND1/FRADJ stages0–2, with independent clocks and hidden-memory checks.
- Tested in private `/home/lhy/dev/CTEAS-next/local-science/s4-r1c9v-hour4-g26a-preflight-20261024`: process exit code 0; `S4R1C9V_HOUR4_G26A_STAGE0_2=PASS_PRECOMMIT_ONLY`; G22 unverified default hour_index>1 branch **correctly rejected**; original native hour3 candidate unchanged SHA256 `58d65642a1fae53fd3bce41225a0fe31ea4c08a9b0255f387e49079253769301`.
- Current exact test executable SHA256 `5b2bbe96041c1356b039f682e00f900c0fee4777826a9b7c05467e5a6226eb59`. GCC12 optimized incremental Docker compilation of the updated G65 CLI passed `dev-20261024T000604-d8372c7c`, `DEV_PASS`, exit 0 (no exact SHA full).
- The fourth-hour PREPDI/FRADJ test is an **input/clock/historical-state handoff**, not G22 thermal parity or completed fourth-hour output; hours4–6 45-field comparison: **NOT_RUN**.

## Next required admission

Use the revised dev-only cache for an isolated fourth-hour G22/G23/G24/G26B/G64 same-input original-vs-native stage-by-stage numerical comparison with new history and thresholds. Do not unlock default production guard, weaken tolerances, emit private data or mark P6/P7 accepted. Only after continuous hours3–6 physics and independent source provenance freeze the final SHA, run one official Ubuntu Docker exact-SHA build/full, publish software-only `ubuntu-docker-full` if warranted, and perform independent science review.
