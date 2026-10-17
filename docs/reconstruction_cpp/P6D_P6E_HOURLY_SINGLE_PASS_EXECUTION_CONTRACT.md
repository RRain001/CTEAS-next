# P6D/P6E: original CALMET single-pass hourly scheduler, integration contract

Date: 2026-10-13. Target: original CALMET 6.5.0, frozen Hefei 2022, 50×50×9, 143 hourly intervals, HTFAC=1. Physical status: **NOT PASS**.

## Main finding (do not conflate algorithm parity with callgraph parity)

The old `scripts/run_p6_end_to_end.py` runs the complete 143h P6D producer, writes a partly original-backed CALMET.DAT with P6F, and runs the complete 143h P6E producer; an optional follow-up consumes its earlier P6E state on a subsequent P6D pass. This is a **forensic multistage replay**, not original CALMET's one-pass COMP/DIAGNO model.

The old script now explicitly records `scientific_acceptance=NOT_PASS` and `native_single_pass_comp_diagno=false`. `--require-native-single-pass` rejects that route without running the scientific comparison. Its legacy `status` remains a *diagnostic comparator exit status only*. Do not elevate a green workflow to G2/G3/G4 acceptance.

Reference reads in P6F `--statics-from` and `--met-fields-from` may assist investigations, but must never be used as native physical outputs in an accepted solver.

## Selected-case original source order to port, without replays

The original source callgraph is recorded in `P6D_CALLGRAPH_COMPLETENESS_AUDIT_20261013.md` on PR #51. Source anchors: COMP calls DIAGNO near L4511; PREPDI near L4424; DIAGNO FRADJ L5643; HEATFX/AIRDEN/ELUSTR/SLOPE L5685–5732; first WINDBC(UG,VG) L5748; STHEOR/ELUSTR2/MIXHTST near L5943–5952; INTER2 L6055/6059; **HTFAC=1 second WINDBC(U,V)** L6092–6101; SMOOTH/DIVCEL/W L6119–6148; COMP MIXHT L4692–4699, AVEMIX L4715, WSTARR L4744, TEMP3D L4766.

Native single-pass contract:

1. Before hour `n`, own one committed `REAL*4` state (ZI, ZICONV and /TJMP/ DPTT), initialised according to original SETUP. PREPDI/CGAMMA for hour `n` reads *hour n−1* ZICONV, not current hour ZI.
2. For hour `n`, consume real SURF/UP observations and run native PREPDI then DIAGNO; distinguish WIND1 neutral SIMILT station profile from the STHEOR→ELUSTR2→MIXHTST→SIMILT station calculation. Honor original missing-data sentinels and REAL*4 conversions.
3. Execute FRADJ with the native CGAMMA, HEATFX/AIRDEN/ELUSTR, then SLOPE using these same-hour native QH/TEMP2D. Capture first WINDBC(UG,VG), then INTER2, **then second WINDBC(U,V) for HTFAC=1**, then SMOOTH→DIVCEL→W. Do not keep only the first boundary snapshot.
4. Station STHEOR/ELUSTR2/MIXHTST updates /TJMP/ DPTT *before* COMP grid MIXHT in this same hour. Pass this mutated state to COMP (not the old DPTT from hour n−1).
5. Run COMP's native grid MIXHT/AVEMIX/WSTARR/TEMP3D and commit the full updated grid state only after all hour-n native stages and native output are complete. Failed hour must leave prior state and clock unchanged.
6. Serialize the independently generated complete hour to the C++ CALMET.DAT writer. Do not read original met.dat except in the separate comparator.

## Code delivered in this branch

`include/cteas/p6/hourly_comp_scheduler.hpp` provides a strict C++20 single-pass hour authority with immutable preceding-hour memory, 17 source-ordered hooks, selected HTFAC=1 double-WINDBC ordering, grid state validation, all required native output arrays, provenance rejection for original Fortran oracle or frozen reference backfill, and rollback of state/clock on an aborted hour.

