# S2-2B: native P1/P2 output serialization into original MAKEGEO inputs

This is **an I/O adapter**, not a reimplementation or modification of P1/P2/P3 physics.
Supported scope: frozen Hefei 2022, 50×50@100m, UTM50N WGS84, fixed x0=510.885 km / y0=3531.269 km, 38 land-use categories.

## Build and example

```bash
cmake -S native_cpp/p3 -B /tmp/cteas-p12-p3
cmake --build /tmp/cteas-p12-p3 --parallel 2
ctest --test-dir /tmp/cteas-p12-p3 --output-on-failure
/tmp/cteas-p12-p3/cteas_p12_to_p3_dat terrain /path/to/native-p1.csv /tmp/terrel.dat
/tmp/cteas-p12-p3/cteas_p12_to_p3_dat landuse /path/to/native-p2.csv /tmp/lu.dat
/tmp/cteas-p12-p3/cteas_p3_makegeo /path/to/makegeo.inp /tmp/lu.dat /tmp/terrel.dat /tmp/p3.csv /tmp/geo.dat
```

The writer preserves P1/P2 numerical results at original source-file display precision (terrain F8.1, land use three decimals), converts terrain south-to-north native CSV into the original north-to-south TERREL.DAT v2.0 ordering, and retains south-to-north LU.DAT v2.1 indexing and exactly 38 original category IDs. Malformed/partial/missing/nonfinite input or destination collisions are fail-closed. No missing-terrain interpolation, rescaling, original Fortran execution or source-data download is performed.

## What the automated test proves

The CTest harness synthesizes diagnostic P1/P2 CSV **from existing captured original TERREL/LU scientific data**, feeds the new C++ adapter, then executes the **unchanged P3 C++ binary**. It compares the P3 CSV and emitted GEO.DAT values to the captured original GEO.DAT with existing predeclared field tolerances (20,000 displayed values). It also tests malformed native CSV, illegal fraction, missing terrain, row/category ordering, output immutability and reproducibility.

**This does not prove newly computed native P1/P2 fields are equivalent to original Fortran**: the test inputs are seeded from the original reference for isolation of the format contract. Full P1→P2→P3 same-source native scientific comparison is still BLOCKED until native P1 (requires excluded authorized cropped SRTM GeoTIFF) and P2 (source data available) are actually run, audited and handed to the unchanged P3. P3 historical scoped numeric parity remains unchanged. GUI, P6, P7 and their scientific acceptance are explicitly outside this PR.
