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
