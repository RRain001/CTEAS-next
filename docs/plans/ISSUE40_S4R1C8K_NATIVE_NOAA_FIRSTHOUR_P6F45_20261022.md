# Issue #40 S4-R1c8k — genuine mixed-WATER native first-hour 45-record P6F file

Date: 2026-10-22. Branch is **stacked on still-draft #262**; do not merge until source integer and original file acceptance are green. The already merged #261 established firsthour 43 REAL4 source P6F fields, 299,710 verified original/native scalars (zero frozen exceedance). The #262 G58 integer phase is required to independently establish exact IPGT/IRH over the same 6,970-cell original 2SS/1US NOAA source domain.

## Test-only physical output

Native G59 uses **only the same authentic P1–P5 source** and:
- G57 computed 43 REAL4 fields: original G24 9-layer U/V/W, G56 9-level T, source G53 WATER USTAR/EL, G54 native COMP mixing ZI/HEATFX temperature/density/QSW, G55 WSTAR;
- G58 computed two INTEGER4 records **IPGT and IRH** using existing P6E kernels;
- the existing **G18C6 selected 45-record original P6F source-backed dataset builder** and the frozen **P6F CALMET.DAT 2.1 writer/parser** for original `met.inp`, genuine 82×85 GEO static fields, original full 2SS+1US positions, ZFACE, NEARS, land-use, roughness, terrain, LAI, projection and firsthour source clocks;
- **NO original Fortran original CALMET.DAT physical payloads enter native G59**. This is a genuine *new native 1-hour file* candidate, never an original-output rewrite.

## Independent science gates

A separate Python gate reads the untouched original six-hour CALMET.DAT as forensic reference **after native completion**, and asserts:
- original 6×45 labels and the valid native 1×45 layout, exact 82×85×9 source geometry, 2SS/1US station counts, fields, source time (2022-06-01 hour 01 UTC), record sizes/Fortran markers;
- independent static field record inventory and binary values from source original `GEO.DAT` versus new native P6F. Any static field mismatch fails (no original-output backfill into native);
- native original 43×6970 REAL4 physical values compared at the frozen per-label tolerances already fixed in #261, and both integer fields at exact equality per #262; **total 45×6970 = 313,650 hourly values** with no exceedances allowed;
- uses separate SHA-bearing #261 43-real receipt and #262 2-integer receipt, both from the **same original six-hour MET.DAT hash**.

Any failed source stage/size/static/physics/control leaves the PR draft. Use actual i,j and per-label worst error, do not widen thresholds, do not synthesize missing fields or meteorological values from the original output.

## Acceptance boundaries

On success: only the genuine source-scoped **single first hour** of a readable 45-field CALMET.DAT 2.1 file. There is **still no true six-hour G14 causal loop** carrying previous-hour `ZI/ZICONV/DPTT`, no 6×45 native file admission, no P6 full production, and no P7 #36 (or wet deposition). C1/C2 143h regressions unchanged; no Copilot review requested.
