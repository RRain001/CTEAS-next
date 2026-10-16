# P4 READ62 v5.661 L110225: scoped C++20 reproduction

Status (reviewed 2026-10-11): **PASS_JDAT2_IFMT1_FULL_YEAR_NUMERIC_AND_BYTE_PARITY** / **PASS_CPP_CALMET_FINAL_PUBLICATION** / **UNSUPPORTED_LEGACY_ALTERNATE_OPTIONS**.

## Authority and source protection

- Frozen original `engine/vendor/src/READ62_v5.661_L110225/READ62.FOR` and associated legacy INP/source files are unchanged; the Ubuntu compiler runs the original source with temporary case-normalized include aliases and 72-column fixed-form syntax.
- Original Python `engine/preprocess/read62_upperair_data/` remains unchanged. `download_igra.py`, `parse_igra_to_csv.py`, `read.py`, source README and strict requirements were originally copied into `native_cpp/modules/p4_read62/data_prep/`. `merge_final_upperair.py` is now also copied **byte-identically** for final-stage publishing. Only the scoped copies of data download/parse/FSL are changed.
- Branch: `codex/cteas-p4-read62-reference`, **PR #6 Open / Ready for Review**, not merged to its base branch or `main`.

## Supported and implemented

- Annual station selection: valid distinct **original cleaned** 00/12 UTC sounding slots (not copied missing intervals) / 730 or 732; **strictly greater than 80%**. All qualifying in-domain stations remain at true coordinates. If none qualifies, one nearest passing external station is relocated horizontally to chimney coordinates, while source coordinates and original elevation remain auditable; repeat independently every year.
- Preserve original missing-profile cloning and first-level wind/temperature repairs. For targeted pressure-level insertion, use shortest circular wind direction arc, 180-degree ties clockwise.
- FSL generated from copied upstream Python. Legacy fixed-width latitude F7.2 / longitude F6.2 remain intact; optional `P4EXACT_LAT=...` and `P4EXACT_LON=...` suffixes with 3–6 decimals are accepted by new C++ while ignored by original Fortran.
- Independent C++20 `cteas_p4_read62` reads FSL and writes the READ62 `JDAT=2, IFMT=1, PSTOP=500 hPa, LHT/LTEMP/LWD/LWS=F, ISUB=0, LXTOP/LXSFC=F` UP.DAT output. Scoped Python runner `run_cpp_pipeline.py` uses it per station/year, then the copied legacy merger builds CALMET case files and exact station metadata.

## Independent production-relevant evidence

Actual public NOAA IGRA `CHM00058424` ANQING 2022, 5×5 km Hefei model domain, 100m grid; source lat/lon 30.6167/116.9667, effective lat/lon 31.939774444/117.141610855, station source elevation 62 m, 728/730=99.726% valid original 00/12 UTC soundings.

- 2022-01-01 through 2022-01-06: **12/12 profiles, 729/729 levels, 3,645/3,645 numerical fields identical** to original READ62.
- **Full 2022:** **730/730 profiles, 42,577/42,577 levels, 212,885/212,885 P/Z/T/WD/WS numerical fields identical** to original READ62. The single original top-level missing-data annotation was reproduced.
- Both six-day and full-year **UP.DAT byte-for-byte equality** is enforced by dedicated GitHub Actions `cmp`.
- Coordinate suffix precision **3/4/5/6 decimals**: four actual Fortran/C++ runs; original Fortran UP.DAT byte-identical to baseline; new C++ parses the appended exact coordinate with corresponding precision and produces identical numerical UP.DAT.
- Case pipeline `run_cpp_pipeline.py` publishes `project/current/met/upperair/final/up_58424.dat`, `stations.csv`, and an execution manifest. Final legacy merger clips to CALMET's 99-level limit and adds one boundary record; this is a separate transformation from the raw UP.DAT Fortran/C++ parity input.

CI: `https://github.com/RRain001/CTEAS/actions/workflows/p4-read62-fortran-parity.yml`. See PR #6 for SHA-locked run and artifact links.

## Explicit limitations

