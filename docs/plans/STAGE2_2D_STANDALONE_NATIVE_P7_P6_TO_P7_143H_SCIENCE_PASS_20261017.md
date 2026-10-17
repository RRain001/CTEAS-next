# S2-2D — standalone no-oracle native P7 143-hour scientific acceptance, selected Hefei 2022

Date: 2026-10-17. **Result: PASS_SCOPED**, not all CALPUFF options or all sites. Owner-mandated computational UTM origin remains **exactly three decimals in km**, for this case `XREFKM=510.885`, `YREFKM=3531.269`; no higher-precision origin may replace the selected grid coordinates.

## 1. New executable delivered

New independent numeric command `cteas_p7_native_hefei_2022` lives at `native_cpp/modules/p7_calpuff/src/native_hefei_2022_main.cpp`, linked by `native_cpp/modules/p7_calpuff/CMakeLists.txt`. It is **not** the old `tests/original_hefei_sixhour_native_receptors_tests.cpp` test program:

```
cteas_p7_native_hefei_2022 --met <actual native P6 MET.DAT> \
  --control <frozen selected puff.inp> \
  --makegeo <frozen selected makegeo.inp> \
  --output <non-existing file> --hours 1|6|143
```

Its numerical entrypoint derives native METFM1 PRFIN/source release, advances the stateful real CALPUFF C++ `OriginalCompRiseMultiPuffHours` sampled COMP, applies selected dry deposition and terrain-aware receptor CALCPF, then writes actual hourly H-3 concentration via `HourlyConcSeriesWriter` and source-derived `create_original_hefei_2022_wrout1_writer`. It accepts **no original `puff.con` or DGM path/argument** and does not read them.

Selected physics include the frozen one-point H-3/HE-3 source, `METFM=1`, `MCTADJ=2`, `MDRY=1`, `MTRANS=1`, `MXSAM=99`, `IWET=0`, and 50×50 grid with 100 m cell size. Other physical options are **not accepted** by this report.

## 2. Native-only real 1h / 6h / 143h execution without original CON/DGM

[GitHub Actions #39038369856](https://github.com/RRain001/CTEAS-next/actions/runs/39038369856), **SUCCESS**; [derived-only artifact #12102713082](https://github.com/RRain001/CTEAS-next/actions/runs/39038369856/artifacts/12102713082). The original `puff.con` and original DGM `*.bin` were removed from checked-out selected-case reference locations before the new CLI executed. The original frozen C1 MET was available **as input for this software-isolation smoke**, not claimed to be freshly native P6.

| Native P7 run | H-3 words | Positive H-3 values | Physical puff substeps | WROUT1 records | Result |
|---|---:|---:|---:|---:|---|
| 1 hour | 2,500 | 137 | 1,275 | 3,229 | PASS |
| 6 hours | 15,000 | 2,216 | 11,458 | 3,244 | PASS |
| 143 hours | 357,500 | 42,685 | 254,687 | 3,655 | PASS |

Actual 143h WROUT1 size = **1,896,056 bytes**; integrated gridded H-3 concentration sum across 143h and 2500 cells = `11743.117102298125` Bq/m3 in model concentration field arithmetic (not an integrated emitted inventory). Independent Python Fortran record parser checked each 1/6/143h output field count, physical nonzero values, Fortran record frames, and original-compatible comment headers. Invalid hour 144 and nonexistent MET input are denied without producing output. Previous failed run #39037932288 was a **validation-script-only record count bug**: 3,218 WROUT1 comment records were accidentally excluded; the fixed 3,226 + 3 × hours count passed, with no physics source change.

## 3. Real fresh native P6 MET → native-only P7 → independently rerun untouched original CALPUFF

**Authoritative full-chain Actions #39038152375: [SUCCESS](https://github.com/RRain001/CTEAS-next/actions/runs/39038152375)**.
**[Numerical/hash metrics-only artifact #12103301618](https://github.com/RRain001/CTEAS-next/actions/runs/39038152375/artifacts/12103301618)**.

The Actions checked out source HEAD `5ed8894c94e313470e8a4e2acd841dffcdf97f9e` (later PR head `77673251a490a8beb0dd4cc4fd5eb0f63be3207a` changed only a standalone test's independent comment-record count; new P7 C++ executable unchanged). Original vendor CALPUFF code was restored from immutable `RRain001/CTEAS@dfad99a78ed84d655e21411c9d25eb0d2583bf13` into a separate original comparator build only.

1. Built existing accepted native P6D/P6E/P6F and newly added native P7 C++ executable. Historical original `run/met/met.dat` was **moved out of the native P6 staging directory** before 143h computation and restored only afterward to serve as original numerical reference.
2. Real P6 143h produced `native_causal_independent_header_calmet.dat` and strict P6 manifest. Full 143h native P6 MET passed unchanged 45-field baseline comparator to historical reference. Source GEO used in this integration is the **frozen, previously validated three-decimal 2022 case**, with its **20,000 physical GEO values separately proven identical** to genuinely regenerated canonical P1/P2/P3 on [Actions #39034270535](https://github.com/RRain001/CTEAS-next/actions/runs/39034270535). **P1/P2/P3 were not rerun in this integrated Action**; P4/P5 use accepted frozen UP/SURF/station metadata.
3. Compiled and actually ran **unaltered CALPUFF 7.2.1** with the **exact newly produced native P6 MET** to create `C-original-calpuff.con` as an independent comparator (not an input to native P7).
4. Removed frozen original `puff.con` and DGM binaries from the selected native compute checkout, ran new `cteas_p7_native_hefei_2022` with **only actual native P6 MET + frozen puff.inp + makegeo.inp**, generated genuine `D-new-native-met-standalone-native-p7.con`, with full 143h H-3 source/COMP/sampling/writer.
5. Independently parsed C/D outputs using existing unaltered `compare_p7_hourly_concentrations.py --require-bit-exact` and asserted all values. Actual Actions log:

```
P7_COUPLING_FIELDS=PASS HOURS=143 NX=50 NY=50 REAL4_MATCH=357500/357500 BITWISE=True FIRST=None MAX_ABS=0.0
S2D_NATIVE_P6_TO_NO_ORACLE_NATIVE_P7_VS_UNMODIFIED_ORIGINAL=PASS_SCOPED
```

**Science verdict:** `P6_NATIVE_MET_143H=PASS_SCOPED`, `P7_NATIVE_ONLY_H3_143H=PASS_SCOPED`, `CALPUFF_ORIGINAL_VS_NATIVE_SAME_MET_H3_REAL4=357500/357500_BIT_EXACT`. No original CON/DGM values were used to advance native puff state. No numerical threshold changed.

## 4. Scope limits and remaining engineering hardening

The result covers exactly **Hefei 2022 frozen geography and selected H-3 point-source/no-rain physical options**. It does **not** certify generalized CALMET/CALPUFF alternative dispersion/rise/chemical/wet-deposition physics, fully fresh P4/P5 original data source provenance, future location case profiles, or G5 (untouched).

Before **production-quality Ready for Review / merge** under the stricter S2-2D contract: bind new native P7 to authenticated P6 producer manifest/executable+source hashes and exact accepted native MET rather than trusting valid-looking input metadata; strengthen invalid/tampered input, temporal-gap, altered-option and source-coordinate negative gates; ensure incomplete/failed output is not published at the final path; add appropriate test coverage and **rerun full same-MET science gate at the resulting source HEAD**. Leave PR #28 Draft until those tests pass.

No repository-local Codex or user workstation was used in this stage: commits, builds, full 143h runs and evidence were performed through GitHub.
