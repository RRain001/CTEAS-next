# Issue #40 — S4-R1c8c: actual G41 real WATER/LAND COMP source partition

Date: 2026-10-22. Baseline merged PR #254, `main@beb61cf4402b0c64dfd306d3abf342372a582502`.

## Scientific boundary

Merged #254 established **only** source-scoped first-hour actual NOAA COMP `SURFVAR(IALL=1)` temperature parity (6970/6970, max abs 6.1035e-5 K vs frozen 2e-4 K). That does **not** mean the rest of CALMET COMP is ready.

For real NOAA 2SS+1US 82x85x9, true original GEO has 6907 LAND cells and 63 WATER cells; the source original CALMET uses `NOWSTA=0, ITWPROG=0, ICOARE=10, IMIXH=1`. Crucially original COMP executes `WATER` (or `WATERP` for other controls) **before** land `MIXHT`/AVEMIX. In the currently selected original no-overwater-station branch `WT=0` and original WATER `QH=WT×RHOCP=0` is water buoyancy flux; non-neutral WATER physics for other control tuples is outside scope. The existing `g26b_source_test_comp_controls(G19FileBackedCase)` explicitly rejects WATER and must not silently reclassify water to land, nor accept fake already-solved WATER ZI/EL/USTAR.

## Code

New `g26b_real_water_comp_partition_source_only(G41SelectedNoowWaterFirstHourSource, MultiHourFrame, opt-in)`:

- Demands exact same original live source first-hour GRID/SURF/SS/US/clock/terrain geometry and correct G41 no-overwater-water source admission, including original source water-cell ordinals.
- Splits 63 genuine WATER and 6907 genuine LAND indices **without changing grid landuse** and fails closed on missing, reindexed, or wrongly masked water cells, wrong station IDs or unmarked use.
- Reads original G18D5 READCF MIXHT land scalar controls; only exposes **metadata**. NEARU/AA/BB/FCORI and prior COMP ZI/ZICONV/DPTT are not bound here; G18A land MIXHT is NOT invoked.
- Explicitly leaves `source_water_comp_physics_accepted=false`, `original_causal_comp_history_accepted=false`, `g26_45fields_accepted=false`; G26B original all-land guard stays unchanged.

The G52 negative tests reject forged previous admissions, source station identity changes, missing water ordinals and WATER→LAND reclassification. The genuine source PR workflow retains fresh original Fortran/P1–P5/first-hour G24 and COMP-third numeric gates, then compiles and runs G52. No original forcing is uploaded.

## Next physics gate

After preflight is proven, source-native COMP must **first** reproduce original `WATER` selected routine outputs (water Z0, USTAR, EL, ZI, QH, WSTAR, PGT), independently using real NOAA input and original source no-overwater station controls; then separate real `LAND MIXHT` with authentic source third COMP temperature, initial G14 memory and actual original SETCOM/AA/BB/NEARU mapping; then AVEMIX, WSTARR, TEMP3D, P6F and six-hour previous→next causality. Do not extend original G26B WATER physical permission before proof. S4 #40 and P7 #36 remain OPEN.
