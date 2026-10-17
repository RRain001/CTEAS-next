# P7 CALPUFF: provenance and runtime roles of original CTEAS preprocess/grid

Date: 2026-10-12. Scope: frozen `hefei5km_2022_reference_case_20261011` and selected `METFM=1` dry run. This is an **input audit**, not a numerical-physics acceptance.

## Original CTEAS data flow

```text
project/cases/<case>/case.yaml
       │ preprocess.grid.center, domain, resolution, NZ
       v
engine/preprocess/grid/configure_grid_cmn.py
       ├── project/current/grid/grid.cmn
       │      IMAP, IUTMZN, LSOHEM, DATUM,
       │      XREFKM, YREFKM, DGRIDKM, NX, NY, NZ, ZFACE, XBTZ
       └── project/current/grid/center_location
              longitude, latitude
                      │
                      ▼
engine/run_puff/prepare_puff.py --case ...
       ├── loads grid.cmn
       ├── reads center_location or point_sources in case.yaml
       ├── uses center_location_to_utm.py to project WGS-84 into UTM
       ├── writes GRID metadata in puff.inp at 3 decimal places for origins
       └── writes point-source X/Y in puff.inp at 3 decimal places
                      │
                      ▼
CALPUFF-v7.2.1 runtime (selected METFM=1)
       ├── puff.inp  [authoritative CALPUFF grid, projection, sources, options]
       └── MET.DAT   [authoritative CALMET binary meteorology, grid REAL*4
                     metadata, U/V/W, Z0, ILANDU, ELEV, XLAI etc.]
                      │
                      ▼
puff.con, puff.lst, original QA outputs (qapnts.dat, qarecg.dat, ...)
```

The original scripts **do not pass `grid.cmn` or `center_location` directly to the CALPUFF executable**. They are authoring/provenance inputs used to build `puff.inp`. `GEO.DAT` belongs to the upstream P3/P6 generation chain; in the selected `METFM=1` path P7 reads the meteorological grid/static fields from `MET.DAT`, not `GEO.DAT` as a second geometry authority.

## Frozen 2022 values and coordinate namespaces

| Item | Frozen authoring/runtime role | Selected value |
| --- | --- | --- |
| `center_location` | WGS-84 authoring reference only | 117.141610855° E, 31.939774444° N |
| `grid.cmn` | Preprocessing authoring grid | IMAP=UTM, zone=50N, DATUM=WGS-84 |
| `grid.cmn` | Horizontal / vertical geometry | NX=50, NY=50, NZ=9, DGRIDKM=0.1 km |
| `grid.cmn` | Rounded SW origin | XREFKM=510.885, YREFKM=3531.269 km |
| `puff.inp` | **Actual runtime** projected grid | PMAP=UTM, IUTMZN=50, UTMHEM=N, NX/NY/NZ/DGRIDKM/ZFACE and XORIGKM=510.885, YORIGKM=3531.269 |
| `puff.inp` | **Actual runtime** stack input | X=513.385, 3533.769 km, stack height=70.800 m; `IPTU=8` (Bq/s) |
| `MET.DAT` | **Actual runtime** meteorological grid and fields | CALMET binary 2.1; source of REAL*4 stored origins and spacing |
| `puff.inp` XLATIN/XLONIN | Single-point alternative-met fields, **not** required in this `METFM=1` branch | -999/-999 |
| `qapnts.dat` / `qarecg.dat` | Original-produced **reference outputs**, never runtime inputs | 1 point and 2,500 gridded receptor positions |

The original CTEAS `prepare_puff.py` source-mode rule is not a CALPUFF input requirement: `source_mode=case_yaml` takes the author's point-source `longitude/latitude`, converts it to UTM, then writes a **rounded** `X` source row. `source_mode=center_location` instead uses the center record. The selected frozen 2022 case uses `source_mode=case_yaml` and the same numerical center point.

Do not feed original longitude/latitude or the converter's full-precision GIS result into P7 after reading the frozen `puff.inp`. The text's rounded coordinates are the original executable's input.

## REAL*4 boundary that explains the 2022 QA discrepancy

- Frozen control: YORIGKM=3531.269 and source Y=3533.769 km; `REAL*4(3533.769)` = 3533.76904296875 km.
- The original `qapnts.dat` prints source Y=3533.76929 km. Its `REAL*4` value is 3533.769287109375 km.
- The observed QA frame is reproduced by converting the CALMET origin `3531269.0f * 0.001f` to km **in REAL*4**, forming the source offset relative to the independently parsed control origin, then adding it in REAL*4. The difference from a naive `float(control_source_Y)` is **0.244140625 m**.
- All 2,500 entries in the original `qarecg.dat` match the selected frame with the grid origin's half-cell offset evaluated in REAL*4 **before** adding the REAL*4 integer-index offset. These observations have a standalone oracle test in `p7_grid_preprocess_contract.py` (provenance) and `original_grid_qa_tests.cpp` (observable QA-frame parity).
- These are QA **absolute UTM** coordinates, not the vendor's internal `XPT1GRD/YPT1GRD` (relative meteorological-grid units). The original internal source-state comparison and 1h/6h/143h concentration verification remain separate acceptance gates.

## New fail-closed checks

`cteas_p7_original_grid_preprocess_contract` loads the **frozen** `grid.cmn`, `center_location`, and `puff.inp`. It compares projection, datum, zone/hemisphere, grid extent and dimensions, ZFACE, meteorological input mode and the original rounded point source. It independently reruns the original CTEAS WGS-84 authoring conversion **as a test only**, without supplying recalculated coordinates to the C++ model. Negative test mutations reject origin, zone, dimensions, datum, projection, source coordinates and center drift.

`cteas_p7_original_2022_qa_real4_coordinates` compares the original QA file records with the selected C++ REAL*4 coordinate path. Both are mandatory on the updated dedicated P7 job, and also registered on the opportunistic `[self-hosted,Linux,X64]` fast job.

P7 shall not require the preprocessing grid files when executing an already-generated original `puff.inp` with `MET.DAT`; the provenance check is for **case audit and regression** only. Do not generalize the 2022 UTM50/100m/one-source test to other projections, grids or meteorological modes without their own original-source oracle.
