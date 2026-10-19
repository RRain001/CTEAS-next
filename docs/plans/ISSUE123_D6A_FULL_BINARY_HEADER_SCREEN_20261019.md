# Issue #123 D6-A: authentic Full binary polygon-header preflight (2026-10-19)

## Motivation and scope

D5 authenticated the official `gshhg-bin-2.3.7.zip` and actual `gshhs_f.b`
SHA. D4 matched 568 synthetic, identical-input original Fortran PNPOLY cases.
Neither result means that original `COASTEXT` or `COASTRD` emitted real BLN,
nor that real `IPTYPE` or `LU.DAT` matches.

This D6-A stage adds a **bounded index screen** of every genuine binary
polygon HEADER, using the same packed v2.x 44-byte big-endian structure that
original CTGPROC `BREADH` expects. Each record's `npoints*8` bytes are
skipped in source order; truncated, corrupt or unreasonable records fail
closed. Each nonzero-area header with a conservatively over-inclusive
Wolsong geographic bbox is a **candidate**, not a proven COASTEXT polygon.
No vertex arrays are transformed, sampled or clipped in D6-A.

## Frozen case and envelope

- Wolsong #119: 20 km x 20 km, EPSG:32652, `XREFKM=533.215`,
  `YREFKM=3942.629`, `NX=NY=200`, `DGRIDKM=0.100`.
- Diagnostic WGS84 bbox: lon [129.30,129.66], lat [35.56,35.88].
  It deliberately exceeds the approximate inverse UTM extent
  lon [129.3668,129.5891], lat [35.6260,35.8073] for the corners/midpoints.
  It is **not** the exact original projection/datum or the original 1%
  COASTEXT screening envelope. Do not claim candidate parity from counts.
- Only GSHHG Full; no High comparison. Existing frozen GLC2022
  `EXACT_AREA_V1` and all production P2-A/P2-B code remain untouched.

## Source and CI

The `scripts/s2g/issue123_original_full_header_screen.py` CLI invokes D5
`verify(cache)`, re-verifies the original official archive SHA, extracted
Full member, bytes and manifest, then streams every binary record and emits
a bounded JSON header report. It has limits on record count, per-polygon
point count, candidate sample size, file size, and malformed offset handling.
Candidate metadata, SHA, counts, source order and envelope are report-only.
Do not upload the actual binary, original code, raw BLN or raw vertices.

PR CI runs **synthetic offline negative tests only**. After merge, the
path-scoped `push: main` scientific step automatically obtains and validates
the genuine binary and produces the provenance artifact; it is also eligible
for authorized agent `workflow_dispatch`. Both triggers comply with the
project-wide superseding `docs/ci/SCIENCE_TRIGGER_POLICY.md`.
This PR's initial state is `D6A_SOFTWARE_PENDING_CI`; the real scan
must not be marked PASS until the actual main Actions run succeeds.

## Mandatory next gate: genuine original BLN

1. Fetch exact unmodified CTGPROC `ctgproc.for` from
   `RRain001/CTEAS@dfad99a78ed84d655e21411c9d25eb0d2583bf13`
   with SHA256 `719abbd2327269bb0377208b3a7a0c74000b878efc756686023bbb2ef932f281`.
2. Run **unmodified Fortran COASTEXT** with authenticated original
   `gshhs_f.b`, legal GLCC/GLAZAS input and the frozen Wolsong grid and
   datum/projection/control deck. Keep the original executable out of
   the public repository and artifacts. Verify BLN file SHA and capture
   polygon count, ordered type/source/id and vertices, real/constructed
   surrounding polygons, closing and first differences.
3. Feed the exact original output BLN and exactly identical original
   REAL*4 test/sample points into independent original Fortran
   `IPTYPE` and native `OriginalBlnIptypeR4`; require zero integer
   mismatches. Original `COASTEXT` may produce different geometry
   from independently clipped Full Shapefiles.
4. Only then connect isolated ORIGINAL_SAMPLING to the authentic GLCC
   P2-A counter. Demand 38-category integer HITS equivalence under
   `LFINAL=F` and 3-decimal LU.DAT fractions under `LFINAL=T`;
   audit 52/55/54 mixing and `LMARSWAP/LMARFILL` option behavior.
5. Keep #123 OPEN through this scope. Pass of D6-A alone explicitly
   leaves `ORIGINAL_COASTEXT_BLN`, real `IPTYPE`, full CTGPROC
   and 38-class LU.DAT scientific parity all `NOT_RUN`.

No modification to #119, P3 #46, or P6/P7 is permitted in D6-A.

## Authentic v2.3.7 level 5/6 compatibility correction

The original official GMT GSHHG 2.3.7 binary includes level **5** Antarctic
ice/ocean-front and level **6** grounding-line/ocean boundary polygons in
addition to the ordinary level 1–4 hierarchy. The first authentic D6-A
main run [#39262939077](https://github.com/RRain001/CTEAS-next/actions/runs/39262939077)
correctly failed closed because this source index initially only admitted
levels 1–4. Bounded second run
[#39263648936](https://github.com/RRain001/CTEAS-next/actions/runs/39263648936)
identified first failure at record #4, offset 21,225,312, legitimate
level 5/version 15. The fix admits levels 5 and 6 **as global source
header records only** but excludes them from Wolsong geographic candidates;
the production original `IPTYPE` land-use hierarchy remains 0–4 and the
frozen #119 method is unchanged. All six levels are counted separately.
Reference: https://www.soest.hawaii.edu/wessel/gshhg/
