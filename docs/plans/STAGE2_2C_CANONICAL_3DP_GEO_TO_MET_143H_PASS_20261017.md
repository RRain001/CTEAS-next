# S2-2C canonical three-decimal GEO → native MET scientific verification (2026-10-17)

## Executive verdict

**PASS_SCOPED_HEFEI_2022_143H** for the exact three-decimal kilometer UTM computational origin mandated by the owner. The native 1h, 6h and 143h CALMET P6 ran physically using newly generated P1/P2/P3 GEO, P4/P5 frozen 2022 vetted UP/SURF/station metadata, with original historical `MET.DAT` absent from the native scratch case. Two independent 143h × 45-field science comparators passed under the unchanged legacy limits.

Authoritative [GitHub Actions #39034270535](https://github.com/RRain001/CTEAS-next/actions/runs/39034270535) **SUCCESS**; [non-binary numerical and hash artifact #12101173388](https://github.com/RRain001/CTEAS-next/actions/runs/39034270535/artifacts/12101173388). The current PR #27 native source pinned at `87dbb3120facba33094e4a3fa756d4ac8194bc8d`, not a checkout of default `main`.

## Input precision and data chain

- Canonical frozen Hefei origin `XREFKM=510.885` km, `YREFKM=3531.269` km — **3 decimals** (0.001 km, equivalent to 1 metre); do not increase for this or future cases.
- Actual P1/P2 binaries check exact three-decimal precision and selected-case origin; generated fresh genuine native `TERREL.DAT`, `LU.DAT` and `GEO.DAT` with unchanged SRTM, GENERIC land use, and MAKEGEO deck.
- Python GEO decoder independently inspected 8 physical fields × 2500 grid cells = **20,000 original-vs-native reported numerical values; mismatches = 0**. New GEO file SHA can differ from original due to nonphysical header/text metadata; we make no unsupported byte-identity claim.
- Stage P4/P5 uses previously scientifically vetted **frozen** `UP.DAT`, `SURF.DAT`, two `stations.csv` and control card; this is not a fresh 2022 P4/P5 source regeneration in the same run.
- Native P6 process call physically excludes historical `run/met/met.dat`. New `native_causal_independent_header_calmet.dat` is derived from native P6 143h outputs, not substituted from original MET.

## Real execution and independent science gates

| Check | Evidence from Actions | Result |
|---|---|---|
| Fresh P1/P2/P3 canonical GEO vs frozen GEO | 8 × 2500 values, total_mismatches=0 | PASS |
| Native P6 1h real computation | `S2C_REAL_NATIVE_P6_FINISHED_HOURS=1` | PASS_EXECUTION |
| Native P6 6h real computation | `S2C_REAL_NATIVE_P6_FINISHED_HOURS=6` | PASS_EXECUTION |
| Native P6 143h real computation | `S2C_REAL_NATIVE_P6_FINISHED_HOURS=143` | PASS_EXECUTION |
| New native MET vs **freshly compiled and rerun untouched original CALMET 6.5.0 on the byte-identical new GEO, UP, SURF and deck** | `S2C_SAME_FRESH_GEO_ORIGINAL_NATIVE_143H=PASS_SCOPED` | PASS_SCIENCE |
| New native MET vs **pinned historical original 2022 MET.DAT** | `intervals=143, total_exceedances=0, status=PASS`; `S2C_ROUNDED_GEO_NATIVE_MET_VS_HISTORICAL_ORIGINAL_143H=PASS_ZERO_EXCEEDANCES` | PASS_SCIENCE |

Comparisons use the existing P6E 45-field comparator; no field ignored and no numerical tolerance relaxed. Original CALMET source pinned to `RRain001/CTEAS@dfad99a78ed84d655e21411c9d25eb0d2583bf13` and unchanged `calmet.for` blob; historical original MET SHA256 `b1823cda92280888d70b00961ab39486036a3086e18637fff21efb4f4b237d30`. Audit logs, GEO comparisons and comparator JSON are preserved in the metrics-only Actions artifact.

## Scope limits / P7 dependency

This validates the selected **Hefei 2022** source/options and existing 143-hour original/native P6 criteria; **not** general P6 meteorological option coverage or a completely fresh P4/P5 source-to-MET provenance chain.

Separately, S2-2D [Actions #39031608292](https://github.com/RRain001/CTEAS-next/actions/runs/39031608292) completed the genuine C1 frozen-same-MET native P7 143h H-3 test: **357,500/357,500 REAL4 words matched original, PASS_SCOPED**. That test is an existing comparator harness which reads original `puff.con` as the **independent reference**, not yet a standalone P7 production CLI consuming the newly generated canonical native P6 MET. Thus `P1_P7_FULL_NATIVE=NOT_READY`, `S2_2D_STANDALONE_PRODUCTION_CLI=NOT_READY`, G5 deferred.

No P6 or P7 physics modification, numerical-threshold modification, coordinate precision increase or merge authorized by this report.
