# Isolated C++20 implementation

Configure: `cmake -S native_cpp -B /tmp/cteas-cpp-build -DCMAKE_BUILD_TYPE=Debug`
Build: `cmake --build /tmp/cteas-cpp-build -j2`
Test: `ctest --test-dir /tmp/cteas-cpp-build --output-on-failure`

Requires CMake >=3.20, a C++20 compiler, GDAL development headers and library (GDAL::GDAL). This builds only the isolated native C++ subtree; original Python/GUI/Fortran paths are unaffected.

**P1 initial scope**: strict GeoTIFF elevation-band / WGS84-geographic input metadata, raw int16/NoData mask, bbox; NOT full TERREL terrain-grid algorithm or numeric parity.
**P2 initial scope**: GEN strict category + point ingestion; NOT original CTGPROC class fraction / coordinate conversion.
PASS on a synthetic test is only PASS_SOFTWARE. Original Fortran and 100m true-case references have not yet been captured.
