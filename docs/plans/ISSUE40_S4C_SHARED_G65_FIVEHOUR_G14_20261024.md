# Issue #40 — S4-C shared native G14 genuine NOAA WATER fifth-hour continuation

Date: 2026-10-24. This is a narrowly scoped original Fortran numerical
comparison, NOT general P6/P7 production acceptance or human scientific review.
The existing GitHub PR #308 remains Draft and must not be merged.

## Actual physics and source isolation

`G65RealNoaaFifthHourTrialActor` was moved without altering physical
formulas from the original G65 research runner into the same native shared
header used by hour1–hour4. Both the original G65 research program and
`cteas_p6g_s4b2_unified_selected` now compile exactly the shared native
hour1–hour5 G14 17-stage actors.

S4B2 adds a mutually exclusive, explicit research opt-in
`--selected-experimental --water-fifthhour-g14-trial-only --hours 6
--probe-prefix-hours 5`. A full and true six-hour NOAA source must be
present, with 82×85×9, 2 surface stations, 1 upper-air station and 63 WATER
cells. Incorrect prefix, missing input, unwanted `--native-comp-trace`,
normal production G26, source-only preflight or other research hour switches
all fail closed without publishing MET output.

One G14 scheduler computes original NOAA hours 1–5 with separately fresh
same-family native actors, 17 native physics stages per hour, P6F 45-field
precommit, state/clock preflight and atomic native G14 commit. Starting with
hour3, **only the previous committed native P6F** `USTAR`/`EL` fields
supply typed G66 WATER physical history. The fifth hour uses hour4 native
P6F — with original UTC interval, native-source provenance and all 6,970
cells checked — alongside byte-identical committed `ZI/ZICONV/DPTT` arrays
and published AA/BB/CGAMMA clocks. No original Fortran `MET.DAT`, archived
Fortran traces or external reference array is consumed by the native solver.

Authentic fifth-hour model-internal CALMET COMP G43/MISSFC repairs the five
nonwind fields on the detached research source copy. Original raw P5
SURF.DAT wind and precipitation observations stay unchanged and are
checked against those copied to G14. This is not a generalized station
imputation/physical HFLUX algorithm.

## Fixed independently read Fortran science

The unchanged original Fortran 6h `MET.DAT` was generated in a prior source
run and held read-only. It was NOT rerun in this increment. Original SHA256:

`a7004fbf780212d58536be3957306c2aecc53abe2e58bfec870571b12d8b8e14`

The newly compiled unified S4B2 native five-hour `MET.DAT` SHA256:

`41d505e8bc00701b506f6b566fdbe4c2ef3f2400fbc28b94b9130320d1b4cab9`

The existing independent offline scientific reader
`scripts/s4/s4c_compare_noaa_unified_threehour.py --native-hours 5`
validates SHA, distinct original/native files and empty report destination,
original six-hour 2.1 header vs native five-hour 2.1 header, 82×85×9 grid,
2SS/1US, 225 original canonical hourly field labels and order, UTC source
chronology, finite REAL4, integer exactness and **unchanged frozen field
specific tolerance**. The original Fortran result is read ONLY by that
post-execution audit and is never fed back into C++ physics.

| Genuine NOAA hourly interval, UTC | Values compared | Raw 4-byte words identical | Frozen exceedances |
| --- | ---: | ---: | ---: |
| 2022-06-01 01–02 | 313,650 | 298,578 | 0 |
| 02–03 | 313,650 | 239,527 | 0 |
| 03–04 | 313,650 | 231,976 | 0 |
| 04–05 | 313,650 | 240,362 | 0 |
| 05–06 | 313,650 | 248,716 | 0 |
| **Total** | **1,568,250** | **1,259,159** | **0** |

Result: `PASS_SCOPED_S4C_SHARED_FIVEHOUR_FORTRAN_225`.

The same new binary has separately regenerated **all four** prior native
prefix outputs and exactly matched their previous SHA256, proving no
bytewise regression at prefix 1/2/3/4:

- 1h `d8e6065e2d26bc517f72619bd1822c6832d04ec7c42c4b93d12d32910a3c984c`
- 2h `30eb55977283f7b9c09a4002e9781d32e1d58af30ac408e15959d8c928d9f0f3`
- 3h `a80edb2467807635c2c1ea6e285533c6981f4469e41fc4dcf0031a2a035b1989`
- 4h `412aabb4dfa0ef02af80a70a5ba0dca63fb15ac541ded53a0bb43b484e93177d`

Private frozen original/native files and detailed audit JSON:
`/home/lhy/dev/reports/cteas-s4c-unified-20261024/s4c-shared-fivehour-vs-original.json`.
Do not upload proprietary/original inputs, original binary, original outputs,
or private science cache to public GitHub.

## Scoped software gates and next step

- GCC12 compiles both original G65 and S4B2 against the same fifth-hour actor.
- P6 source/mode guard CTest 7/7 PASS: positive first-four prefixes preserved,
  fifth research opt-in refuses wrong prefix/hours, mode mixing, absent real
  inputs, default production and occupied output. Reuses existing combined
  third/fourth/fifth negative CLI driver; NO new clone script.
- `test_s4c_compare_noaa_unified_threehour.py` now also asserts fifth-hour
  source SHA mismatch fails before source decoding. The independent audit
  itself continues to be a single reusable fixed-original 3–6 hour reader.
- Next: reuse native G65 hour-six 17-stage actor on this same S4B2/G14,
  derive typed WATER USTAR/EL from committed hour-five P6F, use genuine
  hour-six detached G43, and validate **270 fields** against frozen
  Fortran. After 6h complete, perform same-HEAD C1/C2 143h science,
  independent second location/station configuration, negative rollback
  evidence and non-Bot scientific review. General production P6 and P7
  remain blocked, `scientific-admission` expected FAILURE. Do not merge
  PR #308 or apply `science-validated`/`merge-verified`. Formal Docker
  release verification remains post-S5 as separately decided.
