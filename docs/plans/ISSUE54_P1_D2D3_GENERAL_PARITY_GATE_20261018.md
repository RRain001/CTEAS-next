# Issue #54 — D2/D3 generic TERREL original/native parity gate

Status: comparator software only. Neither real SRTM90m nor SRTMGL1 30m independent original run is accepted.

## Original same-source requirement

The comparator reads the original Fortran TERREL.DAT v2.0 and TERREL.SAV, original control file, original executable, selected TIFF, native terrain.csv and native P1 output manifest. A separately prepared original_run attestation JSON must contain exactly these digest field names:

```json
{
  "route": "P1_A_90M_LOCAL",
  "grid_sha256": "<source grid.cmn SHA256>",
  "selected_tif_sha256": "<selected TIFF SHA256>",
  "original_terrel_dat_sha256": "<DAT SHA256>",
  "original_terrel_sav_sha256": "<SAV SHA256>",
  "original_control_sha256": "<TERREL control SHA256>",
  "original_executable_sha256": "<original TERREL binary SHA256>"
}
```

For route B, change route to P1_B_30M_DOWNLOAD. All hashes must refer to actual original run files and the exact selected TIFF already referenced in the native P1 manifest. Do not claim source authenticity from names or attestation alone. An independent reviewer must verify original execution command/logs and the input control actually used the same selected TIFF and three-decimal-km grid values. The numerical comparator never independently certifies this original-run provenance.

## Frozen numerical acceptance criteria

- Exact original/native hit counts per cell and identical missing masks.
- Fortran TERREL.SAV preformatted REAL*4 mean vs native CSV: absolute difference <= 0.00001 m.
- TERREL.DAT F8.1 printed height vs native CSV: <= 0.0500001 m.
- Validate dynamic NX/NY, zone/hemisphere, XREFKM/YREFKM exactly three decimals, spacing, model cell sequence, north-to-south DAT vs south-to-north native/SAV, and original F8.1 lines of at most ten values (including non-multiple-of-ten NX).
- Failure report includes first 20 differing i/j and raw differences, counts, maximum errors and exact SHA identities.

Numeric match yields NUMERIC_PASS_PROVISIONAL, never SCIENCE_ACCEPTED_SCOPED. Final acceptance requires independently checking original TERREL controls, executable, source/version, product licence, coverage and comparison reports.

## Actions staging

The workflow issue54-p1-general-parity.yml runs cheap synthetic parsing and negative tests on PRs. It has a separately **manual-only** workflow_dispatch job on the existing cteas-managed Linux self-hosted runner. The runner must have authenticated original and native files staged outside the repository, under repository variable CTEAS_P1_EVIDENCE_ROOT with case_id and route.

Expected path root: EVIDENCE_ROOT / case_id / a90m (or b30m).

```
selected.tif
native/p1_native_manifest.json
native/terrain.csv
original/terrel.dat
original/terrel.sav
original/terrel.inp
original/terrel.x
original/original_attestation.json
```

Only a JSON numerical comparison is uploaded as an Actions artifact; do not upload TIFFs, vendor source/binaries, original DAT/SAV or control files. Authentic original execution and selected inputs must be prepared outside this PR; the workflow does not fabricate vendor results or bypass licensing.

## Real-data blockers verified

The six tracked 90m SRTM tiles under calpuff_terrain_and_landuse_data/china_srtm are Git LFS pointers in the Git tree. The original six full TIFFs have documented SHA256, dimensions and nominal three-arcsecond resolution, but the current tool access has not proved runner-side LFS materialization, exact product version, vertical datum or NoData coverage. The 600 km area is a prepared dataset footprint, not a new-site scientific regression. The current native full-raster limit is 30 million pixels; use the already-approved #49 buffered mosaic rather than pass full multi-tile rasters directly.

The 30m SRTMGL1 download adapter exists with secret isolation, but no actual cached 30m file and independently rerun original TERREL dataset were validated here. Original vendor files must be restored on the authorized runner; they are excluded from the public repository.

D2 P1_A_REAL=NOT_RUN, D3 P1_B_REAL=NOT_RUN, D4 SCIENCE=NOT_ACCEPTED; Issue #54 remains OPEN.

## Additional mandatory original input-deck binding (#54 follow-up)

For a provisional numeric comparison, it is no longer sufficient merely
to attest that a TERREL control file exists and has a stable SHA256.
The independent comparator now parses the actual `terrel.inp` and
requires exactly one active `PMAP=UTM`, `DATUM=WGS-84`,
`UTMHEM`, `IUTMZN`, `XREFKM/YREFKM`, `NX/NY`,
`DGRIDKM`, and `NTDF=1` field. Every geometry value must match
the native admitted grid. There must be exactly one numbered
`1 !GEOTIFF = ... !` input card, and its currently reachable
file bytes must hash to the **same** selected TIFF that produced the
native CSV. Symlinked, missing and otherwise unreadable original source
paths fail closed. The real asset paths and original input-control
must remain accessible to the trusted runner for independent review.

This rule does not rewrite the control, change original TERREL, allow
multiple GeoTIFF records, or claim that original Fortran truly executed
the inspected control. The actual execution command, timestamps,
stdout/stderr and original data product/rights still require human
independent provenance review; numeric pass remains PROVISIONAL.
