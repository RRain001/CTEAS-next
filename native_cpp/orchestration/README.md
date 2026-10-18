# S2-2A1 native case contract — read-only

The original **S2-2A1 `plan.py` component** implements only a bounded, JSON-producing `dry-run` contract for the frozen Hefei 2022 case. It is *not* an executor, general case planner or claim of numerical/scientific acceptance. The separate S2-2C experimental `run_p6.py` is described below; its presence does not change `plan.py` or imply science acceptance.

```bash
python -m native_cpp.orchestration.plan --case-yaml project/cases/hefei5km_2022_reference_case_20261011/case.yaml
python -m unittest discover -s native_cpp/orchestration/tests -p 'test_*.py' -v
```

The CLI **only reads the YAML** and prints a JSON object with immutable source-YAML SHA256, known grid/UTC/meteorology/point-source admission, and P1–P7 DAG. The returned status is always `DRY_RUN_ONLY_EXECUTION_BLOCKED` (`ready=false`, no legacy fallback, no files written). Invalid/out-of-scope cases yield exit code 2 and a blocked JSON result. No execution flag exists.

Strictly accepted *schema profile for planning*: exact 2022 Hefei case identity, 50x50x9 @ 100 m, UTM50N WGS84, locked UTC dates/station/source and known dry-deposition-free wet/chemistry switches. Case file SHA is reported, not claimed as independent source provenance. No implicit assumption about a 143-hour execution is made from the inclusive 2022-01-01..2022-01-06 labels.

This intentionally differs from `engine/gui_g5/pipeline.py` and neither imports nor modifies it. Existing C++/Fortran numerical kernels and P3 independent reference outputs remain unmodified. The P1/P2→P3 native bridge has since been accepted in its restricted same-source Hefei scope; P4/P5→P6 and P6→P7 production connections remain separately gated.

## S2-2C Draft — opted-in scoped P6 execution (experimental)

`plan.py` above remains exactly **read-only and BLOCKED**; do not conflate it with the new, separately invoked `run_p6.py` for isolated development. The new `handoff_gate.py` checks a separately authored manifest for the known native P3/P4/P5 file roles, byte lengths and SHA256, but producer names/source Git SHA are still self-assertions rather than independent provenance. A valid handoff is `INPUT_INTEGRITY_VERIFIED_ONLY`.

`run_p6.py` builds the existing C++ `cteas_p6_native_hourly_driver` command after an actual `case.yaml` scope check and byte-integrity preflight; it refuses staging that includes original `run/met/met.dat` and **only** chooses `--p6e-source-builder` metadata-only routing. It requires explicit paths to the existing native `p6d/p6e/cgamma/bridge` tools and, for 143h, `p6f-writer` + `--p6f-direct-hourly`. `--hours` is restricted to diagnostic checkpoints **1, 6 or 143**; no other grid/case/physics path is unlocked.

Without `--execute`, `run_p6.py` only prints a launch plan and does not create output. With `--execute`, it runs in a **new scratch** (no default publishing) and verifies the resulting existing C++ manifest and native MET hash. Even when the executable returns success, it emits `P6_EXECUTED_SCIENCE_NOT_ACCEPTED` and `scientific_acceptance=NOT_EVALUATED`. It cannot substitute for real original/native 45-field comparisons, time-axis verification, full P3/P4/P5 producer provenance or independent tests.

Example (only after a real scratch-staged 2022 case and source manifest exist; binaries must already be built):

```bash
python3 -m native_cpp.orchestration.run_p6 \
  --case-yaml /authorized/scratch/hefei5km_2022_reference_case_20261011/case.yaml \
  --manifest /authorized/scratch/s2c-p6-input-manifest.json \
  --work /authorized/scratch/p6-candidate-work \
  --hours 143 \
  --driver /path/to/cteas_p6_native_hourly_driver \
  --p6d /path/to/native_p6d --p6e /path/to/native_p6e \
  --cgamma /path/to/native_cgamma --bridge /path/to/native_bridge \
  --p6e-source-builder /path/to/native_p6e_source_builder \
  --p6f-writer /path/to/native_p6f_writer
# add --execute only when explicitly doing isolated numerical execution
```

