# #54 D2/D3 — original TERREL per-pixel coordinate lineage (forensic-only)

## Why this is a separate gate

Unchanged genuine 90m and 30m source DEM bytes now run through original
CTEAS TERREL 7.0.0 and native C++ P1, sharing the exact lossless
uncompressed TIFF, grid, and original data product. They still **NUMERIC_FAIL**:
90m has 18 cell hit-count residuals, mainly adjacent north/south shifts;
30m has 493, mainly east/west. Previous
[Issue #54 evidence](https://github.com/RRain001/CTEAS-next/issues/54#issuecomment-6250168123)
establishes these are real repeatable differences, not simulated tests.

The current C++ algorithm uses GDAL/PROJ WGS84→UTM followed by
REAL*4 staging and historical CELLIND truncation. Original TERREL calls
COORDLIB/GLOBE with its own projection logic before doing REAL*4 CELLIND.
To establish *which stage differs* before changing physics, this PR adds a
**forensic-only scratch copy** of the pinned original, instrumented at
LOADTIFF immediately before SAVEELEV to trace selected source pixel i,j,
the original projected (x,y) and the original CELLIND (ix,iy).

Forensic workflow rules:

- Compile/run the original production TERREL **unmodified** first, with
  no trace, then perform the existing #67/#71 DAT/SAV/CSV comparison;
  its PASS/FAIL status remains the scientific authority.
- Only if real numeric comparison fails, make a new scratch diagnostic
  copy of the pinned **same** original Fortran source and add a tracing
  write. Do not edit CTEAS, write this copy into CTEAS-next, or use the
  instrumented binary as reference science evidence. The debug output
  stays in ephemeral runner temporary storage.
- A Python/pyproj GDAL/PROJ+REAL*4 **proxy** computes the native-path
  projected coordinates/cell indices for those exact source pixel
  centers. The output records only aggregate coordinate differences,
  east/west vs north/south assignment counts, and at most 20 model-cell
  disagreements; it does not upload source TIFF, vendor, detailed traces,
  full terrain elevations, individual pixel coordinates or binary.
- The proxy is **not yet instrumented C++** and must not be labeled
  a definitive PROJ-vs-COORDLIB finding. If mismatch persists, next
  work is direct C++ or original COORDLIB projection regression against
  known pixel centers followed by independent numerical audit.
- Never adjust projection algorithms, source product, NoData,
  coordinate precision, tolerance or output fields merely to make a
  diagnostic number look better.

Normal PR CI executes only synthetic 3x3 WGS84 TIFF and source-hook tests.
Original compilation, instrumentation and real source processing are
restricted to explicitly manually triggered `workflow_dispatch` on main.
Expected D2/D3 status remains `NUMERIC_FAIL` until numerical evidence
independently proves otherwise; the diagnostic cannot make it pass.
