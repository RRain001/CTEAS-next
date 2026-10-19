# Issue #84 — genuine NOAA Wolsong zero-domain / 2024 leap-day raw SURF acceptance

**Date:** 2026-10-19. **Verdict:** `PASS_SCOPED_REAL_NOAA_ZERO_VIRTUAL_2024_LEAP_RAW_SURF_BYTE_PARITY`; Issue #84 remains **OPEN** for natural primary switching and 1/≥3 in-domain full-production parity.

## Independent run and source custody

- [Authentic manual Actions #39249039833](https://github.com/RRain001/CTEAS-next/actions/runs/39249039833), `workflow_dispatch`, **SUCCESS**; `main@a1a16ee125679a5a0038be1c3c7304a89b34b841`.
- Artifact **12185180682**, `issue84-real-zero-leap-scoped-metadata-39249039833`; contains `wolsong-zero-virtual-2024-leap-parity.json`, execution log, pinned original source and binary SHA checks. Actions artifact retained 14 days; this document retains essential immutable provenance without republishing NOAA originals/vendor code.
- Original CALMET SMERGE vendor source is independently compiled from `RRain001/CTEAS@dfad99a78ed84d655e21411c9d25eb0d2583bf13` (`SMERGE_v5.7.0_L121203`) outside the current repository. Original executable SHA-256: `c80c2bab3ce2d2c1781c04a58a4cd42ebe6bef10d0a5b725b50d7f9e5460beb8`.
- Direct real original sources: NOAA full Global Hourly ISD `https://noaa-global-hourly-pds.s3.amazonaws.com/2024/47152099999.csv` SHA-256 `9740198e2df44eb8d99ec49ee779f3d000bf5dfd49a2cc526a9600ea00e23eed`; NOAA ISD-Lite `https://www.ncei.noaa.gov/pub/data/noaa/isd-lite/2024/471520-99999-2024.gz` SHA-256 `ed8ec2563d380fe72cc185f7ef7400cedc80963a69e6c31d0a03a64fd4b0bd04`. SHA mismatches fail closed.

## Actual case geometry and calendar

- The already-authorized #119 Wolsong 20 km × 20 km UTM52N frozen grid has `XREFKM=533.215`, `YREFKM=3942.629`, 0.100 km spacing, 200×200 cells. `grid.cmn` SHA-256 `d9cc31da4ccf8addce51ce89f97575d85bdb2eb316156b9d4e84e09a94054af7`.
- Real 2024 NOAA full-year catalog: **0 in-domain stations**. The production original selector chose 1 **VIRTUAL_RELOCATED** nearest ULSAN original station SID **47152099999**, `IFSTN=471520`. Original site (lat,lon) `(35.593,129.352)`, virtual effective source at the case's representative point `(35.716670,129.477780)`, approximately 17.840 km away. The representative point is **not a verified physical exhaust-stack location**.
- Both independently downloaded original NOAA sources contain **8612 of 8784** unique raw UTC hours in 2024, strictly >90%. Each has **24/24 actual Feb 29 hours**; these are original timestamps, not software-added weather.
- Modeled hour-ending `(BEGIN,END]` window **2024-02-28 00:00 UTC → 2024-03-01 00:00 UTC**, precisely **48 hours**. Fresh `case.yaml` SHA-256 `a6020e7b61d252ab1305f3ded0c65e645d2002c618d91316d7d7d072b599d877`, time-file SHA-256 `0e3be499ac2b2b239191817b4e40ea2ffbb0f770e83472d8339aabd340ec43c7`; original station-year manifest SHA-256 `bdd9ff08e2ccd2487fcc1824c2c5793fb8ce29d6391b85e456bbf4444e8abd01`.

## Same-input original SMERGE versus C++ and independent reader

- Existing P5 producer with **offline re-selection** emitted the same GENERIC inputs and `smerge.inp` for independently compiled original Fortran and reconstructed C++ SMERGE. Frozen controls only: `JDAT=8, IOFORM=2, IOPACK=0, LPREV=F, LPCALC=F, UTC+0000`. Shared `smerge.inp` SHA-256 `7418b2e5780e7c564688404bde387b54e8893d1ccc9e657145a0d051a3345189`.
- Real RAW `SURF.DAT` **4816/4816 bytes, 103/103 lines, exact byte identity**. Both original/native RAW SHA-256: `3467cde8fcf88533860f90d50f3bf4033cc6cee623fae7448ab3bff3defec42e`. First mismatch: **none**.
- Independent C++ P6 source **reader only**: `48/48` hour records, `NSSTA=1`, 48 populated station-hours, 0 missing and 48 valid wind station-hours, `SS_IDS=471520`. Reader's single-station source-only CLI guard was repaired via [PR #133](https://github.com/RRain001/CTEAS-next/pull/133), with an offline 2024 leap-day 48-hour reader regression. This is **not** P6 windfield numerical acceptance.
- `CTEAS_NEXT_P5_TO_ISSUE42_D4_SOURCE_HANDOFF_V2` validated exact hour/station identities. Across 48 hour×station records, source reader declared **48/48 valid** for wind, temperature, humidity, pressure, ceiling, cloud and precipitation **code** fields. No cloud fallback was actually needed (**0 changes**); raw and published SURF SHA match. **Valid precipitation codes are not proof of physically adequate rain intensity or wet-deposition inputs.**

## Explicit unaccepted items

`NATURAL_YEARLY_PRIMARY_SWITCH=NOT_RUN`; `REAL_ONE_IN_DOMAIN=NOT_RUN`; `REAL_AT_LEAST_THREE_IN_DOMAIN=NOT_RUN`; `P5_TO_G19=NOT_RUN`; `P6_NUMERICAL=NOT_RUN`; `P7=NOT_RUN`; `WET_DEPOSITION=NOT_RUN`; `OTHER_SMERGE_OPTIONS=NOT_RUN`.

The earlier source screening [Run #39247024823](https://github.com/RRain001/CTEAS-next/actions/runs/39247024823) was **PARTIAL** because a *different* out-domain Pohang 47139099999 2024 original source returned HTTP 404. It remains documented as a candidate-source limitation, and does **not** invalidate the independent complete 2024 ULSAN original bytes re-fetched and SHA-verified in this successful parity run.

Do not treat this case as a full #84 closure or as P1–P5 G19 acceptance. #84 requires naturally observed annual primary switching and additional real 1/N site examples with independently repeated original-vs-native comparison.
