# P6 Mode A — CALMET original met.inp station input and upstream interface audit

Date: 2026-10-12. Scoped case:
`project/cases/hefei5km_2022_reference_case_20261011`, UTM 50N/WGS-84,
50×50×9 @ 100 m, one surface and one upper-air station.

## Evidence hierarchy

1. **Authority for P6 station location:** `run/met/met.inp` Group 7 `SS1` and Group 8 `US1`, containing absolute UTM km.
2. **Original physics authority:** unchanged CALMET 6.5.0 L150223
   `engine/vendor/src/CALMET_v6.5.0_L150223/calmet.for`
   Git blob `437f43bb7f0e51a1919e56664663e1a046986ed0`.
3. **Upstream source/metadata:** P4 `UP.DAT + stations.csv`, P5
   `SURF.DAT + stations.csv`. CSV latitude/longitude are NOT substituted
   for original CALMET station locations or station-physics latitude.
4. **Grid geometry:** P3 `GEO.DAT` plus `grid.cmn`, reconciled with P6
   `XORIGKM/YORIGKM, NX/NY, IUTMZN, DGRIDKM`.

Original `calmet.for` source anchors:
- L25882–25912: read Group 7 original station record into `XSSTA/YSSTA`.
- L25926–25952: read Group 8 original station record into `XUSTA/YUSTA`.
- L27053–27070: `GLOBE` derives station geographic latitude from **UTM km** before local-metre conversion.
- L27073–27076: `DGRID = 1000.*DGRIDKM`, `XORIGR = 1000.*XORIGKM`, `YORIGR = 1000.*YORIGKM`.
- L27128–27133: surface `XKM=XSSTA(I)`; `XSSTA(I)=1000.*XKM-XORIGR` and Y counterpart.
- L27183–27188: corresponding upper-air conversion.
- L5123–5145: DIAGI station-grid and `UTMXST=0.001*XSSTA` mapping.

**Critical order:** evaluating `1000.f*(xkm-xorigkm)` is NOT the original operation.
The source evaluates `(1000.f*xkm)-(1000.f*xorigkm)`, with every
intermediate held in single precision (REAL*4). The P6 implementation and
its selected-source oracle preserve this order.

## Original CTEAS grid generation is upstream of every P1–P6 grid

The original `engine/preprocess/grid/configure_grid_cmn.py` is the
authoritative **grid construction step** for this workflow. It reads
`project/cases/.../case.yaml` (`preprocess.grid.center`,
`domain.length_km/width_km`, `resolution_km`, `nz`) and publishes:

- `grid/center_location`: original requested geographic centre (lon/lat).
- `grid/grid.cmn`: UTM zone/hemisphere, **XREFKM/YREFKM rounded to 0.001 km**,
  NX/NY, spacing, NZ/ZFACE, with XREF/YREF identifying the SW origin.
- `grid/research_time`: research interval, separately consumed downstream.

Propagation of the published **numerical** grid:

```text
case.yaml (user request, geographic centre + domain)
    └─ engine/preprocess/grid/configure_grid_cmn.py
         ├─ grid/center_location (requested lon/lat, metadata and station selection)
         ├─ grid/grid.cmn (published UTM geometry)
         │    ├─ P1 TERREL:  terrel.inp  (IGRID=1, cell 1,1 SW CORNER)
         │    ├─ P2 CTGPROC: ctgproc.inp
         │    ├─ P3 MAKEGEO: makegeo.inp → GEO.DAT
         │    └─ prepare_met.py → met.inp XORIGKM/YORIGKM, NX/NY/ZFACE
         └─ grid/research_time → model interval controls

P4/P5 effective stations.csv (metadata) ── prepare_met.py
                                              └─ met.inp SS1/US1 UTM km
                                                   └─ P6 CALMET Mode A
```

**Do not identify `case.yaml` geographic centre with the rounded model-grid
centre**, and do not use it as a P6 station-position replacement. In the frozen
Hefei case, the original grid-generator's projected requested centre is about
`(513.3846439571, 3533.7689270075) km`, while the published grid centre is
`(513.385, 3533.769) km`: an east/north shift of about
`(+0.356043, +0.072993) m` caused by publishing XREF/YREF to 3 decimals.
This is not a new physical error; it is the original upstream rounding.
P6 must use the already-published geometry without reversing this rounding.

