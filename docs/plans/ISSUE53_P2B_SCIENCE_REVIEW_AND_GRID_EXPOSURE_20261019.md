# Issue #53 / P2-B: model-grid scientific mapping decision ledger

2026-10-19. **Status: P2_MAPPING_REVIEW_REQUIRED**. P2-A 1km historical GLCC is `PASS_SCOPED` for Hefei and Tokyo original-same-source cases; that result **does not transfer** to P2-B, whose source taxonomy, year and area sampling differ.

## Reviewed primary taxonomy authorities

- Zhang et al. (2024), **GLC_FCS30D**, ESSD 16, 1353–1381, §3.1 Table 1: https://doi.org/10.5194/essd-16-1353-2024 . The class system is 35 fine classes inherited from GLC_FCS30-2020 and GWL_FCS30; source class 52 is **open evergreen broadleaved forest**, not water.
- Anderson et al. (1976), **USGS Land Use and Land Cover Classification**, Professional Paper 964: https://pubs.usgs.gov/publication/pp964 . Relevant distinct historical Level-II codes include USGS 16 mixed urban, 21 cropland/pasture, 41 deciduous forest, 42 evergreen forest, 51 streams/canals, 52 lakes, 53 reservoirs, 54 bays/estuaries, 61 forested wetlands and 62 nonforested wetlands.
- Separate GWL-FCS30 wetland type definitions (contemporaneous detailed study): https://isprs-annals.copernicus.org/articles/X-2-2024/137/2024/isprs-annals-X-2-2024-137-2024.pdf . **Flooded flat** is *non-vegetated* flooded ground along rivers/lakes. It is not universally nonforested vegetated wetlands (USGS 62); saline/tidal wetland status cannot be inferred from `GLC 183` alone.
- Source license/version/reprojection and real buffered histogram: `data/landcover/glc_fcs30d/v1_2022/hefei/metadata.json` + `ATTRIBUTION.md`, 6168-byte 2022 172×172 UTM50N TIFF, SHA256 `340d224d961c88637363be9616302bdf6b955b4921144edc814b875ef9798473`. The cached TIFF is a 5km Hefei site extract only; it is **not a globally usable input**.

No source above publishes or approves the entire **GLC_FCS30D 35 → historical USGS92 Level-II 38** crosswalk for CTGPROC/MAKEGEO. Candidate taxonomy similarity cannot prove that target albedo/roughness/Bowen/soil-heat/vegetation parameters in #46 are physically unchanged.

## 12 actually present in source TIFF; decision by class

The underlying full 35-class unapproved proposal is
`docs/plans/ISSUE53_GLC35_USGS92_REVIEW_CANDIDATES_20261018.json`.
Buffered-TIFF counts here are **not** model-grid weighted coverage.

| GLC code | Buffered pixels | Candidate target (USGS-92) | Review tier | Condition before approved P2→P3 |
| --- | ---: | --- | --- | --- |
| 10 rainfed cropland | 3413 | 21 | candidate | Explicitly accept loss of rainfed attribute |
| 11 herbaceous cropland | 376 | 21 | candidate | Confirm farm vs natural grass distinction |
| 20 irrigated cropland | 21814 | 21 | candidate | Preserve irrigation attribute in raw evidence |
| 52 open evergreen broadleaf | 298 | 42 | candidate | Evergreen forest; record canopy-open information loss |
| 62 open deciduous broadleaf | 74 | 41 | candidate | Deciduous forest; record canopy-open information loss |
| 72 open evergreen needleleaf | 1 | 42 | candidate | Retain the actual one-pixel area if it intersects model grid |
| 130 natural grassland | 142 | 31 | candidate | Grassland vs cultivated pasture may require plot audit |
| 182 freshwater marsh | 238 | 62 | site_evidence | Verify nonforested emergent wetland vs seasonally open water |
| 183 flooded flat | 17 | **NO APPROVED TARGET** | blocked | Wetland vs transient flood vs bare ground needs site water/land evidence |
| 190 impervious surfaces | 2809 | 16 | site_evidence | Mixed urban land is a proxy; check land-use mix and parameter sensitivity |
| 200 bare areas | 9 | 77 | site_evidence | Mixed barren proxy; distinguish rock/sand/construction if consequential |
| 210 water body | 393 | **NO APPROVED TARGET** | blocked | Separate USGS 51 stream/canal, 52 lake, 53 reservoir or 54 estuary using site water polygon/type evidence; never assume all lake |

The other 23 legal GLC classes retain their current candidates and `blocked` status, even if absent in the buffered source raster. If a new research area contains any class without an approved policy, reject formal mapping rather than silently making it land/water/0.

## Measured 2022 Hefei *actual-model-grid* 25 km² impact

