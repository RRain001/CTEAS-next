# Isolated original P1/P2 reference capture

This is an executable, experimental reference-capture stage, not a completed numerical reproduction. The GitHub-hosted workflow uses only trusted-branch pushes and no private self-hosted runner, secrets, or repository write permission.

- Checks committed crop input SHA-256, uses the existing Python case-control preparation routines to construct 50x50, 0.1 km UTM50N WGS84 original TERREL/CTGPROC controls under a fresh /tmp directory; uses GEN mode and DNZGEN=ESR-S, without ever mutating original Fortran code or inputs.
- Builds original TERREL and CTGPROC with the repository's documented gfortran legacy options. Runs each original under an isolated working directory. Archives program logs, compiler logs, control files and possible outputs, even on workflow failure.
- On success, records original source/input/output SHA-256 and grid origin. Classification stays REFERENCE_CAPTURED_NOT_PARSED_NOT_COMPARED until an independent decoder and same-input C++ stage comparisons are complete.
- The workspace's numerical XREFKM/YREFKM are set from crop_info.json projected center minus 2.5 km; use IGRID=1, the SW corner of cell(1,1). This is a candidate reference control set pending acceptance of original field contents and exact projection/time semantics.
- Artifacts expire after 7 days: preserve raw evidence and metadata before archival if these become accepted scientific benchmarks.
