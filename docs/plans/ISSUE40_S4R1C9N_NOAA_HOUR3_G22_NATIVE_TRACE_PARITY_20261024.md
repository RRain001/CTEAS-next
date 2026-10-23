# S4-R1c9n — authentic NOAA third-hour G22 source-native intermediate audit

## Scope / scientific boundary

This is a **strictly test-only, non-committing** G66 third-hour DIAGNO intermediate replay, stacked on Draft PR #301 (da41d1348e0849e844f179c7abb1bcf44e70cc7e). It consumes actual P1–P5 NOAA 82×85×9, 2SS/1US six-hour forcing, actual second-hour **native** G14 P6F candidate after positive state/clock commit, and actual third-hour native G26A PREPDI/WIND1/FRADJ stages0–2. It independently computes current-hour G22 SURFVAR/HEATFX/AIRDEN/ELUSTR/SLOPE with the existing source-selected kernels. The **only** prior water friction data is the native-computed second-hour P6F USTAR/EL, never original MET.DAT or Fortran intermediate trace.

Original CALMET 6.5.0 source SHA256 835c351d780c0200be721c2d9cbb8dc45b3a8fcd4cb8815fc47bbd26a56a7b23. Unmodified original six-hour MET.DAT SHA256 a7004fbf780212d58536be3957306c2aecc53abe2e58bfec870571b12d8b8e14; independently instrumented Fortran third-hour G22 source trace SHA256 b6d96dab81af8e9cba89ef55d386aba8082d9136aa7ef569ad0f9e39f1e31869. PR #300 independently verified that adding source-stage tracing leaves the **complete** original MET.DAT byte-for-byte identical.

Source input SHA256: met.inp c5e6b02ac623a3f7d11b464deca657cd26285605753ef185bcc215257dee9744; GEO 5feaa58e5835576b3ae2c03a51e955114d620a7aeb710ded58a9f999695f602a; SURF 6a3f45eebdba8c7b783b5b89d5e1b3a7eecf2ce71f7fdaa814e7a54f04a9f655; UP a4e99dabe6ed246643bb298c3d883c8cde8a5dd07aaa346952f7e096d325ad00.

## Observed source physics and initial fail-closed

The first genuine native third-hour attempt **failed** with G17B AIRDEN missing RDSN pressure/TEMP2D, correctly rejecting the third hour's missing surface-station #1 pressure. The raw SURF.DAT shows station #1 entirely missing during 03–04 UTC, station #2 valid. Original CALMET calls MISSFC before DIAGNO every hour (calmet.for approximately L3986), and its MISSFC L9762 onward repairs only five **non-wind** surface fields from current-hour valid station(s).

The test-only G66 route now applies existing, original-source-reconstructed g43_original_comp_missfc_source_only to a **detached copy** of the third-hour model-internal surface state, verifying original P5 wind/precip values are unchanged. This repair is **not** a new P5 imputation or a change to the production G26 source path. The previous failure is retained in private s4-r1c9n-hour3-native-g22-20261024/native.stderr; successful replay in separate s4-r1c9n-hour3-native-g22-retry2-20261024 scratch.

## Actual independent original-vs-native stage comparison

Host GCC12 Release test-only executable SHA256 a952f4c82f59fbe85aa54625d1a4460ecf2f9976e4ec5efa72cd2feeefbdf8ef; private G66 native third-hour trace SHA256 a26c94a247befc5e33f5f94cbe9f4134c1ec0588826de28e55796bef6541fe00. The native executable never reads original MET/trace. A separate Python read-only comparator independently pins original trace, native trace and original GEO, checks 03–04 UTC, five ordered stages, all 63 water cells, full REAL4 shape and finite values.

**181,220 / 181,220 REAL4 values within the existing pre-registered numerical tolerances; zero exceedances.** The exact bitwise result is **156,808 / 181,220** (24,412 values differ at low REAL4 precision), so this is **not** byte-for-byte equality. All 63 WATER USTAR and 63 WATER EL values at third-hour G22 stage40 match original **126 / 126 bitwise**. The complete QSW field matches 6,970 / 6,970 bitwise.

| Original G22 stage/field | Values | Bitwise unequal | Maximum absolute error | Pre-registered threshold |
|---|---:|---:|---:|---|
| 10 TEMP2D | 6,970 | 1,476 | 6.103515625e-5 K | 0.001 K |
| 20 TEMP2D | 6,970 | 1,476 | 6.103515625e-5 K | 0.001 K |
| 20 QH | 6,970 | 651 | 1.220703125e-4 W/m² | 0.25 W/m² |
| 20 QSW | 6,970 | 0 | 0 | 0.005 W/m² |
| 30 RHO | 6,970 | 1,476 | 2.384185791e-7 kg/m³ | 0.0001 kg/m³ |
| 40 QH | 6,970 | 651 | 1.220703125e-4 W/m² | 0.25 W/m² |
| 40 USTAR | 6,970 | 1,709 (WATER 0) | 1.192092896e-7 m/s | 0.005 m/s |
| 40 EL | 6,970 | 2,124 (WATER 0) | 2.136230469e-4 m | max(0.5 m, 1% original) |
| 50 USLOPE | 62,730 | 6,972 (WATER 0) | 1.192092896e-7 m/s | 0.0002 m/s |
| 50 VSLOPE | 62,730 | 7,877 (WATER 0) | 5.960464478e-8 m/s | 0.0002 m/s |

The original tolerances were fixed before this run in ISSUE40_S4R1C3_REAL_MISSFC_LAND_THERMAL_20261021.md (TEMP2D, QSW, QH, RHO, USTAR, EL) and ISSUE40_S4_P6B2B_REAL_G22_SLOPE_20261020.md (SLOPE). They have **not** been enlarged. A 1-ULP corruption of water USTAR is rejected even when below the general USTAR tolerance.

## Test evidence / remaining barriers

- Ubuntu GCC12 Release compiled with -Wall -Wextra -Wpedantic -Werror. Exact native CLI returned 0, reported G66 trace generated test-only, and independently confirmed the third-hour **production** G22 guard still rejects G26A stage3.
- 27/27 Python regression tests passed across PR #300/#301/new PR, including malformed stage headers, partial payload, nonfinite values, one-bit changes, registered threshold invariance and water carry strictness.
- Original vs native numerical stage comparison: PASS_SCOPED_FROZEN_G22_INTERMEDIATES, **0/181,220 frozen-tolerance exceedances**, but **not bitwise equal**.
- G66 tracer is detached from G26A's production stage3. **Actual third-hour G26A G22 stage3 is still NOT_RUN / guarded**, downstream G23/G24, G26B, G63/G64 and G14 third-hour commit are NOT_RUN, third-to-sixth-hour full 45-field Fortran comparison is NOT_RUN, S4 P6/P7 and independent scientific review remain NOT_ACCEPTED/NOT_RUN.
- Private original/native binary traces, full JSON and raw case remain on Ubuntu under /home/lhy/dev/CTEAS-next/local-science/; **none may be committed or uploaded**.

## Next required gate

Add a separately opt-in **real G26A stage3** route that carries native hour2 P6F WATER USTAR/EL as explicit history, with G43 model-internal nonwind MISSFC applied before G26, then re-run the same independent original third-hour five-stage comparator. Only after that exact live actor is validated may the third-hour G22 scientific guard be reconsidered. Next prove G23/G24, G26B/G63/G64 and hour-three positive G14 memory+AA/BB/CGAMMA publication. Do not remove generic hour_index>1 guards, alter production options, or merge any Draft without independent scientific admission.
