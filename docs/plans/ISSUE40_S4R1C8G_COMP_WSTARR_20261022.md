# Issue #40 S4-R1c8g — Genuine NOAA first-hour native COMP WSTARR

Date: 2026-10-22. Prior merged #258 `main@6a6eece2744cbd35b7f13847744376ef239a77f4` achieved genuine 6970-cell source-native LAND MIXHT + full-domain AVEMIX parity on 27,880 float values (zero original/native tolerance exceedances). WSTARR follows AVEMIX in original CALMET `calmet.for` at lines 4740–4750.

## Physical source path

G55 uses only genuine NOAA P1–P5 data, same G41 2SS/1US live source and **already accepted source-only G54 first-hour MIXHT+AVEMIX**, then calls the **frozen original-backed P6E `wstarr` kernel**. It supplies:
- ZICONV: **post-AVEMIX** from G54, not the pre-MIXHT or pre-AVEMIX values;
- QH: the genuine **COMP third SURFVAR HEATFX→ELUSTR** heat flux, not the earlier DIAGNO slope-flow flux;
- TEMP2D and density: matching **COMP third SURFVAR/AIRDEN** fields, now retained from G54 with source proven same hour;
- exact GEO landuse and WATER 50–55, 6970 cells, 6907 LAND and 63 WATER; selected `NOWSTA=0` WATER wstar initial 0 and stays 0.

The original `WSTARR` routine at vendor line 4744 uses `ZICONV,QH,TEMP2D,RHO`. No original WSTAR nor other computed original intermediate value can enter G55 CLI.

## Independent original oracle

- SHA-pin original vendor Git blob `437f43bb7f0e51a1919e56664663e1a046986ed0` and original WSTARR branch L4740–4750. The scratch original Fortran call appended *after original WSTARR completes* writes six ordered 6970-cell REAL4 WSTAR planes only.
- Independently re-execute **all six true source hours**, validate 6×6970 floats, exact firsthour/UTC packed clock, full finite nonnegative field and nontrivial original convection. The pristine and scratch **six-hour 45-field MET.DAT must be byte-identical**.
- Separate external Python comparator checks all **6,970 first-hour original/native WSTAR values** at a frozen `2e-4 m/s` absolute threshold, reporting worst i,j, mean, max and first failures. Any nonfinite, changed source timestamp, missing byte count or exceedance denies the scientific label.
- Keep all inherited C1/C2 143h frozen checks; no forced calm, no original oracle fields injected to C++.

## Scope

On exact-head pass only, accept real original/native *first-hour WSTARR* for the existing selected source path. This still excludes TEMP3D, P6F full 45-field G26 output, six-hour true COMP causal history, other water regimes, #36 P7 and wet deposition; G26B production remains fail closed. Next work is original-source TEMP3D whole 82×85×9 physical upper temperature and precise P6F output, followed by six-hour causal ZI/ZICONV/DPTT proof.
