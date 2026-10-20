# Issue #46 D3 — Independent original MAKEGEO comparison on genuine Wolsong

2026-10-20. Depends on merged D2 [PR #176](https://github.com/RRain001/CTEAS-next/pull/176), real 40,000-grid-cell SRTMGL1 + 2022 GLC30m + original Full COASTEXT data chain.

## True original numerical-science requirements

- Use **the same** freshly produced Wolsong `TERREL.DAT` and `LU.DAT` from D2's pinned sources under B-0 EPSG:32652, NX/NY=200×200, XREFKM=533.215, YREFKM=3942.629, DGRIDKM=.100. No old Hefei GEO or old Wolsong cached reference is allowed as substitute.
- Independently compile original `MAKEGEO_V3.2_L110401/makegeo.for` from `RRain001/CTEAS@dfad99a78ed84d655e21411c9d25eb0d2583bf13`, preserving its files and physical routines. Do not link the C++ P3 implementation. The original `PARAMS.GEO` maximum grid 464×400 includes 200×200; avoid new capacity changes.
- Stage a separate run directory for original Fortran; stage **exact same bytes** of the real native P1/P2-C TERREL/LU via symlinks, and use generated D2 MAKEGEO.INP with only `LUDAT`, `TERRDAT`, `GEODAT` and `RUNLST` *file paths* updated for the new workdir. Do **not** update grid/control or user-approved 38→14 option table. Any original process failure fails closed; do not fabricate a reference.
- Parse both original and native GEO.DAT v2.1 by strict WGS84 UTM coordinates, dimensions, origin/spacing, 8 ordered field sections, 40,000 nonmissing cells. Original/CPP displayed values must be **exactly identical in all 320,000 category/scalar fields**. Independently compare the C++ higher-precision CSV to original Fortran's display values with predeclared fixed-format tolerances: category exactly 0; elevation, albedo, Bowen, soil, anthropogenic heat, LAI ≤0.0050001; z0 ≤0.00005001. Record max/error counts and first 20 per field; never loosen thresholds after seeing results.
- Publish bounded `p3-d3-wolsong-comparison.json` artifact with source/provenance SHA, original and native GEO SHA and per-field mismatch counts; do not publish restricted original vendor, SRTM/GLC TIFF, BLN, LU or GEO raw files. If D3 fails, the PR remains Draft and #46 stays OPEN with explicit root cause.

## Independent checks

`native_cpp/reference/compare_p3_makegeo_dynamic.py` is a new independent standard-library Python parser, **not** the previous hard-coded Hefei 50×50 comparator and not C++ physics code. A separate quick CI exercises its parsing/negative tests using *only the historical captured original GEO as a synthetic comparator fixture*. That test's success is **not** evidence of Wolsong original science. The heavyweight real-source job reruns D2 upstream inputs to generate original/native same-source P3 evidence, then compiles original standalone MAKEGEO and runs the comparator.

Only if both real-science and parser jobs succeed, and all 320,000 fields satisfy fixed gates, does this selected supported MAKEGEO pathway obtain `P3_NONHEFEI_ORIGINAL_MAKEGEO_PASS`. This does not imply other MAKEGEO switches (snow, alternate land use or split) are covered. Issue #46 may close only when D1–D4 acceptance and #169/S2 handoff criteria are reviewed; #42 S3 combined-site P1–P5 remains separate. Docker deferred until all other development Issues close.
