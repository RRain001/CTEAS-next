# Issue #40 S4-R1c8y — actual NOAA G14 second-hour FRADJ stage 2 (uncommitted)

**Dependent on:** Draft PR #277, actual source-clock-backed hour-two PREPDI/WIND1 with 125,460 REAL4 source-native G45 U/V equal bits; earlier #276 validates firsthour 17-stage P6F, independent G59/G54 parity and atomic G14/AA/BB/CGAMMA publication.

## Same physical owner

On 2022-06-01 02–03 UTC the authoritative scheduler's `preview_next_hour()` inherits the committed 01–02 UTC `ZI/ZICONV/DPTT` and source upper/CGAMMA histories. On **this same live G14 frame**, call a freshly constructed G26A actor's stage 0 PREPDI, 1 WIND1 and now 2 FRADJ through `run(NativeHourStage,...)`, in source order. G21 uses original-source IAVET two-pass SURFVAR, source TERSET/FRADJ and authentic per-US staged CGAMMA from this same actor. No detached numeric output enters the live path.

## Independent source-only comparison, NOT direct Fortran hour-two parity

G45 independently recomputes authentic source NOAA WIND1 for all six observed hours. `G18D2StationClockAuthority::prepare_selected` independently stages/prefights hour-two CGAMMA from *committed* clock histories without publishing. Run a separate `g21_original_source_clock_fradj_kernel` on G45's hour-two source WIND1 + independently staged CGAMMA. Compare these with the **live G26 stage-2** arrays as bit-exact REAL4: FRADJ corrected U/V across 9 layers (125,460), first and second SURFVAR temperature (13,940), and source-grid GAMMA (6,970), totalling **146,370 REAL4 values**. Retain G65 17-stage firsthour atomic rollback, G59 313,650 output word parity, G54 20,910 hidden-state parity, hour-two raw P5 missing wind/precip preservation, and the new stage1 G45 check.

The comparison is a separate re-execution of source-native numerical routines, **not** an independent original CALMET Fortran hour-two numerical audit. True second-hour stage 3–16 (G22 thermal/SLOPE, G23 STHEOR/INTER2, G24 final W and G26B COMP, G64 P6F) and native hour-two atomic commit remain **NOT_ACCEPTED**. The original source-water mixed-WATER G22/G23/G63/G64 still has explicit `hour_index==0` guards and MUST NOT be replayed or loosened absent scientific proof. In this PR, G14 `completed_hours` remains one, all committed `ZI/ZICONV/DPTT` and published AA/BB/CGAMMA are at the preceding UTC hour; no P6F stage16 output or second-hour clock commit is allowed.

Keep Draft pending latest exact-head CI; do not automatically run 143h full tests. Issue #40 OPEN. General P6/P7 NOT_ACCEPTED.
