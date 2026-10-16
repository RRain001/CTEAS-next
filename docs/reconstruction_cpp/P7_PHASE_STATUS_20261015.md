# CTEAS P7 — post-merge phase status (2026-10-15)

## Decision

**P7_SELECTED_HEFEI_DRY_143H = ACCEPTED / CLOSED.** This is **not** `P7_ALL_CALPUFF_OPTIONS = COMPLETE`.

Acceptance is limited to the exact original Hefei 2022 143 consecutive hours, 50×50 H-3 receptor field, single-source `METFM=1`, `MCTADJ=2`, `MDISP=3`, `MDRY=1`, `MTRANS=1`, and `MWET=0` frozen control/source data. The C++ solver generates results autonomously; original Fortran DGM and concentration records are read-only independent oracles.

## Completed evidence and integration

| Evidence / integration | Verified status | Reference |
|---|---|---|
| Uninterrupted 143h source DGM state chronology | **PASS 254,687 / 254,687** | [143h original science run](https://github.com/RRain001/CTEAS/actions/runs/38677457514) |
| H-3 receptor REAL4 float32 bit parity | **PASS 357,500 / 357,500**, no first difference | [143h original science run](https://github.com/RRain001/CTEAS/actions/runs/38677457514) |
| Full native-generated `puff.con` | **PASS**, 3,655 records / 1,896,056 bytes, binary exact | [strict independent SHA gate](https://github.com/RRain001/CTEAS/actions/runs/38684187769) |
| P7 source/science PR | **MERGED** into `codex/cteas-p7-calpuff-20261011`, not `main` | [PR #41](https://github.com/RRain001/CTEAS/pull/41) |
| Old self-hosted CI retirement | **MERGED** into the same P7 branch; P1–P6 original tests preserved | [PR #64](https://github.com/RRain001/CTEAS/pull/64) / [PR #66](https://github.com/RRain001/CTEAS/pull/66) |

Original `puff.con` SHA256: `0d51bdb68ff1a5798048bc41067107d3ffe10dc6222f25336df856bcbf48ba10`.

## P0: scientific CI lifecycle after PR #41 merge

The two expensive original-versus-native CI workflows now have a defined trigger contract for the **actual P7 integration target** `codex/cteas-p7-calpuff-20261011`:

- **Pre-merge:** `pull_request` with `base=codex/cteas-p7-calpuff-20261011` and relevant P7 source, pinned vendor/case-input or scientific workflow changes. This validates the proposed merge result. Scientific code must not be accepted without a strict 143-hour run on its PR SHA.
- **Post-merge:** `push` to that target branch with the same relevant path filters triggers automatic independent H8/H24/H48/H72 plus full H143 replay, explicitly avoiding documentation-only changes.
- **On demand:** `workflow_dispatch` remains available to repeat both tests without source edits.
- **Fail closed:** `.github/scripts/assert_github_hosted_runners.py` rejects loss of target-branch `pull_request`/`push`, P7 path-scope or manual triggers; it still requires every active workflow to use hosted runners.

Two workflows: [full 143h strict DGM/H-3/WROUT1](../../.github/workflows/p7-hefei-real-143h-independent-probe.yml) and [H8/H24/H48 strict + H72 diagnostic](../../.github/workflows/p7-hefei-real-hour7-probe.yml). These retain the original exact comparison and SHA256 gates. **Completion of this CI migration is separately confirmed only by checks on the new PR and the merged branch**, not inferred from October 15 historical scientific run IDs.

## Scope explicitly not accepted

- `MWET>0` and wet deposition/wet scavenging variants.
- Arbitrary multi-source, multi-grid, species or control-deck generalization.
- Extreme active `MXSAM=99` / SWAP / ROLLDN pressure branches not exercised by the frozen sequence.
- Production-level dynamic CALMET→CALPUFF native coupling, packaging and full cross-platform certification.

These are **future independent work items**, not reopened failures of the accepted single-deck case. The [2026-10-12 remaining-gates report](P7_REMAINING_FUNCTIONAL_GATES_20261012.md) is an explicitly historical snapshot; the [scoped P7 final acceptance record](P7_HEFEI_143H_REAL4_PUFFCON_ACCEPTANCE_20261015.md) is authoritative for the accepted case.
