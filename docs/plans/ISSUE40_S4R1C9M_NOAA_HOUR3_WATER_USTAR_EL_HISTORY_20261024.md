# S4-R1c9m — real NOAA original WATER USTAR/EL cross-hour state, plus native hour-two seed

## Fixed scope and provenance

- Stacked on Draft PR #300, parent SHA e13b5485b74e8f29fd4714cfc2241c9dac9dfd1d. This PR adds a read-only, fail-closed auditor, ten software regressions and this report. It does not change native G22/G26B/G63/G64 or any production guard.
- Authentic NOAA 2022-06-01 six consecutive hourly original CALMET 6.5.0 outputs: 82×85×9, 2SS/1US, 63 GEO WATER cells. Original MET.DAT SHA256 a7004fbf780212d58536be3957306c2aecc53abe2e58bfec870571b12d8b8e14; independent write-only instrumented original G22 DIAGNO stage trace SHA256 b6d96dab81af8e9cba89ef55d386aba8082d9136aa7ef569ad0f9e39f1e31869; original GEO SHA256 5feaa58e5835576b3ae2c03a51e955114d620a7aeb710ded58a9f999695f602a. Instrumented MET bytes had previously matched pristine MET exactly in PR #300.
- Native hour-two G14 P6F candidate from Draft PR #298 (0e2a5ef19d686b49224838adee4509e83fb9feaa) SHA256 d0612c0fee5d25baf1c640f730e6932733ffc82d6878ba56bb7ef6b157464d82. It was previously independently compared against the original second hour: 313,650 fields, zero frozen-tolerance exceedances. Native candidate is an input to the independent comparator only; it is never injected into native G14.
- Private audit reports: /home/lhy/dev/CTEAS-next/local-science/s4-r1c9m-water-history-20261024/original-water-history.json and original-native-hour3-water-seed-v2.json. Original source, binaries, raw MET, GEO and trace remain outside public Git.

## Proven cross-hour original behavior

Original CALMET calmet.for source call sequence is DIAGNO SURFVAR→HEATFX→AIRDEN→ELUSTR→SLOPE, followed by COMP WATER() (source near lines 4619 and 4663–4670). ELUSTR updates land cells, while WATER() updates the 63 water cells' USTAR and EL (neutral no-overwater-station branch at approximately lines 32810–32814). There is no reset of those WATER arrays between the prior COMP and the following DIAGNO for this selected option.

The auditor checks every one of the five adjacent hour transitions (02→03, 03→04, 04→05, 05→06, 06→07 UTC): for each of the 63 GEO water cells, the previous hour's original MET.DAT USTAR and EL are bit-for-bit identical to the following hour's original G22 stage-40 USTAR and EL, before that hour's COMP WATER executes. Thus 5 transitions × 63 cells × 2 REAL4 = 630/630 exact bitwise matches. First-hour original G22 WATER USTAR/EL are cold zero.

For the critical third model hour ending 04 UTC, the native second-hour P6F candidate's 63 WATER USTAR and 63 WATER EL are independently compared to the third-hour original G22 stage-40 fields. 126/126 native-origin REAL4 values are bitwise identical, zero exceedances under existing frozen USTAR/EL tolerances. This is a strong, source-proven input-history invariant, not a native third-hour G22 physical computation.

| Check | Measured | Admission |
|---|---:|---|
| Original prior MET → next original G22 WATER USTAR/EL | 630/630 bitwise equal | PASS_ORIGINAL_WATER_USTAR_EL_CARRYOVER_630_REAL4_BITS |
| Native hour-two P6F WATER → original hour-three G22 WATER USTAR/EL | 126/126 bitwise equal | PASS_SCOPED_NATIVE_HOUR2_TO_ORIGINAL_HOUR3_WATER_SEED_ONLY |
| Ten parser/carryover tests, including 1-bit and nonfinite rejection | 10/10 | PASS_SOFTWARE_SCOPED |
| Native third-hour G22 TEMP2D/QH/QSW/RHO/land USTAR/EL/SLOPE actual stage3 | Not run | NOT_RUN |
| Third-hour production G22/G26B/G63/G64, full P6 six hours, P7 | Not accepted | NOT_ACCEPTED |

## Why this changes the next implementation

The existing G39/G22 source adapter correctly leaves water USTAR/EL at zero for its first-hour selected WATER stage because original COMP WATER has not yet run. However, repeating zero for third-hour DIAGNO would be wrong: the original third-hour G22 carries forward the native-computed second-hour WATER USTAR/EL (proven here), then overwrites water fields later in COMP WATER.

The next test-only G22 stage3 tracer must therefore receive committed, native-computed prior-hour water USTAR/EL as an explicit, provenance-checked state, while recomputing current land ELUSTR and preserving water QH=0. It must not import prior original MET, and must not silently inject a detached fixture. A later separate scientific admission must establish the rest of stage3 arrays and all nine SLOPE layers, then verify downstream G26B/G63/G64 and G14 hour-three atomicity. Until then hour_index>1 production guards remain intact.

## Reproduce without dependencies or original redistribution

From this exact checkout, run:

    python3 -m unittest scripts.s4.test_s4r1c9m_original_water_history_parity -v
    python3 -m scripts.s4.s4r1c9m_original_water_history_parity \
      --original-met /path/to/private/pristine-original-sixhour-met.dat \
      --original-trace /path/to/private/instrumented-original-S4_DIAGNO_G22.BIN \
      --geo /path/to/private/original-geo.dat \
      --native-hour2-candidate /path/to/private/exact-SHA-native-hour2-candidate.dat \
      --report /path/to/new/private-audit.json

The auditor rejects any of the four SHA pins drifting, any changed source grid/station/clock/field shape, any original water QH-mask mismatch, any first-hour nonzero water state, any original history mismatch and any native hour-two seed exceeding the frozen scientific tolerance. The original trace is not used by the native solver.

Scientific status: PASS_SCOPED_ORIGINAL_HISTORY_AND_NATIVE_HOUR2_SEED_ONLY; independent native third-hour stage3 physics and full S4/P6/P7 remain NOT_RUN/NOT_ACCEPTED.
