# Issue #40 S4-C | True station-ID independence within selected physics (2026-10-21)

Baseline: PR #211 already merged `main@fc2424fccc8af7178178febf2c10fb9fea639f38` with a 4SS/4US 45-field old Fortran numerical PASS on five controlled source cases, and actual Huoshan 100×100 original-vs-C++ six-hour regression PASS.

## Problem and correction

G20 WIND1/INTER2 still contained a literal `58424/58425` **fixture-only** ID guard when both source station categories had <=2 entries. G19 already checks station IDs between `met.inp`, SURF/UP and each scheduled source frame, and G20 separately checks each upper `station.station_id == source.stations.upper[site].id` and valid sounding brackets. This leftover guard was not an original CALMET physical equation. Remove only literal fixture ID admission; preserve source identity/provenance matching and IEXTRP=-4 first-upper-layer missingness, physical formula and all original field tolerances.

The controlled G19 source exporter can now accept `--station-id-offset K` where 0..5000, adjusting **both sides** of the actual original source SS1..SSN/US1..USM station declarations, SURF station ID list, UP sounding station ID headings (real original-file read), with unchanged numerical meteorology, site coordinates/clock and 1..4 station cardinality. The separate original Fortran runner independently validates these shifted station IDs in source SURF and stages actual altered UP headers before independently rerunning unchanged pinned CALMET 6.5.0.

## Strict source and numerical CI

1SS/1US offset 117, 2SS/2US offset 117, 4SS/4US offset 117, 4SS/1US offset 301 and 1SS/4US offset 301, each six hours in original-format controlled synthetic 12×12×9 source. The exact same selected G14 C++ physics actor and fresh pinned Fortran CALMET both execute first hour and 6h; require all 45 labels per hour, source SHA, independent original and native outputs, `total_exceedances==0` at existing P6E tolerances. No copying original MET into native source, no synthetic station *duplicates*, no relaxation of G26 production guard.

All prior C1/C2/1..4 station regressions and actual NOAA Huoshan S3→P6 original 6h source remain required **before merge**. Positive outcome is **PASS_SCOPED_CONTROLLED_SHIFTED_STATION_IDS**, not proof of arbitrary N/M, observed independent NOAA multisite, all selectable physics, generalized grid/projection or production G26. 1..4 tested cardinality ceiling is intentionally unchanged.
