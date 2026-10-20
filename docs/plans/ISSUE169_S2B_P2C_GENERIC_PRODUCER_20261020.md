# Issue #169 S2-B — P2-C case-driven source-pixel 10×10 sampling

Date: 2026-10-20. This document belongs to [Draft PR #172](https://github.com/RRain001/CTEAS-next/pull/172); it does not close #169 or override the independently accepted #160/#168 science.

## Change boundaries

- **Unchanged**: frozen existing CLI `cteas_p2c_glc30m_sampling inland|wolsong TIFF TIFF_SHA POLICY BLN_OR_DASH NEW_DIR`, historical genuine Hefei/Wolsong data SHA, user-approved modern policy JSON bytes/SHA `a5fa157f57feb1aa160dd96d920a22d267fea78c5828c6040fa95e86536544ed`, original-style 10×10 evenly spaced *source-pixel* subpoint classification, REAL*4 km-grid binning, F6.3 fraction division, `LMARFILL=F`, integer HITS, 38 category order, and original COASTRD BLN/PNPOLY sea test. No P2-B area-intersection revival.
- **S2-B dynamic CLI** accepts legal EPSG 32601–32660 or 32701–32760 and **explicit** `inland` / `coastal`; the raster must already be single-band UTM 30m, north-up, Byte with correct CRS and complete footprint coverage. No reprojection or resampling is performed.
- **Resource boundary unchanged**: source TIFF <=1,500,000 pixels, grid <=250,000 cells, `MESHGLAZ=10`; spacing integer metres in a deliberately limited 1–50,000 m accepted software band. This does not claim original science for every spacing/UTM zone or remove S5 ceilings. Unsupported headers/sources fail closed.
- **Coastal** requires caller-provided BLN **and** verified SHA; polygon domain bound derives from actual grid, not Wolsong constants. No BLN + inland means all GLC210 water remains inland USGS52; coastal IPTYPE determines USGS52/55. BLN source reproducibility from the original Fortran remains a separate provenance/science gate for each new coastal site.

## Explicit native CLI

```sh
cteas_p2c_glc30m_sampling --case-grid \
  inland|coastal SOURCE_2022_30M.TIF SOURCE_SHA256 \
  docs/plans/ISSUE53_GLC35_USGS38_USER_SELECTED_20261019.json \
  UTM_EPSG XREFKM YREFKM NX NY DGRIDKM \
  ORIGINAL_FULL_L1_BLN_OR_DASH BLN_SHA256_OR_DASH NEW_OUTPUT_DIRECTORY
```

`XREFKM/YREFKM` are parsed as exactly three decimal km digits. `UTM_EPSG` is not a location classifier: it must match actual raster CRS. The BLN is optional **only** for explicit inland mode; the coastal flag cannot be silently inferred from a data pixel or a projection zone.

## Shared B-0 case entry

```sh
python3 -m native_cpp.orchestration.p2c_case_producer \
  --case-yaml /independent/case_name/case.yaml \
  --tif /authorized/data/2022-30m-utm.tif \
  --tif-sha256 REAL_SHA256 \
  --policy docs/plans/ISSUE53_GLC35_USGS38_USER_SELECTED_20261019.json \
  --mode inland \
  --native-cpp-bin /verified/native_cpp/cteas_p2c_glc30m_sampling
```

Add `--bln /source/coast.bln --bln-sha256 REAL_SHA256` for coastal sites. The B-0 admission reads the existing `case.yaml`, `grid/grid.cmn`, and `grid/research_time`; records SHA of all three; translates the exact zone, hemisphere, southwest origin, NX/NY, spacing and method; verifies source/policy SHA and output `lu.dat`/`hits.csv` SHA, producer binary SHA, and native manifest dimensions. It writes only under the new staged case `geo/ctgproc/p2c_case/` plus `evidence/p2.json`. The status is **P2C_GENERIC_CASE_PRODUCED_UNVERIFIED** until independent original/source comparison; this is not a P3 science pass and does not authorize replacing raw observations.

The provenance SHA supplied by the case operator establishes **byte identity**, not independent proof of satellite product license, calendar year, spatial relevance, coastline origin, or science equivalence. Case/sample product metadata and its licensed provenance remain S3 source acquisition's responsibility.

## Validation matrix and exact status

| Gate | Evidence | Truth boundary |
| --- | --- | --- |
| Old core frozen Hefei & Wolsong original source | Existing #160 200×200×38 exact integer HITS/F6.3/Missing independent report; automatically re-triggered on core/CLI PR changes | Exact zero differences on those existing frozen sites only |
| Dynamic core software | Unit test adds alternate 32649, 60 m, 1×1 raster, exact 400 forest votes and source-CRS failure | Validates method parameterization, not real site science |
| Dynamic UTM header | Explicit 49S `LU.DAT v2.1` software test, malformed zone rejection | South-header formatting only, not southern real raster original equivalence |
| B-0 native invocation | New dedicated Actions runs real compiled CLI on **synthetic, real-format** 4×3 GeoTIFF and cross-year YAML/grid/time with SHA attestation and fail-closed negatives | Real executable/software handshake, original Fortran NOT_RUN |
| Real Hefei C++ legacy vs case CLI | True pinned 2022 Hefei TIFF, old 200×200 vs new exact same case; byte equality on both `lu.dat` and `hits.csv`; 90×100 alternate geometry against same source with manifest/conservation | Old science unchanged; **new alternate grid produced, independent original parity NOT_RUN** |
| Real Wolsong C++ legacy vs case CLI | Genuine original COASTRD BLN SHA, 2022 TIFF SHA, both CLI modes `lu.dat`/`hits.csv` byte identical | Same-source old science unchanged; not a second independent coastal site's science |
| P2-A & P3 | P2-A original GLCC existing generic CLI preserved; #46 owns P3 real same-grid adapter/original GEO science | Neither accepted solely by P2-C PR |

**After PR acceptance:** finish P2-A B-0 adapter as a separate minimal PR and independently verify any new source/grid original parity needed for `PASS_GENERIC_MODULE`. Only #42 S3 can authorize a full new-site real five-product stack.

**Docker** AMD64/ARM64 full image build, P7 gitless source-SHA provenance, and final packaging verification are deferred until all other development Issues close; they are not required to merge this PR, and are **not** PASS.
