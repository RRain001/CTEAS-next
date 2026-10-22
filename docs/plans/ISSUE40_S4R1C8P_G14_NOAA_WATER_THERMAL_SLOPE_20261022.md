# Issue #40 S4-R1c8p — same authoritative G14 frame through actual G22 mixed-WATER HEATFX/AIRDEN/ELUSTR/SLOPE

Dependent on Draft PR #267 (firsthour G19/G26 PREPDI, sparse WIND1, FRADJ), following merged PR #266 (original-vs-native firsthour hidden ZI/ZICONV/DPTT science and G62 carrier). This is an **explicit real-source scientific trial**; not production P6/P7 acceptance.

## Actual shared physical chain

From one G19 source file-backed 2SS/1US, 82×85×9, 6907 LAND/63 WATER NOAA source frame (2022-06-01 01–02 UTC), retain the original G43 COMP-internal five-field nonwind MISSFC materialization, without mutating source P5 missing SS wind or precipitation. One G26A instance then runs on **one G14 frame** through original ordered stage indices 0–6:

0. G18E4 source PREPDI: source AA/BB and CGAMMA staged, no clock publication;
1. G20/G16 source sparse WIND1: no fictitious missing wind, 125,460 REAL4 native G42 cross-path;
2. G21 source FRADJ including source original IAVET two SURFVAR passes and CGAMMA: 146,370 REAL4 native G41 cross-path;
3–6. G22 original-source HEATFX/AIRDEN/ELUSTR and SLOPE from **same frame**, using existing G39 verified 63-cell neutral WATER heat (QH/USTAR/EL remain zero before actual original WATER) and existing source G22 slope kernel, instead of all-LAND G18D3 call.

Frozen all-LAND G22 path remains unchanged and all new mixed-water physics is behind `source.research_noow_water_source_only`; only actual firsthour 2SS/1US, 82×85 63 WATER and original source controls are admitted. Native G14 previous ZI/ZICONV/DPTT remains unchanged, no `G14` complete-hour commit, and neither AA/BB nor CGAMMA is published.

## Independent scoped checks

The same first-hour `g47_actual_noow_water_after_elustr_slope(paths,true)` source-native comparison path rebuilds original source-owned G43/G44/G39/G22 from real GEO/SURF/UP/deck independently of G26's live stage state. Compare the following native REAL4 planes **bitwise** without injecting comparison values into the actor:

| Physical quantity | REAL4 count |
|---|---:|
| Post-FRADJ HEATFX surface temperature | 6970 |
| AIRDEN near-surface density | 6970 |
| ELUSTR QH | 6970 |
| ELUSTR USTAR | 6970 |
| ELUSTR EL | 6970 |
| Post-SLOPE U, V across 9 vertical layers | 125460 |
| **Total compared** | **160310** |

The strict comparator also continues to require 20,910 G62 hidden-memory elements, first-hour genuine NOAA original 45-field MET21 parity and separate original Fortran DPTT COMMON scientific validation. Source-path bitwise identity does not substitute for an independent unmodified original Fortran G14 end-to-end 45-field validation.

All-LAND accepted C1/C2 cases must remain unchanged. Stages 7–16 (STHEOR/INTER2, wind tail, COMP MIXHT/AVEMIX and P6F) remain unexecuted on this live water actor; true native second-hour previous-state consumption and original-vs-native 6h×45 comparison are **NOT_ACCEPTED**. No original/oracle output fields enter native physics. Full 143h tests remain manual-only. Issue #40 remains OPEN; no P7 or wet deposition changes.

Scientific admission status: `CI_PENDING` until exact head compile, original-source comparison and independent numeric receipts pass.
