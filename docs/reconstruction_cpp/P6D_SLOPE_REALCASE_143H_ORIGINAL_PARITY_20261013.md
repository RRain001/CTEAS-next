# P6D SLOPE driver inputs: original-source 143h numerical acceptance (2026-10-13)

## Frozen selected-case scientific verdict

For the **2022 Hefei, 50 × 50 × 9, 100 m, 143-hour** CALMET case, the C++
P6D→P6E **causal native hourly path** now supplies the original source SLOPE
with **bitwise-identical** `QH`, `TEMP2D`, `HMAX`, `HMIN`,
`DISTHMAX`, and `DISTHMIN` at every hour/cell. All scientific tolerances
remain unchanged.

- Primary original-versus-C++ full-chain data: [Actions #38406572248](https://github.com/RRain001/CTEAS/actions/runs/38406572248), job `Original SLOPE drivers vs full native causal P6D-P6E 143h`, result `PASS_SLOPE_DRIVER_INPUT_PARITY` (the separate optional HEATFX/ELUSTR *forensic* step in this run failed due to a stale source-call-site anchor; this does **not** alter the numerical verdict).
- Independent end-product: [Actions #38406572817](https://github.com/RRain001/CTEAS/actions/runs/38406572817), `SCIENCE G3/G4 original 143h 45-field parity` **PASS**, same proposed code head `b8f4c953d3a47a001828799026a0bcd2fab1e689`.
- Original Fortran `MET.DAT` is checked byte-identical against the pinned unchanged-source reference before comparisons; original vendor `calmet.for` remains unchanged.
- Work remains on [PR #53](https://github.com/RRain001/CTEAS/pull/53), Draft and unmerged.

| Field entering SLOPE | Reference/candidate sample pairs | Exceedances | Max absolute numerical difference |
|---|---:|---:|---:|
| QH | 357,500 | **0** | **0** W/m² |
| TEMP2D | 357,500 | **0** | **0** K |
| HMAX | 357,500 | **0** | 0 |
| HMIN | 357,500 | **0** | 0 |
| DISTHMAX | 357,500 | **0** | 0 |
| DISTHMIN | 357,500 | **0** | 0 |

**Total: 2,145,000 scalar checks, all bit-identical.** This is a stronger
statement than merely satisfying numerical tolerances for these six inputs.
It is **not** a claim of bitwise equality of every final 45-field output;
those 45 fields pass their separately defined numerical tolerances.

## Root causes and source-faithful corrections

1. Original `DIAGNO` calls `SURFVAR` twice (before and after `FRADJ`);
   a C++ path previously passed the first field directly into
   `HEATFX → AIRDEN → ELUSTR → SLOPE`. The second source-ordered `SURFVAR`
   call restored exact wind-stage provenance and eliminated the original
   60 real-case `TEMP2D` exceedances.
2. Even for **one valid surface station**, original `SURFVAR` does not simply
   broadcast its temperature. Inside `TRADKM`, the reference computes
   `sumwt += wt; tsurf += wt * tmpwrk(station); tsurf /= sumwt`.
   In REAL*4, the multiplication/division can produce a different last bit
   from direct assignment. Original write-only instrumentation detected
   pre-AVETMP nonuniform fields in **121 of 143 hours**; 2,540 cells
   differed from their hour's modal value. The native code now reuses
   the source-faithful inverse-distance interpolation with actual station
   position and `met.inp` `TRADKM/IRAD/NUMTS` (commits
   `8f2b1db08b2849d0a79cae386cc1ece8cb770bde` and
   `b8f4c953d3a47a001828799026a0bcd2fab1e689`).
3. A subsequent source-stage comparison confirmed **all 357,500 U and
   357,500 V** first-level post-FRADJ values matched the original bit for bit.
   That ruled out a missing wind physical correction as the residual QH cause.
4. Previously, a 1-ULP temperature difference at a near-zero cancellation
   inside stable `ELUSTR` could produce a `QH` difference of 0.003478 W/m²
   at a specific cell. This was a *symptom* of upstream interpolation
   precision. An alternative CI-only analytic `theta2` cancellation
   clamp **failed**, increasing QH exceedances to 21,598, and has **not**
   been applied to production C++.

## What this does and does not accept

- **PASS:** Original-source real-case SLOPE six input fields for the
  full, correctly ordered, 143-hour native chain.
- **PASS:** Separately governed 45-field native hourly P6D/P6E/P6F selected-case
  original numeric comparator.
- **Not the acceptance path:** The standalone 143-hour P6D forensic producer
  does not supply the full CGAMMA/previous-hour COMP causal state; it can
  retain **60 TEMP2D exceedances** even when QH passes. Never substitute
  its verdict for full-chain acceptance.
- **Not accepted here:** Generic multi-station/multi-grid P6G configurations,
  in-process P6 scheduling, wet forcing and wet deposition, or full general
  P6F static/header independence.
- **CI housekeeping pending:** A separate, *non-acceptance* HEATFX-versus-ELUSTR
  source-stage diagnostic was selecting a COMP `HEATFX` call rather than
  DIAGNO's `HEATFX` call (original source has four matched HEATFX
  continuations). Fixed its source-site discrimination independently of
  already accepted physical output. The diagnostic must not be mistaken
  for a failed scientific SLOPE gate.
