# CTEAS P7 — C1/C2 2×2 four-arm, six-pair 143h validation

**2026-10-16. Frozen-scope six-pair SCIENCE = PASS, with explicitly distinguished DIRECT versus DERIVED comparisons. No new CALMET or CALPUFF execution is part of this analysis.**

## Validation design and acceptance semantics

Let original/reconstructed meteorology be `M_o/M_r`, original/vendor
CALPUFF and reconstructed P7 be `P_o/P_r`.

| | Vendor `P_o` | Reconstructed `P_r` |
|---|---|---|
| Original CALMET `M_o` | A | B |
| Reconstructed CALMET `M_r` | C | D |

All six unordered pairs are evaluated. Their **acceptance criteria are NOT identical**:

| Pair | Factor held constant | Scientific question | Acceptance |
|---|---|---|---|
| AB | Original `M_o` | Native P7 versus original CALPUFF | **143h H-3 REAL4 bit-exact**, strict |
| CD | Reconstructed `M_r` | Native P7 versus original CALPUFF | **143h H-3 REAL4 bit-exact**, strict |
| AC | Vendor `P_o` | Original versus reconstructed meteorology | Quantify, **not** force bit-exact |
| BD | Native `P_r` | Original versus reconstructed meteorology | Quantify and agree with AC if AB/CD exact |
| AD | Neither | End-to-end replacement versus reference | Quantify; mathematically implied by AB/CD/AC |
| BC | Neither | Crossed combination | Quantify; mathematically implied by AB/CD/AC |

If every cell and hour satisfies `A=B` and `C=D` bit-for-bit,
then **as H-3 REAL4 arrays** all cross-MET oriented differences satisfy

```text
A - C = A - D = B - C = B - D
(D - C) - (B - A) = 0
```

This is a **logical closure for the selected outputs**, not a claim that
the meteorological files, entire Fortran output binaries or all CALPUFF
physical options are identical. It does NOT follow that `A=B=C=D`.
Six comparison rows exist, but only three independent edges are necessary
to establish the numerical relation (AB, CD, AC); the measured fourth
edge BD is an independent closure check.

## Independently executed archived-evidence postprocessor

- Source: [`p7_six_pair_matrix.py`](../../native_cpp/modules/p7_calpuff/reference/p7_six_pair_matrix.py).
- Positive/negative tests: [`test_p7_six_pair_matrix.py`](../../native_cpp/modules/p7_calpuff/reference/test_p7_six_pair_matrix.py), including same-MET mismatch, missing hour, altered hourly difference, wrong provenance SHA and invalid bit-exact status.
- Dedicated [lightweight six-pair workflow](../../.github/workflows/p7-six-pair-postprocess.yml). It downloads **preexisting** artifacts with frozen run IDs. It does not rebuild either meteorology model, invoke the puff solver or compare invented reference fields.
- Separate structured JSON results are uploaded as `p7-c1-c2-143h-six-pair-archived-matrix`. Each row carries a machine-readable `provenance` label. Other preexisting P7 regression workflows may trigger on a new PR commit due to their existing broad path filters; those runs are not part of this postprocessor.

### C1 source provenance and proof strength

