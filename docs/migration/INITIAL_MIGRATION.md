# Initial CTEAS-next migration — Ubuntu, 2026-10-16

Status: **source/package migration for Draft PR review**. No automatic merge and
no new declaration of general scientific acceptance. Third-party upload rights
remain asset-specific pending items; they do not block migration of the owner's
self-developed code. See [third-party asset decisions](THIRD_PARTY_ASSETS.md).

## Exact source and old checkout protection

- Source URL: https://github.com/RRain001/CTEAS
- Actual fetched `origin/main`: `dfad99a78ed84d655e21411c9d25eb0d2583bf13`.
- This is exactly the known [PR #75](https://github.com/RRain001/CTEAS/pull/75)
  integration merge. Difference from the requested trusted starting SHA: **none**.
- Full source commit metadata: RRain001 / GitHub, 2026-10-16 15:46:15 +0800;
  parents `3b94cdbf` and `409d0911`; subject “Merge PR #75: integrate accepted
  P1–P7 C++20 reconstruction”. Exact fetch command `git fetch origin main` was
  executed and confirmed the same SHA after the initial `git fetch origin`.
- Old Ubuntu checkout: `/home/lhy/CTEAS`; remote fetch/push URL
  `git@github.com:RRain001/CTEAS.git` (no embedded credentials).
- Initial and retained checkout: detached HEAD
  `ad6848fcb6c91806dc41aa4c96bfb9cc5808f739`; `git status --short` was empty.
- Old local `main` remains `608d2949f100ee2e38054d6f987199ff5d4c0981`, which
  **is not** the newly fetched `origin/main`. Because the current checkout was
  detached, Issue #1 Stage 0's non-main exception was used: export the remote
  snapshot directly, without switching/resetting/stashing or moving local
  branches. No old history branch was deleted, rebased, rewritten or pushed.

## New independent history and tracked-file export

- New clone: `/home/lhy/CTEAS-next`, remote
  `git@github.com:RRain001/CTEAS-next.git`.
- Initial new `main`: `75865dbcf95f7a1bcb47554798e6debfedb198a5` (README only).
- Working branch: `codex/bootstrap-p1-p7`.
- Tested bootstrap source commit: `7f1a7468619129683f2ee7494d8451133b621fb0`.
  Its only parent is the independently initialized new `main`. There is no old
  CTEAS commit ancestry. Numerical source trees in the final evidence commit
  remain identical to this bootstrap and the upstream snapshot. Final review
  branch HEAD is recorded in the PR execution comment (avoids self-referential
  commit hashing inside this report).
- Export command: `git archive dfad99a78ed84d655e21411c9d25eb0d2583bf13`, extracted
  into a temporary staging directory; only the manifest-approved files were
  copied/staged. The new README was retained and extended; the old source has
  no README path collision. The exported snapshot contained **no symlinks**.
- [SOURCE_MANIFEST.json](SOURCE_MANIFEST.json) records every one of the 3,012
  source tracked files: original path, mode, Git blob ID, SHA256, size,
  classification, migrated path or explicit exclusion/local dependency.
- **2,799 source files retained**, including 119 disabled historical workflows;
  **211 external assets not committed** (209 vendor files, 2 CGIAR terrain
  crop/bbox files); **2 font files excluded**. There are no copied old Git
  metadata, credentials, virtual environments, executable binaries, object
  files, untracked workspaces or newly generated simulation outputs.

## Inventory, rationale and minimal packaging changes

The first export deliberately retains the complete tracked dependency closure:
`native_cpp/` (all CMake entrypoints, src/include, handwritten oracle drivers,
Python data preparation and scientific tests), `engine/` excluding original
vendor packages, `scripts/`, `docs/`, setup scripts and requirements, Linux
rebuild Dockerfile, binary-directory placeholders, retained small USGS land-use
inputs, and both frozen upstream `project/cases/` reference cases.

[INVENTORY.json](INVENTORY.json) gives category counts/bytes. Production C++ and
Python are distinguished from source-parity harnesses, frozen reference data,
historical forensic experiments and disabled Actions. No historical test is
silently promoted to production/scientific PASS. Historical audit documents
remain unchanged and retain their dates and original limitations.

The 1,605 `project/cases/` files (462,376,906 bytes) are a **specific frozen-fixture
exception** to the ordinary ignored `project/` workspace policy. Their exact
upstream tree is preserved because actual CMake/Python tests reference their
original paths. They include NOAA raw subsets, transformed inputs, controls,
original `.dat`/`.con`/`.lst` oracles, captured logs and manifest evidence.
They are not a copy of this machine's untracked current workspace and are not
assumed reproducible merely because they were tracked. New runs write outside
the checkout and remain ignored. Removing duplicate-looking deliverables or
old fixtures before proving dependencies would break the source-parity gates.

Packaging-only changes are confined to README, `.gitignore`, `.gitattributes`,
new `scripts/migration/` tools, `docs/migration/` evidence, and new CI wiring.
No upstream numerical source, core CMake, test assertions or tolerances changed.
The source manifest carries both original and updated hashes for the two
modified packaging files. It maps archived workflows to their exact old blobs.

## Frozen Git tree identity

The staged/committed directory trees were calculated with `git write-tree` and
`git rev-parse <tree>:<path>`, not inferred from similar-looking source text.
[Machine-readable results](TREE_IDENTITY.json):

| Path | Source tree | Migrated Git tree | Result |
|---|---|---|---|
| `native_cpp` | `677531b1a7fa85768b1ca8d0ab290efa61a0f60c` | `677531b1a7fa85768b1ca8d0ab290efa61a0f60c` | IDENTICAL |
| `native_cpp/p1` | `3879f8dd4f14495f0a849177b51744c52c9c193c` | `3879f8dd4f14495f0a849177b51744c52c9c193c` | IDENTICAL |
| `native_cpp/p3` | `8e34ca3e3db07405d92ca3229362559e33f32ab7` | `8e34ca3e3db07405d92ca3229362559e33f32ab7` | IDENTICAL |
| `native_cpp/modules/p4_read62` | `f533abc753a4752299c690e890f78876f3a99bbe` | `f533abc753a4752299c690e890f78876f3a99bbe` | IDENTICAL |
| `native_cpp/modules/p5_smerge` | `68404c2cd8781549816f2f2b11248697a344efda` | `68404c2cd8781549816f2f2b11248697a344efda` | IDENTICAL |
| `native_cpp/modules/p6_calmet` | `0325287b3441e4a728c470e95f7bcd97754b34e3` | `0325287b3441e4a728c470e95f7bcd97754b34e3` | IDENTICAL |
| `native_cpp/modules/p7_calpuff` | `4c563d8d3e58224ff4aaceee64c297386d43628b` | `4c563d8d3e58224ff4aaceee64c297386d43628b` | IDENTICAL |
| `engine` | `078ec491045ee444d52d4140d80b1a31b1ade67c` | `e93df80a23bcbc2b99ae826db66af793ced487e1` | EXTERNAL_ASSETS_EXCLUDED |
| `engine/gui_g5` | `70d0555cf611054f3ec1fac655094482187c2a64` | `70d0555cf611054f3ec1fac655094482187c2a64` | IDENTICAL |
| `engine/vendor` | `f9cc9421d1984dd0228eb12f4e57f00e8c465950` | Absent from new Git tree | EXTERNAL_ASSETS_EXCLUDED |
| `project` | `2ade3724ca7233c17a161a246ff05ff16c3da7ab` | `2ade3724ca7233c17a161a246ff05ff16c3da7ab` | IDENTICAL |
| `calpuff_terrain_and_landuse_data_crop` | `ebdddb62343adf83fb23a30f8927a0618c9566ed` | `24490ce60b9c732d555f25f85fa3a8cc386be24b` | EXTERNAL_ASSETS_EXCLUDED |

`engine/vendor` is intentionally absent from the new Git tree, so **no tree
identity is claimed for it**. Every local external vendor file is nevertheless
verified using its original blob/SHA256 manifest entry. The only `engine/`
difference is that exclusion. Likewise, the crop tree differs solely because
CGIAR terrain is external. The entire `native_cpp/` tree, P4/P5/P6/P7 subtrees,
G5 and frozen case tree are byte/mode identical.

## CI decisions

All 119 old workflows were inventoried and archived as `.disabled`
files under `historical-workflows/`; none is executable by GitHub Actions. The
scientific programs they invoke remain in their original paths, and full C1/C2
commands are preserved for review/rerun. This avoids enabling old branch guards,
self-hosted runner assumptions, artifact-fetching experiments and historical
forensic jobs in the new repository. The only original composite helper is
retained byte-for-byte but is not needed by the new explicit toolchain workflow.

**Post-review R1 CI distinction (2026-10-17):** The initial source snapshot
is a historical, immutable provenance record, not the baseline for every future
pull request's source contents. `scripts/migration/verify_snapshot.py` is
retained unchanged and should be run manually against pinned migration commit
`699b09e7ff554218d0b184fbc138b367052a94da` (for example in a detached
read-only worktree) when verifying the original migration. It is deliberately
**not** invoked by the general pull-request CI: legitimate future native/Python
source changes must be checked by builds and runnable tests, not automatically
rejected solely for differing from the 2026-10-16 source hashes. The historical
tree/hash and test evidence remains unchanged. This is an execution-policy
change, not a physical source or numerical-tolerance change.

One new read-only `ubuntu-bootstrap.yml` workflow builds all nine CMake projects,
runs the explicit external-free portable CTest/Python selections, starts G5
with offscreen Qt, and uploads command/result/selection logs. It does not restore
or upload vendor/CGIAR assets, write to Git branches, merge PRs or reuse historical
science PASS labels. The one Python test reading original SMERGE/CALMET is
explicitly NOT_RUN in portable mode; its full local execution is separate.

## Ubuntu execution environment and commands

Ubuntu 22.04.5 LTS, Linux x86_64; CMake 3.22.1; GCC 12.3.0; GFortran 11.4.0;
GDAL 3.4.1; Python 3.11.15. New `.venv` was created by `./bootstrap_venv.sh`
with uv and the unchanged pinned requirements (including NumPy 2.4.4,
pandas 3.0.2, PyYAML 6.0.3 and PySide6 6.11.0). It was not copied from the old
repository. System Python 3.10 and old default compiler executables were not
used for final validation.

```bash
./bootstrap_venv.sh
.venv/bin/python scripts/migration/configure_external_assets.py --source-repo /home/lhy/CTEAS
.venv/bin/python scripts/migration/configure_external_assets.py --check
.venv/bin/python scripts/migration/verify_snapshot.py --source-repo /home/lhy/CTEAS
CXX=/usr/bin/g++-12 FC=/usr/bin/gfortran-11 .venv/bin/python \
  scripts/migration/validate_ubuntu.py --out /tmp/cteas-next-gcc-validation --jobs 4
.venv/bin/python scripts/migration/validate_python.py --out /tmp/cteas-next-python
```

The first full local run used a 180-second CTest timeout; individual slow P6F
checks timed out and were retried with a 600-second execution budget, with
unchanged binaries/inputs/comparators. The validation wrapper now exposes
`--test-timeout` (default 600 seconds) and isolates `TMPDIR` per execution to
avoid fixed-filename collisions in upstream test helpers. This is an execution
budget, **not** a relaxed numerical tolerance. Final results and exact commands
are recorded below and in the committed evidence logs.

A second staged-file-only checkout at `/tmp/cteas-next-clean` contains **none**
of the 211 external files, either font or a virtual environment. All nine
CMake projects were independently configured and rebuilt there with GCC12/
GFortran11 and `--portable --jobs 8`. It uses the new, separately bootstrapped
Python runtime only, not imports or files from the old repository. This run
passed **33 portable CTests**; P3 has no registered CTest and is covered by its
separately executed original-vs-native harness. Portable Python passed **73**
tests with the vendor-dependent test explicitly NOT_RUN. Raw full Python
discovery in this external-free checkout first failed that one test with a
missing-vendor error; the failure is retained as evidence and no source test
was modified. Full local Python passed all **74** after external provision.
G5 and the retained PySide6 desktop both started offscreen without bundled fonts.

## Current execution results

[Machine-readable summary](VALIDATION_SUMMARY.json), with exact argv, return
codes, initial failures and reruns retained in [evidence/](evidence/).

| Suite | Configure RC | Build RC | Test result | Evidence |
|---|---|---|---|---|
| inputs | 0 | 0 | 3 PASS | [log](evidence/local/inputs-ctest.log.txt) |
| p1 | 0 | 0 | 1 PASS | [log](evidence/local/p1-ctest.log.txt) |
| p3 | 0 | 0 | No registered CTest; original-vs-native P3 comparison PASS_SCOPED | [log](evidence/local/p3-ctest.log.txt) |
| p4 | 0 | 0 | 1 PASS | [log](evidence/local/p4-ctest.log.txt) |
| p5 | 0 | 0 | 1 PASS | [log](evidence/local/p5-ctest.log.txt) |
| p6 | 0 | 0 | 62 PASS | [log](evidence/local/p6-ctest.log.txt) |
| p6e | 0 | 0 | 27 PASS | [log](evidence/local/p6e-ctest.log.txt) |
| p6f | 0 | 0 | 5 initial PASS + 3 PASS on timeout retries | [log](evidence/local/p6f-ctest.log.txt) |
| p7 | 0 | 0 | 109 PASS | [log](evidence/p7-local/p7-ctest.log.txt) |

**212 distinct local CTests passed after targeted retries**, plus all **74**
local Python tests **discovered under precisely three configured directories**:
`native_cpp/modules/p4_read62/data_prep/tests`,
`native_cpp/modules/p5_smerge/data_prep/tests` and `engine/gui_g5/tests`.
The 74 count does not assert repository-wide Python test discovery, coverage
of archived/historical workflows, or scientific end-to-end acceptance. This is not one uninterrupted green CTest invocation: P6F's
first pass returned 8 with three 180-second timeouts. Each of those exact test
commands was then rerun successfully with the same Debug binaries, data and
assertions and a 600-second limit. The sequential driver was stopped after
P6F to avoid rebuilding P7 twice; the independently logged P7 run configured,
built and completed all 109 applicable tests with return code 0.

- [Initial P6F timeouts](evidence/local/p6f-ctest.log.txt);
  [real-reference retry](evidence/auxiliary/p6f-roundtrip-retry.log.txt),
  [P6D array retry](evidence/auxiliary/p6f-array-retry.log.txt),
  [original CALPUFF reader retry](evidence/auxiliary/p6f-original-reader-retry.log.txt).
- [Clean external-free native run](evidence/clean/results.json): all nine full
  builds, 33 selected CTests, all return codes 0.
- [Full Python results](evidence/python-local/python-results.json): 74 PASS;
  [clean portable Python](evidence/python-clean/python-results.json): 73 PASS,
  1 vendor-dependent test NOT_RUN. The preceding raw discovery failure without
  vendor is retained in [its failure log](evidence/auxiliary/clean-p5-python.log.txt).
- G5, generic-stage rejection, and the retained desktop offscreen startup:
  [G5](evidence/auxiliary/clean-g5-offscreen.log.txt),
  [retained desktop](evidence/auxiliary/clean-retained-desktop.log.txt).
- [Snapshot integrity](evidence/auxiliary/snapshot-verification.log.txt),
  [external dependency check](evidence/auxiliary/external-current-check.log.txt),
  [empty-directory restoration](evidence/auxiliary/external-restore.log.txt),
  [mismatch rejection without overwrite](evidence/auxiliary/external-restore-negative.log.txt).
- Initial inherited Intel MPI CXX/FC selection failed to compile several C++20
  targets. Those obsolete probe logs are preserved under
  [obsolete-host-toolchain/](evidence/obsolete-host-toolchain/). All final builds
  explicitly used GCC12/GFortran11; no physics workaround was made.

Scoped P1/P2/P3 original Fortran comparisons were **actually regenerated and
executed in the new directory**, using unchanged upstream capture/comparator
programs and local external assets:

| Gate | Actual result | Limits / evidence |
|---|---|---|
| P1 terrain 50×50 @100m | PASS_SCOPED; all 2,500 hit-count cells match, 0 bad height cells; original 0.0500001 m printed-height and 1e-5 m unrounded tolerances unchanged | [report](evidence/p123-scoped/p1_terrain_comparison.json); no multi-CRS/void-fill/ocean generalization |
| P2 GEN fractions | PASS_SCOPED; 95,000 fields, max error 0; original/native accepted points both 10,011 | [report](evidence/p123-scoped/p2_numeric_comparison.json); other CTGPROC algorithms NOT_TESTED |
| P3 MAKEGEO no-snow | PASS_SCOPED; 17,500 float fields and 2,500 categories, no failures | [report](evidence/p123-scoped/p3_scoped_comparison.json); scoped 50×50 case only |

The P6F binary round-trip preserves all 64,762,556 bytes and the pinned SHA256
`b1823cda92280888d70b00961ab39486036a3086e18637fff21efb4f4b237d30`;
the independent P7 decoder accepts 6,435 fields. Its array-adapter rerun checks
202,500 mapped values and 11 negative cases. The original-reader regression
is an I/O/reader compatibility gate, **not** renewal of full native P6/P7 C1/C2
physical acceptance.


## Science boundaries and remaining review items

- All historical/ad hoc scientific workflows not explicitly listed as executed
  in this report: **NOT_RUN**. Optional CMake tests not registered because their
  untracked DGM assets are absent are not counted as passes.
- Complete C1/C2 strict 143h scientific workflows: **NOT_RUN** in this migration.
  Prior [C1 run 38846349292](https://github.com/RRain001/CTEAS/actions/runs/38846349292)
  and [C2 run 38846032814](https://github.com/RRain001/CTEAS/actions/runs/38846032814)
  are historical evidence only. See [exact rerun plan](SCIENTIFIC_RERUN_PLAN.md).
- Two historical P7 first-hour/six-hour receptor diagnostics were explicitly
  excluded from the initial software CTest pass: **NOT_RUN**, no renewed PASS.
- Tests mentioning 143h/8784h can be clock/input/binary-reader contracts. Their
  software results do not establish arbitrary-grid/site/year physics acceptance.
- G5 `met` (generic P6), `puff` (generic P7), and `all` stay fail-closed;
  upstream preprocessing/upper-air restrictions also remain. This PR does not
  expand accepted station counts, grids, time ranges, physics or legacy fallback.
- Rights for uploading original vendor/CGIAR/font assets remain pending. They
  are not submitted. Exact hashes, original-source identity, private local
  configuration and restoration instructions are supplied; no redistribution
  authorization is claimed.
- Historical C2 jobs depend on specific old artifacts and case inputs not all
  regenerated here. Future full reruns must pin and provision those explicitly.
- The new repository retains large frozen data fixtures to keep real tests
  runnable; a future fixture registry/LFS/storage redesign is separate work.
- ChatGPT technical/scientific review is still required in the same Draft PR.
  Do not automatically merge or mark broad scientific completion.
