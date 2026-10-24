# S4-R1c9t — third-hour native COMP stages12–15 original numerical parity

## Exact provenance and selected result

- Stacked after Draft PR #307 HEAD eaa1fc674d936cc55567624aee86657ae8fb2e4b. Only a narrow explicit test-only extension from already verified third-hour G26B stage12 through stages13–15, with read-only stage trace and independent Python comparison. Stage16 P6F and positive third-hour G14 commit are still refused.
- Genuine NOAA 2022-06-01 02–08 UTC, 82x85x9, 2SS/1US, third hour ending 04 UTC. Same frozen original Fortran COMP stage12–15 source trace SHA256 4851f7be2d19df7a6e5e2cf5d73653c282cfea579b9c0b2444365a842d27a02e from PR #306; source instrumented sixhour MET byte-identical to pristine SHA256 a7004fbf780212d58536be3957306c2aecc53abe2e58bfec870571b12d8b8e14.
- Native GCC12 Release binary SHA256 0bf41dc9f98296cdfd87815ccdf9dacab5379c84d0e61f692f5f9cf1f50c8ccd; private native trace SHA256 4c0e2bcb22fbd7dac4871a9f53cd7083ab8a425b96cab1a44be5bbf08f1ff8a1. Same pinned met.inp/GEO/SURF/UP inputs and native second-hour committed G14 memory/clocks as PR #307; original MET/trace never injected into C++.

- **PASS_SCOPED_HOUR3_G26B_COMP_STAGE12_15_ORIGINAL_NATIVE: 132,430/132,430 REAL4** within previously frozen field tolerances, **0 exceedances**, **107,805 bitwise identical**. No threshold relaxed. Native G26B stage12 output was independently confirmed byte-identical before and after extending the trial through stages13–15.
- Stage12: current-hour COMP WATER + LAND MIXHT, 7 fields. Stage13: AVEMIX ZI/ZICONV. Stage14: WSTARR. Stage15: TEMP3D nine levels. Original Fortran trace is read only by separate comparator, not by G26B/G63/G64.

| Stage | Field | REAL4 compared | Bitwise equal | Frozen exceedances | Max absolute difference |
|---|---|---:|---:|---:|---:|
| 12 | zi | 6,970 | 5,668 | 0 | 0.0106201172 |
| 12 | ziconv | 6,970 | 5,668 | 0 | 0.00445556641 |
| 12 | qh | 6,970 | 6,073 | 0 | 0.000122070312 |
| 12 | temp2d | 6,970 | 5,489 | 0 | 6.10351562e-05 |
| 12 | rho | 6,970 | 5,489 | 0 | 2.38418579e-07 |
| 12 | ustar | 6,970 | 5,289 | 0 | 1.1920929e-07 |
| 12 | el | 6,970 | 4,655 | 0 | 0.000244140625 |
| 13 | zi | 6,970 | 5,516 | 0 | 0.00256347656 |
| 13 | ziconv | 6,970 | 5,534 | 0 | 0.00115966797 |
| 14 | wstar | 6,970 | 5,660 | 0 | 8.34465027e-07 |
| 15 | temp3d | 62,730 | 52,764 | 0 | 9.15527344e-05 |

## Guard and scientific scope

- Third-hour stage13–15 is explicitly opted-in only after the native G26A **12 stage0–11 checkpoints**, native G26B stage12, committed second-hour ZI/ZICONV/DPTT and AA/BB/CGAMMA clocks. All G26B stages12–15 execute on one live hour-three frame and one actor; stage16 remains rejected by the opt-in guard.
- Native scheduler remains at exactly two committed hours; third-hour G14 state and clocks are not published. No original source, MET, trace, input or full field arrays are committed or uploaded.
- New Python 9/9 schema/tolerance tests PASS; combined original COMP, stage12 and stage15 regressions 32/32 PASS; GCC12 Release native compilation and genuine NOAA run PASS_SCOPED. Exact-SHA Ubuntu Docker full and independent scientific review are NOT_RUN pending separate execution.
- Next: validate third-hour G64 P6F stage16 as an unpublished, test-only candidate against the original third-hour 45 MET fields (313,650 values), then require independent review before any positive G14 commit. Hours4–6, generic P6/P7, wet deposition and science review remain NOT_RUN/NOT_ACCEPTED. All stacked PRs stay Draft/unmerged.
