# S4-R1c9w — Real NOAA fourth-hour G22 thermal stages3–6, scoped science audit

**Scope: TEST-ONLY, NOT production P6.** 2022-06-01 NOAA six-hour 82×85×9, 2SS/1US, 63 authentic WATER cells, fourth hour end 05 UTC. Parent is local `8ddf591de8309f16c55dcda6f2e143ae18f06a50`, after stacked Draft PR #308. No existing Draft merged; independent science review NOT_RUN.

## Original-source physical authority

- Original fixed CALMET 6.5.0 `/home/lhy/CTEAS/engine/vendor/src/CALMET_v6.5.0_L150223/calmet.for`, pinned SHA256 `835c351d780c0200be721c2d9cbb8dc45b3a8fcd4cb8815fc47bbd26a56a7b23`.
- `COMP` calls `MISSFC` before `DIAGNO` (original source COMP approx L3986; MISSFC L9762–10000). True NOAA SURF hour 04–05 UTC has missing temperature/pressure/humidity at SS1. The earlier hour-three path already applied verified G43 original `CMPD2/MISSFC`; fourth hour omitted that source preprocessing and initially failed `G17B AIRDEN missing RDSN pressure/TEMP2D` (exit code 2).
- Corrected only the **detached model-internal test-only copy** for hour four using unchanged `g43_original_comp_missfc_source_only` and actual raw hourly station identity. Validate resolved five nonwind fields and unchanged wind speed/direction, validity and precipitation code. P5 raw SURF.DAT remains read-only; no fabricated weather, no modified original Fortran.
- G66's original third-hour scoped kernel is preserved through a source-compatible wrapper. New hour-four-only G66 entry verifies `hour_index=3`, original UTC 05, exact raw GEO/station cardinality, and genuine native hour-three P6F `USTAR/EL` historical handoff; it rejects other hours and paths.
- The new explicit G26A hour-four stage3–6 actor runs on the same scheduler-owned preview only after a separate default actor correctly fails the existing production G22 guard. All seven native stages 0–6 use native WIND1/FRADJ/G22. The detached G66 and genuine G26A bytes agree **bit for bit**, without feeding original MET/trace into native.
- No fourth-hour G14 state/clock commit, no fourth-hour G23/G24/COMP/P6F, no original data committed to Git. Production hour_index>1 guards remain unchanged.

## Scientific comparison (read-only external original oracle)

The authentic original six-hour `S4_DIAGNO_G22.BIN` was independently generated before this work. Frozen SHA256 `b6d96dab81af8e9cba89ef55d386aba8082d9136aa7ef569ad0f9e39f1e31869`. Compare only original hour end 05 UTC against native 05; original trace not consumed by native C++. Original pristine 6h MET SHA256 `a7004fbf780212d58536be3957306c2aecc53abe2e58bfec870571b12d8b8e14`.

**PASS_SCOPED_FROZEN_G22_INTERMEDIATES: 181,220 / 181,220 REAL4 within pre-registered R1c3/P6B2B tolerances; 0 exceedances; 156,712 bitwise equal.** WATER USTAR and WATER EL are both bitwise exact on all 63 cells against original; no relaxation of the strict WATER-history gate.

| Original DIAGNO stage | Compared quantities | Count | Scope result |
|---|---|---:|---|
| 10 | Pre-FRADJ TEMP2D | 6,970 | 0 exceed |
| 20 | TEMP2D, QH, QSW | 20,910 | 0 exceed |
| 30 | AIRDEN/RHO | 6,970 | 0 exceed |
| 40 | QH, USTAR, EL | 20,910 | 0 exceed, WATER USTAR/EL 63/63 bitwise |
| 50 | USLOPE, VSLOPE (nine levels) | 125,460 | 0 exceed |

- Native candidate G66 trace SHA256: `36257fc6eb83b30e2ce032c491d206c35ba524c77ecbe78289d2511025a38357`. Live G26A stage3–6 writes precisely the same trace SHA; the cross-path comparison is byte-identical.
- Last native GCC12 Release executable SHA256: `4bdf6551ff46a960e56d5046c89e8c82bc0dda5f25cbceb27c5f3da6eaa72781`.
- Independent Python strict schema/frozen-tolerance tests plus third-hour regression: **20/20 PASS** (Docker DEV_ONLY `dev-20261024T003608-5ae462e7`).
- Development builds `dev-20261024T004136-f3cce93c`, `dev-20261024T004520-bd8c0ab2`: **DEV_PASS**, exit 0; not official exact-SHA Docker full.
- The real native trial after applying internal original MISSFC: `/home/lhy/dev/CTEAS-next/local-science/s4-r1c9w-hour4-g22-missfc-20261024` (exit 0, original/native comparison), followed by `s4-r1c9w-hour4-g22-live-stage6-20261024` (exit 0, separate live G26A byte identity). All raw records, binary and per-cell output remain local.
- The first-hour4 failed trial is separately preserved at `s4-r1c9w-hour4-g22-native-20261024`, not overwritten or reinterpreted as a PASS.

## Required next gates

Implement fourth-hour source-native G23/G24 STHEOR/INTER2/WINDTAIL on the existing G14 preview, compare against the pinned original six-hour stage90/100/110 trace; then fourth-hour G26B/COMP stages12–15 and G64/P6F 45 fields; verify fourth-hour G14 atomic commit/rollback before proceeding to hours5–6. Preserve the fast DEV_ONLY versus frozen exact-SHA Docker full distinction. Generic multi-case P6, P7, wet deposition and **independent scientific review remain NOT_ACCEPTED/NOT_RUN**.
