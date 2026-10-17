# CTEAS-next scientific rerun: current status and reproducibility

**Current status (2026-10-17):**
- C1, 2022 single-station **143h**: `PASS_SCOPED`, original 2022 CALMET MET from SHA-checked frozen input.
- C2, controlled 2024 two-surface/two-upper-air **143h**: `PASS_SCOPED`, **both original Fortran CALMET 6.5.0 and native P6 fresh-ran**.
- Full all-option CALMET/CALPUFF science: **`NOT_READY`**; specifically wet deposition `MWET>0` and alternative plume-rise/dispersion/terrain branches remain unaccepted.
- The original [Issue #6](https://github.com/RRain001/CTEAS-next/issues/6) was closed as **completed for these selected scientific cases**. [PR #11](https://github.com/RRain001/CTEAS-next/pull/11) was merged.

See the **audited numeric results** in [C1/C2 science report](../science_acceptance/C1_C2_143H_RERUN_20261017.md).

## Frozen provenance and measurements

| Acceptance | C1 | C2 |
|---|---|---|
| Actual new-CTEAS Actions execution | [39001955056](https://github.com/RRain001/CTEAS-next/actions/runs/39001955056) | [39012460127](https://github.com/RRain001/CTEAS-next/actions/runs/39012460127) |
| Native P6/P7 source SHA | `41a1be3d4b6b0a00e213774e5274fe6c27b94b60` | `62fe98afdab661d90ae3327e2b068b27acd27935` |
| Source of unchanged original vendor | `RRain001/CTEAS@dfad99a78ed84d655e21411c9d25eb0d2583bf13` | Same |
| 143h native/original P6 comparison | 143×45 fields, 0 exceedances; original MET **frozen** | 143×45=6435 field comparisons, 0 exceedances; **original and native freshly run** |
| Original/native P7 A/B same-MET | 357500/357500 H-3 REAL4 | 20592/20592 H-3 REAL4 |
| Original/native P7 C/D same-MET | 357500/357500 H-3 REAL4 | 20592/20592 H-3 REAL4 |
| Reported verdict | `PASS_SCOPED` | `PASS_SCOPED` |

C1 same-MET full `puff.con` A/B and C/D files were byte-identical; C2 **only H-3 REAL4 concentration arrays**, not full `puff.con` SHA, were proven bitwise-identical. C2 input is a **controlled synthetic 2SS/2US case** and not independent observation-driven validation.

## Re-run or review protocol

1. Verify the intended `main` commit, two same-source P6/P7 checkouts, frozen source cards/time axes, and SHA256. Preserve vendor/license boundaries. The frozen `project/cases/` fixtures are tracked for reproducibility; other raw/restricted files stay local.
2. Restore permitted excluded vendor data in an ephemeral job directory with `scripts/migration/configure_external_assets.py --source-repo <authorized-local-CTEAS>` and `--check`; never publish original vendor or restricted CGIAR terrain.
3. Trigger the existing `.github/workflows/science-c1-143h.yml` and `science-c2-143h.yml` manually via GitHub Actions or with their branch-specific validated single-file request pushes; no automatic 143h runs on ordinary PRs. Both use original-vs-native A/B/C/D and require nonzero H-3 plume.
4. Preserve true source SHA, full original/native logs, job/Artifact IDs, compiler versions, source/case/output hashes, 143-hour time axis, per-field error counts and cross-MET difference statistics. Never reinterpret a C2 2024 synthetic scenario as field validation, or a C1 frozen original MET as an original CALMET fresh run.
5. Current GitHub scientific report artifacts (C1 ID `12091014129`, C2 ID `12093607182`) have short retention and are scheduled to expire on **2026-10-31**. Long-lived original `MET.DAT`/four-arm `puff.con` private storage was **not** demonstrated; treating hashes as original data is invalid. Follow up separately if long-term archival is required.

## Historical workflow recovery

The 119 inactive `.yml.disabled` experimental workflow copies were pruned from the live tree on 2026-10-17. They are still available in the exact pre-cleanup Git commit:

[Historical workflows at `2f1747434e42`](https://github.com/RRain001/CTEAS-next/tree/2f1747434e4217a99b9b9c6fed4d413e90006bd5/docs/migration/historical-workflows).

The 2026-10-16 migration snapshot `SOURCE_MANIFEST.json` remains the immutable **historical export manifest**; `scripts/migration/verify_snapshot.py` must be run against that frozen Git snapshot/worktree rather than assumed to validate the slimmed current head. Never copy archived experimental workflows back into `.github/workflows/` without new scientific review.
