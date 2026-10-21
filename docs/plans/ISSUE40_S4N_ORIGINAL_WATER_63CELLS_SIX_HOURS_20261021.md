# Issue #40 S4-N — true NOAA observed water, 63 × 6 actual original Fortran WATER numeric state

Date: 2026-10-21. Continues merged #228 (true fresh original CALMET six-hour full 45-field reference), #229 (safe structural G19 water source), #230 (independent 24-mode HEATFX water QSW/QH original source parity), #231 (true NOAA B0 original WATER NOWSTA0 control-source proof).

## Exact originally selected scientific scope

Unmodified CALMET 6.5.0 `calmet.for` Git blob `437f43bb7f0e51a1919e56664663e1a046986ed0`; genuine independent 2022-06-01 01–07 UTC two observed NOAA ground sources **583140/583210**, actual Anqing IGRA upper **58424**; identical pinned original-SRTM + original-historic-GLCC 82×85@1km WGS84 UTM50N site, including **63 actual water GEO cells** (IWAT1..IWAT2, categories 50..55). Source READCF selects `NOWSTA=0, ITWPROG=0, ICOARE=10, IMIXH=1`.

The original COMP execution order is **HEATFX → RADFLX → WATER → ELUSTR**. Original `HEATFX` leaves water QH unchanged but fills water QSW; original WATER's true no-overwater-station branch at L32731 selects the neutral fallback with `WT=0` at L32815. Original WATER then writes water buoyancy-flux `QH = WT×RHOCP` at L33065 (not land sensible heat flux), original neutral Monin-Obukhov `EL=9.9e9`, water Hosker roughness, neutral friction `USTAR`, water mixing height, `WSTAR=0` and PGT class. The next phase has not been shown to be native equivalent, so no physics guard is relaxed here.

## Reference-only independent numerical science

New `scripts/s4/s4n_real_water_63cells_original_probe.py` accepts exactly the pinned unchanged original Git blob and validates original physical source line identities. It injects **seven reference-only record/open/close/format lines** into a fresh *scratch copy* of `WATER` at exact original L32708 and L33080-81. Vendor checkout remains untouched, and no modified original source is committed or uploaded. The instrumented copy is separately compiled with **the exact same** original gfortran flags and source include directory as the accepted independent original CALMET baseline. The genuine NOAA source case is independently restaged in a fresh folder, without importing earlier MET output.

A fresh untouched original CALMET produces `MET.DAT` on this exact B0; a **separate scratch instrumented Fortran** runs the same six-hour case. The gate rejects any difference between final independent untouched and instrumented **MET.DAT byte content**; the reference instrument is not allowed to change even one production output byte. For **all 63 real water cells × all six source hours = 378 independent water cell-hour rows**, it captures original `QH, USTAR, EL, ZI, WSTAR, Z0, WT, WS10` and original PGT classification. Strict positive friction/roughness, finite values, real Hosker roughness and neutral original friction formula, actual 50–3000 m mixing-height bounds, true source GEO water-cell membership, exactly 63 per hour, six disjoint hours, neutral original QH/WT/WSTAR zero and PGT class D must hold. No invented water station/SST, no land-use coercion, no synthetic station-hour fills.

The uploaded artifact contains **only computed 378-row numeric state**, source SHA, original/instrumented binary SHA, JSON scientific scalar extremes, and full five-source scientific SHA receipts. It must not include third-party Fortran source or a new large MET.DAT. The original full 6×45=270 reference field groups are independently decoded by the unchanged P6E scientific reader, with baseline artifacts tied to this exact case.

## Acceptance is intentionally narrow

`S4N_ACTUAL_VENDOR_63_WATER_CELLS_SIX_HOURS_NEUTRAL_WATER_VALUES_PASS_SCOPED_ORIGINAL_ONLY` means **instrumented original numerical water physical-state reference established**. It is not a new C++ water implementation and does not claim native vs original parity or G26 output acceptance.

Next S4-O: use these frozen numerical reference values and *only the selected actual no-OW-station neutral branch* to implement separately gated C++ `WATER` physical state, compare same 378 original water-state records with tightened numerical tolerances including hour-to-hour `ZI` handling, then stage real full G14/G26 selected with unchanged 270-group original-vs-C++ 45-field gate. Keep all-land original G18D3 default refusal until that independent test passes. P6 production #40 and P7 #36 remain open; wet deposition, Docker, and unrelated S5 unaffected.
