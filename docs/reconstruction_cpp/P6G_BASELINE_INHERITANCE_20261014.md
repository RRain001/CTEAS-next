# P6G baseline inheritance, 2026-10-14

Frozen accepted parent: `8d6642272d0abb77153880591e150f93e14d4479`, [PR #53](https://github.com/RRain001/CTEAS/pull/53). Hefei one-surface/one-upper 2022 143h 50×50×9 100m: P6D/P6E native 45/45 fields source parity PASS, 0 exceedances; P6F independent file and original CALPUFF read PASS.

This branch **directly inherits** the accepted P6A–P6F source, unlike earlier G5–G13 diverged branches. All 26 transferred source files are P6G-only independent headers/test drivers/original-Fortran comparators; the single-station P6D/P6E/P6F scientific implementation files, hourly state owner, and case runner are untouched. CMake appends only G6–G13 isolated executable/test registrations.

G6–G12 scope: dynamic UTM grid, multi-SURF and multi-UP, selected 2SS+2US 10km cross-year 48h and leap-year 8784h inner-kernel stress; G9 WIND1 original-selected source, G10 DIAGNO tail, G11 terrain, G12 observed temperature/HEATFX under **synthetic solar and thermal coefficient test inputs**.
G13 scope: 72 original CALMET Fortran SURFVAR 2SS 10km 12×12 scenes, 31104 scalar comparisons per Debug/Release build. **This is not full multi-site original CALMET parity.**

The branch CI checks parent ancestry and unmodified frozen source before selected multi-site CTest/Fortran source comparisons. Inherited `p6-native-causal-hourly.yml` must also pass a new 143h Hefei 45-field G3/G4 strict scientific regression because CMake changed.

Integration PR stays Draft until CI and original multi-station end-to-end physics gates are validated. Keep original PRs #54–#62 as historical experimental evidence but do not merge them over the accepted baseline. GitHub-hosted Ubuntu is the sole runner. No precipitation/wet deposition claim.