- Does **not** claim equivalence for TD-6201 `JDAT=1`, `IFMT=2` comma records, substitute profiles `ISUB>0`, advanced original READ62 repair switches `LXTOP/LXSFC`, non-default missing-layer dropping, alternate climate/operating settings, or other IGRA stations. The frozen eligible case only needs `JDAT=2, IFMT=1` defaults.
- The original Fortran **still reads 2 decimals** from legacy fields. The optional suffix carries up to 6 decimal precision to C++; this does not change original Fortran computations or historical compatibility.
- Moving off-site observations to chimney is a **virtual proxy** and cannot be described as direct site measurements.
- Multi-year annual reselection is implemented for inputs. Before CALMET production with yearly changes in station membership/location, review station identity and time-dependent metadata compatibility rather than assuming static station continuity.
- No Fortran `READ62.LST` reproduction in C++ (Fortran log exists as independent audit); final CALMET P6 physical wind equivalence is a separate module.

## P4 2026-10-11 handoff: implementation inventory and original-code mapping

**Scope and interpretation:** P4 is a restricted but independently executable C++20 reimplementation of the **READ62 FSL->UP.DAT numerical/output path**, not merely a parser. The standalone Fortran READ62 was compiled and run independently for parity. Data acquisition, cleaning and final CALMET-stage merging remain **Python**, as deliberately isolated copies. Only the frozen control configuration has Fortran parity evidence.

| Responsibility | Refactored location | ORIGINAL code / controlling option | Current status |
| --- | --- | --- | --- |
| Select stations and download IGRA upper air | `native_cpp/modules/p4_read62/data_prep/download_igra.py` | `engine/preprocess/read62_upperair_data/download_igra.py`; `engine/resources/igra/igra2-station-list.txt` | IMPLEMENTED Python copy + annual >80% original cleaned 00/12 UTC profile gate; multiple eligible in-domain stations; otherwise nearest qualifying external virtual station |
| Determine study years, orchestrate Python preparation | `.../data_prep/prepare_inputs.py` | `engine/preprocess/read62_upperair_data/run_upperair_pipeline.py` and its substeps | IMPLEMENTED selected years from `grid/research_time`; --execute preflight; reselect separately each year |
| Parse IGRA profile, QA, construct/repair mandatory target levels | `.../data_prep/parse_igra_to_csv.py` | `engine/preprocess/read62_upperair_data/parse_igra_to_csv.py`; target `PSTOP`; Fortran `READ62.FOR` `COMP` | IMPLEMENTED scoped Python; preserves rules for observed vs derived profile counts and copied missing 00/12 slots; includes shortest-arc wind interpolation with clockwise 180-degree tie |
| Build READ62 FSL stream and annotate precise geography | `.../data_prep/read.py` | `engine/preprocess/read62_upperair_data/read.py`; Fortran `READ62.FOR` `COMP`, `JDAT=2` FSL parser | IMPLEMENTED fixed-column FSL; optional `P4EXACT_LAT/LON` 3-6 decimal suffix read by C++ only. Original fixed-column 2-decimal parser remains unchanged |
| Parse FSL station/time/layer/unit/missing masks in C++20 | `native_cpp/include/cteas/met_input/p4_read62.hpp` | `READ62.FOR` `COMP`, `JDAT=2`; `read62.inp` controls `LHT/LTEMP/LWD/LWS` | IMPLEMENTED, tested for targeted original flags `F` and `WSUNIT=ms/kt` reading |
| WRITE UP.DAT (numeric, header, formatting, temperature, missing masks, QA) | `native_cpp/include/cteas/met_input/p4_updat.hpp`, `native_cpp/modules/p4_read62/p4_read62_main.cpp` | `engine/vendor/src/READ62_v5.661_L110225/READ62.FOR`: `COMP` and `WRHD`; `read62.inp` `JDAT=2, IFMT=1, PSTOP=500, ISUB=0, LXTOP/LXSFC=F` | **PASS_REFERENCE** for frozen options, 730/730 profiles, 42,577/42,577 levels, 212,885/212,885 numerical fields and byte-for-byte UP.DAT |
| Run per station/year, final UP.DAT merge and CALMET metadata | `.../data_prep/run_cpp_pipeline.py`, copied `.../data_prep/merge_final_upperair.py` | `engine/preprocess/read62_upperair_data/run_read62.py`, `merge_final_upperair.py`, `run_upperair_pipeline.py` | IMPLEMENTED: C++ replaces original Fortran invocation, **original Python merge algorithm is reused**, publishes `met/upperair/final/up_WMO.dat`, `stations.csv` |
| Reproduce and verify original READ62 | `native_cpp/modules/p4_read62/verify_updat_parity.py`; `.github/workflows/p4-read62-fortran-parity.yml` | Original `READ62.FOR`, `read62.inp`, `QA.R62`; full 2022 NOAA IGRA source | **PASS_REFERENCE** both short window and whole-year; independent Fortran executable and SHA-locked input |
| Handoff into unchanged CALMET | P4 final outputs `UP.DAT` + `stations.csv`; cross-branch reference workflow on P5 PR | `engine/run_met/prepare_met.py`, `engine/run_met/run_met.py`; vendor `CALMET_v6.5.0_L150223/calmet.for` | **PASS_REAL_CASE_SMOKE**: unchanged original CALMET 2022-01-01..06, 100m grid; this is not independent P6 field-equivalence proof |

