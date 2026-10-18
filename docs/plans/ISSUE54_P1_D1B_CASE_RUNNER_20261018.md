# #54 D1-B — two-route offline P1 native case runner, software scope

Depends on merged #42 B-0 shared admission PR #61; no standalone `grid.cmn`
parser is created in this PR. `p1_native_case` verifies the immutable
case/grid/time identities and consumes **only** the output manifest of
the previously merged #49 dual-source adapter. No network access, download,
mosaic or alternative DEM physics is added.

The new `cteas_p1_terrain_case` C++ CLI accepts precisely the admitted
3-digit kilometre origin, UTM zone/hemisphere, NX/NY and DGRIDKM; it
passes the source TIFF through the same generic native P1 float32
projection/CELLIND/mean kernel that was merged in PR #59. The original
frozen Hefei CLI is untouched. It rejects unfilled model cells
(hits==0); source NoData rejection remains fail-closed. #54 limits
full image reads to <=30 million pixels, requires source resolution
consistent with either **P1-A local 3-arcsec SRTM** or **P1-B cached
OpenTopography SRTMGL1 1-arcsec**, and cross-checks upstream/source hashes.

Outputs `terrain.csv` (i fastest; j south-to-north) and a **preliminary**
`p1_native_manifest.json` marked `PRODUCED_UNVERIFIED`. Product
declaration is not authentication: named CGIAR/NASA products still require
original-source SHA/licence and same-source original TERREL parity before
any scientific PASS. Product-specific 90m/30m scientific equivalence
remains `NOT_RUN`; raw source georeferencing, datum, NoData and local
access remain constrained by #49 admission. No TERREL.DAT writer or P3
is added: #46 owns that format and downstream science.

This D1-B software runner is deliberately **not** the full B-1 scratch
coordinator or final evidence schema. The caller must provide a fresh
independently staged case outside the checkout, following #42 B-0/B-1.
Restricted data never belongs in PR artifacts, public repo, or Docker image.
