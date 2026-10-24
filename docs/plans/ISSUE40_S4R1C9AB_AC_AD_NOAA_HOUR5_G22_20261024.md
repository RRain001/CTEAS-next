# S4-R1c9ab/ac/ad — Genuine NOAA fifth-hour G26A G22 validation

## Scope, inputs, original authority
- Issue #40 OPEN; P7 Issue #36 OPEN. Only selected CALMET P6 physics paths; no generic P6 production admission.
- Original NOAA 2022-06-01 02–08 UTC, 82 × 85 × 9, 2 surface stations, 1 upper station, 63 WATER cells. Fifth native hour end UTC 06 (05–06 interval).
- Unmodified original Fortran CALMET 6.5.0 source SHA256 835c351d780c0200be721c2d9cbb8dc45b3a8fcd4cb8815fc47bbd26a56a7b23; original met.x SHA256 1c2d1227d1ba7e8135bd81488be48d3d1e54f041839f20cd466bcd0176f41322.
- Frozen original six-hour G22 staged trace SHA256 b6d96dab81af8e9cba89ef55d386aba8082d9136aa7ef569ad0f9e39f1e31869 (private /home/lhy/dev/CTEAS-next/local-science/s4-r1c9l-hour3-original-g22-20261024/run/met/S4_DIAGNO_G22.BIN). This task did not recompile or freshly rerun Fortran.
- Identical original/native P1–P5 inputs SHA256: met.inp c5e6b02ac623a3f7d11b464deca657cd26285605753ef185bcc215257dee9744; GEO 5feaa58e5835576b3ae2c03a51e955114d620a7aeb710ded58a9f999695f602a; final SURF 6a3f45eebdba8c7b783b5b89d5e1b3a7eecf2ce71f7fdaa814e7a54f04a9f655; UP a4e99dabe6ed246643bb298c3d883c8cde8a5dd07aaa346952f7e096d325ad00. No original MET output feeds native physics.

## Fifth-hour original-source MISSFC and native stage0–2
- Explicit test-only fifth-hour preflight depends on validated native fourth-hour G14 positive state and published AA/BB/CGAMMA station clocks. G43 original COMP nonwind MISSFC is applied only to a detached internal source copy. It preserves unchanged P5 winds, precipitation code, station identity and hour clocks.
- Source-native PREPDI/WIND1/FRADJ stages0–2 run on the live fifth G14 preview and verify native fourth-hour committed ZI/ZICONV/DPTT bitwise inheritance; no fifth commit. Default production G22 stage3 remains correctly rejected.
- Ubuntu Docker DEV_ONLY GCC12 compilation run dev-20261024T024344-558511b2 EXIT 0. Private genuine fifth-hour stage0–2 run /home/lhy/dev/CTEAS-next/local-science/s4-r1c9ab-hour5-source-preflight-20261024 EXIT 0.

## Fifth-hour G22 science audit and live actor
- Extend strict G66 native forensic to expected_hour_index=4, and add explicit fifth-hour-only G26A stage3–6 actor. Prior WATER USTAR/EL comes from actual C++ fourth-hour P6F that is verified during positive fourth-hour G14; not frozen original CALMET outputs.
- Standalone G66 G22 stage10/20/30/40/50 and native live fifth-hour G26A stage0–6 execute independently. Their native G22 binary traces are BYTE-IDENTICAL (SHA256 e8ae792ac9a6cca11e5d1a3348206a446cc5eb38100a262aff2ccf2aca019f3a); neither commits fifth-hour memory or clocks. Default G22 production rejection is rechecked separately.
- Original-vs-native independent Python strict comparator: scripts/s4/s4r1c9ac_compare_hour5_g22_trace.py. Checks original SHA, native SHA, genuine GEO SHA, source WATER mask, frozen stage schema, exact end-hour header, fixed pre-registered tolerances and WATER bit equality.
- PASS_SCOPED_FROZEN_G22_INTERMEDIATES: **181,220 / 181,220 REAL4 in original frozen tolerances**, 0 exceedances, **161,162 bitwise equal**. 20,058 values differ bitwise but all remain inside tolerances. At all 63 WATER cells, USTAR and EL historical fields individually match original bitwise: 63/63 each.
- Independent science report SHA256 3d58ef145e38ef14f6a552d11652b0999538be99502db5294a2504583d05e3d9, matching for both private native paths:
  - /home/lhy/dev/CTEAS-next/local-science/s4-r1c9ac-hour5-native-g22-20261024
  - /home/lhy/dev/CTEAS-next/local-science/s4-r1c9ad-hour5-live-g22-20261024
- Ubuntu GCC12 Docker DEV_ONLY build passes: dev-20261024T024643-ae438233, and live actor dev-20261024T024950-62cd10ff. Latter also passes 20/20 related Python tests. Final live native executable SHA256 011f30a8399e377f7c7afdbb7bf9ee6312f9a8976094ec65d6ff2c56ac084a30. Both real runs EXIT 0.
- First local Python fixture copy contained an incorrect fifth-hour clock constant in the truncation test. It was corrected and 7/7 corresponding tests plus 20/20 Docker selections passed. No thresholds were changed or relaxed.

## Acceptance status / next steps
- Fifth-hour G23/G24 STHEOR/INTER2/SMOOTH/DIVCEL_W stages7–11: NOT_RUN.
- Fifth-hour G26B COMP stages12–15, G64 stage16 original 45-field P6F parity and G14 rollback/positive memory-clock commit: NOT_RUN.
- Sixth-hour stages0–16, authentic general configurable P6, P7 and wet deposition: NOT_RUN / NOT_ACCEPTED.
- Exact-SHA Docker full, GitHub required checks and external independent scientific review: NOT_RUN. No auto-merge or science-validated/merge-verified label.
- Next use same fifth-hour live G26A G22 stage6 state to execute source-native G23/G24 stage7–11 in G14, compare independent pristine original six-hour stage90/100/110, then COMP/P6F. Maintain default production rejection and identical science tolerances.
