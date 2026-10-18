# #54 D2 SRTM90m six-tile real-asset gate

Owner-provided six raw TIFFs are listed in
`calpuff_terrain_and_landuse_data/china_srtm/README.md` with SHA256,
nominal tile bounds, 6000x6000 size, 3-arcsec spacing and 72,096,675
bytes per TIFF. GitHub tracks LFS pointers, not guaranteed runnable TIFF
bytes. Exact provider product/version, vertical datum/height units and
redistribution rights have **not** been independently authenticated.

This PR adds `scripts/s2g/p1_real_srtm90_admission.py`, a narrow
**read-only independent preflight**. It computes the buffered WGS84 bbox
from the agreed grid, identifies the necessary subset of those six
tiles, and hashes **each actual file**, checking the owner's expected
file size, exact SHA256, 6000x6000, WGS84 EPSG:4326, 3-arcsecond
north-up grid, tile bounds and a valid NoData sentinel through the
existing #49 reader. It will not accept a Git LFS pointer, symlink,
truncated file, mismatched tile, unrepresented region or missing source.

No product/version/vertical-datum assumption is inferred from names or
hashes: the output says
`P1_A_OWNER_SUPPLIED_TIFF_BYTES_AND_GEOMETRY_VERIFIED_ONLY`,
`source_product_version=NOT_AUTHENTICATED`,
`science_acceptance=NOT_ACCEPTED`. This preliminary inventory is **not**
the #49 merged/cropped source, not the native P1 producer and not an
original TERREL comparison. The existing #49 adapter is still required
for edge overlaps, NoData in the actual case window and source
selection; no third DEM route or resampling policy is introduced.

## Actions

`.github/workflows/issue54-d2-real-90m-admission.yml` has two
non-overlapping jobs:

1. PR: mocked synthetic SHA/geometry checks and LFS-pointer / missing /
   outside-footprint negative checks; no LFS download or real TIFF data.
2. Manually dispatched on main only: use an authorized
   `cteas-managed` self-hosted runner with
   `CTEAS_P1_EVIDENCE_ROOT` and `CTEAS_P1_90M_DIR` repo variables.
   Input `case_id` refers to an independent,
   already-staged `case.yaml/grid/grid.cmn/grid/research_time`
   under the evidence root; #42 B-0 runs first.
   Only required tiles are read from the approved external data mount.
   Artifact is a SHA-only JSON with deliberately unverified science
   status; never upload TIFF/vendor/data files. No automatic heavy run.

This does not run the original TERREL or produce P1 scientific
acceptance. Next: verify actual LFS materialization on the runner;
perform #49 mosaic using the same independently staged case; execute
native P1 and authorized original TERREL with the **identical selected
TIFF bytes**, then run the original/native comparator merged in #67.
`P1_A_REAL=NOT_RUN` and `P1_B_REAL=NOT_RUN` until those executions
really occur. Keep #54 open.
