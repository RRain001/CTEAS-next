# Issue #40 — S4-C full fixed-NOAA six-hour WATER G14 native scoped parity

Date: 2026-10-24. Scoped original CALMET Fortran parity research only.
**General production P6 and all P7 remain NOT_ACCEPTED; PR #308 stays Draft.**

## Single native G14 source executor: final six-hour integration

Original G65 `G65RealNoaaSixthHourTrialActor` is physically unchanged,
extracted into `p6g_g65_shared_noaa_firsthour_actor.hpp` with the other
five original G65 research native actors, reused by **the same** S4B2
parameterized CLI. S4B2 now admits explicit research-only
`--selected-experimental --water-sixthhour-g14-trial-only --hours 6
--probe-prefix-hours 6`, requiring the **complete genuine original NOAA
meteorological source**: 82×85 horizontal grid, nine vertical levels,
2 surface stations, 1 upper station, 63 WATER / 6,907 LAND cells and
exactly six source hours.

A single G14 scheduler runs all 102 (6×17) original native G26A/G26B
physical stages with separately fresh first–sixth-hour physics actors,
P6F 45-field per-hour precommit, strict atomic source clock/state commit
and verified complete source window on final sixth-hour flag. For hours
3–6 the typed prior WATER state uses *only the immediately preceding
committed NATIVE P6F* fields `USTAR` and `EL` (6,970 cells, exact UTC
interval, explicit native provenance). The final hour uses **native hour5
P6F**; no original Fortran MET.DAT, reference trace or vendor output
contributes solver input. Grid memory `ZI`, `ZICONV`, `DPTT` inherits the
precise committed previous-hour bits; AA/BB/CGAMMA clocks are published
only after all physical stages and P6F precommit succeed.

The existing source G43/MISSFC repairs original COMP's five nonwind
fields for hour6 *only on the detached model-internal G14 source copy*.
Original P5 meteorology, surface wind and precipitation, and upper-air
observations remain intact. Wind, rain and source UTC bounds are
independently checked. Research CLI refuses non-original geometry,
missing true source, false hour count, other research hour flags,
normal production G26, source-only preflight and `--native-comp-trace`.
Production admission remains fail-closed.

## Original six-hour Fortran vs fresh native six-hour P6F

Read-only frozen original six-hour Fortran `MET.DAT` SHA256:

`a7004fbf780212d58536be3957306c2aecc53abe2e58bfec870571b12d8b8e14`

Fresh S4B2 native `MET.DAT` output six-hour SHA256:

`32d9f049b1739e1d568a0f7ba65bf9d3718d8bd1c1b7dcdb147c94d41a4753b3`

Original Fortran scientific executable was **not rerun** for this scope;
its previously executed result remains immutable and separate. The only
original MET.DAT read happens in independent *post-execution* Python
`scripts/s4/s4c_compare_noaa_unified_threehour.py --native-hours 6`.
The independent reader checks both locked SHA identities, source/oracle
isolation, complete MET.DAT 2.1 unformatted records, header dimensions,
6h source UTC chronology, 270 original canonical P6F labels/order,
finite REAL4, exact INTEGER4 and **unchanged frozen field tolerances**.

| UTC 2022-06-01 hour | Cells×fields | 4-byte bitwise equal | Exceedances |
| --- | ---: | ---: | ---: |
| 01–02 | 313,650 | 298,578 | 0 |
| 02–03 | 313,650 | 239,527 | 0 |
| 03–04 | 313,650 | 231,976 | 0 |
| 04–05 | 313,650 | 240,362 | 0 |
| 05–06 | 313,650 | 248,716 | 0 |
| 06–07 | 313,650 | 248,915 | 0 |
| **Total** | **1,881,900** | **1,508,074** | **0** |

Result is **`PASS_SCOPED_S4C_SHARED_SIXHOUR_FORTRAN_270`**. It verifies
this particular fixed NOAA source and recorded tolerance matrix, NOT a
new site/station geometry, broader production equivalence, P7, or a
separate independent scientific human review.

Original Fortran input/output, native six-hour output and audited detailed
JSON live on authorized Ubuntu only, outside Git:
`/home/lhy/dev/reports/cteas-s4c-unified-20261024/s4c-shared-sixhour-vs-original.json`.
**Never commit original Fortran, genuine observational source data, or private
original/native results** to the public repository.

## Regression and remaining science admission gates

- Shared physical actor compiled by both original G65 research C++
  executable and S4B2 with GCC12. No modifications to numerical stages.
- The existing shared research CLI negative-test script also handles
  `--research-hour 6`; wrong prefixes, no explicit opt-in, competing modes,
  fake sources and accidental publication are refused. Independent audit
  SHA, original/native disjoint, 3..6h gate and output-file collision
  protections continue unchanged.
- The same new S4B2 binary must reproduce frozen 1/2/3/4/5-hour output
  SHA256 exactly before releasing this commit. Six-hour completion must
  call scheduler.require_complete() even with an explicit 6h research
  prefix so no window remains implicitly uncommitted.
- Stage S4-C six-hour **one configuration** is now scoped and complete.
  Generalizable production still requires same-SHA C1/C2 143-hour native
  regression, second independent **original** geographical/station
  configuration (not merely synthetic contract tests), negative atomic
  rollback checks for real source, independent non-Bot scientific review,
  and the rest of Issue #40 S4/P6 gates. P7 and wet deposition are separate
  unfinished work. Keep `scientific-admission` enforcing BLOCKED and the
  PR Draft without science-validated/merge-verified labels.
