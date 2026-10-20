# Issue #40 · S4-C four independent stations: original CALMET numerical gate

Date 2026-10-21. Baseline main `f86e7ec91ea5940fefc221d9afd3c1d95b180840`; prior PR #210 independently accepted five controlled 3-station cases against freshly compiled original CALMET and real Huoshan six-hour regression.

**Hypothesis.** The C++ selected G14 WIND1/DIAGNO/COMP/P6F scientific formula should remain unchanged when the actual original-format source station count independently increases beyond 3. Only source generator and explicitly selected science guards change. The four-station experiment extends **bounds to 4, not arbitrary N/M or general production**.

## Scientific matrix

- `4SS+4US`
- `4SS+3US`
- `3SS+4US`
- `4SS+1US`
- `1SS+4US`

Each source file has unique original-format station records, UTM positions and station IDs. Fourth surface station (SS4 ID 583240) has deliberately distinct hourly wind 6 m/s, 215 deg, whereas first three stations preserve frozen previous controlled observations; fourth sounding station (US4 ID 58427) has distinct independently assigned winds at both sounding heights/times. Actual historical NOAA evidence is NOT claimed. Same 12x12x9 source and six-hour known valid 2024 cross-year original-format controlled meteorology.

The **unchanged** original CALMET Fortran 6.5.0 from pinned CTEAS source must be compiled and run separately for each 1h and contiguous 6h. G19 file reader must verify the actual station counts, station IDs and source 00/12 bracket. The *same* C1/C2/Huoshan G14 selected native C++ actor computes original layout `MET.DAT`; independent P6E compares all 45 fields for each model hour with existing frozen tolerance and zero exceedance, zero missing. No original MET field is ever used as a native calculation input. In case of failure preserve the original listing, source hashes and native trace; **do not suppress difference by changing physics or tolerances**.

Keep 1/1, 1/2, 2/1, 2/2, 1/3, 3/1, 2/3, 3/2, 3/3 science and true Huoshan 1/1 original full six-hour reacceptance as independent CI gates before merge. G26 normal `run()` remains fail-closed.

## Limitations

These are **controlled synthetic** cases, not four independent field-observed NOAA stations. They use a bounded original-selected 9-layer land path and fixed scenario. A positive result is `PASS_SCOPED_CONTROLLED_FOUR_STATIONS`, **not** station-unrestricted production. Must later validate independent arbitrary station identifiers/positions, more than four stations and other legal site/time/physical controls; preserve S5 capacity and P7 science separate.
