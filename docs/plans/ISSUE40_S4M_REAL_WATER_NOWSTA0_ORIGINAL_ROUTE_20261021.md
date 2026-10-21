# Issue #40 S4-M — identify actual original WATER / WATERP route for 2022 genuine 2SS+1US water-containing site

Date: 2026-10-21. Follows #228 independently fresh unmodified vendor original six-hour reference and #230 independent **literal HEATFX** water QSW/QH 24-case zero-exceedance parity. #229 keeps genuine G19 source/clock accepted without admitting unverified WATER/HEATFX physical options.

## Correct actual CALMET order, not an all-land shortcut

Pinned CALMET 6.5.0 Git blob `437f43bb7f0e51a1919e56664663e1a046986ed0` has the following full **COMP** stage order:
- Original `HEATFX` (`calmet.for` 4583–4589) computes water QSW, **skips water-cell QH** at L8096.
- After `RADFLX`, COMP executes `WATERP` if `ITWPROG==2` or `WATER` otherwise (L4615–4620). This is the actual source **water-surface physics**, not an unused file reader.
- `WATER` processes only water land-use cells, computes water roughness/friction/Monin-Obukhov length, water mixing heights and water buoyancy flux. In particular **the quantity labelled QH in the original METGRD common block is the water buoyancy flux**, not always the sensible heat flux. At `WATER` L33065, `QH = WT * RHOCP`, where `WT` depends on the genuine selected overwater physics.
- The later grid `ELUSTR` stage L4662–4669 **skips water** (L6439); the `MIXHT` land path likewise does not replace the water-only state from WATER.

An all-land `g18d3_source_hflux_inputs` vector initialised to zero for unused water QH scratch is **not a substitute for WATER physics**. Neither assigning QH=0 generally nor re-labeling water as land is acceptable.

## Exact current 2022 observed site — prove selected original control tuple first

The real source is regenerated afresh as in #228, from the original NOAA 2022 2SS Huoshan 583140 / Luogang 583210 and genuine Anqing 58424 one-upper sounding on **82×85 ×1km** WGS84/UTM50N `426.590, 3464.125` km with genuine water categories. S4-M source auditor takes **this exact generated `met.inp` and `GEO.DAT`**, SHA checks both, and extracts original READCF `NOWSTA`, `ITWPROG`, `ICOARE`, `IMIXH` plus actual SS/US counts. No guessed mode, no synthetic SEA.DAT station, and no acceptance on unmatched original Git blob.

For this no-water-observation station site, the original `WATER` routine itself has a **specific neutral fallback**: when `NOWSTA=0` it bypasses measured overwater temperature and COARE/DELTAT, sets `WT=0` at the original neutral label, and later publishes **water-cell QH=WT×RHOCP=0 (buoyancy flux)**. This deduction applies **only** to the source-qualified no-OW-station, `ITWPROG=0` original path, not to other NOWSTA/ICOARE/ITWPROG combinations. Remaining water USTAR, Z0, EL, ZI, WSTAR and PGT assignments are NOT automatically equivalent in native C++.

The action repeats the entire real P1–P5 fresh original MAKEGEO 55,760/0 case, same-site G19 read/physical blocker, and the separate fresh unmodified original CALMET six-hour 270-group reference. A machine-checked original-source route receipt records line positions, selected actual controls, GEO water-cell count and file hashes without uploading vendor source.

## Acceptance boundary

`S4M_REAL_2SS1US_ORIGINAL_NO_WATER_STATION_WATER_ROUTE_AUDIT_PASS_SCOPED` means accepted **literal original flow / source control tuple**, not a tested standalone original-C++ WATER physical implementation. It is not a native 45-field compare, and not a reason to remove `G18D3 all-land` guard.

Next S4-N should independently test the no-water-observation branch numerically using exact original WATER Fortran or an instrumented reference-only pristine original six-hour run, including pre/post WATER `QH,WT,Z0,USTAR,EL,ZI,WSTAR` at real water grid locations and clock states. Then add a separately gated **native no-overwater-observation selected water adapter** without changing existing P6E HEATFX physics. Reuse frozen P6E 45-field thresholds for full 6 ×45 =270 field-hour comparisons, zero exceedances required before full 2SS/1US G26 trial; P6 production/P7 still locked.
