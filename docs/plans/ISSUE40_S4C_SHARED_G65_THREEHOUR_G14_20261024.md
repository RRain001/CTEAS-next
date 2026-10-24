# Issue #40 — S4-C unified G65 genuine NOAA WATER hour-three transaction

Date: 2026-10-24. Research-only implementation, Draft PR #308.
No generic P6/P7 production admission or independent science review is implied.

## Single native parameterized P6 candidate and actual prior state

The unchanged G65 original native third-hour 17-stage source executor
`G65RealNoaaThirdHourTrialActor` has been extracted into the same shared
`p6g_g65_shared_noaa_firsthour_actor.hpp` as G65 hour one and hour two.
G65's typed `g65_native_hour2_water_from_p6f()` decoder was moved into
`p6g_g65_shared_native_water_history.hpp` without changing numeric
operations, for **both** the original G65 research CLI and the parameterized
S4B2 CLI. The genuine `G66NativeHour2WaterState` uses `USTAR` and `EL`
from **only the preceding *native* hour-two 45-field P6F candidate**, with
hour-begin/end, 6,970-cell shape, and explicitly native provenance checks.
No Fortran `MET.DAT`, independent COMP reference, hidden oracle or third-hour
reference array is consumed by the actual native solver.

`cteas_p6g_s4b2_unified_selected` now admits an explicitly gated,
research-only `--water-thirdhour-g14-trial-only` which requires full
original NOAA 6-hour source and **exactly** `--hours 6
--probe-prefix-hours 3`, known 82×85×9 / 2SS + 1US / 63 WATER source,
no default G26, no native-state trace and no combination with first/second
hour or source-only modes. The G14 scheduler runs on one original source
clock with fresh actors for hours 1, 2 and 3. After second-hour commit,
it checks the published upper/gamma clocks and derives typed next-hour
water history from already-committed native P6F data. The next preview
and committed memory carry `ZI/ZICONV/DPTT` exactly from the previous
native hour; hour 3 then completes original native G26A/G26B 17 stages,
precommit P6F and G14/station-clock atomic publication.

Real third-hour NOAA station #1 has nonwind observational gaps. The
existing original-source G43/MISSFC reproduces the five CALMET COMP
nonwind replacements **only in the detached internal G14 source copy**;
raw P5 SURF.DAT / original surface observations are never modified.
Both wind and precipitation fields are bit/equality checked unaltered.
This reproduces the original G65 specifically scoped input semantics;
it is not a general missing-data imputation algorithm or general WATER
HFLUX acceptance.

## Independent fixed-original 135-field science check

The native three-hour S4B2 output `CALMET.DAT`, SHA256:

`a80edb2467807635c2c1ea6e285533c6981f4469e41fc4dcf0031a2a035b1989`

was generated under Ubuntu from the frozen NOAA original meteorology.
The original Fortran six-hour CALMET output **was not rerun during this
batch**; the locked original reference has SHA256:

`a7004fbf780212d58536be3957306c2aecc53abe2e58bfec870571b12d8b8e14`

No original data or privately sourced Fortran code/output is committed.
The independent post-execution Python auditor
`scripts/s4/s4c_compare_noaa_unified_threehour.py` checks exact original
and native SHA identity, different files and unused output report path,
Fortran sequential unformatted record signatures, UTC period, 3h native
versus 6h original headers, 82×85×9, 2SS/1US, 45-field canonical labels
and ordering, finite REAL4, exact INTEGER4 and **unchanged frozen
field-specific scientific tolerances**. The original reference file is
read only by the external audit process after native G14 execution.

| Scoped real NOAA hour | Values | Identical raw 4-byte words | Frozen tolerance exceedances |
|---|---:|---:|---:|
| 1 | 313,650 | 298,578 | 0 |
| 2 | 313,650 | 239,527 | 0 |
| 3 | 313,650 | 231,976 | 0 |
| **Total** | **940,950** | **770,081** | **0** |

Result `PASS_SCOPED_S4C_SHARED_THREEHOUR_FORTRAN_135`.

The newly rebuilt S4B2 **also** independently ran the old one-hour and
two-hour research switches, proving byte-for-byte frozen output SHA256
unchanged:

- one-hour: `d8e6065e2d26bc517f72619bd1822c6832d04ec7c42c4b93d12d32910a3c984c`
- two-hour: `30eb55977283f7b9c09a4002e9781d32e1d58af30ac408e15959d8c928d9f0f3`

Audit JSON, native MET and original artifacts remain **private** on Ubuntu:
`/home/lhy/dev/reports/cteas-s4c-unified-20261024/s4c-shared-threehour-vs-original.json`.
This is **scoped numerical parity of a three-hour research candidate**, not
independent scientific approval or general production P6 acceptance.

## Regression and following work

- GCC12 CMake-built original G65 actor and S4B2 shared first/second/third
  actor code without changing numerical equations.
- Existing S4B2 first/second-hour/normal/no-output CTest guards plus new
  `p6g_s4c_water_shared_thirdhour_no_implicit_production` **5/5 PASS**;
  explicitly denies mode mixing, missing opt-in, incorrect prefix, extra
  hours, state trace and all missing genuine source inputs. The new
  independent comparator tamper/SHA/occupied-evidence Python suite adds
  three further tests without external original fixture data.
- Next S4-C step: reuse G65 hour-four physical actor on the same G14
  scheduler and derive its **native previous-hour USTAR/EL** from
  committed hour-three P6F; preserve G43 hourly nonwind repair and original
  SOURCE time/clock proofs. Then verify external hour4 45 fields, hours5/6,
  new-SHA C1/C2 143h baseline and another independent original configuration.
- `scientific-admission`, independent non-Bot same-SHA scientific reviewer,
  P7, and production P6 remain **NOT_ACCEPTED/NOT_RUN**; keep #308 Draft
  and do not apply merge-verified/science-validated or merge. Post-S5 Docker
  delivery remains distinct from scoped Ubuntu native acceptance.
