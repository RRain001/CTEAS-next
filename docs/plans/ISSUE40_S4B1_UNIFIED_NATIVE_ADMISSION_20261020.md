# Issue #40 / S4-B1 — common original-source admission boundary

Date: 2026-10-20. This is a **software-scoped** intermediate PR.
S4-A was merged in [#201](https://github.com/RRain001/CTEAS-next/pull/201) at `087d27a23107587ba8ec33817dbc8a364dd3117e`, confirming C1/C2 use different selected P6 binaries. B1 does not alter the accepted formulae or their old call paths.

## Architecture and ownership

1. The only new CLI `cteas_p6g_s4b1_source_admission` accepts `--admit-only met.inp GEO.DAT SURF.DAT UP1.DAT [UP2.DAT ...]`. The UP list is **ordered** exactly as the original `NUSTA` declarations. There are **no fixed Hefei, 58424, 50x50, 12x12, or 143h gates** in this new admission layer.
2. It delegates original READCF met controls, source station identity/coordinates, selected-options control and GEO/SURF/UP data/UTC bracket checks to the pre-existing `g19_load_original_source_case()`. The existing `source.make_scheduler()` owns UTC and committed G14 input-hour authority. Neither is independently reimplemented here.
3. The new C++ admission value checks dynamic `NX × NY × NZ=9`, independently variable `NSSTA>=1` and `NUSTA>=1`, nonempty hours, true original-source + chronological G14 authority and checked size arithmetic. It **never** infers real science validity from mere station numbers.
4. **Physics ownership not yet granted**. No `G26::run()` production enabling, no duplicate STHEOR/INTER2 implementation, no COMP memory mutation, no P6F output, no original `MET.DAT` backfill and no change to C1/C2 frozen programs. `--execute` is explicitly refused.
5. Tests cover 1/1, 1/2, 2/1, 2/2 and other independent station sizes, non-Hefei geometry and non-143h spans; negative cases cover zero SS/US, invalid grid/layer/hours, unauthenticated inputs and integer-overflow sizing. **These are value/contract tests, not proof the actual original files nor subsequent physics support every combination.**

## Follow-on numerical gates

- **B2/B3:** implement a new physically authoritative single G14 runner in one binary using the existing tested G26 DIAGNO + G26B COMP + P6F, with explicit source/stage/precommit/postcommit ownership. Keep G26 production `Unknown,false` until the shared execution and original reference pass. Do not fork another Huoshan-only path or modify accepted physical formulae without a separate original-science audit.
- **C:** bind actual legal 1/1, 1/2, 2/1, 2/2 source files to that new binary; if original CALMET or a selected kernel rejects a combination, record `UNSUPPORTED`, do not synthesize stations or relax original constraints merely for acceptance.
- **D:** same new binary C1 143h vs frozen original reference (explicit `C1_ORIGINAL_FRESH=NO`), C2 143h vs freshly run original, then independent original-vs-native new-site 45 fields/hour. Do not accept field shape alone as parity.
- **E:** P7 after the scientific gate, tracked in #36.

Retained: C1 and C2 `PASS_SCOPED`; current S4-B1 admission `PASS_SOFTWARE` only after CI; unified production `NOT_IMPLEMENTED`; original new-site P6 science `NOT_ACCEPTED`. Docker, wet deposition and S5 capacities are excluded.
