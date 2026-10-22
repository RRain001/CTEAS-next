# Issue #40 S4-R1c8v — genuine G14 firsthour NOAA 45-field P6F staged precommit

Dependencies: PR #274 G26B TEMP3D stage15 → #273 WSTARR → #272 AVEMIX → #271 MIXHT → #270 G23/G24 → #269 mixed-WATER thermal, with #267/#266 merged. All exact-head CI and scientific gates required. This is a **one-hour, source-scoped 17-stage candidate and G18D1 precommit**, **NOT** a committed G14 hour, station-clock publication, hour 2 or general P6/P7 authorization.

## Actual physics and 45 original fields

On the exact 2022-06-01 01–02 UTC original NOAA 2SS+1US mixed 6907 LAND / 63 neutral WATER, 82×85×9 G14 `MultiHourFrame`:

- G26A stages 0–11 compute observed source PREPDI AA/BB/CGAMMA, sparse WIND1, FRADJ, G39 heat/SLOPE, sparse STHEOR/MIXHTST/INTER2 and final three-dimensional G24 U/V/W.
- G26B stages 12–15 compute **within the same actor**, with no reference/original FORTRAN injection: 63 WATER + 6907 LAND native MIXHT; AVEMIX ZI/ZICONV; WSTARR; nine-layer TEMP3D. G63 now preserves true **third COMP SURFVAR HEATFX** shortwave, sun sine and SETCOM nearest observed station ordinal, in addition to temperature/density/QH/USTAR/EL.
- New G64 executes the actual G26B G14 **stage16 P6F native candidate**: 27 U/V/W 3D records + 9 3D temperature records + seven REAL4 surface records from the live actor, two INTEGER4 records IPGT/IRH computed **directly** from current G14 G24 level-1 U/V, real G63 COMP-third source solar/cloud and G43-resolved genuine P5 surface obs. Uses unchanged P6E PGTSTB and SURFVAR multi-SS routines. Writes original source WATER IPGT=4 to exactly 63 cells, preserves actual LAND PGT and computed RH, never fakes a missing SS wind.
- Original P6F `g18c6_selected_one_hour_dataset` builds a **prepared-only** `Calmet21File` with source GEO/NEARS and UTC; frozen `g18d1_validate_p6f_precommit` verifies all 45 outputs against a detached copy of the current *in-flight* G14 next memory/physical fields and produces an uncommitted byte image.
- Only **after G18D1 succeeds**, G26B stage 16 updates `frame.next`/full fields with its own native candidate. It does not call scheduler `execute_and_commit_hour`, publish original AA/BB or CGAMMA clocks, emit a production file or allow a second-hour preview to advance.

## Independent original-source evidence

The already source-verified G59 firsthour full45 path is **re-run exclusively as an independent output comparator**; not one G59 value is fed into G64 or G26B. Require bitwise equality of all **45×6970 = 313,650 four-byte original field words** (43 REAL4, 2 INTEGER4), record types/labels and absolute UTC begin/end. Additionally require in-flight G14 next `ZI/ZICONV/DPTT` identical to separately source-native G54 post-AVEMIX/COMP-firsthour state, and previous `ZI/ZICONV/DPTT` remains original cold start with scheduler completed hours exactly zero.

Negative test: deliberately corrupt one U-LEV1 four-byte word on a detached completed candidate. `G18D1` MUST reject the tampering; no G14 committed memory, source clock or source payload may be changed. Existing independent authentic Fortran original firsthour 45-field numeric comparison, original source sixhour DPTT COMMON and original NOAA G41/G42/G47/G48/G54/G55/G56 checks remain separate mandatory gates. Source-native bitwise paths are NOT by themselves a freshly accepted Fortran multi-hour science comparison.

## The next actual acceptance gates

1. **Do not prematurely call 17-stage hour complete**: this PR stages a validated output candidate but does **not yet execute G14 atomic commit**. A following bounded PR must orchestrate 0–16 via ONE `UnifiedMultistationHourlyScheduler` transaction and implement precommit + postcommit AA/BB/CGAMMA publication with proper rollback on any failure.
2. Only after that commit may actual original hour 2 use the previous post-hour `ZI/ZICONV/DPTT`. Require original Fortran vs native 45 fields and hidden memory every hour through six legal NOAA hours.
3. Only after production branch unification and dynamic station/UTM/UTC config must ONE new P6 binary rerun C1/C2 frozen 143h and real different-site full-field science to close Issue #40. Full 143h remains manual-only; P7 and wet deposition still blocked.

Status: `STAGE16_P6F_CANDIDATE=CI_PENDING`; `G14_HOUR_COMMIT=NOT_ACCEPTED`, `REAL_HOUR2=NOT_RUN`, `S4_PASS_SCOPED=NOT_ACCEPTED`.
