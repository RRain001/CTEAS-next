# P5 SMERGE v5.7.0 L121203 — implementation status, original-code mapping and remaining gaps

**Audit date:** 2026-10-11.
**最低重构验收结论：`P5_MINIMUM_RECONSTRUCTION=PASS`（受控配置 `JDAT=8 / IOFORM=2 / IOPACK=0 / LPREV=F / LPCALC=F / UTC`）。**

[**P5 最小重构验收与结果报告（含完整通过证据、遗留事项、复现指令）**](P5_SMERGE_MINIMUM_RECONSTRUCTION_REPORT_2026-10-11.md)

[**P5 真实多站、跨年独立验证（2站×2年、17,519小时段、2,663,153字节完全等价）**](P5_REAL_MULTISTATION_MULTIYEAR_REFERENCE_2026-10-11.md)
**Status:** `PASS_SCOPED_CPP_GENERIC_INPUT` / `PASS_PYTHON_NOAA_PREPROCESS_AND_ANNUAL_SELECTION` / `PASS_ORIGINAL_SMERGE_CALMET_SMOKE` / `PASS_NATIVE_CPP_SURFDAT_JDAT8_IOFORM2_BYTE_PARITY_AND_CALMET_SMOKE` / `PASS_REAL_NOAA_TWO_STATION_TWO_YEAR_BYTE_PARITY`.

