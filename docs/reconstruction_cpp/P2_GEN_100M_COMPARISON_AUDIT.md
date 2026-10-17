# P2 GEN real-case numerical validation (first scoped acceptance)

Date: 2026-10-10. Status: **PASS_SCOPED_GEN_HEFEI_100M**, not FULL_CTGRPOC_EQUIVALENCE.
Original input: 57,600 ESR-S GENERIC.LANDUSE samples (50m point spacing, 38 USGS classes) from the pinned Hefei crop.
Original program: CTGPROC 7.0.0, L150211 `ctgproc.for`, frozen Git blob SHA `9d065735667c2ef0aa170c3e9709d4c01fb6df27`.
Representative authoritative source branches: original `COMP` GENERIC reader (around lines 3435 onward; `relon,rnlat` default `REAL*4`), `GLOBE` datum transform, `LUGRID` index/count accumulation (around lines 4133 onward).

Evidence (fully executed):
- Initial intentionally strict independent comparison: https://github.com/RRain001/CTEAS/actions/runs/38042526812. **FAIL** for internal count (Fortran 10011 vs C++ 10013), while 2500×38=95000 output fractions matched exactly. All raw inputs and original outputs preserved in artifact.
- Independently reproduced cause: CTGPROC's implicit `REAL*4` lon/lat quantization **before** calling GLOBE. The first C++ candidate had projected doubles read from GEN file; for near-boundary samples, this changed counted locations.
- Corrected code: first quantize input longitude/latitude to `float` as original `relon,rnlat`, then call the GDAL/PROJ transform and apply original `LUGRID` float32 grid index logic. No tolerance, domain, input file or original Fortran result was altered.
- Retest: https://github.com/RRain001/CTEAS/actions/runs/38042633637. GitHub-hosted Ubuntu, CMake C++20/GDAL; **3/3 CTest PASS**; original Fortran compile and execution PASS. C++ retained 10011 points, original retained 10011 points. 47589 cropped GEN sample points outside model domain in C++ (57600-10011).
- All 2500 original grid cells and 38 fractions each compared with the declared 0.0005 absolute tolerance reflecting original three-decimal fractional serialization: `compared_float_fields=95000`, `max_absolute_fraction_error=0.0`, `MAE=0.0`, `RMSE=0.0`, missing-mask mismatches=0, point count difference=0. Both `numeric_fraction_gate` and `internal_count_gate` = PASS.
- Original `LU.DAT` SHA256 `75720a211126ffc1d5dbd931cb1dfcc4b4c54f0f4b19b0bceeb26487ba75c0ea`. Reference field decoder `native_cpp/reference/analyze_p1_p2.py`; comparator `native_cpp/reference/compare_p2_gen.py`.

**Explicit limits**: only supported GEN/LL/ESR-S/USGS-92, UTM50N WGS84, 50x50x100m corner grid, one final run. No generic arbitrary projections, continuation, other classes, coastline, snow, water reassignment, multiple files, time-dependent logic, or full legacy CTGPROC output file writer. The real-case valid cells are all class 21; this test does not exercise mixed land-cover fractions or class boundary heterogeneity. Future independent synthetic mixed-class and reference control-option cases are necessary before broader acceptance. P2 PR must remain Draft and not be merged into foundation until independent review.

The reference and comparison evidence artifacts currently have a 7-day retention window; archive immutably for any formal scientific release.
