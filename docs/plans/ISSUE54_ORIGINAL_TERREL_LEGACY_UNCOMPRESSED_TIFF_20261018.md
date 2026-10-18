# #54 original TERREL TIFF reader compatibility — lossless packaging only

Original CTEAS `engine/vendor/src/TERREL_v7.0.0_L141010/tiffinfo.for`
contains the explicit implementation condition `icompress.ne.1` ->
`lerror=.true.` and states that TIFF Compression=1
(**uncompressed**) is the only accepted format. Its original GeoTIFF
reader is from an era before the compressed TIFFs used by the modern
#49 source mosaic/COG. CTEAS original should **not** be modified to
support DEFLATE, and the C++ sampling kernel and tolerances should
**not** be adjusted to fake parity.

The first two genuine original-vendor GitHub Actions jobs
[#39127579700](https://github.com/RRain001/CTEAS-next/actions/runs/39127579700)
(90m) and [#39127585780](https://github.com/RRain001/CTEAS-next/actions/runs/39127585780)
(30m) both reproduced their prior genuine original DEM source and
identical native P1 CSV hash but could not obtain an accepted original
comparison. A safe diagnostic [PR #85](https://github.com/RRain001/CTEAS-next/pull/85)
identified `ComparisonError` due to missing/empty required original
evidence, consistent with old reader failure but not by itself proof
of the sole cause.

**Fix for the independent ORIGINAL validation job only**:

1. Preserve original `p1_source_manifest.json`, source TIFF and
   initial native `terrain.csv` unchanged. Create **a new** TIFF
   with identical original WGS84 CRS, geotransform, 16-bit signed
   elevation/NoData pixels and integer resolution, but baseline
   `Compression=1` without TIFF tiling/predictors.
2. Re-read **every original pixel** from BOTH compressed and newly
   uncompressed TIFFs and assert exact equality, as well as raw ordered
   int16 SHA, origin, CRS, bounds, pixel shape, NoData sentinel,
   3/1 arcsecond resolution. Do not reproject, resample, fill voids,
   interpolate or smooth. Record original-source TIFF SHA256 and
   new packing's SHA256 with the exact `GTIFF_COMPRESSION_ONLY_LOSSLESS`
   provenance.
3. Feed that exact same newly uncompressed TIFF through the existing
   `p1_native_case.run_case` in an isolated `p1_native_test`
   directory and to unchanged original TERREL input control via
   CTEAS's own `update_terrel`. Original and native share **the
   exact same TIFF SHA**; the original compressed run remains a
   separate production outcome with its own immutable digest.
4. Perform existing strict #67/#71 DAT/SAV/CSV comparison. Report any
   original semantic/schema/numeric difference as **BLOCKED/FAIL**
   without altering scientific tolerances, input source product, data
   version or reference original Fortran code.
5. Keep combined metadata-only artifacts; original vendor binary,
   control file, raw TIFF and log remain out of GitHub artifacts.

This is legitimate **lossless container-format conversion**, not a
different DEM route or elevation processing algorithm. It is required
by original TIFF reader limitations; results remain scientific
`NOT_ACCEPTED` until independent D4 audit.
