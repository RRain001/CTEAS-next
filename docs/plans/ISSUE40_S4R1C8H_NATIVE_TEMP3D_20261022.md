# Issue #40 / S4-R1c8h — true NOAA source-native first-hour COMP TEMP3D

Date: 2026-10-22. Baseline after merged #259 `main@79ae59e42069f1ddff95f8c1f75c634b003f762c`.

## Physical scope

The source contains genuine 2022 NOAA 2SS + 1US, 82×85×9 with 6907 LAND, 63 WATER. Merged #258 and #259 independently proved the original/native real first-hour G54 MIXHT→AVEMIX 27,880 ZI/ZICONV values and G55 WSTARR 6,970 values. This PR's G56 computes the original selected `ISFCMET=0, ITPROG=0, LCALGRD=T` COMP `TEMP3D` from the **existing unchanged P6E** vertical interpolation `temp3d_observed_land`, using:

- the real source G54 **third COMP SURFVAR** surface temperatures, never earlier DIAGNO TEMP2D;
- the true G54 full-grid **post-AVEMIX ZICONV**, not WATER-only or pre-AVEMIX values;
- G18B source hour PREPDI original AA/BB sounding bracket/JUSTA and actual station identity;
- G18B5 original PREPDI physical per-face temperature interpolation on the real G14 `ZFACE(1..10)`, true station coordinate and upper time bracket;
- original READCF `IRAD` and real 2SS+1US station ordering, all 6970 cells including 63 genuine water cells.

The existing G18C3 all-LAND-only entry remains unchanged and fail-closed. This new source-only G56 invokes the same frozen P6E temperature kernel for a separately auditable selected WATER-containing case. G56 also verifies the original `ZTEMP(k=1)` is the true COMP third TEMP2D at all cells. No original Fortran TLEV or precomputed original ZICONV enters the C++ program.

## Original-native acceptance

Pin original source CALMET Git blob `437f43bb7f0e51a1919e56664663e1a046986ed0`, with source-only write after vendor L4772 (immediately after original `TEMP3D`/selected `ISFCMET` branch), preserving all physical statements. Re-run genuine original CALMET six consecutive NOAA hours from scratch and confirm the **original six-hour 45-field MET.DAT remains byte-identical** before and after the instrument, exact model UTC 6 hour record identity, 82×85×9×6 finite physical 3D temperature fields. The reference binary cannot be an input to native G56.

Independently run native G56 on only authentic P1–P5 NOAA input, then compare **62,730** original/native REAL4 TLEVEL values (9×6,970) for first hour at fixed **2e-4 K absolute threshold** and zero exceedances. The separate report records all 9 layer max/min/worst i,j and source hashes; no tolerance tuning to accommodate failure. The inherited G24, MIXHT, AVEMIX and WSTARR real source physical checks plus frozen C1/C2 regressions remain required for acceptance.

## Not accepted

Even if exact-head full Actions succeed, this proves only **source-scoped first-hour native COMP TEMP3D**. The full G26/P6F original 45-field MET.DAT, G14 17-stage atomic commit, real six-hour causal ZI/ZICONV/DPTT and P7 #36 remain NOT_ACCEPTED; also WATERP and non-neutral/non-NOOW branches are not covered. Do not request Copilot review.
