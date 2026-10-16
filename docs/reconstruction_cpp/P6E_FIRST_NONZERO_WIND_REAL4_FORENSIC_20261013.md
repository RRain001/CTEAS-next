# P6E failure: upstream native wind REAL*4 first-divergence audit (2026-10-13)

## Scope and scientific status

This is a forensic note for frozen Hefei 2022, 50×50×9 cells, 143 hours.
P6D 27/27 U/V/W source-comparator fields PASS, but **P6E is NOT yet accepted**.
Do not weaken acceptance tolerances and never feed original Fortran wind back
into the accepted C++ native candidate. All source-wind substitutions are
explicit isolated controls, not production.

## Controlled evidence

- Baseline [Actions #38362578127](https://github.com/RRain001/CTEAS/actions/runs/38362578127):
  USTAR 5,952 / EL 1,105 / WSTAR 171 outside fixed tolerances, 7,228 total.
  Source-wind input into unchanged C++ P6E produces three PASS: a one-variable
  diagnostic that implicates upstream wind numerical differences, but does not
  establish which stage caused them.
- Confirmed native-vs-original PREPDI discrepancy:
  original pinned `calmet.for` at L13890 uses
  `WDRAD = 0.0174533 * WD` with Fortran REAL*4 arithmetic, while the old
  native code used `WD * pi / 180.f`. This changes the station's U/V before
  the station flux and extrapolation calculations. Corrected in
  [commit c864c13](https://github.com/RRain001/CTEAS/commit/c864c13ff848befdb640bbf252fcae41488ac60d).
- After changing ONLY the native wind-to-radians literal, frozen numeric gate
  [Actions #38365068473](https://github.com/RRain001/CTEAS/actions/runs/38365068473):
  USTAR **1,935**, EL **236**, WSTAR **38**, **2,209** total outside the
  unchanged tolerances. Reduction 69.4%, but still FAIL. First failing
  USTAR hour 14, EL/WSTAR hour 9. P6D 27/27 remain PASS.
- Old U/V level-1 max differences 5.96e-6 / 9.54e-6 m/s, now both
  9.536743e-7 m/s. Old AVETMP integer shift flips: 6,187
  (with 187 USTAR failures), after fix 422 (with only **7**
  USTAR failures). Therefore discrete integer-shift flips cannot explain
  most remaining P6E USTAR failures.

## Exact REAL*4 source boundary trace

The write-only Fortran source instrumentation in
`scripts/p6d_trace_original_inter2_first_layer_143h.py` copies SHA-pinned
vendor CALMET and requires its original emitted MET.DAT to retain the frozen
SHA-256; it does not write into the vendor codebase.

- [Actions #38365657386](https://github.com/RRain001/CTEAS/actions/runs/38365657386)
  after radians fix: surface U/V first-hour differences now vanish to
  REAL*4 accuracy; the earlier CSV decimal comparison had negligible
  formatting-only artifacts. Original `before_slope_u/v` first level
  remains nonzero, max 1.90735e-6 / 1.43051e-6 m/s;
  `inter2_u/v` max 9.53674e-7 / 1.43051e-6 m/s.
- [Actions #38366338218](https://github.com/RRain001/CTEAS/actions/runs/38366338218)
  adds an original after-WIND1 source snapshot and compares all 143 hours to
  native `wind1_u/v_*.f32`. The **first observable nonzero wind stage is
  WIND1**, hour 1, (i=1,j=1), U Δ=1.1920929e-7,
  V Δ=2.3841858e-7 m/s. 143h WIND1 max differences
  U 1.90735e-6 and V 1.43051e-6 m/s.
  The downstream FRADJ/SLOPE/INTER2 outputs inherit this drift.

Independent synthetic first-guess WIND1 tests pass exactly zero difference,
so the real-case divergence is in **runtime preparation and/or REAL*4
arithmetic for actual station neutral SIMILT profiles, real station coordinates,
or other actual-case inputs**, not proven to be in the interpolation kernel.
Do not claim all 2,209 downstream exceedances have been causally attributed
to a single WIND1 computation until the full native-wind 143h strict comparator
and same-wind internal-stage A/B controls substantiate it.

## Next narrow acceptance experiments

1. For each hour, trace the source and native *station neutral SIMILT*
   (USTMP/VSTMP) before WIND1 interpolation and record REAL*4 bit differences;
   if identical, compare frozen real-case station coordinate and normalized
   WIND1 `RSQWT` at first differing (i,j,k).
2. Test original implicit REAL*4 intermediates and REAL*4-to-REAL*8 promotion
   at SIMILT `ELINV / DH200 / PSIM / R8` as a single bounded change,
   using strict source-stage trace and 143h comparator.
3. Re-run the original P6E fields with **native** P6D input; require
   USTAR, EL, WSTAR to have zero tolerance exceedances. Also retain
   27/27 P6D PASS, fail-closed input/output, source-case SHA, and 143h
   C++/Python coordinator byte parity.
4. Any residual should be localized by first-failing hour/cell and P6E
   `AVETMP→SURFVAR→ELUSTR→MIXHT→AVEMIX→WSTARR` stage tracing before
   modifying physics. Near-neutral EL has high condition sensitivity due to
   heat-flux denominators. No post-hoc relaxation of scientific tolerances.

**Hold:** PR #53 remains Draft and source scientific P6 G4 is FAIL
until all three native-driven P6E fields meet original fixed tolerances.

## Negative controlled experiment: isolated SIMILT precision rewrite

- [Commit cad1ce0b](https://github.com/RRain001/CTEAS/commit/cad1ce0b7bc6f8950aa8ea324b303310f8d4c2c7) changed selected SIMILT intermediate values from C++ double to Fortran implicit REAL*4 and adjusted the REAL*4-to-REAL*8 PSIUD promotion, without altering source formulae or accepted tolerances.
- [Actions #38365989475](https://github.com/RRain001/CTEAS/actions/runs/38365989475): independent original SIMILT kernel parity PASS; first 6-hour causal test PASS.
- Crucially, [Actions #38365989371](https://github.com/RRain001/CTEAS/actions/runs/38365989371): full 143h strict source comparison showed **exactly the same** remaining USTAR **1,935**, EL **236**, WSTAR **38** = **2,209** exceedances as the previous source-radians-only fix; P6D still 27/27 PASS. Therefore this precision hypothesis did **not** improve the actual case and should not be described as a causal fix.
- The experiment was reverted in [commit 248a66b](https://github.com/RRain001/CTEAS/commit/248a66b25892b63f064e6111126a78ca16876d2a), retaining only the measured beneficial PREPDI surface-direction radians fix. If future experiments revisit SIMILT, change one cause at a time and use the first nonzero original WIND1 trace as the tighter intermediate acceptance gate.

Keep this negative result frozen as scientific evidence, not as an open recommendation to apply the same change again.


## Decisive native vs source WIND1 neutral station profile test

[GitHub Actions #38367919692](https://github.com/RRain001/CTEAS/actions/runs/38367919692)
uses a new original Fortran write-only `dgmwind1neutral(ustmp,vstmp)` hook
immediately after station extrapolation within WIND1, **before** spatial
interpolation. The native C++ P6D independently writes its corresponding
neutral SIMILT 9-level profile. Both tracks include all **143 hours, 9 vertical
layers and U/V** and compare raw IEEE-754 REAL*4 data; the original instrumented
Fortran emitted the identical frozen reference MET.DAT hash. The profile
comparison is:

| Native-vs-source station profile | Nonzero values | Max absolute error | RMS |
|---|---:|---:|---:|
| `USTMP(:,surface)` from neutral SIMILT | **0** | **0** | **0** |
| `VSTMP(:,surface)` from neutral SIMILT | **0** | **0** | **0** |

The original source output **after WIND1** is still not byte-identical to
native C++, with first level first cell differences U 1.1920928955078125e-7
and V 2.384185791015625e-7 m/s (the 143h grid maxima are U 1.9073486328125e-6
and V 1.430511474609375e-6 m/s). This conclusively eliminates the neutral
surface-station SIMILT profile as the origin of the observed WIND1 discrepancy
for this frozen case, and narrows it to **WIND1 spatial weighting, station
relative coordinates and/or REAL*4 grid accumulation order**. The very first
nonzero grid field appears already in WIND1, before FRADJ/SLOPE/INTER2.

**Next exact diagnosis:** capture original-vs-native `RSQWT` (normalized
inverse-distance weights) and `VVW(k,station)` (vertically varying and
missing-upper corrected weights), starting with hour 1 and cell (1,1). If
RSQWT or VVW differ, audit geometry and normalization arithmetic; if both
agree at the bit level, audit the original `UNEXT/VNEXT` two-station
accumulation order and compiler-level floating-point contraction, **without
changing P6E physics**. This is an evidence-driven narrowing step, not yet
proof that correcting WIND1 weights alone will eliminate all 2,209 residual
P6E exceedances. Strict native-wind P6E science status remains FAIL.

## READCF effective BIAS root cause and remaining P6E hold

Original CALMET calmet.for L26579-L26593 (READCF) resets BIAS(1)=-1 when IEXTRP<0 and NOOBS!=2, even when met.inp states BIAS(1)=0. The frozen case uses IEXTRP=-4 and active surface observations. Previously C++ WIND1 consumed the raw BIAS=0. This was an actual preprocessing reconstruction defect.

- Source/native WIND1 neutral SIMILT station profile 143h x 9 levels U/V bit-exact: Actions #38367919692.
- Initial WIND1 two-station RSQWT 2500 cells bit-exact: Actions #38368765844.
- Pre-fix after-BIAS VVW differed on all 2500 cells (original surface/upper first-cell 1/0; C++ approximately 0.500201/0.499799). A shortcut forcing VVW=1 was reverted as non-source-exact and ineffective.
- Production C++ real-case READCF normalization fixed in commit 35930faa97d66cebb70dd5ecfd6cef5c17ce432e; generic WIND1 kernel unchanged.
- Post-fix original-vs-native first-hour RSQWT, before/after-missing VVW 2500 cells bit-identical, 0 ULP differences: Actions #38371413791.
- Post-fix 143h strict G3/G4: P6D U/V/W 27/27 PASS. P6E still FAIL: USTAR 1,919, EL 237, WSTAR 38; total 2,194 exceedances (previous radians-only baseline 2,209). Actions #38371224052. No science tolerance change.

READCF was a genuine WIND1 reconstruction defect but fixing it reduces P6E failures only by 15 points, not by 2,209. The remaining P6E root is NOT proven to be WIND1. Next target: first-failing EL and WSTAR hour 9, USTAR hour 14; compare source/native AVETMP, SURFVAR, ELUSTR stability iterations/convergence, QH/RHO/TEMP2D, MIXHT, AVEMIX, WSTARR using native P6D drive. Keep PR #53 Draft.

References: https://github.com/RRain001/CTEAS/actions/runs/38371413791 ; https://github.com/RRain001/CTEAS/actions/runs/38371224052 ; https://github.com/RRain001/CTEAS/commit/35930faa97d66cebb70dd5ecfd6cef5c17ce432e


## Closure: frozen 143h native-wind P6E G4 numeric parity (2026-10-13)

**Scientific result: PASS for the locked Hefei 2022 50×50×9, 143-hour case; not a generic CALMET acceptance.**
The independent source comparator in [Actions #38372382572](https://github.com/RRain001/CTEAS/actions/runs/38372382572) passed all 45 output fields using the actual C++ P6D-produced wind and the C++ P6E COMP path, `total_exceedances=0`. The reference CALMET.DAT was SHA-256 pinned; fixed G3/G4 tolerances were not changed. P6D 27/27 U/V/W PASS; P6E 18/18 PASS, including USTAR/EL/WSTAR zero exceedances. Maximum absolute discrepancies: USTAR 1.7881393432617188e-7 m/s; EL 0.078125 m; WSTAR 4.4107437133789062e-6 m/s. Source-wind-only control was independent of the native-wind scientific candidate.

Two source reconstruction errors explain the previous long-running G4 blockers:

1. Original `READCF` (vendor calmet.for lines 26579–26613) resets effective `BIAS(1)=-1` for IEXTRP<0 with surface observations and changes higher level bias when |IEXTRP|=1; C++ previously consumed deck BIAS unchanged. This was corrected in [35930faa](https://github.com/RRain001/CTEAS/commit/35930faa97d66cebb70dd5ecfd6cef5c17ce432e). Original 143h first-level WIND1 and pre-SLOPE U/V subsequently became bit identical; 2500 gridpoint RSQWT, pre-/post-missing VVW bit parity and entire first-hour nine-level WIND1 U/V were independently demonstrated in [38371413791](https://github.com/RRain001/CTEAS/actions/runs/38371413791) and [38372106802](https://github.com/RRain001/CTEAS/actions/runs/38372106802). After this fix alone: still USTAR 1,919, EL 237, WSTAR 38, total 2,194 exceedances.
2. Original `INTER2` (vendor calmet.for line 8526) computes `WT = WO(I,J,K)/(RS(L)**2)` with REAL*4 operands, *then* assigns to DOUBLE PRECISION WT. Native C++ had computed the RHS with double operands, yielding a numerically different effective observation weight and first-level wind. Corrected in [6be6581b](https://github.com/RRain001/CTEAS/commit/6be6581b437b919b69e6ef3971cdb38477d3b56c), casting the *REAL*4 expression result* to double afterward, for both regular and LVARY nearest branches. Independent source INTER2 selected test + all 32 CTests: [38372382463](https://github.com/RRain001/CTEAS/actions/runs/38372382463) PASS.

Combined changes eliminated all remaining 2,194 P6E exceedances in the frozen actual-case native C++ G4 gate; there was no relaxation of comparison thresholds, Fortran wind substitution, or P6E physical-formula rewrite. The 143h C++ scheduler-vs-Python byte-parity gate [38372382584](https://github.com/RRain001/CTEAS/actions/runs/38372382584) also passed.

**Scope exclusions / remaining work:** this is one locked Hefei scientific case, not proof of all prognostic/NOOBS/other geometry branches. The full native independent original-header/static-generation P6F acceptance and general G5/P6 overall scope remain separately gated. The current C++ hour authority still calls process-backed physics kernels (not final in-process `step_diagno/step_comp`). PR #53 remains Draft until broader architecture and P6F requirements are resolved.

Earlier FAIL counts and hypotheses above are historical diagnostic milestones, not the current G4 state.
