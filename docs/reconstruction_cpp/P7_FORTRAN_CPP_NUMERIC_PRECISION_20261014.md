# P7: original CALPUFF vs C++ numerical-precision ledger (2026-10-14)

**Scope:** CALPUFF v7.2.1 original `calpuff.for` at immutable SHA256
`da40372cab1c181158d0ee5faac16f678e876fc14415073c38c8e3bdabfbc568`,
C++ P7 in Draft PR #41. This ledger supplements, but does not supersede,
`P7_COMP_ORDER_ARCHITECTURE_GATE_20261013.md`.
All original inputs and `puff.con` remain unmodified.

## Precision ABI versus evaluation precision

The pinned original Fortran recipe uses gfortran-11 with
`-std=legacy -ffixed-line-length-72 -fno-automatic -fno-align-commons
-fallow-argument-mismatch -O0 -fdec-format-defaults`. The compiled
`audit_original_precision.py` kind probe demonstrates:

- unqualified `REAL`, including implicit `PFSAMP` and `CALCPF` locals: **4 bytes**
- explicitly declared `REAL*4`: **4 bytes**
- `DOUBLE PRECISION` and `REAL*8`: **8 bytes**
- default `INTEGER`: **4 bytes**
- **no blanket `-fdefault-real-8` or `-freal-4-real-8`** in the frozen build.

C++ public APIs use `double` for some geometries and
`SamplingIntegrals.i1/i2` storage. They **must not** thereby promote an
original `REAL*4` arithmetic expression to 64-bit evaluation. The selected
physics kernels use local `float` or `R=float` for original REAL4 and
widen only at explicit storage/output boundaries.

| Original stage and source | Original type and evaluation | Native C++ equivalent | Result |
| --- | --- | --- | --- |
| `COMP` `QOLD/QNEW`, original L10965/11108 | Original COMMON `QM/QU`, default REAL4, snapshot before removal and sample after | `std::vector<float>` through VMASS/DRY, original-order driver | 196/196 **bitwise** for live receiver |
| `SETPUF`/virtual transport sigmas | Original REAL4 `SYB1/SYM1/SYE1` and `SZB1/SZM1/SZE1` | Internally `float`; some C++ envelopes use `double` | 1275/1275 original case selected motion/sigma fields were previously accepted |
| `PUFRECS` `FREC/SYREC/SZREC` | Original REAL4, true trajectory extrapolation `FCLIP` is distinct from `RCONST` sampling radius | `receptor_pg_sigma` uses `float`, caller passes independent `FCLIP` | First-hour hotspot `SYREC/SZREC` **196/196 bitwise**, after prior separate-FCLIP fix |
| `PFSAMP` L4715/4737–4748, `XI1` | `RT2=1.4142136`, `RTPIBY2=1.2533141`; both default REAL4; `XI1` is REAL4 | `R=float` internal, then widened public `i1` | **196/196 bitwise** |
| `PFSAMP` L4747–4748, `XI2` | `B2DA=B*B/A`; `XI2=-B*XI1/A+(XXEXP/A)*(EXP(...) - EXP(...))`, **XI1 must be REAL4 at the next operation** | Previously direct `integrals.i1` (double) promoted `-B*XI1/A`. Now `const R xi1=static_cast<R>(integrals.i1)` then `const R xi2=...` | **49/196 → 196/196 bitwise** (commit `0f222d3`) |
| `PFSAMP` L4730–4733 calm/low-wind path | `XI2=0.5*EXP(...)`; `XI1=2.*XI2` with both REAL4 | `const R xi2`, `const R xi1=2.0F*xi2`; widen at output | Source-order precision fixed for branch; **real Hefei selected-state full-branch independent parity not claimed** |
| `CALCPF` L4293–4295, `DINV,T2,T1` | `DINV=ASDF/(6.2831853*SYREC**2)`; **evaluate `SYREC**2` before multiplying by 6.2831853**, all REAL4 | Previously `(two_pi*sigma)*sigma` differed by intermediate rounding. Now `sigma_squared=sigma*sigma`; `denominator=two_pi*sigma_squared`; then T2/T1 as REAL4 | After fix **196/196 bitwise** for `T1/T2` |
| `CALCPF` L4302–4305, `CONC` | `VDPVD*XTEMP*(QOLD*T1+QNEW*T2)` default REAL4; accumulate each sample in original order | `receptor_concentration_increment`, `float`; single `COMP` accumulator | 196/196 selected receiver step increments **bitwise**, 2500/2500 H-3 first-hour words **bitwise** |
| `ERFDIF`/math library | Original REAL4 `EXP/SQRT/ERFDIF` and pinned gfortran math implementation | C++ `std::exp(float)`, `std::sqrt(float)`, `std::erf(float)` and `std::erfc(float)`; exposed API may use double | Selected case agrees in `XI1`; other branches/compilers need independent source-oracle validation before general parity claims |

