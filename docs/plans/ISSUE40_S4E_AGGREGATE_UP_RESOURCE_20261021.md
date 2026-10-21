# Issue #40 — S4-E aggregated UP sounding source budget (2026-10-21)

Previous S4-D accepted the user-selected **20SS+20US, 20SS+1US, 1SS+20US** original-format controlled-synthetic source physical result: independently run unchanged original CALMET 6.5.0 first hour / all six consecutive hours, original 45 fields/hour, zero exceeding P6E cells, merged PR #215. Source-shape checked arithmetic / overflow preflight was merged in PR #216 (main@55ad4e17). The user chose 20 as **test coverage**, never a production station-number limit.

## Actual input safety gap

`read_upper_station_set` previously allocated each independent US sounding history up to `max_soundings_per_station=100000`, without checking the **combined** sounding records stored across the `NUSTA` stations. A large number of individually valid US files could exhaust resource budgets even when every single-file reader passed. The existing SURF source reader already guards `hours*NSSTA <= 2000000`, but that budget is unrelated to total UP soundings.

## Narrow change

Introduce a new optional total upper-record budget `max_total_soundings=2000000` (separate from SURF station-hour count), enforce nonzero budget and at least one real sounding per declared UP station **before reserving the vector**, and give each subsequent original UP reader at most `min(max_soundings_per_station, remaining)` soundings. After parsing, subtract the actual count with checked remaining capacity. This prevents a hidden station-count-times-per-file amplification. This **does not** count peak heap bytes or impose a 20/99/350 station limit. Optional new argument preserves call compatibility, existing G19 identities, full archival time and per-file requirements unchanged. Existing independently original-CALMET-validated physical equations, 45-field tolerances and native stage codes untouched.

Release-build regression reruns genuine original-format G19 input cases 1SS+1US, 1/7, 7/1, 7/7, 20/1, 1/20, 20/20. Each exact source UP set must be read with its exact aggregate sounding count successfully and reject one-record-less or zero total budget, without ever inventing UP files. Original source station identity/order, G14 UTC authority and absence of G26 production permission remain enforced.

**Acceptance classification:** `PASS_SOFTWARE_SOURCE_ONLY`, never `P6_ORIGINAL_SCIENCE_NEW_PASS`; former scientific baselines remain valid by no physics change and the positive original source-load G19 replay. Genuine independent observed multi-station NOAA original parity, heterogeneous missing/calm source behavior, normal production G26 permission and measured peak RSS are next separate tasks. Keep #40 OPEN; #36 P7 remains separate.
