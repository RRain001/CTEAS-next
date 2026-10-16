# P6E G4 source-faithful numeric acceptance — Hefei 2022 (2026-10-13)

## Scientific determination

The **source-locked, native-wind, native-P6D→P6E 143-hour** CALMET 2.1
candidate now passes **45/45 fields, 0 out-of-tolerance points** under the
*unchanged* original comparator limits. This is a selected-case
numeric-equivalence acceptance; it is **not** a claim of general CALMET
configuration parity or complete independent P6F static/header generation.

- Authoritative scientific gate:
  [Actions #38372382572](https://github.com/RRain001/CTEAS/actions/runs/38372382572)
  at commit `6be6581b437b919b69e6ef3971cdb38477d3b56c`.
- Separate Python vs native-C++-clock 6h/143h byte-parity regression:
  [Actions #38372382584](https://github.com/RRain001/CTEAS/actions/runs/38372382584), PASS.
- Frozen original Fortran `MET.DAT` SHA-256:
  `b1823cda92280888d70b00961ab39486036a3086e18637fff21efb4f4b237d30`.
  Its file supplies frozen case/header reference provenance, **not** P6D wind
  input into the C++ production candidate.

## Three independent, source-grounded issues uncovered

1. **Surface-direction conversion**: CALMET PREPDI uses
   `WDRAD = 0.0174533 * WD`, evaluated with original `REAL*4` arithmetic.
   The former C++ `pi / 180` conversion was mathematically more accurate but
   numerically different. Correcting it reduced USTAR/EL/WSTAR exceedances
   from 7,228 to 2,209 without relaxing limits.
2. **Effective READCF BIAS**: `met.inp` values are not always the final
   runtime controls. For the selected `IEXTRP=-4, NOOBS!=2` case, original
   READCF forces `BIAS(1)=-1`. Native C++ previously used the raw
   `BIAS(1)=0`. Correcting the effective control makes WIND1 station
   neutral profiles and all first-hour RSQWT / pre- and post-missing VVW
   compare bit for bit with original CALMET; the three-field exceedance count
   fell from 2,209 to 2,194, so READCF was a real defect but **not** the
   last scientific blocker.
3. **INTER2 RHS precision before widening**: Original INTER2 declares
   `WT` double precision, yet computes `WO(I,J,K) / (RS(L)**2)` using
   `REAL*4` operands. The division and squaring are evaluated in
   single precision, after which the result is assigned to double precision.
   Previous C++ instead cast operands to double **before** the division.
   Reproducing original RHS evaluation order eliminated the remaining 2,194
   USTAR/EL/WSTAR comparator exceedances. Implemented in commit
   [6be6581b](https://github.com/RRain001/CTEAS/commit/6be6581b437b919b69e6ef3971cdb38477d3b56c).

Do not interpret any of these defects as a reason to globally disable
optimization, hard-code an output, substitute original wind, or relax
scientific tolerances.

## Final strict comparator values

| Field | Cells compared | Final max absolute difference | Exceedances |
|---|---:|---:|---:|
| USTAR | 357,500 | 1.7881393432617188e-7 m/s | **0** |
| EL | 357,500 | 0.078125 m | **0** |
| WSTAR | 357,500 | 4.4107437133789062e-6 m/s | **0** |
| P6D U/V/W (27 three-dimensional fields) | 9,652,500 | per-field tolerances unchanged | **0** |
| All 45 output fields | source-scoped 143-hour set | unchanged strict comparator | **0** |

For EL, a larger absolute difference at a high-magnitude location can still
satisfy the original predefined relative error criterion; this is **not**
equivalent to bitwise equality. The reported 45-field numeric acceptance
is therefore distinct from the byte-identical *C++ versus Python control
driver* regression.

## Independent COMP-stage forensic (post-fix)

[Actions #38373270749](https://github.com/RRain001/CTEAS/actions/runs/38373270749)
replayed the first **14 consecutive native hours**, covering the historical
first failing WSTAR/EL hour 9 and USTAR hour 14, against the previously
generated, SHA-locked, write-only original Fortran `DGMSTATE` file.
Without original-wind substitution:

- Original vs C++ post-ELUSTR **QH**: 0 nonzero values.
- USTAR: 6,819 nonzero single-precision values but max only
  `5.960464477539063e-8` m/s and 0 comparator exceedances.
- EL: 6,805 nonzero values, max `0.078125` m but 0 comparator
  exceedances under the unchanged combined absolute/relative rule.
- Post-MIXHT DPTT: bit-exact; WSTAR: only 1 nonzero value, max
  `7.450580596923828e-9` m/s, 0 comparator exceedances.
- The diagnostic scripts record provenance, stage order, first nonzero,
  maxima and RMS; they do not modify P6E physical kernels.

The combination of the complete 143h gate and this 14h stage audit provides
independent evidence that the remaining previous G4 failures were numerical
reconstruction issues rather than an unresolved altered P6E formula.

## Hold boundary

Keep PR #53 **Draft** while the project still has other open release
acceptance tasks, particularly independent P6F/header generation and broader
configuration coverage. An accepted *selected-case P6E 18/18 field result*
must not be silently generalized to production-complete all-case CALMET.