`tests/p6_hourly_comp_scheduler_tests.cpp` uses a **test-only deterministic adapter** to validate 143 consecutive transitions and rejection of state leaks, gaps, wrong inputs, reference injection, missing W and partial-case PASS claims. The GitHub-hosted workflow builds this scheduler on ubuntu-22.04. This contract test is *not* original physics equality; it adds no isolated formulas.

**Unimplemented and blocking:** the existing monolithic `realcase_wind_field_main.cpp` and P6E `calmet_dat21_tool_main.cpp` loops still need to be extracted into *real native per-hour kernel adapters*. Neither is yet wired to the new callback interface. A mock or stub MUST NEVER count as successful scientific execution. No native 45-field output is yet claimed.

## Next code changes — prioritize integration, NOT more stand-alone physics tests

- **G2a**: factor the existing P6D whole-period driver into a reusable native `step_diagno`, holding true COMMON-equivalent memory. Bind native PREPDI/WIND1/FRADJ/SLOPE/INTER2/tail into the first 12 scheduler stages. Retain the selected-case original order without changing validated kernels.
- **G2b**: factor existing P6E `emit_realcase` internal for-loop into native `step_comp` called immediately after that hour’s DIAGNO, with station DPTT mutation and same-hour wind. Replace independent `previous_zi/ziconv/dptt` loops with the scheduler’s single committed state owner.
- **G2c**: run **one** ordered native 143h loop from inputs. Source-instrument original CALMET at PREPDI, WIND1, two WINDBC snapshots, post-INTER2, post-SMOOTH, COMP post-MIXHT and TEMP3D. Compare state at hour 1, hour 6, **first divergence hour 12**, and all 143 hours. Gate real source states, not only stage order.
- **G3**: strict independent C++ 27 U/V/W fields × 143h numeric acceptance; reject any omitted level, change to original tolerance, or Fortran-injected value.
- **G4**: full native 45-field CALMET.DAT output, original met.dat **comparator only**, no `statics-from`/`met-fields-from` as physics. P6F format parity remains a separately proven capability.
- **G5**: only after frozen Hefei succeeds, broaden grids/stations/options. Precipitation and wet deposition stay explicitly deferred.

The existing numeric failures in PR #51 (low-layer INTER2 deviation first at hour 12, WFACE continuity and real SLOPE drivers) remain blockers even if G2 scheduler contract CI passes. Correct them against actual native state propagation rather than hiding them behind oracle feeds.

## Merge policy / branch topology

- #9 is the accepted SLOPE kernel; #10 stays closed, not merged.
- #52 is merged to #40 (input acceptance), but #40 remains Draft until its own downstream CI/science is resolved.
- #46 is merged to #42 (independent 143h WIND1/PREPDI evidence); #49 is merged to #11 (P6E E42 evidence). Neither belongs directly in main yet.
- #44's first WINDBC correction cannot be used alone as source-order completeness: PR #51 also needs the HTFAC=1 **second** WINDBC.
- Preserve separate historical #23/#38/#39 and source-forensic #43/#45/#47/#48/#50 until code ownership and ancestry are reconciled. Do not blindly squash or rebase validated reference traces.
- Use this branch as an integration staging PR **targeting #51**. Keep Draft while real native DIAGNO/COMP adapters, strict 143h parity and independent writer are absent.


## 2026-10-13 implementation follow-up (PR #53, latest)

