# CTEAS P7-C1 / P7-C2 — true P6→P7 weather-variant scientific integration

**Current acceptance, 2026-10-16 — C1 original-MET 143h native P7 full science PASS ([#38830286957](https://github.com/RRain001/CTEAS/actions/runs/38830286957)); original/native-MET C1 four-arm historical PASS ([#38739266720](https://github.com/RRain001/CTEAS/actions/runs/38739266720)). C2 2024 original/native-MET four-arm 143h strict REAL4 PASS ([#38830287087](https://github.com/RRain001/CTEAS/actions/runs/38830287087)); the additive complete [six-pair matrix](P7_C1_C2_SIX_PAIR_MATRIX_20261016.md) PASS ([lightweight postprocess #38840221940](https://github.com/RRain001/CTEAS/actions/runs/38840221940)). Statements below that say C2 OPEN are historical snapshots of unsuccessful earlier commits, not the latest accepted result.**

## Frozen authorities (no hidden branch-tip drift)

| Component | Authority | Scientific scope |
|---|---|---|
| P6-C1 (PR [#53](https://github.com/RRain001/CTEAS/pull/53)) | `8d6642272d0abb77153880591e150f93e14d4479` | Hefei 2022, 1SS/1US, 50×50×9, 100m, 143h |
| P6-C1 accepted artifact | hosted run [#38417406969](https://github.com/RRain001/CTEAS/actions/runs/38417406969), `p6-causal-original-case-143h` | `native_causal_independent_header_calmet.dat`, generated without original `MET.DAT` in model inputs |
| P6-C2 (PR [#63](https://github.com/RRain001/CTEAS/pull/63)) | `7a13cc6a2f2d7b4c99e18b8866043a0319733454` | G35/G36 2024 synthetic genuine-format 2SS/2US, 12×12×9, 10km, 143h |
| P6-C2 accepted CI | hosted [#38731010343](https://github.com/RRain001/CTEAS/actions/runs/38731010343) | original+native P6 meteorology, original CALPUFF read, atomic publication, replay-based restart |
| P7 original-CALMET-science baseline | `6d2ad9fc00297d0ed382c59d7654bbd79c3c50ab` and [#38699935854](https://github.com/RRain001/CTEAS/actions/runs/38699935854) | vendor MET → native P7, 143h / 357,500 REAL4 / complete frozen `puff.con` bitwise equal |

**No 8784-hour run is required.** No P6D/P6E/P7 plume/sigma/deposition formula is changed by this integration project.

## Four arms in EACH frozen case

| Arm | MET.DAT producer | Puff solver | Required evidence |
|---|---|---|---|
| A | unchanged original CALMET | unchanged original CALPUFF | independent reference |
| B | unchanged original CALMET | native P7 | same-MET vendor/native concentration equality |
| C | PR53/PR63 genuine reconstructed CALMET | unchanged original CALPUFF | validated third-party interoperability and 143h concentration |
| D | PR53/PR63 genuine reconstructed CALMET | native P7 | independently generated 143h concentration and full original-format `puff.con` |

Two *different* scientific questions cannot be collapsed into a single file hash:

1. **Same-input solver correctness:** A ↔ B and C ↔ D. Report exact REAL4 word equality first; if a difference exists, document its first original/native calculation stage and do not relax scientific acceptance thresholds.
2. **Different-input propagation:** B ↔ D and A ↔ C. Measure per-hour H-3, source footprint, first changed cell, max/mean/RMSE concentration error and temporal/integrated totals; these may legitimately differ when original/native CALMET numerical fields differ within their own strict source tolerances.

A source-independent P6F OUTHD can change many echoed metadata records, so **whole-file `puff.con` SHA inequality is NOT evidence of concentration error**. Conversely, a green result without authentic 143×H-3 REAL4 fields is not accepted.

## C1 implementation and preliminary gate

The isolated workflow [`p7-c1-pr53-original-vs-native-met.yml`](../../.github/workflows/p7-c1-pr53-original-vs-native-met.yml) downloads only the pinned real PR53 full-143h weather artifact, builds original CALPUFF without modifying vendor sources and runs both A and C. It insists that newly rerun A produces the same original H-3 357,500 float32 words as the pinned historical A artifact. Its test-only native P7 C1 mode runs the real, stateful source-faithful COMP on the **PR53-generated** MET.DAT, with the corresponding vendor-C file used only for an **after-the-fact** scientific comparator, never for state initialization.

The opt-in `CTEAS_P7_INTEGRATION_C1=1` removes **only frozen MET-specific oracle assertions and metadata comment-count assumptions**, not core plume physics or the original-MET strict 143h regression. It requires all 143 hours, the same locked source deck, and a full native P7 `puff.con` artifact. The ordinary P7 143h science gate has no C1 flag and remains strict.

The dedicated [`compare_p7_hourly_concentrations.py`](../../native_cpp/modules/p7_calpuff/reference/compare_p7_hourly_concentrations.py) parses actual Fortran-sequential `H-3` records (not text dumps), rejects malformed markers, missing/nonconsecutive record counts, nonfinite/negative or all-zero fields, and reports H-3 float32 word equality and all concentration deltas.

**Do not mark C1 accepted on a queued/running Actions job.** Inspect actual A/C, B/D, C/D scientific JSON and full generated D output. A failed C1 diagnostic must be debugged from the earliest source stage without injecting original puff states.

## C1 exact observed 143-hour scientific result (Actions #38739266720)

| Arm/Comparison | Independently measured evidence |
|---|---|
| A: original 2022 CALMET → original CALPUFF | Vendor rerun reproduced pinned reference `puff.con` H-3 REAL4 **357,500/357,500 bits** |
| B: original 2022 CALMET → native P7 | Previously accepted unchanged P7 science [#38699935854](https://github.com/RRain001/CTEAS/actions/runs/38699935854), **357,500/357,500**, original full file SHA pinned |
| C: genuine 143h source-generated PR53 `native_causal_independent_header_calmet.dat` → original CALPUFF 7.2.1 | All 143 hours completed from source; **334,126/357,500** float32 words agree with A, MAX_ABS=`0.0011510960757732391 Bq/m³` |
| D: same exact PR53 `MET.DAT` → native source-faithful P7 | **143/143 hours completed; C↔D 357,500/357,500 IEEE REAL4 bit exact**, no first difference; native complete `puff.con` 1,892,696 B |
| B↔D cross-MET sensitivity | **334,126/357,500** words identical; first different cell **hour 1, i=24, j=28**, original=`1.552549747430021e-6`, PR53=`1.5525517937931e-6 Bq/m³`; max abs=`0.0011510960757732391` |

The C1 live native D log contains `P7_C1_NATIVE_ON_PR53_MET HOURS=143 REAL4_MATCHED=357500/357500 FIRST_MISMATCH_HOUR=0 ... SAME_MET_VENDOR_PARITY=PASS NO_ORIGINAL_DGM_AS_INPUT=YES`. The independent `compare_p7_hourly_concentrations.py` separately verifies C↔D bit identity and B↔D meteorological sensitivity. Source-derived P6F input header changes the full WROUT1 binary length; **do not infer whole-file SHA parity with the frozen 2022 A/B artifact**. C1 accepts concentration-field physics and real complete output production, not metadata SHA identity between different input decks.

Acceptance is **source/physics scoped**: 50×50×9 100m, one surface+one upper station, H-3 point source, `METFM=1, MWET=0`, and these 143 consecutive hours. There is no new arbitrary-grid, wet-scavenging, multi-station or all-CALPUFF-feature claim. The integrated C1 candidate is opt-in and never alters existing original-MET science gates.

## C2 measured original CALPUFF response with both real G35 MET.DAT files

[GitHub-hosted run #38743223360](https://github.com/RRain001/CTEAS/actions/runs/38743223360) **SUCCESS** on C2 case input stage; this is **not** native P7 acceptance.

The first non-trivial vendor pairing run [#38742236236](https://github.com/RRain001/CTEAS/actions/runs/38742236236) exposed a scientifically inadmissible all-zero H-3 field: reusing the frozen 2022 point-source XY (513.385, 3533.769 km) placed the source near the southwest corner of the 12×12 10km 2024 meteorological domain, yielding no measurable receptor concentration. The test blocked rather than passing based on vacuous all-zero agreement.

The controlled repair moved only point-source XY to **(565.885, 3586.269 km)**, interior to the same static domain, for BOTH original and reconstructed weather runs; every other source operand (emission rate, stack height and diameter, effluent temperature and exit velocity) and dispersion/deposition/control option remains unchanged. `run_c2_vendor_inside_grid_pair.py` writes the actual 2024 modified source deck and publishes its SHA256/provenance.

Observed true 143h original-vs-reconstructed CALMET parity remained **6,435 hourly original-format fields, zero tolerance exceedances**. Independent original CALPUFF 7.2.1 executed the same time window twice; each 143-hour 12×12 H-3 result contained 292 positive concentration cells. Comparing **20,592** total float32 H-3 words yielded **20,576 bitwise matches**, a maximum absolute difference of `7.450580596923828e-09 Bq/m³`. This demonstrates observable meteorology-to-concentration sensitivity without pretending that different MET inputs must produce the same output.

**C2 next mandatory boundary:** rerun the same frozen original and PR63 METs with native P7 (B and D), compare A↔B and C↔D bitwise and B↔D meteorology sensitivity, audit both native full `puff.con` outputs and verify no oracle injection. The C2 opt-in driver changes grid/time/source-configuration admission only; original C1 and P7 frozen 2022 strict gates must remain intact.

### C2 first native six-hour admission failures and source-backed repairs

The first C2 native P7 attempt [#38744334873](https://github.com/RRain001/CTEAS/actions/runs/38744334873) failed *before plume physics*, because `OriginalMetHourlyReader` had been called with `frozen_hefei_2022=true`; `Calmet21Reader` correctly rejected the 2024 12×12 10km grid. The C2 opt-in now passes `false` to the independently validated generic two-pass CALMET21 decoder while leaving 2022 C1/P7 strict frozen reader untouched.

The next C2 native six-hour attempt [#38744864139](https://github.com/RRain001/CTEAS/actions/runs/38744864139) reached native physical source release but hit a **source-inconsistent PRFIN validity guard**, not a concentration mismatch. Native `original_point_prfin_metfm1` had rejected `HEFF<=HTSTAK`. Original CALPUFF POINTS1 L15603 explicitly evaluates `HEFF_B=HTSTAK(I)-TIPDW+RISE_B` **without a requirement to be above the stack tip**; legitimate downwash can lower effective height below the physical stack. The C2 source-backed correction admits any *finite positive* effective release height, preserves the original arithmetic and leaves the stack-height input unchanged. It continues to reject zero/negative or nonfinite outputs and includes the operands in the error if triggered.

Neither failed run may be represented as native P7 C2 physical parity evidence. Rerun [#38745638332](https://github.com/RRain001/CTEAS/actions/runs/38745638332) includes both admission corrections, mandatory six-hour actual-source smoke, full 143h B/D runs subject to the smoke gate, and separate A↔B/C↔D/B↔D independent REAL4 comparisons. Until the run succeeds with real 20,592/20,592 same-MET H-3 bits on each arm, **C2 P7 acceptance remains OPEN**.

## C2 planned sequence (not yet accepted)

G35 original and native weather must be rebuilt or staged **within the same accepted 2024 12×12×9/10km scientific scope**, preserving their exact source manifest, first/last UTC timestamps, all 143×45 records, 2SS/2US upper-air bracket and G36 READY seal.

G36A already shows that **original CALPUFF** can read 143h *native* P6G weather. It does **not** prove original-CALMET weather ↔ native-P7 physics or native P7 can run 12×12 weather. The G36A original `puff.inp` fixture adjusts run clock, meteorological domain, receptor and sampling indices for 2024; preserve the original source/diffusion options and only make physically admissible geometry changes.

The current P7 strict physics test still contains explicit 2022/50×50/100m assumptions. C2 requires an independent source-driven **configurable grid, clock, source-admission, receptor-count and WROUT1** path. Do not bypass bounds checks, inject reference concentration, or call an all-zero plume a pass. First run vendor/P7 on the *same* original multi-station MET.DAT, then the *same* native multi-station MET.DAT, and compare all 143 hourly H-3 grids and puff chronology where applicable.

**Latest verdict:** C1 A/B/C/D original/native 143h science **PASS on run #38739266720**, validated by live real-value comparisons. C2 weather dual-run science is under independent development; do not claim native P7 12×12 scientific acceptance without its own real run.

## C2 latest forensic status (2026-10-16; no unverified PASS)

Full 143h original-CALMET/native-P7 A/B and PR63-CALMET/native-P7 C/D runs **both completed**, with original CALPUFF A/C independently completed. The native P7 source-integration scientific gate remains **FAIL**: [last completed post-VDPVD 143h #38768796276](https://github.com/RRain001/CTEAS/actions/runs/38768796276) yielded **20,555/20,592** H-3 REAL4 bitwise values for **each** same-MET pair (37 residual words each), maximum absolute concentration difference `1.7462298274040222e-9 Bq/m³`. Source-first H1 receptor (4,6) audit isolated a uniform ICODE=2 dry deposition VDPVD handoff omission, now fixed; remaining H1 event 23 required VMASS/DRY midpoint-state forensics. See [C2 source forensic report](P7_C2_2024_143H_FIRST_DIFFERENCE_FORENSICS_20261015.md).

The subsequent native [`e20b4a4`](https://github.com/RRain001/CTEAS/commit/e20b4a423218ef29cfe32b62efa53de129674de1) corrects the native DRY diffusion path to use COMP's post-ADVECT midpoint `DPBL` rather than pre-step sampled PBL. This is **code committed, not yet independent 143h scientific PASS**. PR #69 remains Draft/unmerged until both same-MET pairs achieve 20,592/20,592, and the unchanged 2022 C1 full 143h scientific regression remains passing. No adjustment to frozen thresholds, vendor sources or PR63 meteorology is permitted.


## Superseding six-pair acceptance (2026-10-16)

The definitive C2 current P7 code [`63fdc01`](https://github.com/RRain001/CTEAS/commit/63fdc01d00623c071c62d4ca5281fbb1d9c2cd2b) corrected the original COMP→DRY start-cell versus midpoint-input interface and achieved **A/B 20,592/20,592**, **C/D 20,592/20,592**, full 143h, no receptor divergence in [#38830287087](https://github.com/RRain001/CTEAS/actions/runs/38830287087). The original-MET C1 143h complete puff.con, DGM and concentration science also passed on that head [#38830286957](https://github.com/RRain001/CTEAS/actions/runs/38830286957). The six-pair follow-on **does not rerun solvers**, but re-evaluates archived outputs and provenance; source/method/metrics and limitations are in [the formal report](P7_C1_C2_SIX_PAIR_MATRIX_20261016.md). C1 D native-MET 143h was originally accepted on a preceding code revision, not reexecuted with final P7 head. No full-year model simulation is asserted.
