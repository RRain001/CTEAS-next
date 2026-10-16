# P7 COMP source-order correction and architecture gates — 2026-10-13

Repository: `RRain001/CTEAS`. Development authority: [draft PR #41](https://github.com/RRain001/CTEAS/pull/41). Do not introduce competing P7 branches or merge the draft without complete frozen-case parity.

## Original CALPUFF 7.2.1 authority

Original bundled source: `engine/vendor/src/CALPUFF_v7.2.1_L150618/calpuff.for`. The selected `COMP` path requires this partial order:

1. `SETUP` initializes output header via `WROUT1` (L49981).
2. `COMP` loads hourly meteorology, prepares output accumulators, and calls `INITPUF/POINTS1` (L9463+, L9796).
3. Old and newly admitted puffs traverse source/slot and `KSAM` loops (L9916+, L10417+); each actual substep resolves `GETCELL/PUFFDZ/ADVECT/RISEWIND/FSTEP`, then updates position.
4. `VMASS` operates **before** `SETPUF` (L10859 vs L10940). It consumes **old** `SIGZB` and can alter `ICODE`, `QM/QU`, `ZIOLD/ZIMAX` internally. The next `SETPUF` consumes the updated `ICODE`.
5. `SETPUF` and optional `CHEM/WET/DRY` precede `CALCPF` receptor concentration sampling (L10940+, L11022+, L11053+, L11084+, L11174+).
6. Only **after** concentration sampling does `COMP` finalize `IPUFCD`, `ZIMAX=max(ZIMAX,HLID)`, and `ZIOLD=HLID` (L11391–11398), then evaluate domain exit and FSTEP re-entry (L11400+).
7. Hourly `OUTPUT` data records (L11553, L57584+) are **not** the same call as `WROUT1` header initialization.

The 2026-10-13 native patch separates `commit_vmass`, `commit_sigma`, and `commit_lid` in `OriginalVerticalLifecycle`. Both restricted neutral and rising drivers now use this ordering and the `VendorSubstepOrder` guard. Unit regression forces a real `ICODE 1 -> 5` transition with reduced PBL, rejects stale SETPUF input, and asserts that historical lid state remains pending until the final phase.

## Architecture decision

Preserve separately testable physical kernels (RISEWIND, FSTEP, VMASS, SETPUF, receptors, deposition), but delegate actual source/vendor ordering to **one** native COMP orchestrator. Own the **whole-hour transaction** in that orchestrator, not separately in coupled physics components. Use one canonical puff inventory preserving mutable source slots and stable internal IDs.

Required stage boundaries for full-case mode:

- **Admission and inventory**: old puff slots, original POINTS1 release count, any `SWAP`, inactive `ICODE=99` holes, capacity `MXPUFF`, conditional `ROLLDN`. Existing post-hour eager compaction is a prototype and not original-equivalent capacity timing. A future change must model this pressure explicitly, rather than compacting unconditionally.
- **Per-puff substep**: previous complete state -> wind/cell/rise/FSTEP -> moved position -> pre-SETPUF `VMASS` -> `SETPUF` -> optional species conversion/removal -> `CALCPF` receptor accumulation -> late next-step history -> bounds/retirement -> FSTEP re-entry.
- **Hour boundary**: source-specific concentration sums, hourly `OUTPUT` records, mass budget, restart/checkpoint. A failure anywhere must roll back puffs, receptor accumulators, source scheduler and output writes.
- **Shared state**: physical puff XY/Z, sigma and age, ICODE, mixed/upper species masses, `ZIOLD/ZIMAX`, and source identity survive across meteorological hours. The 143h case must **not** be modeled as 143 independent one-hour runs.

## Explicit remaining gates

**Not validated:** full `CHEM/WET/DRY -> CALCPF -> late lid` integration, original condition-based `ROLLDN/SWAP` timing, complete `WROUT1` and `OUTPUT` binary records, autonomous 1h/6h/143h frozen Hefei 2022 puff trajectories and 2500-receptor concentrations. Existing 143h synthetic continuity is not frozen-case numerical parity.

Suggested order: (1) native VMASS source-order and ICODE tests plus CI; (2) source-slot inventory and capacity-pressure ROLLDN admission; (3) CALCPF per-substep callback integrated with mass/deposition and hour-atomic accumulator; (4) complete output header/data writer; (5) frozen-case first mismatch at 1h, then 6h, then 143h. Preserve the user's postponed precipitation/wet deposition extension gate; do not label `MWET=0` as wet-deposition support.

Acceptance must always record original source line anchors, actual PR commit SHA, full CI result (including failures), and the first independently reproduced numerical mismatch. No PASS without tested equivalence.


## Re-audit 2026-10-14: single authority and source-visible phase ownership

This audit takes priority over dated acceptance predictions above. Authority:
unmodified `engine/vendor/src/CALPUFF_v7.2.1_L150618/calpuff.for`
(SHA256 `da40372cab1c181158d0ee5faac16f678e876fc14415073c38c8e3bdabfbc568`).
Original source anchors were checked through GitHub-hosted source-print tests;
`MWET=0` is the *case condition*, not wet-deposition implementation.

| Source and original stage | Original-owned state and order | Current C++ owner | Audit result |
| --- | --- | --- | --- |
| `SETUP` + `WROUT1` header, `COMP` met-hour entry | Initialize header *once*, then read the new meteorological hour; never recreate old puffs | Native controls/MET reader; accepted independent 3226-record header | Header parity PASS; single production run-loop/output attachment OPEN |
| `POINTS1`/`INITPUF` and `SWAP/ROLLDN` | Append fresh point emissions after optional capacity-triggered compaction of old `ICODE=99` slots | `OriginalCompRiseMultiPuffHours::advance_hour_capacity`; `OriginalPuffCapacityInventory` | Scoped original-pressure inventory present; synthetic and frozen-case release tests; full 143h source-slot equality OPEN |
| `COMP` old then new `KSAM` loops, `FSTEP` | Old puff is advanced first; new puff J begins at KSAM=J; FSTEP re-entry carries leftover time | `original_comp_rise_hourly.cpp::advance_hour_mxsam99_core` | Structural order in place, real 1h 1275 substeps; full historical 6h/143h validation OPEN |
| `GETCELL→PUFFDZ→ADVECT→RISEWIND→FSTEP→XNEW/YNEW` L10473–10619 | Read pre-step position, select old vertical extent/wind, use final selected transport time | `OriginalCompRisePointDriver::step_pg_rise` | Fortran-backed component gates; selected first-hour native path active |
| `WDIV→VMASS→SETPUF` L10629–10942 | Update diversion and vertical mass `QM/QU/ICODE` using old sigma *before* SIGTY/SIGTZ/CTADJ2 | `original_comp_rise.cpp` and `OriginalVerticalLifecycle` | Correct sequence implemented in selected driver |
| `QOLD` L10965; `CHEM` L11022; `WET` L11053; `DRY` L11084; `QNEW` L11108 | Snapshot pre-removal mass, then optional species/removal kernels, then sample with both mass endpoints | Native pre-DRY `receptor_qold_mixed`, VDCOMP/DRY `commit_dry`, post-DRY VMASS state | H-3/HE-3 scoped source path and first-hour live H-3; CHEM/WET and general source modes OPEN |
| `CALCPF` L11174, `PUFRECS→SIGTY/SIGTZ→MCTADJ2→VCOUP→PFSAMP` L4190–4311 | Receptor impact, site-specific sigma/terrain/vertical coupling and original `QOLD*T1+QNEW*T2` | `original_flat_calcpf.cpp`; tested native callback at post-SETPUF/pre-history seam | Real first-hour execution runs, but 137/2500 H-3 float32 words differ |
| `IPUFCD/ZIOLD/ZIMAX` L11391–11398, late domain check L11400+, hour `OUTPUT` | Only after receptor sampling finalize next-step lid/history and process exit; output data at hour boundary | `commit_lid`, bounded exit/retirement, hour-scoped receptor result, separately accepted writer | Hour-memory transaction PASS in scoped modes; full original `OUTPUT`/puff.con parity OPEN |

### Confirmed integration/contract defects (separate from unproven first-hour root cause)

1. **Phase-guard coverage gap:** `VendorSubstepOrder` previously marked only eleven
   steps from cadence to late history, with *no enforceable phases between
   `CommitSetpuf` and `CommitNextStepHistory`*. Thus passing
   `vendor_order_tests` could not prove that a requested DRY or CALCPF had
   actually happened, despite the selected driver currently calling them.
   Add conditional, explicit pre-removal mass capture, dry removal and receptor
   accumulation phases. The selected physical stages must each complete before
   late history; disabled physics must not create false PASS claims.
2. **CALCPF old/new mass short circuit:** `original_flat_calcpf.cpp` returned
   zero when *post-removal* `QNEW<=0`. This incorrectly discarded
   **`QOLD>0,QNEW=0`**, although original CALCPF L4295/L4304 still computes
   `QOLD*T1+QNEW*T2`. Correct this guard with an exact-endpoint regression.
   This edge case is NOT established as the source of the current Hefei
   6.47%-maximum receiver discrepancy (native frozen H-3 masses remain positive
   in diagnosed influential steps).
3. **Historical API coexistence, not a proven stage inversion:** the repo
   retains older `PuffTransport`, neutral one-step, eager-compaction and
   simplified midpoint/VCBAR samplers for dedicated regression purposes.
   They must NOT be described as independent complete CALPUFF schedulers.
   The current scientific trajectory authority is the stateful
   `OriginalCompRiseMultiPuffHours` capacity-and-sampling path, backed by
   `OriginalCompRisePointDriver` with per-substep callbacks.
4. **Full-run authority remains incomplete:** stateful 143-hour synthetic
   continuity is distinct from 143-hour original-case concentration parity;
   standalone header/records byte tests are distinct from a connected
   `COMP→OUTPUT` writer; `CHEM/MWET` are not silently implied by the
   selected H-3 dry-case path.

### Verification order before further formula changes

Keep the old/new `QOLD/QNEW`, `VMASS→SETPUF→DRY→CALCPF→late-history`
source-order contract strict, then compare the **same native and original**
puff ID/KSAM/receptor values, preserving the true step input state. Only then
is a formula or REAL4 change justified. The 2026-10-14 hotspot
`(i=19,j=50)` receives 196 positive increments; reconstructed native REAL4
hourly concentration matches exactly while original field does not.
Centroid shift about (-0.0242,+0.1148) 100m receptor cells demonstrates
spatial residuals: a near-equal domain-total concentration is not parity.
Do not loosen tolerances, use frozen `puff.con` as model input, modify P6,
enable wet deposition, or merge Draft PR #41.
