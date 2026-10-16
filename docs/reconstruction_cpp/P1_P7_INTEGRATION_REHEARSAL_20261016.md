# CTEAS P1–P7 independent integration rehearsal — 2026-10-16

## Scope and non-destructive policy

This document records the **integration branch**, not a main merge.
`integration/p1-p7` originated at main SHA
`3b94cdbfbb5f44146ba51a4ef112114f199d28b9`.
All changes and provisional science checks are confined to that branch.
Original PRs #53/#63/#68/#69 remain open and their heads are unchanged.
Do not merge any of those to `main` merely because this preflight passes.

P1–P5 were already in `main`, with scoped scientific reference
acceptance. Their numeric/reference scope is **not** broad legacy-option
equivalence, arbitrary-grid GUI support, or universal geographic coverage.

## Git ancestry / integration history

| Authority | Original head | Rehearsal operation | Result |
|---|---|---|---|
| P1–P5 | `main` | Ancestor of integration | already inherited |
| P6 single, PR #53 | `8d664227` | temporary [PR #70](https://github.com/RRain001/CTEAS/pull/70), merge commit | `eab5dc6` |
| P6 multi, PR #63 | `7a13cc6` | temporary [PR #71](https://github.com/RRain001/CTEAS/pull/71), merge commit | `9677178` |
| P7 core (PR #41/#67 already merged to its foundation) | `6d2ad9f` | guarded manual two-parent Git-tree merge; temporary [PR #72](https://github.com/RRain001/CTEAS/pull/72) automatically recognized ancestry | `334d0a5` |
| P7 C1, PR #68 | `c8dc2f6` | temporary [PR #73](https://github.com/RRain001/CTEAS/pull/73), merge commit | `03a84c5` |
| P7 C2, PR #69 | `6ff9387` | temporary [PR #74](https://github.com/RRain001/CTEAS/pull/74), merge commit | `ff20340` |

**Actual P6/P7 core conflict:** independent [no-commit dry-run](https://github.com/RRain001/CTEAS/actions/runs/38845342842)
found **nine** content-conflicted files, all in
`.github/workflows/p6d*.yml`. Two `p4-read62-*.yml`
workflow files were also touched on both branch lines but Git would
auto-merge them. No C++ physics source file was conflicted.

Resolution: retain P6 multistation accepted versions of all **eleven**
overlapping P4/P6 workflows; adopt the precise original Git blobs for the
**227 nonoverlapping P7 paths**, including 149 P7-module paths.
New two-parent merge `334d0a5` has original P7-core commit and the
integrated P6 branch as real Git parents. No squash, no source-code
conflict marker, no force push. Because two P4 workflow files were
resolved to the newer P6 copies rather than Git's auto-merged candidate,
their review history should be retained in case any later P4 CI trigger
behavior needs to be revisited.

The first automatic resolution attempt was fail-closed by a broad
whitespace audit of preexisting P7 source whitespace. The next
attempt validated all nine conflicts and unchanged P6 code but was
**blocked by the Actions GitHub App's workflow-writing permissions**.
Neither attempt pushed an integration merge. The final Git-object
two-parent merge is the only successful P7-core integration operation.
One-time diagnostic and merge-attempt workflows were then **removed
from the integration branch**; no unattended future write workflow remains.

## Source-tree SHA integrity audit (read from actual GitHub trees)

| Scoped path | Authority | Audit result |
|---|---|---|
| `native_cpp/src/p1_terrain_cli.cpp` and `src/geo/` | main | byte-identical Git blobs/trees |
| `native_cpp/src/p2_gen_fraction_cli.cpp` | main | identical |
| `native_cpp/src/p3_makegeo_cli.cpp` | main | identical |
| `native_cpp/modules/p4_read62/` | PR #63 P6 head | identical subtree |
| `native_cpp/modules/p5_smerge/` | PR #63 P6 head | identical subtree |
| `native_cpp/modules/p6_calmet/` | PR #63 P6 head | **identical subtree**, SHA `0325287b3441e4a728c470e95f7bcd97754b34e3` |
| `native_cpp/modules/p7_calpuff/` | PR #69 P7 head | **identical subtree**, SHA `4c563d8d3e58224ff4aaceee64c297386d43628b` |
| `engine/gui_g5/` | PR #63 P6 head | identical subtree |
| `engine/vendor/src/` | main | **identical untouched vendor subtree** |

The GUI's legacy `engine/gui/` subtree differs from `main`, due to
P6 development changes; it is NOT in the frozen numerical P6/P7 core
assertion. The G5 arbitrary-case P1–P7 executor remains explicitly
restricted as previously audited. Scientific source identity does not
establish GUI production completeness.

## Unified codebase science

### C2: 2024 multi-station 2SS/2US, 12×12×9 @ 10 km, 143h — PASS

[Live integration science run #38846032814](https://github.com/RRain001/CTEAS/actions/runs/38846032814):
**SUCCESS**, true original and reconstructed CALMET plus original and
reconstructed CALPUFF, all on the selected four-arm scenario.
Both C++ **P6 and P7 were checked out from one identical integration
SHA** `68d329dae01ca509f75f0b44a1e839145a9faa48`, verified by a dedicated
fail-closed same-head source step. This **does not** use pinned PR63
code for the native P6 build.

- 143h original and reconstructed CALMET 6,435-science-field gate PASS.
- A/B same original MET, H-3 REAL4: **20,592/20,592 bit exact**.
- C/D same reconstructed MET, H-3 REAL4:
  **20,592/20,592 bit exact**.
- AC cross-MET: **20,576/20,592** words matching; MAX_ABS =
  `7.450580596923828e-09 Bq/m³`.
- Scientific final line `P7_C2_143H_FOUR_ARM_SCIENTIFIC_GATE=PASS`,
  verdict `C2_ACCEPTED=true`. No original DGM injected into P7.
- This was 143 continuous model hours, **NOT the 2024 leap-year 8,784h**.

### C1: 2022 single-station original MET, 143h strict — PASS

Dedicated integrated [Actions #38846349292](https://github.com/RRain001/CTEAS/actions/runs/38846349292)
completed **SUCCESS** at 2026-10-16 04:11:59 UTC, duration
approximately 35m 41s. Source SHA for C1 verification:
`86f2cc1d9e5e9fc8404ebece5b953bc44a62c6d0`.
The original Fortran DGM generator and full 143h native C++ P7 COMP
stateful replay **both completed**.

Independent log evidence (not simply the GitHub conclusion):

- `P7_HEFEI_REAL_EXTENDED_SOURCE_PROBE=PASS HOURS=143 ORIGINAL_DGM_ROWS=254687 H3_REAL4_WORDS=357500/357500 FIRST_DIFFERENCE=NONE 143H_SCIENTIFIC_ACCEPTED=YES FULL_PUFF_CON_ACCEPTED=YES`.
- `P7_REAL_FULL_143H_WROUT1_SHA256_GATE=PASS RECORDS=3655 BYTES=1896056 SHA256=0d51bdb68ff1a5798048bc41067107d3ffe10dc6222f25336df856bcbf48ba10`.
- `P7_REAL_FULL_143H_SCIENTIFIC_PROBE=PASS HOURS=143 H3_REAL4=357500/357500 DGM=254687/254687 WROUT1=BINARY_EXACT`.
- Both original and native `puff.con` compared with `cmp` (strict byte parity).
- [Uploaded artifact #12024269127](https://github.com/RRain001/CTEAS/actions/runs/38846349292/artifacts/12024269127) contains the full native `puff.con` and replay log.

### Git object / CI conflict disposition verified again before review

Both authoritative tree snapshots and current integration-head tree snapshots
were read through GitHub (nontruncated recursive trees). P1–P3 and original vendor
source trees agree with current `main`; P4/P5/P6/G5 agree exactly with
`7a13cc6a2f2d7b4c99e18b8866043a0319733454`; P7 module agrees exactly
with `6ff9387a4f1416377a41275aed62a52c13e4b251`.
All **eleven** overlapping P4/P6 workflow blob SHAs on integration match
the P6 multistation authority, including the two that Git could have
auto-merged. No accepted P6 workflow was replaced by P7's earlier snapshot.

The current integration head includes subsequent **documentation and CI-only**
changes after the pinned 2022/2024 scientific run SHAs; the respective physical
module Git subtree SHAs were checked on the current branch and match the
accepted science authorities exactly. The new main PR itself and any
required branch-level CI still need formal review.

## Acceptance boundaries and next action

Status after final C1+C2 results: **P1–P7 GIT_INTEGRATED_ON_ISOLATED_BRANCH; C2_UNIFIED_SCIENCE_PASS; C1_INTEGRATION_FULL143_PASS; MAIN_UNTOUCHED.**

- C1 integrated 2022 143h and C2 integrated 2024 143h accepted, as documented above.
- Keep source SHA pinning evidence and review the eleven accepted P6
  workflow resolutions before final `main` merge.
- For final main integration, preserve original PR ancestry
  (merge commits; no squash/rebase history rewrite), retarget stacked PRs
  carefully, and require science CI on the **actual** new main candidate.
- This rehearsal proves scoped numerical compatibility, not arbitrary
  user-defined stack, general site/geography, full-year model runs,
  all-legacy-options parity, or end-to-end GUI/native P1–P7 orchestration.

No original PR has been merged to `main` by this rehearsal.
