# PR #63 inheritance audit against formally accepted PR #53

Date: 2026-10-14. Audit source: remote Git blob/tree and GitHub compare APIs, not PR title or comments.

**PR #53 authoritative HEAD:** `8d6642272d0abb77153880591e150f93e14d4479`.
**PR #63 audited HEAD:** `1f239e2ff0bcba3aa1b733ab3a058c5d67269a7d` (before audit-only workflow changes).
**Original superseded G13 HEAD:** `b895e4675e4ce77a7a1ff511085c1c97e458d08a`.
The PR #63 branch is a strict **descendant** of #53 (ahead 4, behind 0 at audit point).

## 1. Exact Git tree invariants

| Check | Result |
| --- | ---: |
| PR #53 tracked Git blobs | 2,640 |
| PR #63 tracked Git blobs | 2,689 |
| Added files | 49 |
| Modified existing files | 7 |
| Removed files | **0** |
| Existing accepted P6 core files inspected | **163** |
| Existing accepted P6 core changed or deleted | **0** |
| Added files with blob identical to old G13 branch | 42 |
| Modified existing files with blob identical to old G13 branch | 6 |
| Added old-branch files with intentional changes | 3 |
| Completely new added files at audit point | 4 |

The accepted immutable P6 core inventory consists of files already present at #53 under:
- `native_cpp/modules/p6_calmet/src/`
- `native_cpp/modules/p6_calmet/include/cteas/p6/`
- `native_cpp/modules/p6_calmet/p6e/`
- `native_cpp/modules/p6_calmet/p6f/`
- `scripts/p6_run_native_causal_hourly.py`

There are **exactly 163** such old files. This includes the source-selected WIND1, INTER2, SIMILT, DIAGNO, P6E heat/mixing and native single-hour/stateful execution programs. The single-station 143-hour physical algorithms are byte-identical to #53. Only the P6 module `CMakeLists.txt` and the station *test* `tests/check_case_station_contract.py` are modified outside this protected inventory.

**Conclusion for existing single-station modules: 0 confirmed incorrectly inherited/overwritten files.** This is a source-provenance finding, not a new generic physical acceptance.

## 2. Nine newly introduced P6G headers imported from obsolete G5–G13 branches

These are all **new paths**, not replacements for a #53 physical implementation. They are byte-identical to old G13 at the audit point, and their source-selected work must not be mistaken for fully integrated multi-site CALMET.

| Scope | New C++ headers (count) | Acceptance boundary |
| --- | --- | --- |
| Dynamic domain and observations | `read_geo_dynamic.hpp`, `read_surface_dynamic.hpp`, `read_upper_dynamic.hpp`, `calmet_station_set.hpp`, `observation_input_contract.hpp` (**5**) | Input geometry, multi-station identity and hourly bracket CTests; not full native scheduler |
| Multi-site first-guess | `p6g_multi_wind1_firstguess.hpp` (**1**) | Original-source selected WIND1 parity, Debug/Release; not production wired |
| Terrain correction | `p6g_terrain_hour.hpp` (**1**) | Original-source selected TERSET→FRADJ→SLOPE parity; real thermal / previous-hour integration pending |
| Thermal state | `p6g_observed_thermal_hour.hpp` (**1**) | Selected SURFVAR→HEATFX with `synthetic_radiation_fixture=true`; original SUN/CGAMMA not yet integrated |
| Multi-hour bridge | `p6g_selected_hour_bridge.hpp` (**1**) | Selective WIND1→INTER2→DIAGNO demonstration; `synthetic_identity_diagno_tail` / explicit selected terrain modes, not original COMP/PREPDI full scheduler |

**Counts:** 9/9 new P6G headers are imported experimental functionality; **0/9 have been shown to replace an accepted #53 core file**, **9/9 still lack an independently accepted complete real multi-station hourly end-to-end route**. That is a *scope/completeness gap*, not proof 9 bad numerical algorithms.

Other P6G artifacts: 2 new C++ stand-alone Fortran-comparison executables; 4 Fortran source comparator scripts; 11 new P6G test/probe `.cpp` files. These are isolated behind test targets in CMake; no production P6D/P6E/P6F native executable depends on them.

