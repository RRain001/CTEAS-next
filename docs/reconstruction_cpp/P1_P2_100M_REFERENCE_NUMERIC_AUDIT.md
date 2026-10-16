# Hefei 100 m: first original Fortran field audit

Evidence date: 2026-10-10.
Implementation branch: `codex/cpp20-p1-p2-foundation-20261010`.
Original main: `66e30ffb1ff4638a97af8a060748ce30b7578350`.
Action: https://github.com/RRain001/CTEAS/actions/runs/38042172559 (completed SUCCESS).
Tool: `native_cpp/reference/capture_p1_p2.py` followed by independent `native_cpp/reference/analyze_p1_p2.py`.
Artifacts: Actions upload `p1-p2-original-reference`; time-limited (7 days), not yet frozen in persistent scientific archive.

| Parameter | Original P1 TERREL 7.0.0 | Original P2 CTGPROC 7.0.0 |
|---|---|---|
| Output format | TERREL.DAT 2.0 | LU.DAT 2.1 |
| SHA256 | `d74a5a1045ea4cf25e120099196a3962ab012aaebdf37354ec8264fad0e27678` | `75720a211126ffc1d5dbd931cb1dfcc4b4c54f0f4b19b0bceeb26487ba75c0ea` |
| File bytes | 20648 | 648139 |
| Output grid | 50 × 50 | 50 × 50 |
| Grid origin printed (km) | x=510.885, y=3531.269 | same |
| Horizontal spacing (km) | 0.100 / 0.100 | 0.100 / 0.100 |
| CRS | UTM 50N / WGS-84 | same |
| Independent parsed denominator | 2500 finite terrain cells | 2500 rows × 38 class fractions |
| Reference missing | 0 terrain -999 values | 0 all-zero class fraction rows |
| Range | 25.0–59.5 m | fractions 0.000–1.000 |
| Other | mean terrain 42.91588 m | all 2500 rows sum exactly 1.000; all 2500 show category 21 at fraction 1.000 |

**Original data headers print origin to three decimal km**; actual original control files were produced from `crop_info.json` at higher precision. Do not use the printed origin as a high-precision reference without checking original Fortran grid rounding. The original crop data use 90 × 77, 6930 raw int16 values, all valid; these are not the 2500 interpolated terrain cells.

Original program logs: TERREL reported 3456 terrain points extracted within grid, no missing raw points; CTGPROC reported 10011 GENERIC points used to update grid, no missing LU samples. Original landuse input has 57,600 points across an approximately 7 km data crop sampled at 50 m; those counts must not be conflated.

The parser validates original data version, CRS/datum, physical units, geometry equality, row positions, number of values and missing/sum distributions. It does not derive acceptable numerical error tolerance from the outputs, assume NoData replacement, execute the C++ terrain allocation/classification methods, or compare C++ field values. **Gate status: ORIGINAL_FORTRAN_REFERENCE_PARSED; CPP_NUMERIC_EQUIVALENCE_NOT_TESTED.**

## Blocked steps
1. Independently reconcile Fortran source routine use, control flags and original grid coordinate float quantization.
2. Implement P1 TERREL per-grid elevation algorithm; compare all 2500 cells/masks against original.
3. Implement P2 GENERIC coordinate transformation (ESR-S -> WGS84 UTM50N) and class accumulation/normalization; compare all 2500 × 38 output fractions.
4. Freeze a second original reference execution and archive artifact in persistent hash-controlled storage; then control numerical tolerances and repeatability.
5. P4/P5 depend on actual Hefei 2022 meteorological input station files, independent reference outputs, provenance and time-axis validation. P3/P6/P7 not yet implemented.