- 2022 single-site 1SS/1US, 50×50×9, 100 m, 143 consecutive hours.
- A, C and D: independently generated `A-original-calpuff.con`,
  `C-original-calpuff.con`, `D-native-p7-native-met.con` archived by the **historically accepted** four-arm science [run #38739266720](https://github.com/RRain001/CTEAS/actions/runs/38739266720).
- B: **actual 2026-10-16 HEAD-era native P7** `native-full143-puff.con`, from strict independent [run #38830286957](https://github.com/RRain001/CTEAS/actions/runs/38830286957); pinned full binary SHA256 `0d51bdb68ff1a5798048bc41067107d3ffe10dc6222f25336df856bcbf48ba10`. This is NOT substituted with the vendor output. B has its own original DGM and complete H-3 regression.
- Six pairs are read and measured **directly from four actual Fortran-sequential concentration files**, validating all 143×50×50 H-3 REAL4 words per pair. A/B and C/D are required bit-for-bit; source file SHA, numerical error and hourly details are exported.
- **Temporal provenance limitation:** archived D is from the earlier C1 accepted revision, not a newly rerun D on the present `63fdc01` P7 physics commit. The new head's original-MET B independently passed 143h; only the historical accepted C/D 143h is reused here. This six-pair postprocessor does **not** claim a new HEAD-native-MET C1 D simulation. If a policy later requires C1 D on the exact final P7 HEAD, it would require a separate 143h run.

### C2 source provenance and proof strength

- 2024 synthetic but true original-format 2SS/2US, 12×12×9, 10 km, 143 consecutive hours (2024-01-01 02:00 to 2024-01-07 01:00 UTC, not the 8,784h leap year).
- Pinned PR63 P6 code `7a13cc6`, genuine original versus reconstructed CALMET meteorology, original vendor solver A/C and native solver B/D all complete on original four-arm [run #38830287087](https://github.com/RRain001/CTEAS/actions/runs/38830287087). That run independently calculated AB, AC, CD, BD and its fail-closed overall `C2_ACCEPTED=true`.
- Published C2 archive includes `C2-same-MET-A-vs-B.json`, `C2-A-vs-C-science.json`,
  `C2-same-MET-C-vs-D.json`, `C2-different-MET-B-vs-D.json`, the control/source SHA manifest and an overall acceptance verdict; **not all four full `puff.con` files**.
- Postprocessor audits the recorded 143 consecutive hourly results, totals, identical AC/BD hourly delta metrics, matched A/C/B/D SHA chains and frozen PR63 authority. C2 **AD and BC are mathematically derived, clearly flagged `ALGEBRAIC_DERIVATION_NOT_REMEASURED`**; they are not misrepresented as new direct comparisons.

## Actual six-pair outcomes (both 143h)

`REAL4` counts below denote **identical H-3 floating-point words**, not
the fraction of total *physical* transport that agrees. Concentration error
uses Bq/m³; zero here means exact output equality, not zero plume.

| Pair | C1 identical / 357,500 | C1 max absolute difference (Bq/m³) | C2 identical / 20,592 | C2 max absolute difference (Bq/m³) | C1 evidence / C2 evidence |
|---|---:|---:|---:|---:|---|
| **AB** | **357,500** | **0** | **20,592** | **0** | DIRECT / measured archived |
| **AC** | 334,126 | 0.0011510960757732391 | 20,576 | 7.450580596923828×10⁻⁹ | DIRECT / measured archived |
| **AD** | 334,126 | 0.0011510960757732391 | 20,576 | 7.450580596923828×10⁻⁹ | DIRECT / **DERIVED** |
| **BC** | 334,126 | 0.0011510960757732391 | 20,576 | 7.450580596923828×10⁻⁹ | DIRECT / **DERIVED** |
| **BD** | 334,126 | 0.0011510960757732391 | 20,576 | 7.450580596923828×10⁻⁹ | DIRECT / measured archived |
| **CD** | **357,500** | **0** | **20,592** | **0** | DIRECT / measured archived |

**C1** has 23,374 cross-meteorology REAL4 differences out of 357,500;
**C2** has 16 out of 20,592. Every observed cross-MET difference is due
to the difference in meteorological input *within this validated solver
configuration*, since the replacement puff solver introduces no
measurable REAL4 error on the same inputs. This statement does not imply
the wind fields are identical or their differences always negligible.

The uploaded JSON also retains 143 per-hour bit-match counts, first changed
receptor, maximum error location, maximum symmetric relative error,
MAE, RMSE and sums of hourly receptor concentrations for all six pairs.
The latter sums are **not mass, release inventory, population dose or
a time/area integral** without explicit weighting.

## Audit/decision

- **PASS:** 2×2 six-pair matrix has complete coverage with provenance flags;
  strict AB/CD REAL4 identity holds in both frozen accepted scenarios;
  independently measured C2 AC/BD scalar + hourly metrics agree exactly,
  and C1 all four cross-MET pairs agree directly.
- **PASS:** selected-output interaction `(D-C)-(B-A)` is exactly zero on
  validated REAL4 concentration words because AB and CD are bit-exact.
- **NOT CLAIMED:** AD/BC direct remeasurement on C2 missing full four
  concentration files; new 143h physics runs; 8,760/8,784h scientific
  full-year parity; wet-deposition/other untested options; exact-current-head
  C1 native-MET D validation.
- **Release discipline:** Keep PR #63 untouched, and do not alter or relax
  any original Fortran, CALMET/CALPUFF physics or same-MET strict thresholds.
  Report the six-pair closure as an additive verification layer, not a
  replacement for primary 143h science gates.

## Artifact navigation

- C1 frozen four-arm historical [Actions #38739266720](https://github.com/RRain001/CTEAS/actions/runs/38739266720)
- C1 latest strict native B [Actions #38830286957](https://github.com/RRain001/CTEAS/actions/runs/38830286957)
- C2 original four-arm [Actions #38830287087](https://github.com/RRain001/CTEAS/actions/runs/38830287087)
- [PR #69](https://github.com/RRain001/CTEAS/pull/69) — remains unmerged pending review.