## Frozen real-case numerical regression history

| Revision | 2500 real first-hour H-3 concentration words identical | Nonidentical | Max abs error |
| --- | ---: | ---: | ---: |
| Before separate PUFRECS `FCLIP` fix | 2363/2500 | 137 | 0.0499834418 Bq/m³ |
| After `FCLIP`, before precision repairs | 2484/2500 | 16 | 4.47034836e-7 Bq/m³ |
| After `PFSAMP` XI2 REAL4 fix `0f222d3` | 2489/2500 | 11 | 4.47034836e-7 Bq/m³ |
| After CALCPF square-first grouping `717ccfe`, trace mirror `7bf9107` | **2500/2500** | **0** | **0 Bq/m³** |

Independent original CALPUFF and native first-hour replay:
- Frozen 2022 Hefei, hour 1; real `MET.DAT`, `puff.inp`, no original DGM or `puff.con` fed into the solver.
- 54 released puffs, 1275 original-ordered `COMP` substeps, 50×50 H-3 grid, 137 nonzero concentrations.
- Original `puff.con` and original 143-hour DGM hashes are unchanged by write-only `CALCPF` instrumentation.
- Receptor (i=19,j=50), **196/196 original/native substeps**: all `QOLD,QNEW,SYREC,SZREC,ZPR,ZRPOLE,VCOUP,XI1,XI2,T1,T2,XTEMP,CONC` match REAL4 bits, not merely tolerances.
- All **2500 first-hour H-3 concentration float32 values match bitwise**, total 39.4597444 Bq/m³ when summed as reported by frozen-case test.
- CI evidence: [original CALCPF 196-stage gate](https://github.com/RRain001/CTEAS/actions/runs/38509596333) and [frozen first-hour concentration gate](https://github.com/RRain001/CTEAS/actions/runs/38509368374).
- The runnable original/C++ interface/type/source manifest is `native_cpp/modules/p7_calpuff/reference/audit_original_precision.py`; first-difference comparison is `.../dgm_p7_advection_2022/compare_h3_calcpf_receiver_traces.py`. Preserve failure-on-any-mismatch behavior.

## Strict boundaries / follow-on

**Accepted numerically:** selected source/physics branch, first meteorological hour,
H-3 2500 receptor concentrations and the 196 physical substeps at receiver
(i=19,j=50), for the pinned original Fortran compiler and GitHub-hosted
Ubuntu C++ build.

**Not yet accepted:** arbitrary controls/dispersion options, alternate Fortran
or C++ math libraries/compiler flags, independent `HE-3` 143-hour result,
continuous source-specific 6h/143h puff state and capacity-triggered
`SWAP/ROLLDN`, per-hour original output records, full `puff.con` file
equivalence, or wet removal (`MWET=0` in the selected real scenario).
A PASS for numerical parity in the accepted subset must not be promoted into
P7 production-ready status.

Next sequence: finish all hosted Ubuntu source-kind/float ABI gates; verify
`COMP` historical state and release/retirement on hours 2–6; extend to all
143 hours with canonical `SWAP/ROLLDN`; finally attach full output writer.
Do **not** loosen bitwise gates, retrofit arbitrary `double` arithmetic,
seed native transport with original diagnostic states, modify the P6 solver,
or merge Draft PR #41 without complete equivalence evidence.
