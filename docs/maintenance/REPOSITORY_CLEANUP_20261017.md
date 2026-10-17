# Repository cleanup ledger — 2026-10-17

**Baseline:** `CTEAS-next@2f1747434e4217a99b9b9c6fed4d413e90006bd5`. **Purpose:** reduce confusion between shipped tools and historical reconstruction experiments, without any physical/algorithmic change.

## Removed from current HEAD (162 tracked paths)
- 119 **disabled** historical GitHub workflow snapshots under `docs/migration/historical-workflows/`. These are *not* active workflows.
- 30 old root `scripts/p6d_*`, `scripts/p6e_*`, `scripts/p6f_*`, `scripts/p6_diagnose_*` single-purpose forensic scripts. The still-referenced `scripts/p6d_trace_original_inter2_first_layer_143h.py` is preserved as an original-source trace precedent.
- 3 old machine-dependent migration commands: `scripts/sync_to_lhy_desktop.sh`, `scripts/bootstrap_remote_host.sh`, `scripts/migrate_runtime_names_to_met_puff.py`.
- 3 no-longer-called `.github` historical helper files: `actions/cteas-linux-toolchain/action.yml`, `scripts/assert_github_hosted_runners.py`, `scripts/p6d_verified_checkout.py`.
- 7 stale structure/path inventory files: `docs/refactor_logs/**` (6) and `docs/project_structure_for_chatgpt.md` (1).

**Retention:** all active `.github/workflows/*.yml` (4), vendor restore/check and portable CI runners, `scripts/local_gate.py`, `scripts/run_p6_end_to_end.py`, `scripts/p6_run_native_causal_hourly.py`, native P6/P7 reference comparators, full CMake/CTest sources, G5 fail-closed dispatch and both `project/cases` scientific frozen data trees. No `engine/` or `native_cpp/` files have been removed.

## Exact recovery

Every deleted blob remains in Git history; no external backup is needed to inspect it. Example:

```sh
git show 2f1747434e4217a99b9b9c6fed4d413e90006bd5:scripts/p6d_compare_original_gamma_diagnostic.py
git show 2f1747434e4217a99b9b9c6fed4d413e90006bd5:docs/migration/historical-workflows/p6d-original-gamma-real4-143h.yml.disabled
git ls-tree -r --name-only 2f1747434e4217a99b9b9c6fed4d413e90006bd5 docs/migration/historical-workflows/ scripts/
```

The `docs/migration/SOURCE_MANIFEST.json` was intentionally NOT rewritten: it documents the old export. `scripts/migration/verify_snapshot.py` is a **snapshot baseline check**, not a check that all pre-cleanup paths are still on new `main`.

## Explicit limitations

No current hardware execution was performed by this GitHub API-only cleanup. There is **no CI status to inherit** from C1/C2 runs at older commits, and 143h science would require explicitly re-triggered runs if physics or live test inputs were changed. The cleanup does not alter physics, G5 dispatch, four current workflows or frozen case data. Future manual Ubuntu software regression and Docker checks remain recommended before production deployment.

Large `project/cases/**` (roughly 441 MiB of raw tracked file sizes) and `native_cpp/**/reference/` remain deliberately in place because reproducibility and active current scientific verification depend on them. De-duplication or externalization of these assets should only occur in a separately audited fixture/storage migration.

## Second-pass results and documentation pruning

Second pass baseline: `e06db8ff5f448a1dd2186935ca0fa671a1e4f9e8`. Proposed deletion of **284** more tracked paths (case files 34, documents 248, unused scripts 2), representing **147.60 MiB** of raw tracked working-tree payload. All eight `deliverables/` copy files and old run/log outputs were removed, while the 2022 frozen MET.DAT, puff.con/puff.lst, 2023 MET.DAT and input control decks remain because current P6F/P7 CMake or C1/C2 science compare them. Frozen P6F/local-gate comparison paths now point to those retained single copies under `run/`.

Deleted historical migration evidence, low-level P6/P7 development journals, stale legacy path/installer notes and two nonessential environment diagnostic scripts. The current science report, physics option matrix, vendor hash-check manifest, current Actions and two GUI implementations remain. The deleted documentation and outputs can be recovered from the pinned pre-cleanup commit above.

**No claim of executed tests on this new branch.** Static changed-file and required-path review is not a substitute for portable Ubuntu/Docker or full 143h scientific reruns. The previously accepted C1/C2 verdict remains tied to its original source SHAs; the cleanup itself must be assessed separately.