The predecessor G9 fixture used the obsolete `999999.f` missing-upper observation sentinel, whereas accepted #53 requires original `EDIT=999.f`. This was **a confirmed old fixture incompatibility**, corrected in #63 `a5913b15` (test-only 2 replacements). No accepted physics file changed.

## 3. Two imported operational preprocessor programs need separate consideration

Two **existing, potentially executable** P4/P5 data-preparation files were overwritten with bytes from old G13, not algorithmically ported from #53:
- `native_cpp/modules/p4_read62/data_prep/download_igra.py`: replaces center-latitude approximate station rectangle with published `grid.cmn` strict UTM footprint; keeps annual coverage and station fallback logic.
- `native_cpp/modules/p5_smerge/data_prep/download_isd_by_grid.py`: similarly replaces approximate longitude/latitude bbox with WGS-84 UTM projection and grid-southwest-origin station selection.

These 2 files have an **intentional input-selection behavior change** relative to #53. They are NOT edits to accepted P6D/P6E/P6F wind/heat/mixing formulas. Related P4/P5 tests and P6 station provenance test (4 other modified existing files) are also inherited verbatim from old G13. The new `engine/run_met/station_grid.py` is the shared grid authority.

Selected regression evidence: [shared P4/P5 strict UTM #38505969602](https://github.com/RRain001/CTEAS/actions/runs/38505969602), [P5 strict UTM / frozen Hefei source hashes #38505969613](https://github.com/RRain001/CTEAS/actions/runs/38505969613); **PASS**. The frozen Hefei source selection and pinned hashes are unchanged; this does NOT certify arbitrary global station manifests or real multisite full CALMET parity. New site/station metadata must be versioned and validated if the selected candidate set changes.

## 4. GUI origin and production integration

`engine/gui_g5/` contains 10 deliberately new/copied files from old G5/G13; legacy `engine/gui/` is unchanged. The copied G5 dispatcher **fails closed** for generic `met`, `puff`, and `all`: this is an intended protection, not evidence that complete P6G has a real physical production route.

The actual accepted 143-hour native chain still calls the frozen single-site executable `cteas_p6_native_hourly_driver` + fixed 50×50×9 realcase P6D / P6E programs. It does **not** call `p6g_selected_hour_bridge.hpp` or the new multi-site WIND1 kernel. G6–G13 Debug/Release selected-kernel PASS is therefore not full CALMET multi-station acceptance.

## 5. Source of truth, evidence and pending work

Existing [#63 G6–G13 selected tests #38505969622](https://github.com/RRain001/CTEAS/actions/runs/38505969622) PASS (Debug and Release, original SURFVAR source parity), [#63 G9–G11 literal original Fortran tests #38505969703](https://github.com/RRain001/CTEAS/actions/runs/38505969703) PASS (Debug and Release), G5 GUI smoke [#38505969600](https://github.com/RRain001/CTEAS/actions/runs/38505969600) PASS. [#63 143-hour original 45-field physical gate #38505969665](https://github.com/RRain001/CTEAS/actions/runs/38505969665) has scientific G3/G4 PASS on inherited source tree.

**The weakness fixed by this audit:** before the audit, the `frozen-science-ownership` workflow compared only 9 manually selected accepted files. It could miss edits to the other **154** accepted core files. The new workflow enumerates all **163** files directly from #53's Git tree and fails if any one differs in #63 or the inventory changes. Newly added experimental P6G files are not falsely treated as inherited originals.

### Final classifications

1. **Incorrect overwrite of accepted #53 single-site P6 physics:** **0 confirmed**.
2. **Added independent old-P6G source headers needing full native multi-site integration:** **9** (5 input and 4 selected-physics/bridge).
3. **Old-branch operational preprocessing programs deliberately changed from #53:** **2** (P4 IGRA and P5 ISD); scoped UTM/frozen-case acceptance PASS, more arbitrary-site tests pending.
4. **Confirmed wrong old-branch test fixture repaired:** **1 test file** (G9 missing-upper sentinel), **not a current physics failure**.
5. **Fail-closed copied GUI pending production unlock:** 1 application, 10 separate files.

**Merge rule:** keep #53 immutable, #63 Draft. Rebuild a truly generic, stateful, all-hour CALMET physical chain only after real multi-station P6D/P6E/P6F source equivalence is proven; never rename selected-test PASS to production PASS or replace original #53 formulas solely to make old G6–G13 branch compile.