PR [#7](https://github.com/RRain001/CTEAS/pull/7) on `codex/cteas-p5-smerge-reference` is **Open / Ready for Review**, not merged. Native writer validated by immutable reference CI at `3f4f0a8d218161a5b07f983b5bad79c652ada93a`; subsequent tests follow new changes.

## 1. Three distinct levels of completion

1. **P5 station selection and weather preparation (Python): implemented** as isolated copies/extensions under `native_cpp/modules/p5_smerge/data_prep/`. This prepares SMERGE GENERIC data from original NOAA **complete ISD nonwind** and **ISD-Lite wind**. It is not C++.
2. **P5 C++20 input contracts (C++): implemented and unit-tested.** `native_cpp/include/cteas/met_input/p5_smerge.hpp` decodes the scoped `JDAT=8` `GENERIC 2.0` 12-column input, masks `9999`, checks station identities/UTC time/units, supports deterministic multi-station hourly assembly and missing-hour counts. The independent C++20 executable `native_cpp/modules/p5_smerge/p5_surf_main.cpp` **NOW writes** a complete formatted original-compatible `SURF.DAT` for the real-case restricted controls `JDAT=8, IOFORM=2, IOPACK=0, LPREV=F, LPCALC=F, UTC+0000`. It reads the existing real `smerge.inp` and all model-time GENERIC records directly, with NO Fortran dependency.
3. **Independent SURF.DAT reference PASS:** original SMERGE v5.7.0 and independent C++20 both write SURF.DAT from the EXACT SAME input/control; synthetic 2-station records **721/721 bytes equal**, real Hefei 2022-01-01..06 **13,841/13,841 bytes equal** and all 293 lines equal. The unmodified CALMET v6.5.0 then successfully reads the **native C++ SURF.DAT**. The isolated post-SMERGE cloud fallback is retained separately, unchanged.

The original `engine/preprocess/smerge_surf_data/`, `engine/vendor/src/SMERGE_v5.7.0_L121203/`, and `engine/vendor/src/CALMET_v6.5.0_L150223/` remain unchanged.

## 2. Approved station selection and preprocessing specification

### 2.1 Annual raw-data coverage

For each station and **each calendar year**, raw hour coverage is the number of unique original UTC-hour records / **8760** in a common year or **8784** in a leap year. **Source record present but wind missing still counts**. Fully absent hour does not count. Do NOT use post-fill rows to calculate coverage. Both the original complete ISD and the original ISD-Lite coverage are recorded separately.

- **Zero in-domain stations:** search outside stations by increasing geodesic distance from **chimney**. Accept the FIRST with BOTH original ISD and ISD-Lite coverage **strictly >90%**. Exactly 90% fails. Use a **single relocated virtual station** and process it fully. Select independently next year.
- **One in-domain station:** retain it regardless of original coverage (provided source files are usable); fully process it.
- **Two or more in-domain stations:** keep all at real station coordinates. For each year select **one primary** with highest original ISD-Lite hourly coverage; tie-break original complete ISD coverage then station ID. Fully process ONLY the primary; all others are sparse auxiliaries. Recompute next year; do not lock first-year winner.

Annual provenance: `project/current/met/surface/isd_raw/station_selection_YEAR.json` with `station_selection_case`, `primary_sid`, yearly source coverage, `wind_treatment` for each station, preserved NOAA source identity, station coordinates and stable numerical `IFSTN` aliases across selected years.

### 2.2 Annual primary / relocated virtual station: full treatment

- Merge complete ISD's nonwind meteorology and ISD-Lite wind at the same **UTC hour**, with wind not falling back to complete ISD `WND`. Source reports with missing values are still source reports for coverage.
- Construct every hour of the selected calendar year, including **any arbitrary source-absent time**: single missing hour, consecutive hours, midnight, full days, across months. Distinguish `NO_ORIGINAL_ISD_LITE_HOUR` from source-present-but-wind-invalid.
- Nonwind fields: each missing field independently uses its previous valid value, without maximum hold duration; leading missing without donor remains missing `9999`.
- **Valid noncalm donor** is an original complete wind pair WD in (0,360], WS>0. Any partial/invalid wind pair becomes **both components invalid** and is held from the last real observed valid **noncalm** vector; observed calm never seeds an invalid wind hour.
- Standard original calm (0,0) and source (360,0) normalize to (0,0) in stage1 (`*_cleaned.csv`). Stage2 (`*_calm_interpolated.csv`) replaces **only original calm** using the constant circular midpoint from nearest real valid noncalm observations on either side for an entire calm run, **speed 0.5 m/s**. Exact opposite endpoints tie toward the **clockwise** path from earlier to later direction: 90→270 yields 180; 270→90 yields 360; 1→181 yields 91. Nonzero north wind is **360**, never WD=0.
- Leading/trailing original calm run without one side's real observation copies **both** components of the available opposite-end real noncalm vector; if no real noncalm donor exists, fail explicitly. Leading *missing* wind pair without a previous good noncalm donor is not silently backfilled.
- Store `*_filled.csv` numerically equal to stage2 for the downstream GENERIC pipeline; retain stage1/stage2 and their JSON markers, source-hour provenance, SHA256 and per-hour+annual audit.

### 2.3 Other in-domain stations: source-sparse format normalization ONLY

- **Crucial: “18:00 and 20:00 but not 19:00” was an EXAMPLE, NOT a special-case rule.** There is NO restriction on missing hour number, time of day, duration or adjacency. **For any absent original UTC hour or consecutive absent-hour interval, write NO extra row** in the persistent sparse station GENERIC file.
- Source-present hour: preserve the exact timestamp; only format/units and sentinel normalization. Never forward-fill wind OR any other weather field; never fabricate observations or reconstruct an annual timeline. Source (0°,0 m/s) and (360°,0 m/s) become (0°,0 m/s), **not** 0.5 m/s or a new wind direction.
- If any wind component is invalid or missing, **both** output `9999`. Every other missing meteorological number outputs `9999`; `-9999` belongs solely to original ISD-Lite source coding, not GENERIC.
- This applies to **arbitrary multi-hour gaps**, including multi-day, multi-month and date-boundary gaps, and also holds when one or every recorded auxiliary wind pair is missing.
- The downstream file `*_filled.csv` is a compatibility filename **only**; it does not mean any missing auxiliary hours or variables were actually filled. Output is sparse in the original-hour dimension.

**Fortran-only I/O note:** the *original* SMERGE `RDWRITS` routine may read past EOF if a sparse station ends before the end of the common model period. The scoped `generate_smerge_input_sections.py` may stage an **isolated temporary runtime COPY** at `run/smerge/original_smerge_sparse_runtime/`, adding precisely **one all-`9999` terminal record** at the last modeled hour (only when required). **No interior absent hours are created** and the actual `isd2smerge_ready/USAF-WBAN.csv` remains unchanged. This sentinel is not recorded as an original observation or weather imputation, and is not needed by a future native sparse-aware writer.

A **pre-SMERGE input guard** requires the annual primary to supply a complete valid **noncalm** wind vector at **every active model UTC hour**, so at least one primary site is never source-calm/invalid at a modeled time. This is an input condition, **not proof of CALMET physical accuracy**.

See [current detailed P5 source and wind policy](../../native_cpp/modules/p5_smerge/data_prep/ISD_LITE_HYBRID_WIND_POLICY.md).

## 3. Function-to-original-code inventory

| Capability / interface | Scoped new implementation | Original Python or Fortran authority / important controls | Status |
| --- | --- | --- | --- |
| Candidate station history, original-hour coverage, annual roles, distance/coordinates | `native_cpp/modules/p5_smerge/data_prep/download_isd_by_grid.py`, `station_identity.py` | `engine/preprocess/smerge_surf_data/download_isd_by_grid.py`; NOAA `engine/resources/isd/isd-history.txt` | IMPLEMENTED in Python; external strict >90 both sources / in-domain cases / annual station role |
| NOAA ISD-Lite download, time/units/wind-only parse, raw SHA256 | `data_prep/isd_lite_wind.py` | Original `download_isd_by_grid.py` and NOAA ISD-Lite coding (new source added to P5); original complete ISD `WND` no longer supplies wind | IMPLEMENTED Python; 0.1 m/s source speed and 1-degree source direction |
| Full ISD nonwind field parse, UTC pairing with ISD-Lite wind, GENERIC field mapping | `data_prep/isd_to_smerge_and_fill.py` | `engine/preprocess/smerge_surf_data/isd_to_smerge_and_fill.py`; `SMERGE.FOR` `RDWRITS` `JDAT=8`; `smerge.inp` `SFCMET/IFSTN/ASTZ` | IMPLEMENTED Python; hourly source audit |
| Main/virtual station missing whole-vector and original-calm policies | `data_prep/wind_policy_v2.py`, `interpolate.py` | Original `engine/preprocess/smerge_surf_data/interpolate.py`; `SMERGE.FOR` `RDWRITS` `JDAT=8` plus downstream `CALMET calmet.for` calm logic | IMPLEMENTED Python; user-prescribed preprocessing intentionally differs from preserving original measured calm |
| Sparse auxiliary station, arbitrary timestamp gaps, `9999`, 0/0 calm | `data_prep/sparse_station_policy.py`, `interpolate.py` | Original `interpolate.py`, original `SMERGE.FOR` `RDWRITS` `JDAT=8` with backspace for missing hours | IMPLEMENTED Python; no synthetic hours, no element/value fill |
| Annual stage selection, no stale role cache, source audit and QA | `data_prep/isd_to_smerge_and_fill.py`, `interpolate.py`, `wind_policy_v2.py` | Original `isd_to_smerge_and_fill.py`, `interpolate.py`; original source record identity | IMPLEMENTED Python |
| Merge years, clip to research hours, one valid moving primary per model hour | `data_prep/clean_merge_filled_by_research_time.py`, `convert_cleaned_to_smerge_ready.py` | `engine/preprocess/smerge_surf_data/clean_merge_filled_by_research_time.py`, `convert_cleaned_to_smerge_ready.py` | IMPLEMENTED Python; all auxiliary absent hours stay absent |
| Original SMERGE control file, station metadata, dates and legacy sparse EOF adapter | `data_prep/generate_smerge_input_sections.py` | Original `engine/preprocess/smerge_surf_data/generate_smerge_input_sections.py`; `SMERGE.FOR` `READCF`, `OPENS`, `RDWRITS`; `smerge.inp` `JDAT=8, SFCMET, IFSTN, ASTZ, NFF, ABTZ` | IMPLEMENTED Python config and runtime-only adapter; **not C++ physics** |
| Generic station format, UTC exact-hour parse, field/mask mapping, multi-station hourly assembly | `native_cpp/include/cteas/met_input/p5_smerge.hpp`; `native_cpp/tests/p5_smerge_tests.cpp` | Original `SMERGE.FOR` `RDWRITS` `JDAT=8`, `RDS`/`WRS` data model, original 12-column GENERIC | **PASS_CPP_CONTRACT**, no original binary SURF writer |
| Run original unchanged SMERGE, surface file publication | `data_prep/run_smerge_and_monitor.py` | Original `engine/preprocess/smerge_surf_data/run_smerge_and_monitor.py`, `engine/vendor/src/SMERGE_v5.7.0_L121203/SMERGE.FOR` `COMP/RDWRITS/WRS` | Original Fortran PASS_REAL_CASE; postprocesses cloud-cover gaps in copied final SURF.DAT; **not a native C++ substitute** |
| Test on original CALMET | `.github/workflows/p4-p5-original-calmet-integration.yml` | `engine/run_met/prepare_met.py`, `engine/run_met/run_met.py`, `engine/vendor/src/CALMET_v6.5.0_L150223/calmet.for` | PASS 100m 2022-01-01..06 original-model compatibility, NOT CALMET physics parity |
| Original Python complete surface pipeline | Scoped `data_prep/prepare_inputs.py` and original SMERGE runner | `engine/preprocess/smerge_surf_data/run_isd_surface_pipeline.py` | Python stages implemented in scoped copy, original unchanged |
| **Native formatted SURF.DAT writer** | `native_cpp/modules/p5_smerge/p5_surf_main.cpp`, `--native-cpp-bin` in scoped `run_smerge_and_monitor.py` | Original `SMERGE.FOR` `RDWRITS/WRHD/WRS` `JDAT=8, IOFORM=2, IOPACK=0, LPREV=F, LPCALC=F` | **PASS_CPP_REFERENCE** for synthetic two-station + real Hefei single station complete-file byte parity; output read by unmodified CALMET. Other IOFORM/IOPACK modes remain unsupported |

## 3A. New independent native SURF.DAT implementation (2026-10-11)

**Writer:** [p5_surf_main.cpp](../../native_cpp/modules/p5_smerge/p5_surf_main.cpp) is compiled by
`native_cpp/modules/p5_smerge/CMakeLists.txt` as executable `cteas_p5_smerge`.
It consumes the SAME `smerge.inp` controlling the original Fortran reader and
the SAME NOAA-derived GENERIC source files. The source contains no Fortran calls,
no shell-outs to SMERGE and no frozen/snapshotted SURF.DAT data. The independent
C++ module implements actual WRS and WRHD output formatting and correctly
applies original SMERGE 2.1 explicit beginning-time-to-hour-ending conversion.
It honors station IFSTN order, all eight output fields, source masks and actual
timestamps; sparse auxiliary original-hour gaps are mapped to 9999 directly.

**Command (from checkout root, with configured project/current):**

```bash
cmake -S native_cpp/modules/p5_smerge -B /tmp/p5-native -DCMAKE_BUILD_TYPE=Debug
cmake --build /tmp/p5-native -j2
ctest --test-dir /tmp/p5-native --output-on-failure
python3 -m native_cpp.modules.p5_smerge.data_prep.run_smerge_and_monitor \
  --native-cpp-bin /tmp/p5-native/cteas_p5_smerge
```

The Python publishing wrapper runs the C++ binary, checks exit code, publishes
actual native output into `met/surface/final/surf.dat`, writes effective station
metadata, and applies the existing original cloud-cover missing-data fallback
to the published copy. Without the `--native-cpp-bin` flag the original Fortran
backend is still available as a reference; do not conflate it with native.

**Independent reference evidence:**

- [P5 synthetic 2-station original-vs-native byte parity](https://github.com/RRain001/CTEAS/actions/runs/38110709094):
  3 time records, two input stations, intentional missing whole hour, calm,
  no temperature, precipitation and RH/cloud decimal conversion;
  **721 bytes each, 17 lines each, zero differences**.
- [P5 real Hefei 2022, original-vs-native byte parity AND original CALMET](https://github.com/RRain001/CTEAS/actions/runs/38110709086):
  **13,841 bytes** original and native, **293 lines**, byte-identical;
  unmodified original CALMET consumes published NATIVE SURF.DAT and produces
  MET.DAT 64,762,556 bytes with zero detected fatal patterns.
  Additionally, [the complete reference run](https://github.com/RRain001/CTEAS/actions/runs/38111038279)
  independently tested synthetic sparse-secondary data: native C++ directly
  consumed the untouched sparse GENERIC time axis WITHOUT the legacy
  Fortran-only EOF sentinel; the entire SURF.DAT byte stream matched the
  independent original, and original CALMET successfully consumed and
  completed on the native two-station output.
  `P5_NATIVE_SPARSE_NO_SENTINEL_BYTE_PARITY=PASS` and
  `P5_NATIVE_SURFDAT_ORIGINAL_CALMET_SPARSE_MULTISTATION=PASS`.

**Explicitly REJECTED by native writer:** IOFORM=1 (Fortran unformatted),
IOPACK!=0, LPREV=T (previous SURF.DAT continuation), LPCALC=T
(empirical station-pressure reconstruction), JDAT other than 8, any
ASTZ/ABTZ nonzero UTC offset, or nonhourly seconds. These are not
replaced by guessed formats or silently passed to legacy Fortran.
Output is the full **formatted** active production-case SURF.DAT, not a
generic replacement for every vendor SMERGE configuration.


**Current minimum reconstruction gate:** **PASS** for this explicitly frozen
JDAT=8 + formatted SURF.DAT configuration. All other original formats,
binary/packed and LPREV continuation remain **out of scope**, not silently
included. For evidence and reproduction, see the linked acceptance report.

## 4. Unimplemented functionality / remaining reference gates

| Gap or deferred capability | Original code / control of record | Minimum validation before claiming it complete |
| --- | --- | --- |
| **Non-target binary/packed SURF.DAT output and previous-SURF continuation** | `SMERGE.FOR`: `WRHD/WRS/PACKS/UNPCKS/RDS`, `IOFORM=1`, `IOPACK=1`, `LPREV=T` | Formatted `IOFORM=2, IOPACK=0, LPREV=F` is implemented and byte-verified. Binary/packed and continuation branches NOT implemented; require their own frozen Fortran references |
| Other original surface inputs beyond `JDAT=8` GENERIC | `SMERGE.FOR` `RDWRITS`, `READCF`, `JDAT` switches; original `smerge.inp` | Explicit original-format input vectors, reference snapshots and parser/writer tests |
| Alternative original time-zone offsets and daylight-time control variants | `smerge.inp` `ASTZ/ABTZ/XSTZ`; `READCF` and `RDWRITS` | Offset and day-boundary original comparisons; current path accepts UTC only |
| Legacy accumulated/previous-year and derived meteorology branches | `smerge.inp` `LPREV/LPCALC`, related original `SMERGE.FOR` routines | Freeze corresponding cases and independent numerical references, not implied from hourly GENERIC success |
| Original cloud, precip and station-pressure conversions beyond scoped path | `SMERGE.FOR` `CLOUDS`, `PCODES/PCODES2`, `ALP2STP/SLP2STP`; `RDS` and `WRS` | Explicit field-level comparison on wet/cloudy/pressure-gap conditions |
| Real **2 NOAA meteorological stations × 2 calendar years** | Complete ISD + ISD-Lite source, original Fortran `SMERGE.FOR`, native C++ `p5_surf_main.cpp` | **PASS real input software test:** 2022–2023 all 17,519 hourly intervals and 2,663,153 bytes fully equivalent; note stations geographically separated, primary identity did not change. Physical same-domain and natural primary-switch tests remain open |
| Multi-year original-Fortran continuous computation including change of virtual source or primary | `smerge.inp` station block `IFSTN/XELEV/SFCMET`; CALMET `stations.csv` and original `CALMET calmet.for` | End-to-end actual multi-year run; source positions/station membership and time-varying metadata validated instead of assumed |
| Long unobserved spans and forcing sensitivity | User-defined unlimited previous-valid hold and artificial 0.5m/s original-calm replacement, CALMET diagnostic wind | Report hold-length distribution and calm-replacement rate; independent meteorological validity/sensitivity study; raw coverage alone is not quality assurance |
| Full original SMERGE log and QA/precipitation code reporting | `SMERGE.FOR` `FIN`, `PCODES`, `QA.SMG`, original `SMERGE.LST` | Implement C++ equivalent and compare |
| Native replacement of original-Fortran EOF workaround | `SMERGE.FOR` `RDWRITS` at EOF; `stage_original_smerge_terminal_record` adapter | Native sparse-aware writer must honor all missing time labels directly, without a runtime sentinel |
| Full independent CALMET or CALPUFF numerical parity | Original `CALMET calmet.for`; future P6/P7 branches | Outside P5; original execution success alone is not a field-level comparison |

## 5. Evidence, precise scope, and source protection

- **Real NOAA two-station, two-calendar-year verified:** [workflow #38111753787](https://github.com/RRain001/CTEAS/actions/runs/38111753787), 2022–2023 17,519 hourly intervals; 52,565 original lines and 52,565 C++ lines; 2,663,153 bytes each, SHA-256 equal `f6e80e8005d27208799c3881390ab705fc92edfccfdf7f55abccf08d870d5816`. 2022 Hefei 8,692 observed raw hours, Huoshan 2,828; 2023 Hefei 8,642, Huoshan 2,729; one fully processed primary per year and all 5,557 auxiliary observed hours preserved with zero synthetic missing-hour insertions. Not a valid claim of simultaneous in-domain 5km CALMET station geography; winner stayed Hefei both years. See [detailed report](P5_REAL_MULTISTATION_MULTIYEAR_REFERENCE_2026-10-11.md).


- **2022 NOAA 583210-99999**: 8,692 original ISD-Lite source hours / 8,760 (99.22%), 68 fully absent hours, **474 invalid wind hours INCLUDING absent**, 203 originally recorded calms. Full primary cleaned/calm-transformed outputs and 144/144 ready model hours matched; data-only original wind provenance. [Real-data capture CI](https://github.com/RRain001/CTEAS/actions/runs/38108309205) — PASS.
- **20 NOAA station-years**: five station identities × four calendar years 2021–2024; raw codes audited, full source rows 147,503 across station-years; rule replay and source time denominators checked. [Multistation data audit](https://github.com/RRain001/CTEAS/actions/runs/38108309197) — PASS.
- **P5 scoped Python/C++ tests**, including annual reselect, strict external coverage and synthetic sparse stations with arbitrary time gaps: [P5 C++20 CI](https://github.com/RRain001/CTEAS/actions/runs/38108309196) — PASS at pre-documentation baseline.
- **Unchanged ORIGINAL SMERGE v5.7.0 → unchanged ORIGINAL CALMET v6.5.0**: six-day Hefei 2022 50×50, 100m grid, P4 real IGRA UP.DAT, P5 real NOAA main site. First stage original `met.dat` **64,762,556 bytes**. Synthetic 48-original-row sparse auxiliary added; original SMERGE+CALMET both PASS with runtime-only EOF sentinel, `met.dat` **64,762,844 bytes**. [Head-locked full integration CI](https://github.com/RRain001/CTEAS/actions/runs/38108309198) — PASS. Synthetic station validates **I/O compatibility**, not real observed wind at that location.
- **Validated C++ output scope:** independent formatted `JDAT=8/IOFORM=2/IOPACK=0/LPREV=F/LPCALC=F` SURF.DAT is **complete and verified byte-for-byte against untouched Fortran**. Full legacy mode coverage (binary/packed, continuation, other JDAT) is deliberately UNSUPPORTED and must not be claimed. Scientific fidelity of filled wind forcing remains an independent question.
- Original scripts `engine/preprocess/smerge_surf_data/`, original Fortran `engine/vendor/src/SMERGE_v5.7.0_L121203/` and original CALMET code remain authoritative, unchanged. No base/main merge was performed in this checkpoint.

### 6. Acceptance gate before calling P5 “complete”

1. **DONE for frozen case**: native C++20 formatted `JDAT=8/IOFORM=2/IOPACK=0/LPREV=F/LPCALC=F/UTC` writer; checks original WRHD/WRS header, UTC hour-ending shift, 9999 sentinel, station order, missing type conversions, temperature/rain/cloud code and the full file byte comparison.
2. **DONE for synthetic and Hefei 2022 six-day case**: independently compiled original Fortran and C++ read identical smerge.inp and GENERIC sources, compare all output bytes before publishing C++ output to unchanged CALMET.
3. **DONE for genuine NOAA source data and 2022–2023 full-year boundary:** 2 real stations, 4 station-years, 17,519 hours, full original/C++ byte parity. **OPEN:** physically co-located stations within one actual 5km study domain, naturally changing primary winner and membership, full two-year CALMET physics, and non-UTC modes. See [independent multi-year report](P5_REAL_MULTISTATION_MULTIYEAR_REFERENCE_2026-10-11.md).
4. Audit changes to CALMET diagnostics and resulting fields separately from P5 data-format correctness; do not replace scientific comparisons with “process exited zero.”

See also [P4 READ62 status](https://github.com/RRain001/CTEAS/blob/codex/cteas-p4-read62-reference/docs/reconstruction_cpp/P4_READ62_IMPLEMENTATION_STATUS.md). P4's **>80% original valid 00/12 sounding profile** rule is deliberately different from P5's **strict >90% unique original full-hour surface ISD and ISD-Lite** external source gate.
