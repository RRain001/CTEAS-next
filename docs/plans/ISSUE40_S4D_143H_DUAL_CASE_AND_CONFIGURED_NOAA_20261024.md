# Issue #40 S4-D — unified 143h C1/C2 real original numerical recheck and one NOAA research entry

Date: 2026-10-24. Draft PR #308, production P6/P7 and independent science admission **remain BLOCKED**.

## Verified case identity and provenance

Exactly the *same* C++ `cteas_p6g_s4b2_unified_selected` physics runner executed both independent 143-hour regression fixtures. Previous main accepted C1/C2 runs do not count as evidence for this branch: these two runs were actually repeated under branch parent `f0a3c0aff82e4859503a4a5f726150bbbb208ef2`. The present patch adds only a CLI-normalized NOAA research entry, with no physical formula/staging/output change; **fresh exact-head scientific reruns are still required before signing this new commit**.

- **C1 authentic 2022 single-station case**: 50×50×9, 1SS/1US, 143 native hours, `--selected-experimental --hours 143`, actual C1 `MET.INP/GEO.DAT/SURF.DAT/UP.DAT`. Original independently SHA-pinned `project/cases/hefei5km_2022_reference_case_20261011/run/met/met.dat`: `b1823cda92280888d70b00961ab39486036a3086e18637fff21efb4f4b237d30`. Original Fortran *not freshly rerun* in C1. P6E original/native comparison `intervals=143`, `fields_per_hour=45`, 6,435 field/hour combinations, all 45 canonical fields, `total_exceedances=0`, `status=PASS`. Native MET is original independent C++ computation, not reference-backed.
- **C2 controlled original-format 2024 multisite case**: 12×12×9, 2SS/2US, 143h. Source generated afresh from existing native `cteas_p6g_g19_file_backed_case_tests --export-case ... --fradj-stress --daylight-first-hour --hours 143`, each original-format G19 source file SHA stored separately. Native same S4B2 runner computed all 143h, 6,435 field/hour combinations. **Unchanged Fortran CALMET 6.5.0 freshly ran**, source exact Git blob `437f43bb7f0e51a1919e56664663e1a046986ed0` verified from reference-only `/home/lhy/build/ref/cteas-ref` local directory, gfortran-11 compiler (host `gfortran` was obsolete 4.7). Same authentic 2024 G21 source clock. Fresh original MET SHA `1164c8f992ee40556d1bf26b4e243d773bc67daba14e96785c5b68069cdde31f`. S4B2 native MET SHA `7fbd100b3d75e3b1d0240e3e2c09506ed4333f0ede664081e315425f98e27aac`. Independent P6E 143×45 original-vs-native comparison: `status=PASS`, `total_exceedances=0`, all 45 canonical fields. C2 is a controlled synthetic multi-station test: **it is not an independently observed second real site**.

Frozen scientific tolerances were never changed to induce a pass. Read-only original/native output and detailed field comparisons stay **private** on Ubuntu only under `/home/lhy/dev/reports/cteas-s4d-c1-c2-20261024/`:

- `c1-unified-original-frozen-143h-45fields.json`
- `c2-unified-fresh-original-143h-45fields.json`
- `c1-frozen-source-sha256.txt`, `c2-source-input-sha256.txt`
- `c2-original-gfortran11/g31a-evidence.json`

No original/vendor source, private original observations, or unlicensed physical case data is committed to GitHub. A private, ignored `engine/vendor` symlink was used only for the exact pinned original Fortran; it does not grant general production acceptance.

## Replace incrementing hour-specific research switches

The **one** new opt-in `--water-noaa-g14-trial-only --probe-prefix-hours K --hours 6` with K in 1..6 is a **strictly research-only, fixed NOAA 82×85×9, 2SS/1US, 63 WATER configuration**. After mandatory validation it maps K to the already existing original G65 native G14 actor and 17-stage transaction path. No new physics, G43 equation, P6F history mapping, Fortran oracle, serializer or clock algorithm is introduced. The previously frozen per-hour flags are retained as backward-compatible *legacy test interfaces* only: do not add more.

All K=1,2,3,4,5,6 were actually executed on the source 2022 genuine NOAA fixture through the **new single option** and each whole native `MET.DAT` SHA matched the earlier corresponding frozen research flag **byte for byte**, including K6= `32d9f049b1739e1d568a0f7ba65bf9d3718d8bd1c1b7dcdb147c94d41a4753b3`. Complete K6 still calls `scheduler.require_complete()` after all 102 stages. The only offline original use remains the independent read-only `--native-hours 6` audit, 270 fields / 1,881,900 values, 0 frozen exceedances. C1/C2 land cases continue to use the default `--selected-experimental` 143-hour runner, not the limited NOAA-water flag.

Fail-closed `scripts/s4/s4d_water_noaa_configured_cli_contract.py` tests missing actual source, wrong 0/7/143 hour prefix, incorrect source span, conflicting any six old flags, illegal G26 production or source-only modes, non-empty trace, duplicate opt-in, implicit production entry and output overwrite. One test, not six duplicated tests. Registered in existing P6 research CTest group; 9/9 scoped guards PASS.

## Next independent admission requirements

- This patch should run **exact new commit SHA** native full 11-step Ubuntu software validation, and separately repeat both 143-hour C1 and C2 scientific comparisons using the rebuilt exact-head S4B2 binary. Publish `ubuntu-native-full` only on successful exact-SHA manifest verification.
- Validate independently observed second location/station geometry, nontrivial original native rollback, and non-Bot same-SHA science review. General NOAA/land production case selection/config serialization and arbitrary source data choices remain unimplemented, even though this one fixed NOAA case now has one CLI option.
- Current PR #308 must remain Draft; `scientific-admission` failure blocks merging. Never attach science-validated/merge-verified for these scoped results, and do not start P7 or claim general 143h P6 acceptance across arbitrary cases.

## 2026-10-24 — actual NOAA precommit rollback + fresh-actor replay

The S4B2 **single explicit research-only NOAA entry** additionally admits
`--noaa-precommit-rollback-retry-hour N`, strictly N=2..K with K the allowed
1..6 source prefix. Normal C1/C2, historic hour-scoped flags, default G26,
source-only preflight and absent/invalid-hour requests all fail closed.

At the specified real NOAA hour, the real G65 actor executes all 17 stages
and constructs the genuine native P6F 45-field precommit; the research
precommit callback then intentionally rejects this first attempt **before**
G14 moves grid state or publishes AA/BB/CGAMMA clocks. The same G14 scheduler
checks its previously committed hour count, bitwise-exact ZI/ZICONV/DPTT
memory, and both station clocks unchanged, with no published output file.
It constructs a *fresh* native hour actor, redoes the entire same physical
hour, commits it, and continues through all six real NOAA hours. This is an
in-process tested rollback and retry, NOT an arbitrary process crash
recovery or persistent checkpoint restart mechanism.

Source-only research cases injected failure/retry at actual hour **2, 5, 6**
independently, and each complete 6-hour native `MET.DAT` SHA exactly matches
the original clean 6-hour native output
`32d9f049b1739e1d568a0f7ba65bf9d3718d8bd1c1b7dcdb147c94d41a4753b3`.
The tested 5/6 water history thus survives a genuine rejected precommit
without reference field backfill or timing drift. Private evidence and real
output remain `/home/lhy/dev/reports/cteas-s4d-rollback-20261024/`.
The pre-existing negative CLI contract remains a single shared test driver.
This does **not** prove fault tolerance after the irreversible commit,
simulation interruption recovery or all production station/site options.
