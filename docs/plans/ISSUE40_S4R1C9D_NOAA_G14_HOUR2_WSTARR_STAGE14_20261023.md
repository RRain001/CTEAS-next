# Issue #40 S4-R1c9d — genuine NOAA second-hour G14 WSTARR stage 14

**Base:** main after merged #282 (19/19 CI success), which independently checked authentic secondhour G26B AVEMIX stage13 with 13,940 source-native bitwise REAL4 values; previous #281 G26B MIXHT stage12 already matched 55,760 REAL4 values. This PR is one **research-scoped uncommitted physical stage**, not whole-hour or production P6.

## Source-owned causal path

Use authentic NOAA 2022-06-01 02–03 UTC, 82×85×9 (2SS, 1US, 63 WATER, 6907 LAND), preserving each hour's original observed P5 `wind_valid`, source SS ordinal, original hourly UTC, source G23 station STHEOR and committed firsthour `ZI/ZICONV/DPTT` + AA/BB/CGAMMA. G26A live physics executes stages 0–11; G26B on **the same uncommitted hour2 G14 frame** executes MIXHT12, AVEMIX13 and WSTARR14. All fields feed native P6E WSTARR from current G26B stage12 COMP-third `QH/TEMP/RHO` and stage13 `ZICONV`. No original Fortran/standalone diagnostics feed the live actor.

## Independent bitwise gates

1. Independently preview the authentic secondhour frame after firsthour G14 atomic commit; independently replay G26A stages 0–11 and G26B stages 12–14 from the same published clock and committed firsthour memory. The reexecution must bitwise equal all **6970 REAL4** WSTARR values.
2. Independently compute source `p6e::wstarr` from separately reconstructed source AVEMIX ZICONV, separately computed MIXHT COMP-third QH/TEMP/RHO, original source GEO landuse and exact original water-category bounds. Compare **6970 REAL4** bitwise to the live candidate. Preserve the already accepted 55,760 MIXHT and 13,940 AVEMIX comparisons.
3. Reject nonfinite or negative WSTAR and require **all 63 real WATER cells WSTAR=0** in the selected neutral `NOWSTA=0`, `ITWPROG=0` source path; do not replace water source physics.
4. After successfully computing stage14, the unaccepted stage15 TEMP3D must fail closed. The G14 scheduler completed hours must remain 1, committed firsthour ZI/ZICONV/DPTT unchanged, and latest AA/BB and CGAMMA clocks must remain firsthour UTC. No secondhour G14 commit.

## Limitations and freeze

This is **source-native cross-path plus causal replay**, not independent pristine original Fortran hour2 WSTARR equality. Stage15 TEMP3D, stage16 P6F, hour2 G14 atomic publication, all six original NOAA hours' 45-field parity, generic P6/P7, wet deposition and unsupported station counts remain **NOT_ACCEPTED**. CI exact-head required before marking ready; the full 143-hour frozen regression remains manual only. Issue #40 remains OPEN.
