# P7 — original CALPUFF real six-hour COMP × REAL*4 joint gate

**Date:** 2026-10-14. **PR:** [#41](https://github.com/RRain001/CTEAS/pull/41), Draft.
**Original:** CALPUFF v7.2.1 L150618, vendor SHA256
`da40372cab1c181158d0ee5faac16f678e876fc14415073c38c8e3bdabfbc568`.
**Scope:** Original frozen Hefei 2022 hourly CALMET `MET.DAT`, unchanged `puff.inp`,
and original `puff.con` as a read-only external oracle; real `MDRY=1`,
`MCTADJ=2`, `MXSAM=99`, two transported species, **H-3 concentration DATA
only** (`143` hourly species DATA fields, **not** `286` fields; `286`
are the period/grid metadata records). **MWET=0.**

## 2026-10-14 — real six-hour full-field H-3 REAL4 parity ACCEPTED

**This section supersedes the earlier open 6h mass/concentration entries below.**
The original Fortran source, frozen 2022 Hefei control/meteorology, original
143-hour `puff.con` and 254,687-row DGM remain unchanged. A single native
COMP orchestrator carries each puff and its mass/vertical state through the
six actual consecutive MET hours. No original state initializes native physics.

**Original/vendor source-first divergence closure:**

1. Original [puff200 full 36-substep mass history #38538371865](https://github.com/RRain001/CTEAS/actions/runs/38538371865)
   isolated DGM **#5823**, real hour 4, puff **200**, `KSAM=2`.
   Original unchanged VDCOMP: `TDEGK=284.149933 K` (`0x438e1331`),
   `QSW=522.772034 W/m²` (`0x4402b169`),
   `PDIFF=1.50900005E-5 m²/s` (`0x377d2b0f`),
   `B=2.19108824E-6 m` (`0x36130a9c`),
   `RS/RF=695.630615 s/m` (`0x442de85c`).
2. The previous native DRY path used the **pre-ADVECT starting cell 1678**,
   `QSW=522.7593384`, giving `RF=695.646851`; the original source
   `COMP` post-ADVECT meteorological **midpoint/end cell 1628**
   has `QSW=522.7720337` and `TEMPK=284.1499329`, both original-exact.
   Direct native source-cell evidence:
   [sixhour #38538951679](https://github.com/RRain001/CTEAS/actions/runs/38538951679).
   [`b081295`](https://github.com/RRain001/CTEAS/commit/b081295998e43bb09b9b0228b77f3e6644a11738)
   corrected the `VDCOMP` temperature/radiation cell to original
   post-ADVECT midpoint selection. Sixhour whole-field parity improved
   from **14,696/15,000 to 14,987/15,000**, and puff200
   `QOLD/QNEW/RF` became **36/36** exact.
3. Midpoint substitution for **all** meteorological variables changed
   original-exact aerodynamic/deposition-layer `RA/RD` from 36/36 to 14/36
   for puff200. The original `COMP` transport/stability boundary retains
   the **pre-ADVECT sampled wind, stability and roughness** for those
   resistances, while `VDCOMP` stomatal `TDEGK/QSW` comes from
   post-ADVECT midpoint. [`6991ec8`](https://github.com/RRain001/CTEAS/commit/6991ec89efd256041bb4bae632e1bb9b21544a3b)
   preserves these stage-specific input authorities without changing the
   original resistance formulas, user source or precision/tolerances.

**Independent scientific parity at production fix `6991ec8`:**

- [Real six-hour native-vendor H-3 field and DGM #38539868451](https://github.com/RRain001/CTEAS/actions/runs/38539868451):
  **15,000/15,000** float32 concentration words identical;
  **2,500/2,500 for each of hours 1–6**; first nonidentical hour
  **NONE**. Episode ID/KSAM, XY, SIGY, SIGZ remain
  **11,458/11,458** original REAL4 bitwise.
- [Original puff200 full historical DRY/RF/RA/QM #38539868439](https://github.com/RRain001/CTEAS/actions/runs/38539868439):
  all **36/36** REAL4 steps bitwise equal for every recorded scalar:
  `QOLD,QNEW,FRACDRY,VD,VDPVD,TSAMP,VCBAR,CONST,RA,RD,RC,RG,RF,RCUT,XLAI`.
  First historical mass or resistance difference: **NONE**.

**Fail-closed gate strengthening (on subsequent PR-head commits):**
`original_hefei_sixhour_native_receptors_tests.cpp` now requires all
**15,000/15,000** field words before a test can succeed; the previously
diagnostic-only `compare_puff200_mass.py --require-bitwise` and the
GitHub-hosted mass-history workflow require every original mass/resistance
word to match. Verify the new strict-gate commit SHA and final Actions state
independently; the preceding numerical results at `6991ec8` do not by
themselves certify uncompleted future runs.

**Acceptance boundary:** selected 2022 frozen real six-hour
`MXSAM=99/MDISP3/MCTADJ2/MDRY1` source path, H-3 concentration fields and
documented puff states only. The complete real 143-hour autonomous
puff inventory/calm-specific 989 original substeps, conditional
`MXPUFF/SWAP/ROLLDN`, the **HE-3** full hourly fields,
hour-boundary `OUTPUT` and full 3,655-record `puff.con` equivalence
are still **OPEN**. **MWET=0** is case input, not wet deposition
acceptance. Keep Draft PR #41 unmerged; do not alter P6 or original vendor.

---

## 2026-10-14 CTADJ2 first-REAL4-divergence closure (earlier accepted scope)

The previous 1-ULP REAL4 difference at **DGM record 3874**, 2022 real
meteorological hour 3, puff 138 KSAM=23 is **FIXED**, not tolerated.

- Original vendor **SETPUF** L48627-L48631 and **CTADJ2** L20800 explicitly
  evaluate `ETABYL*(ONE+XBYL2)**2` before dividing the numerator; native
  had left-associated `(ETABYL*(ONE+XBYL2))*(ONE+XBYL2)`.
  The grouping determines the last float32 bit of `DTZ` and `STRAIN`.
- Independent pinned Fortran source replay with **unchanged** full 143h
  `puff.con` and 254687-record original DGM gave at record 3874:
  `R` identical (`0x3f76113e`); **vendor CTADJ2 STRAIN
  `0x3f806eea` versus native `0x3f806eeb`**; downstream
  `SZADJ` `0x4306a3c2` versus `0x4306a3c3`.
  This directly identifies **CTADJ2, not SIGTZ**, as the first discrepancy.
  [Original-vs-native source oracle #38517589533](https://github.com/RRain001/CTEAS/actions/runs/38517589533).
- [`44abb4d`](https://github.com/RRain001/CTEAS/commit/44abb4dfd9755eccd0486fe3782c2df05c7167b0)
  changes **only the vendor-defined REAL4 denominator grouping** in
  `terrain_constraints.cpp`. The original vendor source, P6, original
  case and prior CALCPF physics remain immutable.
- Real six-hour 11,458-step original DGM under the fixed native solver:
  **episode ID/KSAM 11458/11458; X/Y 11458/11458; SIGY 11458/11458;
  SIGZ 11458/11458**, first DGM difference **NONE**.
  **First 3 H-3 hourly fields: 7500/7500 REAL4 bits identical.**
- New hour-4-6 H3 field checks (2500 receptors per hour):
  hour 4 **2252/2500**, hour 5 **2461/2500**, hour 6
  **2483/2500**. Sixhour total **14696/15000** exact;
  **first remaining H3 discrepancy: hour 4, index0 646**
  (1-based grid i=47,j=13).
  Remaining 304 mismatches are **not** cleared by DGM endpoint equality
  and must be traced via historical receptor-specific CALCPF, mass
  and accumulation rather than loosening tolerances.
- Original-vs-native stage gate
  [#38518070871](https://github.com/RRain001/CTEAS/actions/runs/38518070871)
  reported these source-backed science results but the *obsolete diagnostic
  assertion* deliberately expected a DGM #3874 mismatch, making that
  workflow's final assertion fail **because the mismatch disappeared**.
  [`188732d`](https://github.com/RRain001/CTEAS/commit/188732d050c5abbc11e3f0ccc0c86fbe1cc36957)
  now gates **all** 11,458 actual DGM fields and first three original H3
  hours, and
  [`fb82ada`](https://github.com/RRain001/CTEAS/commit/fb82adaff2f1e396cb4d6d9667475c352400af23)
  changes the original endpoint stage job into a true **PASS-on-bitwise-parity
  gate**. Final run status must be checked independently.

**CURRENT SCIENCE VERDICT:** 3h H3 REAL4 parity **ACCEPTED**;
6h original COMP trajectory/sigmas **ACCEPTED**;
complete 6h H3 **OPEN**; complete 143h output, forced MXPUFF
`SWAP/ROLLDN`, and wet deposition **OPEN / OUT OF SCOPE HERE**.

---

## Source-backed CTADJ2 fixed-stage acceptance and hour-4 first mass divergence

**Direct original/native binary32 source gate PASS**:
[GitHub-hosted #38518929684](https://github.com/RRain001/CTEAS/actions/runs/38518929684).
The identical original Fortran DGM #3874 endpoint and production native
C++ now compare exactly in all four isolated expressions:

| Original SETPUF end/CTADJ2 REAL4 parameter | Original | Native | Exact |
| --- | --- | --- | --- |
| `R` before CTADJ2 | `0x3f76113e` | `0x3f76113e` | PASS |
| `CTADJ2 STRAIN` | `0x3f806eea` | `0x3f806eea` | PASS |
| `SZADJ=SZE1*STRAIN` | `0x4306a3c2` | `0x4306a3c2` | PASS |
| `SZE1` after SIGTZ | `0x4306a3c2` | `0x4306a3c2` | PASS |

All **11,458/11,458** original six-hour COMP puff keys, post-ADVECT
X/Y, stored SIGY and stored SIGZ are exact. This is now a strict
fail-closed test; previous diagnostic's expectation of a divergence was
withdrawn, **not** a loosening of its numeric comparison.

**Fourth-hour first divergence is mass, not dispersion geometry**:
[GitHub-hosted write-only Fortran/native stage comparison #38518929871](https://github.com/RRain001/CTEAS/actions/runs/38518929871)
(complete 143-hour `puff.con` and original DGM hash unchanged).
At original 1-based receptor `(i=47,j=13)` = 0-based flat index
`646`, there are **482/482 same physical substep keys**.
Exactly **482/482** `SYREC, SZREC, ZPR, ZRPOLE, VCOUP F1,
PFSAMP XI1/XI2, CALCPF T1/T2, XTEMP` are float32-bit equal.

**First source-stage discrepancy**: global DGM substep **5847**,
hour4 puff **200**, `KSAM=25`, **QOLD**:
- Original `41,251,240 Bq`, float32 bits `0x4c1d5c6a`
- Native `41,251,248 Bq`, float32 bits `0x4c1d5c6c`
- Same step `QNEW`: original `41,215,896 Bq`, native
  `41,215,904 Bq`. Both diverge in the same direction.
- Full 482 stages: `QOLD` 436/482 bitwise, `QNEW` 432/482,
  final `CONC` 435/482; every geometry and horizontal/vertical
  receptor factor listed above **482/482 bitwise**.

**Consequence:** Do not modify `CTADJ2`, `SIGTZ`, `PFSAMP`,
`PUFRECS`, `T1/T2` or directly widen floats. The next first-source
audit must instrument original **hour-4 puff 200 pre-VMASS mass,
post-VMASS/pre-DRY QOLD, post-DRY QM and dry-removal fraction/VCBAR**
on identical steps to distinguish a mass-history rounding error
from the current-step DRY evaluation. Original source outputs
are read-only oracles and must never initialize native mass states.

**Scientific scope:** first three real hours **7,500/7,500 H3
concentration words** ACCEPTED; six-hour source DGM stored
XY/SIGY/SIGZ **11,458/11,458** ACCEPTED; complete 6-hour
H3 fields **14,696/15,000** REAL4 bits (remaining 304, beginning
hour4) **OPEN**. Original 143h and complete WROUT1 remain OPEN.

---

## One source-ordered native scheduling authority

`OriginalCompRiseMultiPuffHours::advance_hour_point_mxsam99_adaptive_bounded_capacity_sampled`
owns the **single** stateful sequence of six real MET hours, complete
historical puff objects, original POINTS1/PRFIN/RLSMET hourly release,
old-puff-before-new-puff order, variable `KSAM/FSTEP` and residual/reentry
time, `WDIV→VMASS→SETPUF→QOLD→DRY→CALCPF→late-history`, capacity slots,
and original post-step puff retirement. The six-hour test uses the same
production physical modules as the first-hour bitwise acceptance test; no
separate approximate equations were written.

**Case-scoped fix for real hour two:** old puff **22**, `KSAM=1`,
starts at `(X,Y)=(18.251936,49.648922)` cells, inside MET domain.
The C++ `PTLAPS` midpoint look-up incorrectly used the **strict**
`original_met_cell` even when the puff crossed a boundary during its
current substep. The original `GETCELL/GRIDIJ` maps such a midpoint/end
position to its nearest valid MET cell and only afterwards does
`COMP` evaluate final puff retirement. New
`original_met_cell_clamped` implements that already-source-ported
`grid_cell` rule in the **post-ADVECT midpoint** call sites (calm and
PTLAPS); strict pre-step look-up remains unchanged. A regression checks
both modes separately. Follow-up exception diagnostics preserve the old
fail-closed `std::invalid_argument` and `std::out_of_range` behavior.

## Actual six-hour native versus original H-3 hourly concentrations

Original concentration `puff.con` never supplies native velocity, mass,
sampling or puff state. Every value below is from independent native
`COMP` calculation followed by a REAL*4 word-for-word comparison:

| Original 2022 hour | Old puffs | New puffs | Active after | Original and native physical substeps | H-3 bitwise words | Max abs deviation (Bq/m³) | Verdict |
|---|---:|---:|---:|---:|---:|---:|---|
| 1 | 0 | 54 | 33 | 1,275 | **2,500/2,500** | **0** | ACCEPTED selected first-hour H-3 |
| 2 | 33 | 83 | 25 | 2,242 | **2,500/2,500** | **0** | **ACCEPTED second-hour H-3** |
| 3 | 25 | 71 | 26 | 1,906 | 2,498/2,500 | 3.576278687e-6 | OPEN |
| 4 | 26 | 64 | 26 | 2,249/2,500 | 2.384185791e-7 | OPEN |
| 5 | 26 | 65 | 24 | 1,742 | 2,461/2,500 | 4.768371582e-7 | OPEN |
| 6 | 24 | 80 | 25 | 2,161 | 2,483/2,500 | 2.384185791e-7 | OPEN |

- All six MET hours execute under **one historical driver**; original
  hour-table FSTEP row counts match exactly, **11,458/11,458**.
- Across all 15,000 H-3 receptor words, **14,691/15,000 bitwise**;
  **hours 1 and 2 both 2,500/2,500 exactly**; first remaining differing
  field is hour **3**, 0-based receptor **2380**.
- [Hosted original+native hour2 CALCPF comparison #38515121418](https://github.com/RRain001/CTEAS/actions/runs/38515121418)
  pins hour 2 receptor (25,28), full original 143h DGM unchanged,
  and proves **167/167 REAL4 bitwise** for `QOLD,QNEW,SYREC,SZREC,ZPR,
  ZRPOLE,VCOUP,XI1,XI2,T1,T2,XTEMP,CONC`. This is an explicit
  *source-backed* concentration-stage contract, not merely a tolerance.
- A successful *diagnostic* workflow is **not** 6-hour scientific parity.
  The hourly H-3 equality state is printed individually and labelled OPEN
  until every real-hour native value matches its frozen original counterpart.
- Capacity pressure is still **nonbinding** at `MXPUFF=4096` for this six-hour
  scope. Full original MXPUFF-pressure-triggered `SWAP/ROLLDN` is a separate gate.

## Authenticated same-puff/same-KSAM original DGM comparison

Independent read-only Fortran instrumentation using
`reference/dgm_p7_advection_2022/original_puff_step_dump.py` replays the
full 143-hour vendor source, proves unchanged `puff.con`, hashes the full
`DGM` against the pinned committed original `dgm_puffstep.json`, then
`reference/extract_original_six_hours.py` extracts the six-hour slice.
The six-hour C++ test optionally reads that slice *after its independent
physical step has already completed*: original state never drives physics.
[Verified hosted Ubuntu run #38513544264](https://github.com/RRain001/CTEAS/actions/runs/38513544264).

Original 6-hour DGM slice: **11,458 records ×352 bytes**,
SHA256 `8b848e9b064ee0c687c166d297978196c39cb253ccdc9d01dc2044976fe71b40`.

| Indexed source state across 11,458 original COMP substeps | REAL*4 bitwise equality |
|---|---:|
| Puff episode identity and `KSAM` | **11,458 / 11,458** |
| Post-ADVECT X/Y position | **11,458 / 11,458** |
| Stored horizontal dispersion `SIGY` | **11,458 / 11,458** |
| Stored vertical dispersion `SIGZ` | **11,220 / 11,458** |

First stored `SIGZ` disagreement is source DGM record **3874**,
hour **3**, puff **138**, `KSAM=23`:
original `SIGZ=134.639679` m versus native `134.639694` m
(about one binary32 ULP). Post-step `X/Y` and stored `SIGY` at
that **same** substep are bitwise equal. Additional
[hosted original DGM re-audit #38515995353](https://github.com/RRain001/CTEAS/actions/runs/38515995353)
records **input SIGZ = 128.979172 m** identically, original/native
SETPUF **begin SIGZ = 129.699402 m** and **mid SIGZ = 132.499527 m**
identically, but the **end-of-step SIGZ** first diverges:
original **135.329788 m**, native **135.329803 m** (one REAL4 ULP).
The earliest demonstrated vertical difference is therefore **within the
SETPUF end-point terrain/dispersion update**, *not* the input SIGZ
or the beginning/midpoint profile. An independent CTADJ2-end strain
and SIGTZ calculation trace is required before altering the code.
The original/natively derived
first/last episode IDs per hour and their exact substep counts are now
mandatory fail-closed regression expectations from the pinned original
DGM metadata.

**Interpretation:** The physical/temporal `COMP` step ordering,
stable episode ID mapping, source release counts, horizontal advection,
and stored `SIGY` have **direct original six-hour bitwise parity**.
Do **not** infer that untraced cross-hour internal states, `VMASS`,
`DRY`, or receptor-specific `CALCPF` stages are equivalent solely from
this. The earlier hour-2 concentration mismatch was traced
to **XTEMP=F1*TFRACT**; original COMP L10447 and L10563 explicitly
evaluate `TAVGI=1.0/TAVG`, followed by `TFRACT=TSAMP*TAVGI` in REAL*4,
whereas the native path had used a direct `TSAMP/TAVG` division.
At global step 1607 the original `XTEMP` was
`0x2d162cd9`, native direct division `0x2d162cd8`.
The source-ordered reciprocal-multiply fix closes all hour-2 receptor
concentrations exactly. Do not fit a tolerance to conceal the still-open
hour-3 end-SIGTZ/CTADJ2 mismatch.

## Next true acceptance work, retaining original control flow

1. **Preserve the now ACCEPTED hour-2 CALCPF gate.** Source-verified
   `TFRACT = TSAMP*(1.0/TAVG)` is a shared original REAL4 precision
   helper and separate binary32 ULP test; additionally retain
   the independent native/original 167/167-hour2-CALCPF stage oracle.
2. Isolate the original versus native **SETPUF end-point** operation
   at DGM record 3874 (hour3, puff138, KSAM23). The entry SIGZ
   and the begin/midpoint SETPUF SIGZ are already identical; instrument
   the authentic original CTADJ2 end-point STRAIN and SIGTZ input/output
   and compare to corresponding native stages. Repair ONLY the first
   evidenced divergent expression; rerun the six-hour H-3 and DGM gates.
3. Require **six hours × 2,500 H-3 REAL4 exact** and original-stage
   vertical history equality before the real 143-hour acceptance run.
   At 143 hours enforce original puff lifetime/conditional
   `SWAP/ROLLDN` capacity and full native `COMP→OUTPUT` data records.
4. Preserve **first and second hour 2,500/2,500 EACH** and the source-tethered
   `PFSAMP/CALCPF` 196/196 stage parity as nonnegotiable regression gates.
   Wet removal, other source modes, compiler/math-library changes
   and complete file-byte equivalence are **out of scope**.

**Decision:** Real six-hour compute/scheduling diagnostic PASS;
source-validated COMP episode/cadence/XY/SIGY PASS;
strict real six-hour concentration and SIGZ parity **OPEN**.
PR #41 remains Draft and unmerged; P6 and immutable Fortran untouched.