### Unimplemented / not qualified (explicit scope)

| Missing or deferred capability | Original source / option to consult | Why still open |
| --- | --- | --- |
| Non-FSL TD-6201 source | `READ62.FOR` `COMP` / `JDAT=1` | No scoped C++ path, no parity inputs |
| Alternate output format | `READ62.FOR` `WRHD` / `IFMT=2` | Writer only validates `IFMT=1` |
| Substitute sounding/replacement source | `READ62.FOR` `RDSUB`, `NEXTSUB`, `SUBMISS`, `SUBREP`; `SUBSOUND.DAT` / `ISUB>0` | No C++ equivalent |
| Nondefault upper/lower extrapolation, layer-drop and QA permutations | `read62.inp`: `LXTOP, LXSFC, LHT, LTEMP, LWD, LWS`; `READ62.FOR` `COMP` and `QAINP` | Only stated frozen settings compared; no general parity |
| READ62 full legacy list, runtime statistics and diagnostics | `READ62.FOR` `FIN`, legacy `READ62.LST`/`QA.R62` | C++ `UP.DAT` parity is not reproduction of legacy log/output inventory |
| Multi-year changes in observed/virtual upper-air station membership in one CALMET case | Python `merge_final_upperair.py` plus `engine/run_met/prepare_met.py` station metadata | Year-by-year input selection exists; multi-year original CALMET station metadata semantics not yet proven |
| Multi-station, alternate pressure tops and broad geography independent original-Fortran parity | Original `READ62.FOR` + cases beyond frozen `PSTOP=500`/Anqing2022 | Current explicit parity results do not authorize other cases |
| Full reconstructed P6 CALMET wind field | Original `calmet.for` / future P6 | Outside P4 responsibility |

### Frozen acceptance evidence and PR state

- PR **[#6](https://github.com/RRain001/CTEAS/pull/6)** — Open, **Ready for Review**, not merged; audited source HEAD at this inventory: `dc4e3f042e5668358fc43f2f2ae98d7a554ecfd3` (this document update adds a newer docs-only commit).
- [Independent READ62 Fortran/C++ parity, 2022](https://github.com/RRain001/CTEAS/actions/runs/38061364090) — PASS; [IGRA input capture](https://github.com/RRain001/CTEAS/actions/runs/38061364089) — PASS; [scoped C++](https://github.com/RRain001/CTEAS/actions/runs/38061364094) — PASS.
- [Cross-stage original CALMET on real P4/P5 data](https://github.com/RRain001/CTEAS/actions/runs/38108309198) — PASS; **this verifies compatibility of the original program with the prepared input**, not all CALMET meteorological physics.
- Preserve original `engine/preprocess/read62_upperair_data/` and vendor `engine/vendor/src/READ62_v5.661_L110225/`. Do not silently upgrade *restricted-control* PASS_REFERENCE to *all-control* equivalence.

P5 is documented on a **separate** still-unmerged branch at [P5 implementation status](https://github.com/RRain001/CTEAS/blob/codex/cteas-p5-smerge-reference/docs/reconstruction_cpp/P5_SMERGE_IMPLEMENTATION_STATUS.md). The P5 annual external **>90%** surface-hour gate is independent from the P4 **>80%** valid 00/12 sounding gate.
