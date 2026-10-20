# Issue #42 S3-B4 — genuine NOAA catalog geometry admission on the actual June Huoshan B0

Date: 2026-10-20. This is an independently executed **catalog / geography** gate after S3-B3 [PR #187](https://github.com/RRain001/CTEAS-next/pull/187) `main@2ac759ab69e4bbc302aafda31e94f9653db247be`. It is **not** NOAA observation coverage, final station selection, P4/P5 source production, G19 or S3 science PASS.

## Why the check is necessary

The authentic June 2022 P5 source-only two-surface-station evidence from [Issue #56](https://github.com/RRain001/CTEAS-next/issues/56) used a much larger UTM50N grid beginning at 426.590/3464.125 km. The independently original-validated Huoshan `GEO.DAT` instead uses 100×100 cells @100m starting 462.305/3501.570 km, centered approximately 31.694°N, 116.655°E. The two geographical domains are not interchangeable.

The selected algorithms use different lawful station rules:

- P4/READ62: retain all **qualifying** 2022 in-domain IGRA soundings, else choose the nearest qualifying outside real sounding and relocate its effective position. Availability is based on authentic 00/12 original profiles with strictly >80% quality/coverage.
- P5/SMERGE: all physically in-domain stations with both authentic ISD and ISD-Lite source files can be retained (including sparse ones); if none are in-domain, the nearest valid out-of-domain single proxy must pass **both** annual source-hour >90% thresholds. Neither historical station number nor coverage may be invented.

## Implemented narrow gate

`scripts/s2g/issue42_s3b4_real_noaa_station_probe.py` reads the exact immutable June `case.yaml/grid.cmn/research_time`, uses the already existing production P4/P5 candidate geometry functions against **complete original station lists** and strict original station metadata, records both actual catalog source SHA256, counts in-domain and outside real IGRA/ISD candidates, and includes the first ten candidate IDs in **actual source-selection order**. No truncated list is treated as the final selected station set.

The June job alone now executes this probe **after** independent real SRTM90 + GLCC + original MAKEGEO 80,000-field parity; the existing January source/physics baseline is left intact. All evidence stays under that exact current case root, with the B0 SHA recomputed and crosschecked against the actual P3 producer evidence. CI fails if either list is missing, the B0 footprint/time differ, the catalogs are missing/symlinked, or the product lineage changes. Metadata is uploaded with each June artifact, not raw NOAA source bytes.

## Explicit remaining scope

Catalog metadata can identify *candidates*, not establish that a given station is actually qualified. Required follow-on action is an **actual same-B0** offline/real NOAA P4 2022 00/12 coverage replay and P5 2022 original ISD/ISD-Lite coverage + selection, then unmodified selected C++ READ62/SMERGE production, new original `UP.DAT` and **published** `SURF.DAT`. Record station source/effective coordinates and original obs SHA, original-vs-native scope, hour-ending and AA/BB brackets. Then run [#184](https://github.com/RRain001/CTEAS-next/pull/184) join and G19 native parser; do not assume previous large-domain 1US/2SS selection is valid.

**Current scope:** `S3_B4_TRUE_CATALOG_GEOMETRY_ACCEPTED_NO_NOAA_OBSERVATION_QA` only after CI; `P4/P5_NEW_JUNE_UP_SURF=NOT_RUN`, `G19=NOT_RUN`, `S3_P1_P5_NEW_SITE_STACK=NOT_ACCEPTED`. P6 physics/P7/wet deposition/capacity/Docker remain deferred.
