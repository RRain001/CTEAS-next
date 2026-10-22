# Issue #40 — S4-R1c7e: unify genuine source-missing SURF WIND1 with existing G16

Date: 2026-10-22. Baseline: merged #250 `main@b5ddf985d731cf86c9436660c711a428ea139705`.

## Why

G42 already implements original WIND1's EDITL-missing station treatment on actual 2022 NOAA 2SS+1US mixed WATER 82×85×9 first-hour source: the surface station remains in its original location and has **zero valid weight** on all levels. An internal 0 m/s carrier is only acceptable with `wind1_present=0` across all nine levels; it is **not** an observed calm. The existing shared G16 `do_wind1` rejected every missing `wind_valid` and therefore did not support this branch.

## Change in the shared selected actor

- G16 `G16SelectedWindPhysics` gains a default-off, **explicit original-source research-only** boolean; all existing callers remain unchanged.
- Without opt-in, any genuine missing wind still fails closed. With opt-in, an absent SS is permitted only if the caller has source-backed station IDs, 9× station-level `wind1_present=0` **and** exact inactive U/V=0 for that station. G16 then calls the same frozen `multi_station_wind1_firstguess` physical kernel used by G42 with an inactive carrier. No source-valid station is altered.
- Existing G48 **authentic real NOAA** first-hour replay now invokes both the unmarked (must reject) and opt-in shared G16 source WIND1 using the very same source-owned G20/G42 `G16ObservedProfiles`. It compares all 82×85×9 native G16 U/V against the separately assembled genuine source G42 native U/V with **elementwise equality**.
- G48 still executes the original-source STHEOR first-hour gate as before; no original wind from instrumented Fortran or MET is imported as forcing, and the original P5 SURF wind/precip is unchanged.
- A dedicated gate is added to the real-source Actions after the existing G48 first-hour output. C1 and C2 full 143-hour original/native regressions must stay green.

## Status / gates

This change can be called `PASS_FIRSTHOUR_9LEVEL_SCOPED` only if the exact-head Actions succeed. Native G16 now shares the SOURCE-only first-guess WIND1 path with G42; this is **not** an independently newly established G16-vs-original CALMET full DIAGNO/INTER2 parity (G42's existing first-guess numerical original oracle is an upstream prerequisite).

G17C3 sparse station column merge from #250 remains source-order preserving. **Do not admit native full-grid G23 INTER2**, G24 final U/V/W, causal G14 COMP, G26 45-field MET, production, #36 P7, or wet deposition. The next work unit is to bind original DIAGI/PREPDI station columns plus mixed-WATER post-SLOPE to the SAME G16/G23 INTER2 stage and compare against genuine #249 original all-grid 9-level INTER2 U/V without oracles as runtime physics.
