# S2-2C GEO root-cause isolation — 2026-10-17

## Authoritative root cause

The historical frozen Hefei 2022 grid and the newly recomputed P1/P2 terrain/land-use inputs used different UTM **grid-origin precision**. The historical `grid/grid.cmn` and TERREL/CTGPROC/MAKEGEO source control inputs pin origin `XREFKM=510.885`, `YREFKM=3531.269` (km). The S2-2C newly reconstructed P1/P2 was explicitly called with `510.8846439571007`, `3531.2689269678035`, obtained directly from the more precise crop center minus 2.5 km.

- Easting difference: 0.3560428993 **m**.
- Northing difference: 0.0730321965 **m**.
- Physical land-use categories and all six surface-parameter fields are identical; the difference is in sampled terrain elevation at **18 / 2500 cells** (max 3.0 m). The change is meaningful to topographic slope and derived wind/turbulence across space and hourly diagnostic updates, even though the origin offset is sub-meter.
- The GEO files may still have different **byte hashes or metadata formatting** even when their displayed physical fields are identical. Distinguish exact displayed physical-field comparison from byte-identical files.

## Independent 8-field isolation

Completed [GitHub Actions #39029900893](https://github.com/RRain001/CTEAS-next/actions/runs/39029900893), which executed the same genuine native P1/P2/P3 on the same pinned SRTM and GENERIC land-use inputs twice, changing **only** P1/P2 origin precision. An independent Python parser (`native_cpp/reference/compare_p3_makegeo.py::parse_geo`) compared all 2500 values in each of eight GEO fields with the immutable October 11 frozen case GEO.

| GEO field | Precise native P1/P2 versus historical frozen | Rounded original-control-origin native P1/P2 versus historical frozen |
|---|---:|---:|
| Land use category | 0 different cells | 0 |
| Terrain elevation, m | **18 different cells; max 3.0 m** | **0** |
| Surface roughness z0 | 0 | 0 |
| Albedo | 0 | 0 |
| Bowen ratio | 0 | 0 |
| Soil heat parameter | 0 | 0 |
| Anthropogenic heat parameter | 0 | 0 |
| Leaf area index | 0 | 0 |
| **Total displayed GEO values** | **18 / 20,000 different** | **0 / 20,000 different** |

Immutable historical GEO: SHA256 `c71133b3775bd4d14854a4787bffd1e403e1b4ee869f38adfef7bc769cd603f1`. Newly generated precise GEO: SHA256 `771c7b502087873ada3bad75e798280876d32d3665dc308f975fe4fdc856ad1d`. Regenerated with the historical rounded origin: SHA256 `447803d5918507f007cdebe9bb53e630d06bf7968583c67ec6e47926a11e1416` (same all 20,000 displayed values as frozen, not necessarily same file bytes). Metrics-only artifact in the linked run.

Example precise GEO terrain differences include (i=42,j=15) old 46.0 m versus new 47.0 m; (i=43,j=16) old 42.0 m versus new 43.5 m; (i=16,j=17) old 36.5 m versus new 34.0 m.

## Why 493 P6 exceedances did not indicate faulty P6 physics

- [Actions #39027746664](https://github.com/RRain001/CTEAS-next/actions/runs/39027746664) held the P6 computational source, UP/SURF, met deck and 143h time-axis constant and swapped **only** the source GEO: new precise-origin GEO compared against **historical-original MET** generated using the rounded-origin frozen GEO → **493** field value exceedances; frozen rounded-origin GEO → **0**.
- [Actions #39028984274](https://github.com/RRain001/CTEAS-next/actions/runs/39028984274) freshly executed unmodified original CALMET 6.5.0 using the identical newly generated **precise-origin** GEO, UP/SURF and deck inputs that native P6 used, then compared both independent **143h × 45-field** outputs with original unchanged tolerances → **0 exceedances, PASS_SCOPED**.

Thus the original error was an **invalid mismatched-input science oracle**, exposed by a **grid-origin precision contract split at P1/P2**. The mathematical P6 physics did not require adjustment in this selected case. The canonical input grid coordinates, not the input producer's independently recomputed high precision coordinates, must govern a given case. When changing the intended spatial origin, always regenerate the original comparator MET from that same origin; never compare it against a frozen result from a different GEO.

## Required engineering follow-up

1. Add fail-closed P1/P2 launch validation: explicitly declare authoritative spatial origin and resolution in the locked case/grid; accept no silently recomputed nonidentical origin for the same scientific run manifest.
2. If retaining the historical Oct 11 frozen case, pin `XREFKM=510.885`, `YREFKM=3531.269` in all P1–P7 preprocessors as the accepted source controls. For future higher-precision cases, use those higher-precision values throughout **both** the original and the native computations and emit new source hashes / new provenance.
3. Preserve two separate regression test obligations: (a) exact displayed GEO-field comparison for a common spatial origin; (b) 143h CALMET original/native compare conditioned on **identical GEO/UP/SURF/deck SHA and derived original reference**, not cross-mixed old/new sources.
4. This investigation neither changes physics/tolerances nor claims full P4/P5 freshness, generic model options, P7 execution, wet deposition, or G5 acceptance.

**Disposition:** `S2_2C_SELECTED_2022_P6_SCIENCE=PASS_SCOPED_SAME_INPUT`, `GEO_CAUSAL_ROOT=GRID_ORIGIN_PRECISION_MISMATCH`, `P1_P7_FULL_NATIVE=NOT_READY`.
