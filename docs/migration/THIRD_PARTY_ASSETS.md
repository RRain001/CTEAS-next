# Third-party assets and local scientific dependencies

Checked on 2026-10-16 (Asia/Shanghai). This is a private research migration, not
an assertion of public redistribution rights. The owner clarified that rights
in the self-developed P1–P7 C++20 implementation do **not** establish rights to
redistribute original CALMET/CALPUFF Fortran or CGIAR data. An earlier affirmative
answer was superseded by this explicit clarification. No third-party license
is granted by this repository.

| Asset | Source / use | Submission decision |
|---|---|---|
| `engine/vendor/**` (all seven versioned model/preprocessor packages; 209 files) | Exact upstream CTEAS tracked vendor sources, controls, include files and old compiler listings. Original copyright notices name Exponent, TRC and other component authors. Used to rebuild original Fortran oracles, not as a silent native fallback. | **EXTERNAL / NOT COMMITTED**. Public availability of the [official CALPUFF distributions](https://www.calpuff.org/calpuff/download/download.htm) does not establish a redistribution license. This excludes all vendor preprocessors as well as CALMET/CALPUFF to avoid inconsistent treatment. |
| `calpuff_terrain_and_landuse_data_crop/hefei_5km/china_srtm/**` (2 files) | CGIAR/CIAT SRTM tile crop and bounding box; exact source/crop hashes in `crop_info.json` and `SOURCE_MANIFEST.json`. The upstream source path is a historical local path, not a download or runtime requirement. | **EXTERNAL / NOT COMMITTED**. [CGIAR's product page](https://bigdata.cgiar.org/srtm-90m-digital-elevation-database/) states restrictions on redistribution; exact original acquisition and terms remain to be documented before any upload. No full raw terrain dataset is migrated. |
| `SourceHanSansSC-Regular-2.otf`, `Times New Roman.ttf` | Legacy desktop typography, not numerical inputs. A family-level license is insufficient to establish the provenance of these exact files. | **EXCLUDED**, no restoration by the external scientific dependency tool. GUI uses system font fallback; offscreen startup tested without both files. |
| Remaining `calpuff_terrain_and_landuse_data_crop/hefei_5km/**` | Small USGS GLCC Eurasia land-use crop, GEN point conversion and crop metadata; 4 files, hashes recorded. The [USGS GLCC archive](https://www.usgs.gov/centers/eros/science/usgs-eros-archive-land-cover-products-global-land-cover-characterization-glcc) describes the global composite as public domain. | Retained with provenance; source raster itself is not included. Local historic paths in crop metadata are preserved for byte identity. |
| `engine/resources/{isd,igra}/**`, NOAA input subsets under `project/cases/**` | NOAA/NCEI station inventories, ISD surface observations, IGRA sounding subsets and project-generated transformations. See [IGRA dataset citation and constraints](https://www.ncei.noaa.gov/access/metadata/landing-page/bin/iso?id=gov.noaa.ncdc:C00975), [NOAA open data policy](https://www.noaa.gov/information-technology/open-data-dissemination), and upstream data-preparation README/capture manifests. | Retained for the exact private research reference cases. Preserve attribution; processed or gap-filled values must not be described as unmodified NOAA observations or NOAA-endorsed results. |
| Frozen model results / `.bin`, `.dat`, `.con`, `.lst` in `native_cpp/**/reference` and `project/cases/**` | Project scientific captures, DGM traces and comparator results. Their source commit, bytes and purpose are recorded in the source manifest and upstream capture documents. They are **data oracles**, not executable build artifacts. | Retained as read-only scientific regression fixtures. This does not establish a general license for future publication of these derived results or underlying inputs. No fresh run outputs are staged. |
| Handwritten `.f` drivers under `native_cpp/**/reference` | Project-authored oracle harnesses that call separately provided original routines; these are not copies of the vendor model package. Original extracted routines are generated locally only. | Retained with tests; vendor source remains external. |
| GDAL, compiler runtimes and Python/Qt dependencies | Installed using system packages and pinned Python requirements, not copied from the old virtual environment. | Not vendored. Their own upstream licenses apply. |

## Restore an authorized local scientific environment

The excluded assets' paths, source Git blob IDs and SHA256 values are stored in
`SOURCE_MANIFEST.json` (`local_dependency_path` and `external_group`). It is the
machine-readable dependency configuration. Nothing here downloads or uploads
restricted assets automatically.

```bash
# Option A: local original repository containing the exact pinned source commit
.venv/bin/python scripts/migration/configure_external_assets.py \
  --source-repo /home/lhy/CTEAS

# Option B: an authorized asset directory with the same original relative paths
.venv/bin/python scripts/migration/configure_external_assets.py \
  --asset-root /path/to/private-assets

# Recheck all external bytes, and reject any external asset accidentally tracked
.venv/bin/python scripts/migration/configure_external_assets.py --check
```

The tool restores the upstream relative paths expected by unmodified CMake,
Python scheduling and scientific harnesses. It refuses hash mismatches and
existing symlinks and does not overwrite differing local files. This preserves
both scientific thresholds and core directory layouts. The original repository
and its Git objects are read-only inputs; no branches or worktrees are changed.
If dependencies are missing, run `--portable` for software checks and record
original-source/terrain-dependent scientific checks as NOT_RUN until restored.

On the migration host these 211 external files are present as ignored local
files with exact upstream hashes. They are **not** Git-tracked files in the new
repository. They must remain excluded from future commits unless a separate,
evidence-backed rights review authorizes submission. Remaining rights questions
concern third-party submission/future distribution, not permission to migrate
the owner's C++20 code or to run authorized local comparisons.
