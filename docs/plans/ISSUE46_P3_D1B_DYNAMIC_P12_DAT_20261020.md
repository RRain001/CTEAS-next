# Issue #46 — D1-B: dynamic P1/P2 CSV → P3 original-format DAT software bridge

Date: 2026-10-20. Baseline `main@7fcf89d370e82b568ae1bb7eae2a94b3ac167e35`. PR [#174](https://github.com/RRain001/CTEAS-next/pull/174).

## Exact D1-B scope

The existing `native_cpp/p3/p12_native_dat_adapter.cpp` retains its frozen `terrain|landuse SOURCE OUTPUT` route, including 50×50, UTM50N, XREFKM=510.885, YREFKM=3531.269, 100 m. An additional **bounded** `--grid` route accepts explicit WGS84 UTM (zone 1–60, hemisphere N/S), exactly three-decimal km X/Y origin, NX/NY 1–500, spacing exact integer metres (1–100000 m); existing P3 domain limit is 500×500. The source CSV is still strictly 38-class fractions for GLCC or real P1 per-cell i,j,hits,elevation, and **never** the retired P2-B area-fraction path.

```
cteas_p12_to_p3_dat --grid terrain SOURCE_P1_CSV TERREL.DAT ZONE N|S XREFKM YREFKM NX NY DGRIDKM
cteas_p12_to_p3_dat --grid landuse SOURCE_P2_38FRACTION_CSV LU.DAT ZONE N|S XREFKM YREFKM NX NY DGRIDKM
cteas_p3_makegeo MAKEGEO.INP LU.DAT TERREL.DAT OUTPUT.csv GEO.DAT
```

The adapter converts P1 raster-cell scalar elevations to TERREL v2.0 F8.1, emitting rows **north→south**, wrapping at 10 values or model-row end; LU v2.1 remains `i,j` **south→north**, original 38 USGS92 classes, printed three-decimal fractions. Strictly rejects missing/uncovered cells; wrong i,j order; wrong 38 category sequence; malformed, NaN or out-of-range fractions; rounded sum outside [0.96,1.005]; unsupported UTM/spacing/footprint; and existing destination.

For a case with the frozen exact 50N 50×50 0.100 510.885 / 3531.269 geometry, the generalized entry intentionally calls the **original retained serializer**: exact output bytes unchanged. This preserves the independent existing 20,000 formatted GEO field Hefei reference regression.

## Software acceptance, boundaries and next actions

| Gate | Implemented here | Meaning |
| --- | --- | --- |
| Legacy frozen Hefei | Existing P3 CTest compares frozen GEO with original references, and new test compares both adapter modes byte-for-byte at frozen geometry | Hefei scientific baseline unchanged |
| Different UTM52N 4×3 @200m | New test emits original-format TERREL and LU from **separately synthesized** native P1/P2 CSV and feeds the real P3 C++ MAKEGEO GEO producer | Dynamic software inputs/header/row order/38→14 handling; **not real DEM/land-use science** |
| Fail closed | Unsupported origin literal, truncated P2, overwriting target, truncated native P1, invalid category index remain rejected | Contract negative coverage |

**Still pending in #46, not accepted by this PR:**

1. **D2 authentic new-site**: choose one of P2-A original GLCC or P2-C 30 m original-style native actual site inputs; execute *real* P1 GeoTIFF, retain source/source-product SHAs and real native P1 CSV, couple actual P2 `LU.DAT` (produced by P2-A/C directly) and the dynamic TERREL on the exact same immutable B-0 case, execute supported P3 MAKEGEO controls and record GEO SHA. Existing P2-A/C native LU writers mean *do not* use a parallel CSV converter for those authentic paths. A real SRTM source is necessary; synthetic P1 does not satisfy D2.
2. **D3 original**: stage independently compiled original MAKEGEO with same non-Hefei authenticated TERREL/LU and the same physical control options. Compare categorical output, 7 gridded scalar fields, formatting and missing/water thresholds. A successful Python handoff does **not** establish original physics parity.
3. **D4 admission to #42 S3** only after D2/D3 and source license + byte provenance are complete. Grid/clock compatibility and P3 output SHA must be checked. No P6/P7 original science claim and no source-data substitution.
4. Both P2-A historical GLCC and P2-C 2022 30m source methods remain separate. The old P2-B EXACT_AREA_V1 is permanently retired.

Docker scientific/full packaging and gitless SHA handling are intentionally postponed until all other development Issues close, as requested; never mark Docker PASS from this PR.

**Status:** `D1B_DYNAMIC_P12_FORMAT=SOFTWARE_CANDIDATE`; `P3_REAL_NON_HEFEI_ORIGINAL_PARITY=NOT_RUN`; `P3_ALL_SITE_GENERAL=NOT_ACCEPTED`.
