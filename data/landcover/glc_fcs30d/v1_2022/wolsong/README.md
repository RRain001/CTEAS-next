# Wolsong — GLC_FCS30D 2022 30 m (Issue #119)

**Status: candidate 20 km grid defined; real Wolsong GLC raster NOT YET ACQUIRED.**

Do not synthesize marine categories, silently replace NoData with ocean, or
reuse a Shanghai GLC crop. The assumed power-station location is NOT a verified
stack position.

Pinned WGS84 / UTM 52N grid (EPSG32652):
- XREFKM: 533.215; YREFKM: 3942.629; DGRIDKM: 0.100;
- NX=200; NY=200; 20 km × 20 km; 400 km².
- Representative site only: latitude 35.716670, longitude 129.477780.
- 2022 GLC_FCS30D v1 annual b23, GEE asset:
  projects/sat-io/open-datasets/GLC-FCS30D/annual.
- GSHHG v2.3.7 Full L1 land polygons from the verified project Release.

First (after merging the PR), manually dispatch
.github/workflows/issue119-wolsong-p2b-real-coast.yml with
validation_scope=coastline_only. This mode needs no GLC raster. It verifies
the official archived coastline, calculates the *union* of clipped land
polygons, reports land/sea areas and avoids double-counting.

On a user-authenticated Earth Engine machine, acquire and verify:
    python3 -m scripts.s2g.p2b_wolsong_case download
    python3 -m scripts.s2g.p2b_wolsong_case verify

For another Earth Engine project append --ee-project PROJECT_ID. The new
wolsong_2022_30m.tif, metadata.json and ATTRIBUTION.md are written in this
directory only after two repeat downloads and source checks pass. All
positive-area raster overlaps must be valid (even boundary slivers); offshore
0/250/NoData is NOT silently recoded to sea.

Only after real TIFF and metadata are independently reviewed and committed,
manually dispatch validation_scope=full_p2b. This invokes the existing C++
35-to-38 area kernel and checks LU.DAT, GLC210 marine USGS55>0, coastal
geometry and conservation. Inland USGS52=0 is permitted when there are no
mapped inland water bodies. Neither mode constitutes P3/P6/P7 acceptance.

Prior Shanghai failure Issue #116 and closed Issue #53 retain their history.
