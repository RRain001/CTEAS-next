# Issue #40 — S4-C unify P6: genuine mixed WATER G19 source admission, not physics

Date: 2026-10-24. PR #308 continues as Draft. This is **source-only**
engineering of the *existing* `cteas_p6g_s4b2_unified_selected` executable;
no new P6 numerical engine and no change to G65 physical equations.

## Initial observed blocker (current frozen input)

The fresh GCC12 S4B2 executable against genuine 2022-06-01 NOAA input
82×85×9, 2 surface stations + 1 upper station, six contiguous UTC hours,
63 source GEO WATER cells, with `--selected-experimental
--g26-normal-entry-trial --probe-prefix-hours 1`, refused **before** hourly
physics, exit 2:

    S4B2_FAIL_CLOSED G18D3 all-land HFLUX default branch only

No `MET.DAT` was created. This is not numerical failure or an excuse to
weaken the G18D3 source heat or physical-stage admission conditions.

## Narrow implementation

`--selected-experimental --water-source-preflight-only` is now a mutually
exclusive option in the **same** S4B2 CLI. It requires actual original-format
`--met --geo --surf --up ... --hours N`, with no `--out`, and forbids every
hour-prefix, raw-memory/field, native-state trace and G26 normal trial flag.
It calls the already available `g19_load_original_source_case(paths,true)`:
G19/SETCOM/READCF + G38 researched NOWSTA=0 neutral water HFLUX source,
creates a G14 scheduler to validate the *full* source UTC/UP bracket and
station order, then S4B1 grid/station/field extent admission. It requires
nonempty authentic G38 water cells. It only emits a source identity/count
summary and returns; no G26A, G26B, G14 stage, G64 P6F, MET.DAT or physical
state publication executes.

Private fixed NOAA inputs remain only under Ubuntu
`/home/lhy/dev/CTEAS-next/local-science/s4h_huoshan_xinqiao_true_2ss_2022`;
SHA256 values are sufficient in public documentation:

| Source | SHA256 |
|---|---|
| met.inp | `c5e6b02ac623a3f7d11b464deca657cd26285605753ef185bcc215257dee9744` |
| geo.dat | `5feaa58e5835576b3ae2c03a51e955114d620a7aeb710ded58a9f999695f602a` |
| surf.dat | `6a3f45eebdba8c7b783b5b89d5e1b3a7eecf2ce71f7fdaa814e7a54f04a9f655` |
| up_58424.dat | `a4e99dabe6ed246643bb298c3d883c8de8a5dd07aaa346952f7e096d325ad00` |

On these files, native return code `0` with:

    S4C_G19_WATER_SOURCE_PREFLIGHT=PASS_SOURCE_ONLY HOURS=6 SS=2 US=1 NX=82 NY=85 WATER_CELLS=63 LAND_CELLS=6907 G14_UTC=ADMITTED G26_G26B_P6F=NOT_RUN MET_DAT=NOT_WRITTEN ORIGINAL_PARITY=NOT_RUN PRODUCTION_ADMISSION=NOT_ACCEPTED

The program successfully verifies genuine G19/G38 and scheduler *input*
semantics; it does not claim production P6, six-hour physics, or any newly
measured original CALMET parity. The prior G65 source-specific six-hour
results cannot be promoted by this preflight.

## Software verification and next physical work

- Compiled S4B2 using GCC12 (`CMAKE_BUILD_TYPE=Release`); standalone local
  output binary is in `/home/lhy/dev/reports/cteas-s4c-unified-20261024/build-p6/`.
- Added `p6g_s4c_water_source_cli_fail_closed` CTest. Exercises 5 mutually
  prohibited option combinations, missing research opt-in, absent normal
  `--out`, duplicate flags and fail-closed nonexistent original input. The
  pre-existing `p6g_s4b2_no_implicit_production` stays active.
- Source-only PASS and CLI guards are not L2 original comparison. No private
  original/source data is part of the published repository or CI fixtures.

The next engineering step must compare *real* data-dependent stage ownership:
1. `G34BSelectedOnlyHour` currently constructs G26A/G26B using default
   no-WATER source/actor parameters; merely toggling G19(true) would bypass
   incomplete WATER physics. Introduce source-selected G41 and G43 original
   COMP `MISSFC` provenance without touching raw P5 observations.
2. Refactor the G65 genuine WATER G22→G23/G24→G26B stage12–15/G64 P6F
   hour-specific research opt-ins into a reusable, index-independent actor
   with historical P6F water state and atomic G14/UTC ownership; **do not**
   use original `MET.DAT`, original COMP trace or vendor values as native
   stage inputs. Keep all restrictive guards until each option is compared.
3. First-hour 17 stages/45 fields genuine original parity, then hours 2–6
   cumulative state and 45-field original comparisons, C1/C2 unchanged
   full 143h regression and second independent configuration. Distinguish
   zero-tolerance-exceedance *scoped* checks from actual independent science
   review; only then evaluate production admission and downstream P7.

`scientific-admission`, non-bot same-SHA APPROVED review and Draft/no-merge
rules remain unchanged; formal Docker delivery remains post-S5.
