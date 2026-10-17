# S2-2D: production native-only P7 executor implementation and acceptance contract

Date: 2026-10-17. Scope: **Hefei 2022 selected no-rain case only**, and the single already-tested CALPUFF physics/configuration. This is an **implementation task**, not completed science.

## Confirmed inherited upstream authority
- PR #27 (squash merged into `main` at `c8ce4a616009672c4dad4a005186fd0ea2274362`) establishes canonical grid origin **XREFKM=510.885, YREFKM=3531.269 km**, **exactly 3 decimals in km for every future case**, scoped native P6 runner, hash-checked P3/P4/P5 handoff, selected real native 143h MET.
- Real P6 1h/6h/143h and 143h × 45-field vs both frozen historical and newly rerun original CALMET have zero exceedances: [Actions #39034270535](https://github.com/RRain001/CTEAS-next/actions/runs/39034270535).
- P7 C++ numerical functions are present but exposed through `tests/original_hefei_sixhour_native_receptors_tests.cpp`, which **unconditionally reads original `puff.con`** for comparison. This is an audit/validation executable, NOT a standalone production P7 executor.
- With the pinned **frozen same-input original C1 MET**, current test executable actually calculated 143h H-3 field values and wrote native WROUT1 output, matching **357,500/357,500 REAL4** concentrations bitwise: [Actions #39031608292](https://github.com/RRain001/CTEAS-next/actions/runs/39031608292). This does NOT prove full native P6→P7.

## Deliver in PR #28

1. New narrow, supported P7 executable in `native_cpp/modules/p7_calpuff/src/`, linked in the existing `CMakeLists.txt`. A possible name is `cteas_p7_native_hefei_2022`, but do not claim it exists before committing/testing. Its only authority to start production is explicitly validated **native P6-produced** 143-hour MET, the frozen selected `puff.inp`, a canonical three-decimal `GEO.DAT`/grid/deck combination, a fresh nonexistent work dir, and a scoped source-hash manifest. Reject unrelated site/geometry/physics and accidental original-source fallback.
2. Refactor the existing scientific 143h test-only `OriginalMetHourlyReader` callback native PRFIN / `OriginalCompMultiPuffHours::advance_hour_pg` / mass/deposition/receiver accumulation / `create_original_hefei_2022_wrout1_writer` / `HourlyConcSeriesWriter` path to share one **production-owned** selected-case runner. Do not duplicate CALPUFF physics algorithms. The production runner **cannot accept any original `puff.con` or DGM path** as an argument and must run successfully when original CON and DGM are **physically absent**.
3. Keep frozen original `puff.con`/DGM readers in independent **comparison/diagnostic test** targets only, never linked into or invoked by the production path. The standalone CLI must produce **genuinely calculated nonzero H-3**, 143 continuous hourly frames, 50×50 cell grids, 357,500 H-3 REAL4 words and a deterministic WROUT1 concentration file. Treat concentration outputs after physical model execution as untrusted until separately parsed/verified.
4. Produce bounded independent execution evidence with exact C++ source HEAD, executable hashes, P6 native MET/CON output SHA/bytes, control/grid hashes, times, selected options, actual native-causal computational path, no original fallback, field/count and mass / finite checks. Do not mark `SCIENTIFIC_PASS` from process exit alone.
5. In an *isolated second comparator environment*, run **unaltered original CALPUFF 7.2.1** with **the exact same accepted native P6 MET** and frozen puff deck; independently compare every H-3 REAL4 word across all 143h, not merely file length or coarse tolerance. Success gate: **357,500/357,500** equal values (unchanged criterion); report first mismatch with H/I/J, bits and source key if any.
6. Execute 1h → 6h → 143h on GitHub Actions with staged native-only P6 MET, no original P7 CON/DGM, no G5. Negative gates: missing or wrong input hashes, non-canonical origin precision, wrong grid/station/timeline or source geometry, original CON/DGM injection, stale work dir, partial failure, all-zero H-3, malformed/partial output, wrong file count, changed model options.
7. For every new site case, adhere to **three-decimal-km UTM origin**, but add a new, independently reviewed case profile rather than weakening the locked 2022 Hefei checks or silently increasing the precision.

## Sequencing and non-negotiable decisions

- Build the native-only runner first, compile and run it without original CON/DGM (no comparator gate yet); then independently compare P7 on same MET, then add end-to-end P1/P2/P3 (fresh GEO) / validated P4/P5 / native P6 / native P7 continuous-case demonstration.
- Do not modify original vendor source, scientific thresholds, S2-2C original GEO precision policy, or G5; wet deposition not covered (IWET=0).
- Existing valid C1 same-frozen-MET P7 test is a **regression baseline**, not a substitute for the new executable.
- Keep PR #28 **Draft** until a genuinely independent production entrypoint and exact-source same-MET scientific evidence are committed and reviewed.

## Required PR reporting
For each milestone, comment on PR #28 with commit SHA, Actions link, source DATA/CASE hash, exact hour counts, first divergence or PASS, changes to assumptions, and remaining blockers. Never call a source-audit document or mock CLI a P7 completion.
