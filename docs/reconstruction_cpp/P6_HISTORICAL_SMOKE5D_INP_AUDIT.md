# P6 historical P1–P7 control reference audit: `smoke5d_coldstart_20260701`

Date: 2026-10-10. Classification: **HISTORICAL_INPUT_CONTROL_REFERENCE_ONLY / LEGACY_METEOROLOGY_NOT_GOLDEN**.

## Provenance and study boundary

User supplied the complete old project at [`project/cases/smoke5d_coldstart_20260701`](https://github.com/RRain001/CTEAS/tree/2908293f061af93e754bc9fe1f00d857d1d6a0d8/project/cases/smoke5d_coldstart_20260701), newly present on `main` commit `2908293f061af93e754bc9fe1f00d857d1d6a0d8`. Original case was processed through P1–P7 and includes `*.inp`, historical `geo.dat`, `surf.dat`, `up_58203.dat`, `met.dat`, `puff.con` and logs. **The user explicitly reports errors in the previous meteorological preprocessing and states that current scripts produce different meteorology.** Consequently:

1. Reuse `*.inp` **as candidate physics option and file-interface examples**, not authoritative 2022 inputs or exact-control templates. Never use historical `SURF.DAT`, `UP.DAT`, `MET.DAT`, `MET.DAT.AUX`, `PUFF.CON` or listed concentration/meteorological values as scientific golden data for the new P6.
2. Preserve the old case unchanged; do not silently swap old/new sources into the same run or create patched copies within `project/cases/`. P6 new inputs/controls must be freshly generated in a separately named reproducible work directory, with explicit script version/sha and weather data hashes.
3. The `20260701` suffix labels the snapshot/case name, **not** the simulation year. Actual controls are January **2023**, not January 2026 or 2022.
4. This record documents inspected text files, **not** a new original CALMET rerun, P4/P5 reprocessing, meteorological numerical validation, or CALPUFF verification.

### Fundamental differences: do not blindly copy history

| Property | historical `smoke5d_coldstart_20260701` | scoped modern Hefei 100 m |
|---|---|---|
| Center | 117.0°E, 32.0°N; `grid/center_location` | Stack 117.141610855°E, 31.939774444°N |
| Horizontal extent and spacing | **50 km × 50 km**, 50×50 at **1 km** | **5 km × 5 km**, 50×50 at **0.1 km** |
| Grid SW corner `XORIGKM,YORIGKM` | `475.000,3515.436` km | modern reference based on target stack/100 m original controls; NOT `475.000,3515.436` |
| Time | 2023-01-01 00:00 through 2023-01-05 23:00 UTC (120 *nominal labels*) | 2022-01-01 00:00 through 2022-01-06 23:00 UTC (144 *nominal labels* pending original hour semantics) |
| Vertical | same 9 layers / 10 `ZFACE`s `[0,20,40,80,160,320,640,1200,2000,3000]` metres | same target ZFACE design, subject to original CALMET layer-center interpretation |
| Terrain source | two full `srtm_59_06.tif`, `srtm_60_06.tif` GeoTIFF tiles | single cropped 90×77 WGS84 GeoTIFF |
| Landuse source | `GLAZAS` binary `eausgs2_0la.img` | `GENERIC.LANDUSE 1.0` / ESR-S point dataset, 38 input categories |
| Meteorology | old manually processed ISD/IGRA 2023, acknowledged faulty by user | forthcoming 2022 processing from current P4/P5 scripts; sources/QC not frozen |

**Input authority distinction:** historical `grid/grid.cmn` has valid 50×50/1km/`475.000,3515.436`, but individual historical P1/P2/P3 `*.inp` also contain **100×100 and `XREFKM=123.456,YREFKM=4567.891` template defaults**. The actual historical `geo/makegeo/geo.dat` header confirms **50×50, 1km, 475.000/3515.436**, thus a valid frozen case must reconcile `grid.cmn`, control groups, and *actual output headers*, rather than assuming any single commented template field is execution authority. Do not reuse the historical placeholder entries in modern P6.

## P1–P7 input control census

| Stage | Historical control file | Observed original-option evidence | Modern action |
|---|---|---|---|
| P1 TERREL | [`geo/terrel/terrel.inp`](https://github.com/RRain001/CTEAS/blob/2908293f061af93e754bc9fe1f00d857d1d6a0d8/project/cases/smoke5d_coldstart_20260701/geo/terrel/terrel.inp) (Git blob `5dfa5994bd04cb6706d8ff90c7a66ad3c54025cc`) | `NTDF=2`, two `GEOTIFF` files, `LPREV=F`, `LCOAST=F`, `LVOIDFIL=F`, `IMODEL=1`, `IGRID=1`; UTM50N/WGS84. | Only retain standard Cartesian mean terrain, no legacy multi-tile dependency. |
| P2 CTGPROC | [`geo/ctgproc/ctgproc.inp`](https://github.com/RRain001/CTEAS/blob/2908293f061af93e754bc9fe1f00d857d1d6a0d8/project/cases/smoke5d_coldstart_20260701/geo/ctgproc/ctgproc.inp) (Git blob `ff5d1612c69d405b0c3e4bc1952e9506d5bbcfca`) | `NDBF=1`, `GLAZAS=...eausgs2_0la.img`, `LFINAL=T`, `LPREV=F`, `LCOAST=F`, `LSNOW=F`. | Modern P2 used GEN input; retain only generalized landuse fractions, **not** historical GLAZAS parser/source. |
| P3 MAKEGEO | [`geo/makegeo/makegeo.inp`](https://github.com/RRain001/CTEAS/blob/2908293f061af93e754bc9fe1f00d857d1d6a0d8/project/cases/smoke5d_coldstart_20260701/geo/makegeo/makegeo.inp) (Git blob `49fec849e965d4f717a2995975e752380fa74761`) | `LTERR=T`, `LLU2=F`, `LSNOW=F`, `NINCAT=38`, `NOUTCAT=14`, `NUMWAT=5`, `NSPLIT=0`, `CFRACT=0.5`, `FLUMIN=0.96`, `GEODAT=geo.dat`. | Compatible physics/control *mode* with P3 minimal path; old `geo.dat` is geometry- and data-specific, not the new golden source. |
| P4 READ62 | [`run/read62/read62.inp`](https://github.com/RRain001/CTEAS/blob/2908293f061af93e754bc9fe1f00d857d1d6a0d8/project/cases/smoke5d_coldstart_20260701/run/read62/read62.inp) (Git blob `9af8d098484979f2d28adeee2279c90a0da3a1ef`) | 2023 *full-year* archive, `JDAT=2` FSL, `IFMT=1`, `PSTOP=500 hPa`, `ISUB=0`, `LXTOP=LXSFC=F`; old station `58203`. | Upstream new script station/year selection and actual validated `UP.DAT` must replace the old archive. Preserve IFMT choice only after reader compatibility proven. |
| P5 SMERGE | [`run/smerge/smerge.inp`](https://github.com/RRain001/CTEAS/blob/2908293f061af93e754bc9fe1f00d857d1d6a0d8/project/cases/smoke5d_coldstart_20260701/run/smerge/smerge.inp) (Git blob `09ad54f4b6a57943485a950a8f93ae8421c1d53e`) | `JDAT=8` GENERIC, `IOFORM=2` formatted `surf.dat`, `IOPACK=0`, `ASTZ=ABTZ=UTC+0000`, `LPCALC=F`, 2023-01-01..05, `NFF=1`, station `58321`. | Keep file format/time-control example. **Do not use historical filled meteorology;** compare newly generated data to independent original P5. |
| P6 CALMET | [`run/met/met.inp`](https://github.com/RRain001/CTEAS/blob/2908293f061af93e754bc9fe1f00d857d1d6a0d8/project/cases/smoke5d_coldstart_20260701/run/met/met.inp) (Git blob `7d4758d9a4ff36f8165b9da3c721d9b3f9f2ca66`) | Detailed active setup in next section. | **Primary historical configuration reference for P6**; preserve on/off model logic where scientifically selected, replace date/geometry/files/station selection. |
| P7 CALPUFF | [`run/puff/puff.inp`](https://github.com/RRain001/CTEAS/blob/2908293f061af93e754bc9fe1f00d857d1d6a0d8/project/cases/smoke5d_coldstart_20260701/run/puff/puff.inp) (Git blob `67dcdb856c0af92d30de346d4877af3b7d80db6f`) | `METFM=1`, `NSECDT=3600`, 2023-01-01..05, `MCHEM=0`, **`MWET=0`**, `MDRY=1`, `NPT1=1`, `NPT2=0`, `NSPEC=2`, `NSE=1`. | Interface reference only; if future wet deposition is needed, **do not adopt MWET=0**. Old emission rates/source settings are not the user's latest research case. |

## P6 historical CALMET modes from the actual `run/met/met.inp`

These are factual observations of the old `*.inp` values, not instructions to copy them uncritically.

### Input schema and output
- Group 0: `GEODAT=../../geo/makegeo/geo.dat`; `SRFDAT=../../met/surface/final/surf.dat`; `UPDAT=../../met/upperair/final/up_58203.dat`; `METDAT=met.dat`, `METLST=met.lst`. `NUSTA=1`, `NOWSTA=0`, `NM3D=0`, `NIGF=0`.
- Group 1: 2023-01-01 00:00→2023-01-05 23:00, `ABTZ=UTC+0000`, `NSECDT=3600`, `IRTYPE=1`, `LCALGRD=T`, `ITEST=2`, `MREG=0`.
- Group 2: `PMAP=UTM`, `IUTMZN=50`, `UTMHEM=N`, `DATUM=WGS-84`, `XORIGKM=475.000`, `YORIGKM=3515.436`, `NX=50`, `NY=50`, `DGRIDKM=1`, `NZ=9`, `ZFACE=0,20,40,80,160,320,640,1200,2000,3000`. **Replace old lower-left origin, resolution and dates for modern case.**
- Group 3: `LSAVE=T`, `IFORMO=1`, `LPRINT=F`; historical `met.dat` and `met.dat.aux` exist. Preserve output record semantics from original binary/file reader validation, not byte-identity against the faulty old weather output.
- Group 4: `NOOBS=0`, `NSSTA=1`, `NPSTA=0`, `ICLOUD=0`, `IFORMS=2` formatted SURF, `IFORMP=2`, `IFORMC=2`. NOOBS=0 means observed station pathway, not prognostic-only.

### Selected wind-field physics (Group 5)
| Control | Historical setting | Interpretation for C++ P6 |
|---|---|---|
| `IWFCOD` | 1 | Diagnostic wind field: core selected pathway. |
| `IFRADJ` | 1 | Froude/blocking adjustment enabled: implement/verify in P6D. |
| `ISLOPE` | 1 | Slope-flow effect enabled: implement/verify in P6D. |
| `IKINE` / `IOBR` | 0 / 0 | Kinematic/O'Brien pathways off **for history**, still document/guard when selected control frozen. |
| `IEXTRP` / `ICALM` | -4 / 0 | Similarity-law station wind vertical extrapolation; do not extrapolate calm observations through unsupported logic. |
| `BIAS` | 9×0 | No preference for surface/upper station in original per-layer bias. |
| `IPROG` / `IGFMET` | 0 / 0 | No MM5/3D or coarse-CALMET first guess; proposed minimal observed route. |
| `LVARY` / `RMAX1,RMAX2,RMAX3` | F / 100,200,200 km | Observation influence radii extend **well beyond modern 5 km box**. Stations do not need to lie inside domain; require verified coordinates and representativeness. |
| `RMIN` / `TERRAD` / `R1` / `R2` | 0.1 / 15 / 50 / 100 km | Inverse distance/first guess and terrain influence radii, **not** 0.1 km `DGRIDKM` by coincidence. |
| `DIVLIM` / `NITER` | 5e-6 / 50 | Divergence minimization convergence, frozen reference tolerances needed. |
| `NSMTH` / `NINTR2` | 2,4,...,4 / 9×99 | Layer smoothing and max weighted stations; single-station case is still meaningful. |
| `CRITFN` / `ALPHA` | 1 / 0.1 | Blocking and kinematic coefficients; not tuning knobs to force a match. |
| `NBAR` / `LLBREZE` | 0 / F | No explicitly specified barriers or lake breeze boxes. |
| `IDIOPT1..5` | 0 / 0 / 0 / 0 / 0 | Original observed-input options. |
| `ISURFT`, `IUPT`, `IUPWND` | -1, -1, -1 | **Selection logic must be source-verified**; negative is not a verified station ID. |

### Surface physics, mixing layer and precipitation (Group 6)
- `IRHPROG=0`, `ITPROG=0`; observed humidity/temperature pathways.
- `IMIXH=1`, `IAVEZI=1`, `MNMDAV=1`, `HAFANG=30`, `ILEVZI=1`, `IZICRLX=1`, `TZICRLX=800`, `ZIMIN=50`, `ZIMAX=3000`, `CONSTB=1.41`, `CONSTE=0.15`, `CONSTN=2400`, `FCORIOL=1e-4`. Selected mixing-height routines must match source and new case observations.
- `IRAD=1`, `TRADKM=500 km`, `NUMTS=5`, `IAVET=1`, `TGDEFB=-0.0098`, `TGDEFA=-0.0045`.
- `NFLAGP=2`, `SIGMAP=100 km`, `CUTP=0.01 mm/h`. **But `NPSTA=0`; this old project has no explicit `PRECIP.DAT` enabled in P6 Group 0.** Therefore these numeric precipitation-interpolation options do not establish valid rainfall forcing.

### Station inventory, masks and source-data warnings
- P6 station `SS1='LUOG' 58321, X=497.827km, Y=3539.106km, TZ=0, anemometer 10.0m`, old surface catalogue `31.988°N,116.977°E,63m`. New study may use stations outside the 5 km grid; no artificial station-inside-domain requirement.
- P6 upper `US1='FUYA' 58203, X=500.000km, Y=3540.436km, TZ=0`, upper catalogue `32.0°N,117.0°E,33m`; `READ62.PSTOP=500hPa`, and `UP.DAT` remains historical/suspect.
- `run/smerge/smerge.lst` reports `NTOTAL=119`, missing sky cover 41/119 (cloud coverage **65.5% valid**), and valid precipitation-code count **0/119**. The old source `met/surface/isd2smerge_ready/583210-99999.csv` uses `9999` as precipitation missing in the inspected rows. **Missing precipitation is NOT zero precipitation.**
- Historical `run/met/met_runtime.log` shows **119** `+Processing ...` lines, from Jan 1 hour 0 to Jan 5 hour 22 ending at Jan 5 hour 23; `run/smerge/smerge.lst` likewise says 119 input records. The input date range contains **120 nominal clock labels**. Do **not** assert a lost hour or correct record count without a separate audit of hour-start/hours-ending conventions and binary record header timestamps.
- Logs report warnings in `run/met/met_runtime.log` and `run/puff/puff_runtime.log`; their existence is additional reason to audit, not automatically evidence of fatal failure. The historical program reached termination and saved outputs, but successful termination does not establish meteorological validity.

## Reuse decision and P6 follow-up gates

1. **Immediately reusable as candidate controls:** `NOOBS=0`, `IWFCOD=1`, `IRTYPE=1`, `IFRADJ=1`, `ISLOPE=1`, `IEXTRP=-4`, `IPROG=0`, `IRHPROG=ITPROG=0`, `IFORMS=2`, `IFORMO=1`, `ZFACE`, all original interpolation/smoothing/divergence and stability controls. Freeze only after verifying chosen scope/new stations in P6B.
2. **Must be replaced:** real-case date/time 2023→2022; domain `DGRIDKM=1` and origin; MET file paths and versioned source hash; station IDs/coords, actual availability; surface and upper-air gap/QA treatment; P7 emission/source/met combination. P1/P2 source types differ (GLAZAS vs GEN).
3. **Wet deposition blocker:** the old surface source has *no valid precip code* and old P7 `MWET=0`. For new HTO wet deposition scenario, explicitly select/validate precipitation stations or other verified CALMET precipitation source and enable/validate wet deposition *at P7*, independently of dry deposition. Do not fabricate rain, replace missing with 0, or infer precip from `NPSTA=0`.
4. **P4/P5 parallel ownership:** their agents control their own modern upstream scripts/readers; P6 only imports immutable verified outputs or explicitly versioned adapters. This historical snapshot is **not** permission to rewrite P4/P5 branches or substitute old weather.
5. **P6B reference capture:** produce new 2022 `calmet.inp` in a fresh workdir; immutable `GEO.DAT`, `UP*.DAT`, `SURF.DAT`, precipitation input + full hashes. Independently compile/run original CALMET on the new identical modern-input data, and only then compare 1 h→6 h→144 h P6 C++ outputs. Original vs C++ parity means same input/control versions, not history vs new input.
6. **Optional historical dry-run for diagnostics:** old snapshot may be used to inspect file headers, station metadata, binary layout and hour records without treating any old meteorological value or modeled concentration as correct.

Current conclusion: `P6_HISTORICAL_CONTROL_MAP = CAPTURED`, `LEGACY_MET_RESULT_GOLDEN = FALSE`, `CURRENT_2022_P6_REFERENCE = BLOCKED_FOR_VALIDATED_MET_INPUT`, `P6_PHYSICS_PARITY = NOT_TESTED`.
