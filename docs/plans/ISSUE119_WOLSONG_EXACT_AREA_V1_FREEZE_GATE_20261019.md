# Issue #119 — P2-B EXACT_AREA_V1 Wolsong freeze gate (2026-10-19)

## Frozen numerical acceptance already established
Manual [Actions #39236968133](https://github.com/RRain001/CTEAS-next/actions/runs/39236968133), main@487c2e68: verified GSHHG v2.3.7 Full L1, real GLC_FCS30D 2022 b23, 200×200@100m, EPSG:32652 and 40,000-cell LU.DAT. The source GLC210 201,504,180 m² is conserved into USGS52 1,512,532.7412982835 m² + USGS55 199,991,647.2587017 m²; raw fraction sum error <1e-9. 222 cells have BOTH printed f52 and f55 positive.

Status: PASS_SCOPED_REAL_COASTAL_ENGINEERING, not proof that historic GSHHG shoreline is the observed 2022 physical shoreline. The production area method, source TIFF and mapping are frozen; audit code is read-only.

## Remaining exact-area acceptance/freeze gates
1. Independent lightweight PR synthetic tests must pass (no real shoreline science on PR).
2. After merging, only the **user manually dispatches** [Wolsong Issue119 workflow](https://github.com/RRain001/CTEAS-next/actions/workflows/issue119-wolsong-p2b-real-coast.yml) with validation_scope = full_p2b. Do not auto-dispatch science tests.
3. The workflow obtains the SHA-verified official GSHHG ZIP, extracts matching High h L1 sidecars, and independently rechecks **each of the 222 mixed 52/55 cells** by intersecting the actual GLC210 source pixels with Full and High land polygons. Fail closed on source hash, grid/row order, or Full-vs-produced LU.DAT fractions differing by >0.000501 (the LU.DAT three-decimal printing tolerance).
4. Evidence: mixed_52_55_cells.csv with 222 UTM cells and Full/High independent 52/55 areas; mixed_52_55_audit.json with full/high SHA, total land area on the entire 20×20 km domain, and the *within-222-cells-only* 52/55 Full/High sensitivity. Do not label the within-222 comparison as whole-domain sensitivity.
5. 2017-era GSHHG/2022 GLC shoreline age and mapping inconsistency remain an explicit **NOT_INDEPENDENTLY_VERIFIED_2022_SHORELINE** limitation. A 52-labelled landward water sliver may reflect an outdated vector coastline, not a confirmed freshwater lake. Independently observed 2022 coastline reference and predefined tolerance are required before claiming real-world shoreline positional truth.
6. When quantitative results are reviewed, freeze as EXACT_AREA_V1_FROZEN_PASS_SCOPED only with documented conditions and limitations. If Full/High changes are material, extend the quantitative audit before freezing. Do not infer accuracy from conservation.

## Next module (deferred)
[Issue #123](https://github.com/RRain001/CTEAS-next/issues/123): ORIGINAL_SAMPLING faithful CTGPROC native Fortran comparison and coast options. Reuse current P2-A native implementation rather than creating a parallel duplicate. P3 Wolsong original-vs-C++ parity remains #46. Nothing in this PR modifies P2-A, the area kernel, P1, P3, P6 or P7.

## User-approved final decision — 2026-10-19 (supersedes provisional freeze gates above)

The user explicitly accepts the existing Wolsong EXACT_AREA implementation and its scientific scope, **chooses only official GSHHG v2.3.7 Full f L1** for subsequent production processing, and **waives Full-vs-High sensitivity as an acceptance criterion**. Full/High output is retained in [Run #39241482533](https://github.com/RRain001/CTEAS-next/actions/runs/39241482533) as historical transparency, not a failure and not a future blocker. No source geometry is silently substituted by High. The choice is a modelling policy, **not** an observational proof that Full is the 2022 ground-truth shoreline.

**Frozen acceptance verdict:** `P2B_EXACT_AREA_V1_FROZEN_PASS_SCOPED_WOLSONG_2022`.

- Frozen grid: Wolsong, EPSG32652, `XREFKM=533.215`, `YREFKM=3942.629`, `DGRIDKM=0.100`, `NX=NY=200` (40,000 cells).
- Frozen GLC_FCS30D 2022 b23 TIFF SHA256: `2a1a208c5386735692d788066f730c7391e87f0981e7b9ad099442af2e217711`.
- Frozen GSHHG Full f L1 SHP SHA256: `121435427911ea80624802e0f352d777eaf6ba6966ca5f07e687650e95329fd9`; official v2.3.7 ZIP SHA256: `8dbbe7e071e77e9e75f2d639239099ebca8d5c16d6a07df8169729d49f15cf41`.
- Frozen C++ `LU.DAT` SHA256: `3bccf3af99681dce1f31bf25c2085f19bef2e0c2b750c451f6fcf36cd11301b7`.
- Source water area 201,504,180 m² = USGS52 1,512,532.7412982835 m² + USGS55 199,991,647.2587017 m² (floating tolerance); 222 cells with simultaneously printed f52 and f55 positive.
- [Run #39236968133](https://github.com/RRain001/CTEAS-next/actions/runs/39236968133) original end-to-end real P2-B engineering PASS. User manually triggered [Run #39241482533](https://github.com/RRain001/CTEAS-next/actions/runs/39241482533) confirms independent geometry recomputation for all 222 mixed cells, PASS; old Full/High sensitivity statistics archived, intentionally **not used to fail acceptance**.
- Interpretation boundary: `USGS52` = GLC210 water **landward under the selected GSHHG L1 geometry**, not an independently certified freshwater body. `USGS55` = GLC210 water seaward under Full L1; this does not verify real 2022 shoreline accuracy or all spatial regions.
- **Not in this acceptance**: Wolsong original/native P3 MAKEGEO same-input GEO.DAT numerical parity (owned by #46), P1–P7 integrated scientific completion, or original CTGPROC alternative coast/sampling options (separate #123).

Acceptance/freeze is **scoped** to the named sources, bounded grid and documented algorithm, not a claim of universal scientific equivalence or observational coastline truth. Current P2-B area algorithm, data, land/water policy and output file are preserved without modification. #119 can be closed as complete within this scope. This approval explicitly enables the next stage [#123](https://github.com/RRain001/CTEAS-next/issues/123) `ORIGINAL_SAMPLING` development, with no automatic full scientific test dispatch.
