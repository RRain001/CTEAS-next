# Issue #40 S4-F — real C1 143h freshly rerun original Fortran versus normal G26 adapter

Date: 2026-10-21. PR #222 merged normal `run()` adapter opt-in **trial**; PR #223 merged same genuine C1 143h source case normal-versus-selected byte parity and **historical frozen** CALMET.DAT 45-field parity.

## Scientific deficit now directly tested

C1 2022 Hefei 1SS/1US 50×50×9 143h source has an independent SHA-frozen original Fortran CALMET.DAT, but PR #223 **did not freshly run CALMET Fortran**. An older Stage 2C same-source original 143h run proved the feasibility of a literal pinned vendor rebuild on these project inputs; it was not the newer normal G26 route.

This workflow restores the unmodified pinned source from `CTEAS@dfad99a...`, requiring CALMET `calmet.for` blob `437f43...`, compiles with the previously accepted `gfortran-11 -O0 -fno-automatic -fno-align-commons` flags and vendor headers, and executes original CALMET over **a distinct copy of exactly the current C1 input case** with historical `run/met/met.dat` physically deleted beforehand. In parallel the current unified C++ actor computes the complete same 143h C1 G26 normal trial with `--selected-experimental --g26-normal-entry-trial`. The C++ must not open original results as inputs.

The independent unchanged P6E original 45-field comparator executes THREE actual gates over 143 consecutive hours / 6435 field-hour groups / every original grid node:
1. Fresh Fortran original vs G26 normal trial C++.
2. Pinned frozen historical original vs freshly rerun independent Fortran original.
3. Pinned frozen historical original vs G26 normal trial C++.

Every gate hard-fails unless all 45 field names, 143 interval count, and **zero** field-cell tolerance exceedances. New source SHA, exact normal/trial code checkout SHA, vendor `calmet.for` SHA, original/native binary SHA and all 3 comparator JSON are uploaded in a restricted resource evidence artifact. Vendor source and raw CALMET output files are not uploaded.

## Scientific scope

This work **does not** add new calculations, broaden CALMET physics, relax P6E tolerances, or enable production G26 without opt-in. It validates exactly the selected C1 2022 observed 1SS/1US weather, frozen 50×50 domain and no precipitation, not real observed 20SS/20US sites, not complete G5 and not alternative original CALMET science options. The stage remains `S4F_C1_FRESH_ORIGINAL_PASS_SCOPED` and P6 Issue #40 remains open for explicit production authority, true multiobservational-station independent science, supported RAM strategy, and eventual G5 gate. P7 #36, wet deposition, Docker/S5 are separate.