- Corrected the scheduler's native W vertical array contract to **(NZ+1) × NX × NY** = 10 × 50 × 50 floats per hour; CALMET.DAT writes only the top 9 faces (WFACE1…9). No reduction of native W state is permitted.
- Added `p6e/native_hourly_comp_steps.hpp`: **existing** physically implemented C++ MIXHT, AVEMIX, WSTARR, and TEMP3D are now callable in this original-order hourly frame, with prior-hour ZICONV and current-hour station-cell DPTT consumed in the correct positions. `CompGridMixht` restores the original MIXHT initial-ZI and previous ZICONV/DPTT contract; updates all current-hour MIXHT states and then AVEMIX before WSTARR/TEMP3D.
- A six-hour native COMP integration test passed on GitHub-hosted Ubuntu, with upstream DIAGNO explicitly **a test fixture**. No fabricated Fortran reference comparisons or new physics formulas were introduced.
- The actual existing `p6e_calmet_dat21 emit-realcase` production executable now has an **opt-in** `--native-hour-comp 1` mode which executes these same four native COMP functions with a per-hour state frame and commits thermal history only after TEMP3D. This mode requires `--station-flux-csv` from native P6D; refusing the old approximate refresh if absent. The original E42 path remains unchanged by default.
- Native P6E source-build and frozen original-wind 143h 18-field baseline strict gate passed once after production-source modification: GitHub Actions run `38340366186`. A further hosted gate compares default and opt-in real-COMP paths over all 143 hours, **both fed by the same native P6D station ELUSTR2 inputs and original frozen wind**, and requires candidate CALMET.DAT byte-identical outputs. It is a *migration guard*, not standalone physical acceptance.
- Remaining primary integration task: transform P6D monolithic wind producer into a **true native per-hour DIAGNO adapter** and feed same-hour U/V/W to these COMP steps under `P6SinglePassHourlyScheduler`. Original `met.dat` must then become read-only comparator. Until that is done, `G2/G3/G4=NOT_PASS`.

### One-P6-focus PR dependency ledger (do not claim merged siblings are in this branch)

| PR | Purpose / disposition |
| --- | --- |
| #8 | Older overall P6 draft; not the active integrator. |
| #9 / #10 | #9 canonical merged SLOPE, #10 closed duplicate. |
| #40 / #52 | Original SS1/US1 station geometry and P5 strict UTM: #52 merged **into #40**. #40 does **not** automatically propagate into #53. |
| #42 / #46 | Source-first P6D REAL*4 reconstruction: #46 merged **into #42**. #42 has diverged from #53; reconcile test/source changes deliberately, not blind merge. |
| #11 / #49 | P6E source implementation: #49 merged **into #11**. Its historical merge does **not** imply #53 contains the #49 workflow. |
| #43–#48, #50 | Frozen source and native-CGAMMA forensic lineage already underpinning #51 where applicable; preserve trace provenance. |
| #51 | P6D full-wind scientific blocker and immediate parent of #53, remains Draft. |
| **#53** | **Only active P6D/P6E source-ordered integration branch**; real hourly COMP adapter in code; DIAGNO adapter and science gates remain open. |

Do not merge #53 into #51, #51 into #42, or any incomplete P6 branch into main just because the contract CI is green. Future PR consolidation should occur only with the exact ancestry, reference SHA and 1/6/143-hour gates checked; closing historical drafts before their sources are accounted for risks losing verification evidence.

### Actual native P6D single-hour entry point, follow-up acceptance

