# Issue #40 S4-R1c8u — real source-native G14 NOAA COMP TEMP3D stage 15

Stacked after Draft #273 (G26B WSTARR stage 14), #272 AVEMIX stage 13, #271 authentic WATER/LAND MIXHT stage 12, #270 G23/G24 12-stage DIAGNO, #269 genuine water heat/SLOPE, merged #267 PREPDI/WIND1/FRADJ and #266 G61/G62 original hidden-memory science.

**Scope:** actual NOAA 2022-06-01 01–02 UTC firsthour 2SS (one genuinely absent wind) + 1US, 82×85×9, 6907 LAND/63 neutral WATER. Source control `ITPROG=0`, `LCALGRD=T`, authentic original IRAD. The existing original source-verified `p6e::temp3d_observed_land` now runs directly as the real G26B **stage 15** on the exact same G14 `MultiHourFrame`, taking:

- Actual G26B stage 12 COMP-third SURFVAR/HEATFX surface temperature, not earlier G22 DIAGNO heat.
- Actual G26B stage 13 post-AVEMIX convective ZICONV, not pre-AVEMIX or original Fortran output.
- Original-source G26A PREPDI/UP selected physical AA/BB FACET temperature faces, original time brackets/JUSTA and genuine spatial UP coordinates.
- Verified G26B stage 14 WSTARR completion and original 9-level grid, but no detached G56 numbers as native forcing.

After G26B calculates 9×6970 = **62,730 REAL4 temperature values**, a separately recomputed genuine-source-native G56 result serves ONLY as comparison, requiring bitwise equality and exact source clock. Fail closed on malformed source face heights, wrong station IDs, negative/nonphysical/nonfinite temperatures, wrong k=1 COMP-third TEMP2D or changed G14 prior/next history. This is independent of original Fortran: original sixhour DPTT COMMON and full firsthour MET21 comparison remain separate mandatory science gates.

**Strong nonadmission:** The next G14 stage 16 P6F must throw, produce zero committed grid/state records, and leave `frame.previous/next` equal with PREPDI AA/BB/CGAMMA still unpublished. No G14 completed hour, no true hour 2 causal state, no source-supported full sixhour ×45 native parity, no P7, no wet deposition. C1/C2 all-LAND selected kernels and manual-only full 143-hour tests remain intact. Issue #40 OPEN. This PR remains Draft pending exact-head scoped CI and original scientific check.
