# P7 Hefei 2022: 143-hour REAL*4 and complete `puff.con` acceptance

**Phase status (2026-10-15): FROZEN_HEFEI_DRY_143H_ACCEPTED / P7_SELECTED_CASE_CLOSED.** Acceptance applies **only** to the unchanged, single-source, dry-deposition 2022 Hefei control deck. This is not a claim of general CALPUFF feature completeness.

**Merge status:** [PR #41](https://github.com/RRain001/CTEAS/pull/41) was **merged on 2026-10-15** into `codex/cteas-p7-calpuff-20261011` (not `main`). Hosted-runner migrations [#64](https://github.com/RRain001/CTEAS/pull/64) and [#66](https://github.com/RRain001/CTEAS/pull/66) were subsequently merged into that same branch without changing original P7 physics.

**Independent science + complete output evidence:** [strict 143h SHA256 gate #38684187769](https://github.com/RRain001/CTEAS/actions/runs/38684187769) PASS: `DGM=254687/254687`, `H3_REAL4=357500/357500`, `WROUT1=BINARY_EXACT`; `P7_REAL_FULL_143H_WROUT1_SHA256_GATE=PASS`. Earlier [artifact-verifiable binary acceptance #38681259722](https://github.com/RRain001/CTEAS/actions/runs/38681259722), commit [`ff4e333`](https://github.com/RRain001/CTEAS/commit/ff4e33389842a0b3677c461efd4aaadb5f3786f8), also remains independently auditable.

**Post-merge CI contract:** `.github/workflows/p7-hefei-real-143h-independent-probe.yml` and `p7-hefei-real-hour7-probe.yml` are configured for PRs targeting and pushes to `codex/cteas-p7-calpuff-20261011`, with manual dispatch; only changes to P7 source, original frozen scientific inputs, or the gate YAML trigger expensive tests (not documentation-only edits). The hosted runner policy enforces these trigger contracts. **The new trigger wiring must be verified on its own merged commit; prior science PASS is not evidence that a newly installed trigger has fired.**

## Explicit positive evidence (not inferred from an Actions green check)

Artifact [#11948049718](https://github.com/RRain001/CTEAS/actions/runs/38681259722/artifacts/11948049718), containing `hour143-probe.log` and generated `native-full143-puff.con`, reports:

```text
P7_NATIVE_PUFF_CON_PREFIX=PASS HOURS=143 RECORDS=3655 BYTES=1896056 BINARY_EXACT=YES NO_ORACLE_INJECTION=YES
P7_NATIVE_PUFF_CON_FULL=PASS HOURS=143 RECORDS=3655 BYTES=1896056 BINARY_EXACT=YES
P7_HEFEI_REAL_EXTENDED_SOURCE_PROBE=PASS HOURS=143 ORIGINAL_DGM_ROWS=254687 H3_REAL4_WORDS=357500/357500 FIRST_DIFFERENCE=NONE 143H_SCIENTIFIC_ACCEPTED=YES FULL_PUFF_CON_ACCEPTED=YES
```

Independently calculating SHA-256 of the generated binary in the Actions artifact yields:

```text
SHA256(native-full143-puff.con) = 0d51bdb68ff1a5798048bc41067107d3ffe10dc6222f25336df856bcbf48ba10
SHA256(original pinned puff.con) = 0d51bdb68ff1a5798048bc41067107d3ffe10dc6222f25336df856bcbf48ba10
SIZE                              = 1,896,056 bytes (both)
Fortran sequential record count    = 3,655 (both)
```

The separately verified WROUT1 source-derived header is 3,226 records (96-byte version, 4-byte comment count, 3,218 x 132-byte echoed comments, and six typed metadata records). The live native driver emits an additional 143 x 3 = 429 hourly period/source/H-3 records. Every H-3 source result uses real C++ native `hour.receptor_concentrations`, written by `HourlyConcSeriesWriter`. The generator reconstructs its header from `puff.inp` and `CALMET.DAT`; the frozen vendor output is only an after-the-fact independent comparator, never injected into native plume or output generation.

## Separate real-case numerical evidence

- [#38677457514](https://github.com/RRain001/CTEAS/actions/runs/38677457514): full uninterrupted 143 h, 254,687/254,687 source DGM puff-step rows (identity/KSAM, REAL4 XY and stored SIGY/SIGZ) and 357,500/357,500 H-3 REAL4 concentration words, `FIRST_DIFFERENCE=NONE`.
- [#38677457304](https://github.com/RRain001/CTEAS/actions/runs/38677457304): 72 h, 150,437 DGM rows and 180,000/180,000 REAL4 concentration words, `FIRST_DIFFERENCE=NONE`.
- [#38674251404](https://github.com/RRain001/CTEAS/actions/runs/38674251404): 48 h, 98,288 DGM rows and 120,000/120,000 REAL4 concentration words, `FIRST_DIFFERENCE=NONE`.
- Source-only original WROUT1 full header test `cteas_p7e_original_wrout1_full_native_header` passed on hosted CI; the complete end-to-end original `puff.con` is accepted by the full 143 h run above, not by the standalone synthetic writer test.

## Boundary of the acceptance

This is a fixed **50 x 50 CALPUFF receptor grid, 143 one-hour fields, 2022-01-01 through 2022-01-06**, locked `METFM=1`, one original point source (`NPT1=1`), original two-species H-3/HE-3 source with H-3 grid OUTPUT, `MCTADJ=2`, `MDISP=3`, `MDRY=1`, `MTRANS=1`, and `MWET=0`, in the selected source/case. The accepted target is **IEEE REAL*4 bitwise original-equivalence**, with no fitted tolerance, no vendor state injection and no source relaxation.

**Not demonstrated:** arbitrary alternative CALPUFF input decks, multi-source or multi-grid generalization, other deposition/chemistry branches including `MWET>0`, real-case activation of `MXSAM=99`/slot-compaction pressure outside observed occupancy, independent plume physics beyond this source configuration, or production packaging. A full file SHA match is strong evidence for this *single* frozen end-to-end path; it is not an all-configurations certification.


## Phase-close and forward scope (2026-10-15)

- **CLOSED — P7 selected real case:** Original-ordered, autonomous native 143h source-to-receptor H-3 transport, dry deposition, 254,687 DGM puff substeps and complete 3,655-record `puff.con` equivalence; original model, frozen inputs, and numerical acceptance thresholds are unchanged.
- **P0 CI wiring:** Full 143h strict and early-hour regression workflows are target-branch PR/push/path-scoped and manually dispatchable. PR review must inspect checks on the **current SHA**, not only historical successes. On a P7 science-code PR, the long test must pass before scientific integration. Following merge, a target-branch push reruns the same frozen strict gate; docs-only PRs do not invoke the expensive replay.
- **Not included in this completed case:** wet scavenging `MWET>0`, multi-source and other original decks, extreme active `MXSAM=99`/SWAP/ROLLDN pressure, broader CALMET→CALPUFF production integration, OS/compiler portability and packaging. Track and validate these separately; never silently broaden this acceptance.
- **Historical records:** [P7_REMAINING_FUNCTIONAL_GATES_20261012.md](P7_REMAINING_FUNCTIONAL_GATES_20261012.md) and intermediate six-hour debugging notes preserve chronology; their old "OPEN", "Draft" and "not accepted" entries do not override this bounded full-143h acceptance.

## Follow-up / reproducibility controls

1. Keep a strict hosted acceptance gate that fails unless the H143 DGM count, all 357,500 concentration words and complete 3,655-record binary output agree. Do not infer scientific acceptance from a green workflow when the probe is exploratory.
2. Keep early H8/H24/H48 regression gates and the original H9 puff598 dry-mass chain. Recheck any updated branch SHA against its own CI; an earlier passing SHA does not automatically certify later changes.
3. Preserve original case SHA256 and exact original vendor source hash as read-only CI authority; do not copy oracle states or binary output into native emission.
4. Tackle unsupported modes only as separately scoped P7 milestones. MWET remains deferred and is not implicitly accepted by this report.
