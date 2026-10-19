# Issue #123 D8 — authentic BLN same-input original Fortran IPTYPE gate

Date: 2026-10-20. **PENDING authentic science run; no PASS inferred from PR CI.**

## Source and predecessor

Frozen P2-B Wolsong EXACT_AREA_V1 (Issue #119) is untouched. Original D6-B Wolsong GSHHG Full COASTEXT generated an authentic, nonempty coast.bln (one land polygon, 136 vertices) at [Run #39284574311](https://github.com/RRain001/CTEAS-next/actions/runs/39284574311) with [Artifact #12201243944](https://github.com/RRain001/CTEAS-next/actions/runs/39284574311/artifacts/12201243944). Original vendor SHA and legal GLAZAS/GLCC Full-source provenance are mandatory. GNU STREAM/EOF adapters apply to the complete original CTGPROC execution; this is not an entirely byte-identical vendor runtime.

## D8 implementation scope

1. On an authentic D6-B run, consume the **same ephemeral original coast.bln** only after original_coastext_report.json, actual BLN SHA, size, polygon geometry and exact vendor source SHA pass. Do not substitute raw shapefile/GEOS geometry or an archived metadata-only artifact.
2. Extract and compile the unmodified original COASTRD, IPTYPE and PNPOLY subroutines at runtime from the SHA-pinned CTGPROC vendor file. A minimal Fortran driver initializes frozen Wolsong COMMON/grid bounds and feeds records to original IPTYPE. OPEN_ERR is an error-only failing stub.
3. Independently compile native C++ OriginalBlnIptypeR4 and read precisely the same BLN. Supply precisely identical decimal-serialized IEEE REAL*4 coordinate records to both programs: all 40,000 model-grid centers, exact extracted BLN vertices and immediate float32 neighbors, successive segment midpoints and 2,048 seeded probes.
4. Require exactly **zero integer point-type mismatches**, complete row counts and values 0–4, and preserve at most first 20 mismatch details if failed. A successful scientific report must come from actual original-source Actions, not from synthetic offline tests.
5. Upload only D6 source/BLN metadata and D8 provenance/report JSON. Original BLN, source, program binary, actual sample points, and raw GLCC remain private ephemeral runner inputs.

## Explicit limits

- This D8 grid-center/edge test is **not** the exact original GLAZAS submesh stream; no original 200×200×38 HITS or F6.3 LU.DAT parity is claimed.
- The Wolsong genuine BLN currently contains one type-1 polygon only: real level-2/3/4 nesting needs other suitable scientific cases. Existing synthetic nested tests cannot substitute.
- D9 must capture the legal original GLAZAS sample mesh, per-cell 38-category integer HITS and independently compare D7 C++ recount. D10 then compares original formatted LU.DAT fractions and missing/marine behavior; accepted P2-B EXACT_AREA_V1 remains unchanged.
- Keep Issue #123 OPEN through independently accepted D8, D9, D10 and separately reviewed integration.