The fully offline real-GeoTIFF review run
[#39195597645](https://github.com/RRain001/CTEAS-next/actions/runs/39195597645)
completed `SUCCESS` using the committed SHA-verified 6168B dataset and
native C++ exact-area D2 source; 13 software/negative tests and real
2,500-cell audit passed. Genuine SHA-bound evidence:
[artifact #12162011795](https://github.com/RRain001/CTEAS-next/actions/runs/39195597645/artifacts/12162011795).

The review percentages below refer strictly to the **25,000,000 m² model
domain**, NOT the 172×172 buffered TIFF pixel counts:

| Review tier | Grid area (m²) | Fraction | Affected model cells |
| --- | ---: | ---: | ---: |
| Candidate-only, still not approved | 22,050,905 | 88.20362% | not a stand-alone sign-off |
| Needs independent site evidence | 2,593,655 | 10.37462% | 990 |
| Scientifically blocked with no USGS Level-II subtype | 355,440 | 1.42176% | 211 |
| Total | 25,000,000 | 100% | 2,500 cells total |

**Exact per-source-class intersected areas** (m²), full raw fraction
preserved (no reclassification or rounding away):

| GLC code | Model-grid m² | Mapping tier | Proposed USGS Level-II |
| --- | ---: | --- | --- |
| 10 | 2,873,205 | candidate | 21 |
| 11 | 313,230 | candidate | 21 |
| 20 | 18,451,190 | candidate | 21 |
| 52 | 228,480 | candidate | 42 |
| 62 | 61,350 | candidate | 41 |
| 72 | 900 | candidate | 42 |
| 130 | 122,550 | candidate | 31 |
| 182 | 196,350 | site_evidence | 62 (conditional) |
| 183 | 15,300 | blocked | NONE |
| 190 | 2,389,205 | site_evidence | 16 (conditional) |
| 200 | 8,100 | site_evidence | 77 (conditional) |
| 210 | 340,140 | blocked | NONE |

The critical source-coverage result is not that the ambiguous classes
are “small”: **211/2,500 grid cells contain blocked categories**,
and **990/2,500 require site evidence**, not necessarily disjoint.
USGS51 streams, 52 lakes, 53 reservoirs, 54 estuaries cannot be assigned
from GLC210 without verified local hydrography. GLC183 covers 15,300m²
of non-vegetated flooded flat; choosing USGS62 or a water class as an
universal fallback is physically unjustified. GLC190 occupies 9.557%
of domain; treating all as USGS16 mixed urban may significantly change
#46 surface roughness/energy terms and needs site/parameter sensitivity
checks before approval.

**Scientific status remains P2_MAPPING_REVIEW_REQUIRED.** Any
`p2_usgs92_candidate_only_NOT_APPROVED.csv` is a partial audit view
that does not sum to 1 in affected cells; must not feed P3 or masquerade
as approved `LU.DAT`.

## Deliverable and stop-line in this PR

The **already existing C++ D2** computes exact 30m→model-cell rectangle-overlap areas; it writes `p2_raw_fractions.csv`, `p2_raw_class_area_m2.csv`, and `p2_manifest.json` with unapproved source status. D2 is **not** rewritten here.

The new independent `scripts/s2g/audit_glc_modelgrid_crosswalk.py` directly consumes these two real D2 files. It SHA-binds the input TIFF and unapproved 35-class proposal, independently checks **all model-grid cells** (areas, code order, 35-way conservation, fraction/area consistency, coverage, category code) and reports:
- `review.json`: true 5km **25,000,000 m²** model area; per-GLC-class actual model-area totals and affected-cell counts; per-tier candidate/site-evidence/blocked area and fractions; first 30 affected cell coordinates/categories; hashes of D2 CSV/proposal.
- `p2_usgs92_candidate_only_NOT_APPROVED.csv`: 38 historical USGS fields only for **candidate tier**, plus separate per-cell `site_evidence_fraction` and `unmapped_blocked_fraction`. This is explicitly **not a normalized 38-category mapping**; totals <1 when unresolved classes are present. Never rename or serialize it as historical `LU.DAT`.

The difference between **buffered 172x172 source pixel histogram** and **actual model-grid area** is critical. Code 183 and 210 may have different site impact than their raw buffered counts suggest. Prioritize review using model cells affected and percentage of 25 km², not raw source pixel count.

**No source-only or synthetic check can grant mapping approval.** No approved USGS92 LU.DAT is generated and #46/P3 is NOT_RUN. Proposed sign-off criteria before P2-B D3: independent review of source legend and 35→38 mapping; site evidence for 182/183/190/200/210; explain affected model-cell fraction and parameter impacts; versioned approved decision matrix and SHA; negative tests to forbid missing/ambiguous classes; only then implement SHA-gated `LU.DAT v2.1` serialization with uniform P2/P3 contract, format tests and genuine offline site-scoped acceptance. Do not begin unrelated P3 refactors here.