The existing `cteas_p6_realcase_wind_field` production executable now supports `--first-hour N --hours 1` with **N zero-based, 0…142**. Default without that flag is unchanged (143-hour existing path). It computes PREPDI-selected 2022 observation time labels through hour N, but only runs DIAGNO wind physics for the requested hour. When `--comp-state-prefix` is provided, the input loader requires only previously committed P6E hours, **not future COMP data**. The consumer at hour N reads ZI/ZICONV/DPTT from interval N−1 (hour 0 starts with CALMET's original zero state). Missing native COMP streams fail closed. Metadata now records `first_hour_zero_based` and actual emitted record count.

GitHub-hosted actual executable integration [run 38341051142](https://github.com/RRain001/CTEAS/actions/runs/38341051142), job `Real P6D station input to P6E 143h native COMP vs prior COMP byte parity`: the new `scripts/p6d_verify_single_hour_windows.py` ran the native P6D full 143 hours with a P6E-produced COMP state history, then ran the *same C++ executable* independently for intervals 0, 5, 11 and 142 with the same history. It compared **13 physical float32 field planes for each hour, 52 planes overall; 0 missing, 0 extra, 0 byte mismatches**. This confirms correct time-index and N−1 input selection for actual production P6D, including hour 12, but DOES NOT prove parity to unchanged original Fortran. The same hosted run also reproduced **143h bit-identical P6E native-hour COMP and legacy COMP files**.

**Status:** per-hour P6D entry and real per-hour P6E COMP code paths each exist and have exact migration acceptance. The missing next integration is a single orchestration authority to call native `DIAGNO(hour N)` and immediately `COMP(hour N)` without prior full-period P6E reference winds or external whole-period state reconstruction. Once connected, strictly compare original 27 wind and 18 P6E fields. Until then `G2/G3/G4=NOT_PASS`. No old source or frozen reference files modified.

## PR hygiene consolidation and actual causal execution (2026-10-13)

**15 older PRs closed without merge and with per-PR immutable-head archive comments**:
- Superseded/canonical P6 diagnostic children: #23, #38, #39, #43, #44, #45, #47, #48, #50.
- Former self-hosted runner migration, obsolete now that GitHub-hosted public Actions are used: #34, #35, #36.
- Historic P6 umbrella and P6E separate branch, and non-merging independent audit report: #8, #11, #37.

Exactly **four P6 PRs remain open**: #40 (input contract), #42 (source-first REAL4 independent verification), #51 (parent P6D source and scientific defects) and #53 (the ONLY active P6D/P6E integration implementation). P7 #41 remains separate. GitHub-close is **NOT git-merge**: some archived branches contain unique commits absent from #53, retained for explicit source review, not considered accepted.

`scripts/p6_run_native_causal_hourly.py` now executes actual realcase C++ modules on the frozen 2022 Hefei case in the original causal order **P6D hour N → native P6E COMP hour N → commit hours N ZI/ZICONV/DPTT → P6D hour N+1**. This path never feeds frozen original CALMET.DAT **winds** to P6E. P6E's experimental `emit-realcase --native-hour-comp 1 --native-p6d-dir ... --first-hour N --hours 1 --previous-comp-prefix ...` loads only the matching P6D single-hour float32 U/V/W and P6E's prior committed thermal state, never future state. Exported WFACE is the top vertical face, not the ground face. The frozen original CALMET.DAT still supplies *case controls/grid/station header*, which is an explicitly unresolved P6F metadata independence issue.

An optional `p6e_calmet_dat21 merge-native-hours` combines the native 45-field hourly records and rejects missing values, non-finite arrays, non-consecutive 1-hour labels, or inconsistent headers. All 45 **meteorological values** are native C++ in this path; this is not independently sourced static geometry and does not imply numerical acceptance. GitHub-hosted run [38345982200](https://github.com/RRain001/CTEAS/actions/runs/38345982200): initial real-case **6-hour causal P6D→P6E with full 45-field CALMET.DAT writer PASS**. The full 143-hour dependent job was launched for continued-state integration acceptance; do not mark PASS without the final job conclusion.

**Scientific holds**: P6D's currently dispatched single-hour wind branch can still omit internally computed CGAMMA/FRADJ forcing and does not yet demonstrate the original numerical equivalence for U/V/W (27 fields) or all 45 meteorological fields. The copied case header makes G4 full-input independence conditional. Once all 143h complete, compare its entire 45-field CALMET.DAT to the fixed original, diagnose the first residual by source stage and hour, and fix the physical kernel coupling rather than adjusting tolerances.


## Real original 143-hour 45-field numeric gate — first result and first divergence

The first strictly compared **fully causal** native 143h CALMET.DAT candidate was accepted as structurally complete, **not** as scientific parity. GitHub Actions [run 38346296680](https://github.com/RRain001/CTEAS/actions/runs/38346296680) separated native 6h/143h execution **PASS** from independent G3/G4 45-field numeric **FAIL**. Unchanged comparator recorded **61,161 total exceedances**.

- At **hour 1**, the old causal driver did not request `--comp-state-prefix` (none exists yet) and accidentally bypassed real STHEOR/MIXHTST/capped SIMILT. As a result native surface-station interpolation was an uncapped neutral substitute: U/V levels 2–9 each diverged on all 2,500 cells in that hour. Example original vs native U-LEV 9 cell 1: 2.46427774 vs 0.71483964 m/s. This is an **upstream initialization/callgraph bug**, not an original WIND1 kernel mismatch.
- The earlier actual-case **hour-12** INTER2 lower-layer mismatch persists in the first numeric run: U-LEV1 969 exceedances (max 0.0017107 m/s), V-LEV1 824 (max 0.0013192 m/s); first exceedance both at hour 12 cell 18. It must be analyzed after hour 1 closure, not conflated with first-hour STHEOR.
- Other current failures include USTAR 5957 exceedances, WFACE9 2504 exceedances (max abs 0.33009 m/s), and native upper-level strong deviations. The original 45-field gate remains **NOT PASS**.
- Independent native COMP migration / hourly clock compatibility gates previously passed; the above test proves those software gates are not substitutes for source numerical equality.

**Immediate corrective change on #53:** `cteas_p6_realcase_wind_field --native-setup-hour0` now explicitly supplies original first-hour zero-initialized thermal COMMON state and runs real native STHEOR→ELUSTR2→MIXHTST→capped SIMILT instead of the neutral fallback. Only hour zero and one-hour window permit this flag; oracle/COMP history mixing fails closed. The coordinator uses it on hour zero and real preceding P6E thermal state thereafter. An independently implemented native `--causal-hours` CGAMMA mode now reads only *already committed* P6E ZICONV states and runs original-order PREPDI before FRADJ, including initial ZICONV=0 at hour 1. This rebuild requires fresh 6h/143h CI and new numeric verdict; **do not reuse the previous 61,161 exceedances as the revised candidate's measured error count**.


### Source-locked 143h numeric second gate after native CGAMMA (first-hour SETUP not yet fixed)

GitHub Actions [run 38346549155](https://github.com/RRain001/CTEAS/actions/runs/38346549155), strict 45-field original comparator, recorded **58,996** exceedances (down from **61,161** before native CGAMMA). The critical hour-12 first-layer residual **disappeared**: U-LEV1 **969→0**, V-LEV1 **824→0** exceedances; maximum absolute errors are now 5.96e-6 m/s for U-LEV1 and 9.54e-6 m/s for V-LEV1. This provides independent numerical evidence that restoring the causal preceding-hour P6E ZICONV → native PREPDI CGAMMA → FRADJ path eliminated the persistent low-level mismatch without changing INTER2's independent kernel or tolerances.

In that *CGAMMA-only* candidate, U/V levels 2–9 still had 2,500 exceedances each during **hour 1**, because real STHEOR/MIXHTST/SIMILT had accidentally not been called with original hour-zero SETUP memory. The subsequent `--native-setup-hour0` patch corrects this; its fresh 143h numeric result must be measured separately and may not be conflated with the above two candidate revisions. P6 G3/G4 full 45-field original numeric acceptance still **NOT PASS**.

## Latest strict original 143-hour 45-field verdict — P6D original numerical acceptance PASS

GitHub-hosted [run 38346726042](https://github.com/RRain001/CTEAS/actions/runs/38346726042) tested **the cumulative CGAMMA + explicit first-hour CALMET SETUP + native causal DIAGNO→COMP** candidate, not the earlier neutral-hour0 variants. Results:

- Real native 6h and full 143h causal execution, true 45-field hourly writer: **PASS**.
- **P6D G3: all 27 U-LEV/V-LEV/WFACE fields × all 143 hours pass unchanged original source numeric tolerances**, zero exceedances each. The initial high-level hourly U/V issue and hour-12 layer-1 INTER2 residuals are resolved.
- Of the 45 written fields, **42 PASS / 3 FAIL**: USTAR **5,952** exceedances (max abs 4.587322473526001e-5 m/s), EL **1,105** (max abs 20,796.34375 m), WSTAR **171** (max abs 4.0731e-4 m/s). Total strict original exceedances **7,228**, down from 61,161 then 58,996 during the two predecessor branches.
- Native P6D 143-hour weather calculation has **P6D_FULL_UVW=PASS_FOR_FROZEN_HEFEI_2022_SCOPE**. Do NOT extend this claim to untested CALMET options, stations, grids or weather periods.
- **P6E strict full-field acceptance still NOT PASS** and hence full P6G not passed. The frozen reference met.dat remains the case's **static/control header input** for the writer; P6F complete static independence remains a separately declared hold.
- The remaining numeric work is to trace USTAR and EL's sensitivity to the DIAGNO first-layer U/V and HEATFX/ELUSTR input, plus WSTAR's propagation through QH/ZICONV/RHO/TEMP2D. The independent CALMET original-wind P6E E42 gate previously passed; use a same-native-state original-wind control to separate P6D physical sensitivity from P6E implementation differences before changing any source-locked formula. Do not relax tolerance and do not retest unrelated P6D formulas.

Scientific CI is intentionally red because the strict comparator rejects those three fields; the P6D 27-field sub-verdict is objectively all green. Never mark P6G as PASS merely because the hourly writer is complete.


## 2026-10-13 actual USTAR/EL/WSTAR wind-provenance and stencil-boundary audit

1. [Actions run 38347278722](https://github.com/RRain001/CTEAS/actions/runs/38347278722) controlled **same native P6D station flux and same native P6E kernels** with frozen original U/V/W and native P6D U/V/W respectively. Original-wind control: USTAR/EL/WSTAR **0/0/0 exceedances** with max abs 1.19e-7 m/s, 0.078125 m, 1.19e-7 m/s respectively. Native-wind path: USTAR 5,952; EL 1,105; WSTAR 171. This localizes failures to a wind-driven input dependence and does **not** justify using oracle winds in production.
2. [Actions run 38350090240](https://github.com/RRain001/CTEAS/actions/runs/38350090240) ran `scripts/p6_diagnose_wind_quantization.py` against all **143×50×50=357,500** source/native first-level winds. Max `|ΔU1|=5.9604790e-6 m/s`, max `|ΔV1|=9.5367577e-6 m/s`. Original AVETMP/AVEMIX-style REAL*4 integer shifts `IETAX/IETAY/ICWX/ICWY` differ in **6,187** grid-hours, but **only 187 of 5,952 USTAR exceedances** overlap a local integer shift; **zero of 1,105 EL** and **zero of 171 WSTAR** overlaps. Thus the initial claim that **INT-boundary flips explain the bulk of P6E failures is falsified**. There are real flips near source values such as V≈−1m/s at hour 39, but most remaining residuals require investigating continuous upstream wind errors and/or other upwind cone/distance/ELUSTR sensitivities.
3. A controlled GitHub-hosted `p6d-real4-arithmetic-sensitivity.yml` matrix comparing source C++ P6D compile arithmetic with fused operations disabled and with `-O0 -ffp-contract=off` is a **diagnostic hypothesis**, not accepted physics and not a tolerance change. Its results must be measured before any production flag change.

Keep the 27 original U/V/W wind fields' explicit frozen-case PASS (no strict wind-record exceedances), but add an independent **coupling sensitivity** gate before declaring P6E complete; wind tolerance PASS does not imply downstream ELUSTR parity.


### Actual C++ P6D REAL*4 compilation semantics experiment (P6E E5/E8 residual)

[Hosted matrix run 38350618893](https://github.com/RRain001/CTEAS/actions/runs/38350618893), using precisely the same original 2022 143h case, causal previous-hour COMP, frozen original numeric comparator, and unchanged native P6E physics. The P6D `-O3 -DNDEBUG -ffp-contract=off` variant completed and gave **exactly the baseline 7,228 original 45-field exceedances**: U/V first-level errors unchanged (U max 5.96048e-6 m/s, V max 9.53676e-6 m/s), USTAR 5,952, EL 1,105, WSTAR 171. Thus changing the C++ compiler's FMA contraction flag is **not a demonstrated fix**, nor is there a scientific rationale to alter production settings on that basis. The `-O0 -DNDEBUG -ffp-contract=off` variant is tested in a separate matrix worker; record its own result before making conclusions about optimization order.

No production physical kernel is altered by these compiler probes; a successful CI probe means the source numerical comparator produced a verdict, **not** numerical acceptance.

### Closure of nonproductive compiler-probe branch, permanent source-stage gate instead

Final result from [Actions 38350618893](https://github.com/RRain001/CTEAS/actions/runs/38350618893): **both** 143h compiler arithmetic probes (`-O3 -ffp-contract=off`, `-O0 -ffp-contract=off`) generated exactly the same 7,228 full-field numeric exceedances and exactly the same U-LEV1/V-LEV1, USTAR/EL/WSTAR residual bounds. Therefore neither optimization order nor FMA contraction was evidenced as the culprit. Their per-push CI matrix and redundant one-off YAML have been **removed from the active branch** to avoid future PR/Actions clutter; pinned completed workflow logs/this document retain the experimental evidence.

The next actual source-level investigation is `scripts/p6d_trace_original_inter2_first_layer_143h.py`, run as a dedicated downstream GitHub-hosted job on the **self-consistent native 143h DIAGNO→COMP causal driver outputs**. `--emit-source-stage-trace` exports native previous-GAMMA FRADJ, before/after SLOPE and post-INTER2 true 9-level float32 fields plus station observations for every hour; the auditor builds a write-only original Fortran trace from pinned source and asserts the frozen original MET.DAT checksum unchanged. This is to identify the earliest **sub-tolerance** original-vs-native wind discrepancy; it does not reset P6D's strict 27-field PASS or declare P6E PASS.


## Native C++ hourly coordinator and COMP state-owner migration (2026-10-13)

This subsection supersedes earlier statements that the *real* native causal C++ hourly P6D→P6E calculation is not running. It is now running as a **C++ time coordinator with existing native C++ physics subprocesses**, not yet an in-process `step_diagno`/`step_comp` kernel library. Do not conflate this with the test-only 17-stage `P6SinglePassHourlyScheduler` callback interface, which is not wired to the production monoliths.

- Current production wrapper: `native_cpp/modules/p6_calmet/src/native_hourly_driver_main.cpp`; 6h, 143h, prior-hour state, and all source-stage trace output byte-identical to Python control in [Actions #38357479805](https://github.com/RRain001/CTEAS/actions/runs/38357479805). The 143h final CALMET.DAT SHA-256 is `d942510459dd7392b03d8cb63f743f7015a7efb9985ea4767277020ac0a75686`.
- Official source numeric comparator after C++ clock cutover: [Actions #38358142191](https://github.com/RRain001/CTEAS/actions/runs/38358142191), native production 6/143 hours PASS; frozen source P6D 27/27 U/V/W PASS unchanged; P6E USTAR/EL/WSTAR FAIL (5,952 / 1,105 / 171 exceedances), total 7,228. This is the **same previous scientific blocker**, not a new scheduler regression.
- The `NativeCompHistory` C++ file-backed state owner now validates the provenance, exact hour, float32 dimensions, finiteness, and all three candidate ZI/ZICONV/DPTT fields **before** exposing any current-hour state. It stages the complete history and metadata, promotes metadata last, and rejects duplicate/gapped hours, partial values, and pre-existing workspaces. A failed hourly validation does not advance the in-process clock or modify earlier committed state. The `DPTT` sign is unrestricted because physically negative jumps are valid; ZI/ZICONV must be nonnegative.
- Cross-file rename is **not an operating-system atomic four-file transaction**. A crash during promotion terminates the program and there is intentionally no automatic resume from a partly committed workspace. Multi-file atomic restart and an in-memory kernel adapter remain separate implementation gates.
- `tests/p6_native_comp_history_tests.cpp` checks prior-hour integrity and fail-closed rollback, and CI compares the refactored C++ route against the unchanged Python 6/143h writer and source-stage traces. The current post-owner CI runs must complete before this latter refactor is marked PASS.
- This state-owner migration changes no P6D/P6E physical kernel, numerical tolerance, frozen original Fortran input, or reference wind provenance. Historical PR #53 remains Draft until complete P6 science G4 and P6E residuals are resolved.

Next architectural step is to extract existing validated P6D and P6E monolithic loop contents into native per-hour callable kernels and bind them to `P6SinglePassHourlyScheduler` without subprocess/file round trips, preserving the same input provenance and these strict numeric gates.

### NativeCompHistory 143h closure (source-scoped, run 2026-10-13)

- GitHub Actions [#38362578396](https://github.com/RRain001/CTEAS/actions/runs/38362578396): the C++ controller with single `NativeCompHistory` state owner passed both build-level fail-closed CTests, 6h original Python-vs-C++ strict byte comparison, and the full 143h byte-by-byte comparison of native hourly CALMET.DAT records, final 45-field MET.DAT, ZI/ZICONV/DPTT state, station flux, observations, and native 143h FRADJ/WIND1/SLOPE/INTER2 stage traces. Full-case MET.DAT SHA-256 remained `d942510459dd7392b03d8cb63f743f7015a7efb9985ea4767277020ac0a75686` (unchanged).
- GitHub Actions [#38362578127](https://github.com/RRain001/CTEAS/actions/runs/38362578127): native first 6h and full 143h production PASS after the state-owner cutover, unchanged original scientific comparator P6D U/V/W **27 of 27 PASS, zero excess points**. The overall 45-field gate remains intentionally FAIL for USTAR 5,952, EL 1,105, WSTAR 171, total 7,228. No tolerances or physical formulas changed.
- Source-order scheduler-contract and standalone native history rollback tests passed independently in [#38362578136](https://github.com/RRain001/CTEAS/actions/runs/38362578136).

**Accepted scope:** frozen Hefei 2022 selected-case C++ process coordinator with one validated file-backed COMP history owner, not generic CALMET and not in-process `step_diagno/step_comp`. Automatic restart following partial OS-level file promotion remains explicitly unsupported. Strict G4/P6E scientific hold remains. Do not merge PR #53 into its parent or main solely on the basis of these migration gates.


## 2026-10-13: original CALMET.DAT physically absent, 143h native source parity PASS

The earlier selected-case C++ coordinator validated 143h P6D 27/27 and P6E 18/18 numerical agreement while still supplying `--reference run/met/met.dat` to the P6E `emit-realcase` adapter. That path was accepted as a numerical reconstruction but not an original-output-independent execution.

The opt-in ref-free metadata path has now crossed three independently documented gates:

1. `cteas_p6f_p6e_source_metadata --geo GEO.DAT --deck met.inp --out SOURCE.DAT` constructs a legal CALMET.DAT 2.1 **metadata-only** envelope from the primary model input files. The producer is self-checking: all 143×45 hourly fields across 2,500 cells are the original missing values (not substituted original winds, PGT, USTAR or other fields). Case controls and static properties are independently sourced. It fails closed on unsupported geometry. [Actions #38381622077](https://github.com/RRain001/CTEAS/actions/runs/38381622077): PASS.
2. `cteas_p6_native_hourly_driver --p6e-source-builder PATH` supplies that file to each single-hour native P6E COMP process, rather than passing original CALMET.DAT. Controlled six-hour evidence from [Actions #38381961459](https://github.com/RRain001/CTEAS/actions/runs/38381961459) compares **all 270 hourly Fortran records byte-for-byte** against the previously accepted original-header native C++ run, and passes. A 143-hour controlled same-case test [Actions #38382378522](https://github.com/RRain001/CTEAS/actions/runs/38382378522) likewise proves **6,435 records byte-identical**, and strict original 45-field source comparison has **zero exceedances**.
3. In the strongest end-to-end input-provenance test [Actions #38382749295](https://github.com/RRain001/CTEAS/actions/runs/38382749295), CI builds an alternate model case directory where `run/met/met.dat` is **physically absent** (the valid `GEO.DAT`, `met.inp`, `surf.dat`, `up_58424.dat`, station metadata and other primary model inputs are retained). The C++ native coordinator completes 6h and all 143h without that file; both hourly records inventories are **byte-identical** to the earlier source-accepted native run (270/270 and 6,435/6,435), and the unchanged official original 45-field comparator again returns **total_exceedances=0**. The original CALMET.DAT is used by independent CI comparisons as an *oracle* only; not a computational input for the ref-free model branch.

**Accepted:** no reference CALMET.DAT is needed as a *runtime input* for the locked Hefei 2022 50×50×9 143h native C++ P6D/P6E case. This does **not** imply source input independence from `met.inp`, GEO, SURF or UP (the actual physical inputs), nor does it prove all grid sizes, multi-station configurations, wet deposition or precipitation-station modes. The temporary process-per-hour adapter is not yet an in-process physics engine. Continue to hold PR #53 as Draft until the agreed full P6 scope is independently resolved. No Fortran code, reference data or P6 science tolerances were altered to achieve this result.