The binary placeholders above are intentionally **not authoritative executable filenames**; use paths/target names inspected from the actual P6 CMake/Ubuntu build before any real run. No original Fortran fallback is configured. Current tests only mock subprocess execution:

```bash
python3 -m unittest discover -s native_cpp/orchestration/tests -p 'test_*.py' -v
```

The S2-2C Draft PR tracks real end-to-end integration and an independent 143h scientific gate. G5 `met`/`puff`/`all` remain blocked.

## S2-G0: new-site case.yaml → real P4/P5 station manifest handoff (metadata-only)

`site_plan.py` is a **separate** fail-closed native integration input contract for non-Hefei projects, developed under [S2-G #36](https://github.com/RRain001/CTEAS-next/issues/36). It **does not modify** frozen `plan.py`, `run_p6.py`, scientific reference files, or G5. It **does not execute P1/P2/P3/P4/P5/P6/P7**; it checks actual annual selector manifest metadata prepared by P4/P5. An independent S2-G0 CI harness invokes the **production P4/P5 original NOAA selectors** to prepare source-backed manifests before this read-only validator.

New-site `case.yaml` uses `schema_version: 1`, a directory-matching non-Hefei `case_name`, `settings.timezone: UTC+0000`, `preprocess.grid` (explicit `utm_zone`, `hemisphere`, `center`, `domain`, `resolution_km`, `nz`) and the published `grid/grid.cmn` as the **sole** numerical footprint authority. The grid must be WGS84 UTM, both `XREFKM` and `YREFKM` expressed in km with **exactly three digits after the decimal**; dimensions/resolution, coordinate validity and stack footprint are cross-checked. User-defined `research_time` is whole-hour UTC and every overlapping calendar year requires original P4/P5 annual selection manifests; multi-year IFSTN aliases must be stable. The no-rain/no-chemistry original selected **control keys and values** remain fixed until independent physics acceptance. One positive HTO point source is supported for *planning only*.

Given a case whose original P4/P5 station-selection programs already ran:

```bash
python3 -m native_cpp.orchestration.site_plan \
  --case-yaml /authorized/new_site/case.yaml \
  --p4-selection-root /authorized/new_site/met/upperair \
  --p5-selection-root /authorized/new_site/met/surface/isd_raw
python3 -m unittest discover -s native_cpp/orchestration/tests -p 'test_*.py' -v
```

P4 root must contain `<year>/p4_station_selection_audit.json`; P5 root `station_selection_<year>.json`. These are checked for station IDs, >80% original 00/12 P4 slots, original ISD and ISD-Lite calendar counts, original/effective physical source positions, external P5 fallback strictly >90% original both products, exact virtual effective placement at stack, one annual P5 primary chosen by raw Lite/full/ID ranking, sparse auxiliaries, and stable IFSTN. **A syntactically valid input manifest does not independently prove that raw NOAA bytes were authentic**. The separate original observation replay records original-source hashes.

CI [PR #37](https://github.com/RRain001/CTEAS-next/pull/37) sources the real 2022–2023 original NOAA P4/P5 records from [S3-F #35](https://github.com/RRain001/CTEAS-next/pull/35). It tests **one new physical footprint** with P5 Huoshan/Luogang as *observed in-domain multi-sites* and P4 Anqing as an *out-of-domain virtual sounding station*, for both calendar years. The distinct P4 Fuyang/Anqing two-in-domain experiment is also verified, but **is not mislabeled as part of the smaller shared footprint**. No new P6/P7 science run occurs.

**Regardless of successful G0 checks:** return status `SITE_STATION_INPUTS_VERIFIED_P6_P7_BLOCKED`, `ready=false`, `model_executed=false`, `scientific_acceptance=NOT_EVALUATED`. P6 hard-coded `up_58424.dat`, station `58424`, `--upper-i 25 --upper-j 26`, fixed 50×50×9 and P7 general production limitations still require independent G1/G2/G3/G4 work. G5 `met/puff/all` is not unlocked. No legacy Fortran fallback or automatic original reference MET/puff reuse is allowed.
