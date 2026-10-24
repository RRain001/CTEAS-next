# S4-R1c9s — genuine NOAA third-hour native G26B COMP stage12 original parity

## Frozen original and exact native inputs

- Stacked after Draft PR #306 HEAD bcde0ec67dbd1ca7e9c5817e7ccec42d289153cb; new changes are a narrow, explicitly test-only hour3 G26B/G63/G53/G52 stage12 admission, G65 test-only trace and an independent Python comparator. All default hour_index>1 guards still reject without explicit opt-in; stages13–16 are deliberately rejected in the hour3 trial.
- Real NOAA 2022-06-01 02–08 UTC, 82x85x9, 2SS/1US; third hour end 04 UTC. Same pinned P1–P5 GEO/SURF/UP/met.inp and native committed second-hour ZI/ZICONV/DPTT, AA/BB/CGAMMA and WATER USTAR/EL. No original MET, source or COMP trace is injected into native G14.
- Original independent sixhour COMP stage12–15 Fortran trace SHA256 4851f7be2d19df7a6e5e2cf5d73653c282cfea579b9c0b2444365a842d27a02e (PR #306); instrumented original MET remains byte-identical to pristine SHA256 a7004fbf780212d58536be3957306c2aecc53abe2e58bfec870571b12d8b8e14.
- Host GCC12 Release native binary SHA256 65e6837e8ece08c9ae2d57382338dbd90f07780994936dea8acb5547957a3eee; private native hour3 stage12 trace SHA256 39ba85377356ee87ab7e5d2d3cb8df3f343ca6cdcf0ff85e055b8bb0aa9c0b69. Original and native full arrays plus JSON remain only in /home/lhy/dev/CTEAS-next/local-science/s4-r1c9s-native-comp12-20261024 and /home/lhy/dev/CTEAS-next/local-science/s4-r1c9r-hour3-original-comp-20261024.

## Independent original/native stage12 result

- **PASS_SCOPED_HOUR3_G26B_STAGE12_ORIGINAL_NATIVE: 48,790/48,790 REAL4** within pre-existing MIXHT/G22 frozen field tolerances, **0 exceedances**, 38,331 bitwise identical. No tolerance was relaxed to obtain this result.
- Stage12 arrays: post-LAND MIXHT ZI/ZICONV; COMP-third QH/TEMP2D/RHO; source-native WATER-reconciled USTAR/EL. This is the same third-hour G26A final wind and same scheduler-owned prior state, not a detached first-hour replay.

| Field | REAL4 compared | Bitwise equal | Frozen exceedances | Max absolute difference |
|---|---:|---:|---:|---:|
| zi | 6,970 | 5,668 | 0 | 0.0106201172 |
| ziconv | 6,970 | 5,668 | 0 | 0.00445556641 |
| qh | 6,970 | 6,073 | 0 | 0.000122070312 |
| temp2d | 6,970 | 5,489 | 0 | 6.10351562e-05 |
| rho | 6,970 | 5,489 | 0 | 2.38418579e-07 |
| ustar | 6,970 | 5,289 | 0 | 1.1920929e-07 |
| el | 6,970 | 4,655 | 0 | 0.000244140625 |

- The 63 original GEO WATER cells have **63/63 bitwise native parity for USTAR, EL and ZI**, and 54/63 bitwise parity for ZICONV (all 63 within frozen MIXHT tolerance). The native COMP WATER USTAR is recomputed from the current-hour G24 final wind; it is not the previous DIAGNO stage40 USTAR and is not set to zero.

## Transaction boundaries, tests, remaining gates

- G26B stage12 returns a private, unpublished candidate; the G65 caller verifies that scheduler committed hours remain exactly two and previous committed ZI/ZICONV/DPTT plus AA/BB/CGAMMA clocks are unchanged. Stage13–16, positive hour3 G14 commit and output publication are not entered.
- New 12/12 Python strict parser/frozen tolerance tests PASS; combined original COMP trace and native stage12 tests 23/23 PASS; GCC12 Release G65 compile PASS; real NOAA native third-hour stage12 run and independent comparison PASS_SCOPED. Exact-SHA Ubuntu Docker full and independent scientific review are NOT_RUN until independently executed.
- Next steps: explicitly test-only G26B stage13 AVEMIX against original stage13 ZI/ZICONV, then stage14 WSTARR, stage15 TEMP3D, stage16 P6F and 45-field third-hour independent original comparison. Do not admit production, positive third-hour G14 commit or hours4–6 before the complete scientific chain and independent review.
- S4 P6 six-hour general acceptance, P7, wet deposition and independent science review remain NOT_ACCEPTED/NOT_RUN; keep all stacked PRs Draft and unmerged.
