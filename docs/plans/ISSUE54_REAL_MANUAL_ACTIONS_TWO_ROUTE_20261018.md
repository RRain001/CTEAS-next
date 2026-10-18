# Issue #54 — actual SRTM P1 manual Actions runner (A and B)

This workflow is **genuinely manual for real input**. Normal pull requests
run only a small grid B-0 geometry check, with no DEM pull, source API call,
native scientific replay or original Fortran use.

A dedicated `workflow_dispatch` action, `.github/workflows/issue54-real-two-route-manual.yml`,
runs on a GitHub-hosted Ubuntu runner in a temporary outside-repository
directory for precisely two mutually exclusive cases:

- `P1_A_90M_LOCAL`: Git LFS pull for **only**
  `srtm_59_06.tif` and `srtm_60_06.tif` (two original, user-supplied
  6000x6000 3-arcsec TIFFs). Exact owner SHA256, byte length, CRS,
  tile footprint, NoData sentinel and matching 115E seam selection
  are verified by the already merged #70 audit tool. This is a genuine
  **multi-TIFF** test, not a synthetic TIFF nor an assumption that all
  six tiles are needed.
- `P1_B_30M_DOWNLOAD`: uses the existing #49 protected
  `OPENTOPOGRAPHY_API_KEY` Actions Secret to fetch genuine official
  SRTMGL1 1-arcsec data for the **same** test grid, via the existing
  downloader; no API key/url or response body is added to outputs or
  artifacts. No switch to 90m or mock fallback on API failure.

Both routes prepare a fresh independent `issue54_p1_seam_2022` staged
case with 50 x 50 cells at 0.1km, authoritative exact-three-decimal UTM50N
origin derived from WGS84 115.0E, 31.94N center and fixed short 2022 UTC
research_time. Stage is outside repo/frozen Hefei and must pass #42 B0.
Both use **the same reviewed** #49 source adapter and the #62 native
`cteas_p1_terrain_case` implementation, with no physics change and no
second grid/admission parser. Compiles native binary and executes its
isolated CTest gates.

Only a compact JSON source/native metadata report is uploaded. No original
DEM, selected mosaic, source credentials, vendor source/executable or model
files are uploaded. A product label may be required by #62 as a route
**declaration**; the report explicitly says true provider version and
vertical datum are `NOT_AUTHENTICATED`.

To trigger the reviewed `workflow_dispatch` using the repository owner's
authenticated GitHub issue comments, the minimal
`issue54-owner-comment-dispatch.yml` bridge accepts **only issue #54**,
**only comment author `RRain001`**, and **only exactly** one of:

```text
/cteas-p1-real-90m
/cteas-p1-real-30m
```

The bridge uses the Actions-scoped `GITHUB_TOKEN` and fixed workflow
name/ref/input; no arbitrary shell code, environment paths or branch names
come from the issue comment. A user-issued command is an explicit manual
trigger and creates an actual `workflow_dispatch` run. (If repository
policy blocks Actions write permissions, it must report blocked rather
than silently run an ordinary PR scientific test.)

A successful route produces `P1_REAL_TIFF_NATIVE_PRODUCED_UNVERIFIED`.
It does **not** execute an original vendor TERREL comparison, validate
vertical datum/product version/licensing, prove the 600km six-tile footprint,
or finish P3/P6/P7. This result can unlock planning independent
original-Fortran same-source D2/D3 parity, but must **never** be labeled
`SCIENTIFIC_PARITY_PASS`. Issue #54 stays OPEN.
