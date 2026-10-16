# P6G G18D4–G18D5 — execute COMP in source stage order, bind MIXHT from met.inp

2026-10-14; PR #63 Draft stacked on accepted PR #53. Frozen physical
sources, strict original-vendor checks, and the 10 km multi-station
CI baseline must remain unchanged.

## Scientific boundary

After G18C1–6 the source-selected 2SS/2US test could compose the
complete four-comp-step result using individually verified kernels, but
was still **calling** MIXHT, AVEMIX, WSTARR, TEMP3D outside their
`NativeHourStage` execution slots. Likewise, MIXHT scalar controls
were manually reproduced test constants, even though the original
`met.inp` contains the effective READCF values. These are
production-integration obstacles, not proof that a kernel formula is wrong.

G18D4 closes the scoped stage-order obstacle in a **test-only**
four-stage adapter; G18D5 closes the hand-entered MIXHT scalar controls
for the selected original 3600-s land path. Neither stage is a fully
accepted 17-stage production native CALMET hour.

## G18D4: actual four COMP calculations at immutable #53 stage slots

New `p6g_g18d4_comp_stage_adapter.hpp` is a
`MultiHourPhysics`-compatible object with a fail-closed
production `run()` returning `{Unknown,false}`. It deliberately
does **not** claim `{NativeCpp,true}` while upstream G17C3
station and G18A multi-US physics coefficients remain partially
source/test scoped.

For the selected verified source test, a separate
`run_selected(stage,frame,true)` executes actual native calculations
in exactly these **frozen PR #53** stage names:

1. `CompGridMixht`: invokes existing G18A / original frozen
   `mixht_observed_mc` with physical multi-UP AA/BB/JUSTA,
   source SS MIXHTST current-hour DPTT and prior-hour memory.
2. `CompAvemix`: invokes literal-vendor-parity G18C1 AVEMIX
   with source `ILEVZI` winds, writing an isolated averaged ZI/ZICONV.
3. `CompWstarr`: invokes unchanged #53 WSTARR **after** AVEMIX.
4. `CompTemp3d`: derives actual G18B5 per-US FACET temperatures and
   invokes unchanged #53 TEMP3D on post-AVEMIX ZICONV, then
   assembles all eight G14 NativeHourFields and ZI/ZICONV/DPTT
   through existing G18C4. The result modifies only the candidate
   `frame.next`, **not** previously committed source state.

Stage reordering, missing/duplicated stages, cross-hour candidate use,
and unmarked fixture-to-production promotion are rejected. The selected
2SS/2US source chain compares the staged final arrays (U/V/W/T/QH/
USTAR/EL/WSTAR and ZI/ZICONV/DPTT) **exactly** against the
previous direct physically tested G18C4 path. Explicit source GEOMETRY
and hour stamps remain mandatory.

## G18D5: read MIXHT scalar controls from original CALMET met.inp

New `p6g_g18d5_source_mixht_controls.hpp` uses the same existing
original READCF named-control parser as earlier G18A/B/C modules, not a
second synthetic configuration authority. It reads:
`IMIXH, IZICRLX, CONSTE, CONSTN, ZIMIN, ZIMAX, DPTMIN,
DZZI, THRESHL, TZICRLX`.

It derives original CALMET SETCOM REAL*4 values:

```
TWODTE = 2.0 * NSECDT * CONSTE
ONEDTE = NSECDT * (1.0 + CONSTE)
```

The selected pinned source has
`NSECDT=3600, CONSTE=0.15, IMIXH=1, IZICRLX=1,
CONSTN=2400, ZIMIN=50, ZIMAX=3000, DPTMIN=0.001,
DZZI=200, THRESHL=0, TZICRLX=800`.
`TWODTE=1080, ONEDTE=4140`, with float operation semantics.
Subhourly 1800s is **not** silently accepted.

The G18A selected integration test no longer assigns these controls
as hardcoded constants. It checks every parsed value against the
pinned original met.inp and verifies the parser can accept a
**legitimate changed CONSTN=2600** from a modified deck while
leaving the original prior controls unmodified. Duplicate, missing,
invalid, and out-of-scope parameter branches fail closed.

## CI and next production gates

G18D4 code [Actions #38567581077](https://github.com/RRain001/CTEAS/actions/runs/38567581077):
Debug 22/22 PASS, Release 22/22 PASS and frozen #53 163-file guard.
G18D5 initial code [Actions #38567960731](https://github.com/RRain001/CTEAS/actions/runs/38567960731):
Debug 22/22 PASS, Release 22/22 PASS, frozen core guard PASS.
The newer valid-CONSTN-edit regression must be checked at its
separate exact source commit before final PASS attribution.

Still required: original source SS–US station association, complete
STHEOR/DIAGI and WIND1/DIAGNO native real-case callbacks, full
original G14 PREPDI/DIAGNO/COMP 17-stage integration, durable
P6F publish/checkpoint recovery, and genuine multi-SS/UP original
Fortran per-value 45-field 1h/6h/143h/year equality.
Do not upgrade PR #63 from Draft or merge it prematurely.