`p6_modea_original_grid_generator_to_metinp` is the non-mutating regression
gate checking case.yaml → center_location → original generator arithmetic →
grid.cmn → P1/P2/P3 input decks (including TERREL `IGRID=1`) →
GEO.DAT → met.inp; it checks ZFACE, grid origin, projection and spacing too.
A future policy to use a more precise grid origin would require a separately
versioned mode and regenerating **all** downstream original reference files;
it must not silently change the frozen P6 Mode A case.

## Frozen reference coordinates

| Record | UTM x km | UTM y km | local x m (REAL*4) | local y m (REAL*4) |
|---|---:|---:|---:|---:|
| grid origin | 510.885 | 3531.269 | 0 | 0 |
| SS1 / 583210 | 513.385 | 3533.769 | 2500 | 2500 |
| US1 / 58424 | 513.384 | 3533.772 | 2498.96875 | 2503 |

Reference decimal literals above are input-file display values.
The local-metre numbers are pinned to original READCF REAL*4 evaluation, not
a geometric approximation using the CSV longitude/latitude.

## Minimal-fix scope and disposition

| Stage/interface | Disposition | Gate |
|---|---|---|
| P1 TERREL, P2 CTGPROC | Scientific kernels unmodified; existing scoped Fortran comparison remains the prior evidence | No general recalculation required because no SS/US dependency |
| P3 MAKEGEO | Scientific kernel unmodified; GEO grid origin, zone and spacing checked against grid.cmn/met.inp | `p6d_p3_p4_p5_metinp_station_contract` |
| P4 READ62 | UP.DAT scientific calculation unmodified; verify effective station ID, met.inp US1, file ID | cross-stage input contract |
| P5 SMERGE | SURF.DAT scientific calculation unmodified; verify station ID, effective SS1, station identity | cross-stage input contract |
| P6D real-case driver | Removed case-centre/equirectangular projection; accepts SS1/US1 as only authoritative P6 station locations; COORDLIB inverse for station latitude | CTest + original Fortran source comparator |
| P6D INTER2/WIND1/DIAGI | Downstream station geometry receives REAL*4 local metres; original station weighting and U/V/W must be rerun | P6D/6G complete original numeric comparison |
| P6E/P6F/P6G | Existing field writer/consumer algorithms remain unmodified | Re-run the 143-hour P6D→P6F→P6E frozen-reference comparison |

### Additional input-semantic observations

- The real-case driver used to silently substitute numeric defaults for
  controls declared non-default in met.inp. Required grid and diagnostic
  distances now fail closed if absent.
- `LVARY=F/T` is a Fortran logical control; parsing it as numeric (default
  false) would silently discard `LVARY=T`. Mode A now parses T/F explicitly.
- Selected isolated P6A–P6C numerical-kernel parity **does not imply**
  actual-case P6D full-field parity.
- Optional original defaults (e.g., `IEXTRP, ICALM, CRITFN, RMIN`) retain
  explicit compatible defaults.
- This audit covers the scoped actual-case P6D station path. A complete
  P6A–P6G control-by-control survey, including every P6E and P6F option and
  unsupported CALMET feature branch, remains **NOT_CERTIFIED**.

## CI gates and status interpretation

The dedicated self-hosted `.github/workflows/p6-modea-station-contract.yml`
runs four CTest gates including a literal unchanged Fortran source oracle and
the actual 143-hour producer, then reruns
`scripts/run_p6_end_to_end.py` for the full P6D/P6F/P6E frozen-reference
U/V/W comparison.

Prior real-case equivalence numbers were obtained from a different coordinate
path. They must **not** be carried forward into new PASS evidence.

**Before completed CI runs:** implementation submitted for review;
`P6D_FULL=NOT_PASS`, `P6E_FULL=NOT_PASS`, `P6_CALPUFF_READY=FALSE`.
The full-field gate is determined by measured original vs new U/V/W
differences, not by a successful build or the output-file writer alone.
