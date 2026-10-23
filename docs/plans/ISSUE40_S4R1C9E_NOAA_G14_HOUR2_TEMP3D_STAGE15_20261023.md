# Issue #40 S4-R1c9e — genuine NOAA hour-two TEMP3D G14 stage 15

**Base:** `origin/main@4d986c192c928ae716c959f58e81bb15697025c5`, after merged PR #283. This change is restricted to the original selected 2022-06-01 02–03 UTC hour-two research branch (2 observed SS, one US, 82×85×9, 63 WATER and 6907 LAND). It is not P6 production acceptance.

## Native physical and causal authority

The same previewed, uncommitted scheduler G14 hour-two frame carries the genuine preceding G26A stages 0–11 and G26B stages 12 MIXHT, 13 AVEMIX, 14 WSTARR. Stage 15 uses the **existing** `p6e::temp3d_observed_land` physical kernel, source `G18B5` AA/BB/FACET temporal interpolation from real upper-air observations, COMP-third native surface temperature and native AVEMIX convective height. It never takes original Fortran 3D temperature, frozen MET.DAT or independent comparator diagnostics as native forcing.

## Scoped acceptance contract

1. Recompute a detached, physically causal G26A/G26B second-hour replay from the prior committed G14 memory. Its 9×82×85 = **62,730** REAL4 TEMP3D words must match the live stage-15 result **bitwise**.
2. Independently rebuild a source-native P6E TEMP3D calculation using the detached genuine second-hour G18B5 upper-air faces, independently recomputed COMP-third source temperature and AVEMIX ZICONV. The 62,730 words must again match live stage 15 bitwise. Require physical finite 180–350 K values and k=1 surface-temperature equality. This checks C++ paths only; it is **not pristine original Fortran hour-two TEMP3D verification**.
3. Stage 16 P6F must reject unaccepted hour-two publication. G14 completed hours stay **one**; AA/BB/CGAMMA published time and first-hour ZI/ZICONV/DPTT remain bitwise unchanged. No G14 second-hour atomic commit.
4. Preserve all earlier stage 0–14 exact parity gates and the selected P5 observation wind-valid and precipitation flags. No synthetic SS or water rewrites, and no widened numeric tolerance.

## Execution status

Code and workflow gates implemented. A single-translation-unit Ubuntu GCC 12 `-std=c++20 -Wall -Wextra -Wpedantic -Werror -fsyntax-only` check passed with exit code 0 using the project P6/P6E/P6F header paths; this is **syntax only**. Full Docker verification, exact-head CI and scientific runtime comparisons are **NOT_RUN until completed on this SHA**. The Ubuntu host was observed running 112 CPU-intensive ROMS processes on 2026-10-23; no ROMS process was stopped or reconfigured. The prior 143h C1/C2 cases remain the already published scoped regressions, not newly re-run by this PR.

## Remaining blockers

Stage16 P6F on hour two, its exact 45-field original/native comparison, real G14 atomic second-hour commit and publication, subsequent 3–6 hourly causal state propagation, new-site full science, P7, wet deposition, and generic production remain **NOT_ACCEPTED**. Issue #40 remains OPEN. Do not merge absent project CI/scientific acceptance and the required independent evidence.
