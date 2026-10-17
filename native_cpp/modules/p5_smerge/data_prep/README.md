> **P5 C++ NATIVE SURF.DAT WRITER NOW IMPLEMENTED (2026-10-11).**
> \`native_cpp/modules/p5_smerge/p5_surf_main.cpp\` writes a complete native
> formatted SURF.DAT for \`JDAT=8 IOFORM=2 IOPACK=0 LPREV=F LPCALC=F UTC\`,
> reading the same SMERGE.INP and GENERIC data as the unchanged vendor.
> Independent original SMERGE vs native C++ full-file byte parity:
> [synthetic two-station 721 bytes](https://github.com/RRain001/CTEAS/actions/runs/38110709094);
> [real Hefei six-day 13,841 bytes + original CALMET reading NATIVE output](https://github.com/RRain001/CTEAS/actions/runs/38110709086).
> Compile with \`cmake -S native_cpp/modules/p5_smerge -B /tmp/p5-native -DCMAKE_BUILD_TYPE=Debug\`
> then \`cmake --build /tmp/p5-native\`; publish with
> \`python3 -m native_cpp.modules.p5_smerge.data_prep.run_smerge_and_monitor --native-cpp-bin /tmp/p5-native/cteas_p5_smerge\`.
> **Unsupported:** IOFORM=1, packed IOPACK, LPREV, other JDAT/UTC offset and
> nondefault pressure estimation. The older provenance/snapshot sections below
> are HISTORICAL and do not describe this native writer; see
> [audited P5 status](../../../../docs/reconstruction_cpp/P5_SMERGE_IMPLEMENTATION_STATUS.md).
>
> **CURRENT P5 POLICY (2026-10-11):** See [ISD_LITE_HYBRID_WIND_POLICY.md](ISD_LITE_HYBRID_WIND_POLICY.md). The approved wind v2 discards the entire pair when either wind field is missing, holds the last *observed complete noncalm vector*, preserves original calm in a first-stage cleaned file, then replaces each original calm run by a constant shortest-arc midpoint WD and 0.5 m/s (calendar boundary copies nearest observed vector). All Scheme-C low-wind/zero-wind sections below are **historical only**, not active implementation. Full-ISD supplies only nonwind; ISD-Lite supplies wind. All nonwind variables now previous-value-fill missing source values.

# P5 surface meteorological preparation — frozen CTEAS Python snapshot

Source authority: RRain001/CTEAS main at 66e30ffb1ff4638a97af8a060748ce30b7578350 (2026-10-10). Original files stay untouched.

| Destination | Original under engine/preprocess/smerge_surf_data | Git blob SHA |
|---|---|---|
| download_isd_by_grid.py | download_isd_by_grid.py | aaf522a97639a05139182c5d4a0261443a2eb63d |
| isd_to_smerge_and_fill.py | isd_to_smerge_and_fill.py | 990886d8d0fe549f41708d635b04850619c27de4 |
| interpolate.py | interpolate.py | 4f417df5ea8c90e933165333690e2e992df473f2 |
| clean_merge_filled_by_research_time.py | clean_merge_filled_by_research_time.py | a2b0e235fe2315fa4f481a7ef77093f2ea04de7c |
| convert_cleaned_to_smerge_ready.py | convert_cleaned_to_smerge_ready.py | 0e2eb707e254edae47b60b35fa3469da84900240 |
| generate_smerge_input_sections.py | generate_smerge_input_sections.py | 3251a0c0512f402698eb403aee31eb08fde1bf10 |
| upstream_README.md | README.md | 8db934cd7207b1b8557127b9ecd45f9b75076074 |

The above Git blob hashes are **source snapshot provenance**, not current file hashes. Files deliberately edited in this scoped branch are download_isd_by_grid.py, isd_to_smerge_and_fill.py, interpolate.py, generate_smerge_input_sections.py, and prepare_inputs.py. Original source files under engine/preprocess/smerge_surf_data remain untouched. The copied run_smerge_and_monitor.py is additionally adapted for effective station coordinates, and is NOT invoked by the default preparation runner. Remaining upstream snapshots are byte-identical. That copied module has **exactly one explicit integration patch**:
- upstream: SCRIPT_DIR = engine_path("preprocess", "smerge_surf_data")
- copy: SCRIPT_DIR = Path(__file__).resolve().parent
This ensures subprocess invocation of interpolate.py uses **the copied script**, rather than silently routing to the original engine/preprocess script. No original file modified. All other algorithms remain unchanged.

From repo root:
- Dry run: python3 -m native_cpp.modules.p5_smerge.data_prep.prepare_inputs --expected-year 2022
- Download and prepare for the configured 2022 case: append --execute
- Existing NOAA input: --skip-download --execute
- Optional legacy SMERGE control generation: --write-legacy-control --execute (modifies project/current/run/smerge/smerge.inp; deliberately off by default)

Pipeline: NOAA NCEI Global Hourly CSV -> converted GENERIC -> *copied* interpolation -> research-time trim and merge -> id-specific ready GENERIC CSV. Original SMERGE input generation is optional; original run_smerge_and_monitor.py is not invoked and no SURF.DAT is published.

Dependencies: existing engine.core.paths, engine/resources/isd/isd-history.txt and non-Git project/current case directory; pandas and numpy for interpolation; external NOAA network to download. Actual 2022 station files are **not** tracked. Data paths remain project/current/met/surface/{isd_raw,isd2smerge_and_fill,isd2smerge_cleaned,isd2smerge_ready}. Default runner is dry-run to prevent overwriting existing case outputs unintentionally.

Important scientific audit items:
- Historical original CTEAS (not changed) clamped calm wind speed below 0.5 m/s to 0.5 in the SMERGE input. The P5 scoped copy now uses approved Scheme C and preserves 0/low speeds; see CALM_POLICY_C_VENDOR_AUDIT.md.
- Quality checks and precipitation conversion are not yet proven equivalent to Fortran SMERGE. The copied inputs are a preprocessing reproducibility path, not validation of a C++ SURF.DAT writer.
- Real 2022 data and original Fortran SURF.DAT output have not been captured on GitHub, so P5 status remains BLOCKED_FORTRAN_REFERENCE.

## 2026-10-10 NOAA endpoint migration
NOAA official June 23, 2026 notice: NCEI ISD CSV HTTPS endpoint retired July 31, 2026. Current official public NODD CSV location: https://noaa-global-hourly-pds.s3.amazonaws.com/ (same ISD CSV station-year keys). The copied download_isd_by_grid.py is intentionally patched to use this endpoint, and validates STATION/DATE/WND headers before writing any downloaded bytes. Previous 200-OK AWS S3 Explorer HTML is rejected. This changes download transport only, not scientific processing.
Reference: https://www.nesdis.noaa.gov/news/service-location-change-integrated-surface-data-global-hourly

## P5 station selection and prior-hour-only reconstruction (2026-10-10)

User-approved policy implemented ONLY in this P5 copy:

- Define the research rectangle from grid/center_location + grid/grid.cmn. For each target calendar year intersect with grid/research_time. All NOAA metadata stations spanning the relevant study interval **inside** that rectangle must be selected; coordinates/elevation stay at observed values.
- If zero eligible inside-domain stations, require explicit stack coordinates via --stack-lat and --stack-lon, or grid/stack_location in the same latitude/longitude YAML-style format. It is not valid to assume the grid center is the stack.
- Rank external stations by great-circle distance from the stack; download in increasing order; compute the **original unique observation hours for the entire calendar year** from the CSV DATE field (not filled/predicted hours). Require >=80% of 8,760 hours (>=7,008 in common years) or >=80% of 8,784 in leap years (>=7,028). Select exactly ONE nearest passing station. Rejected candidates can be downloaded for audit but are explicitly excluded from the processed manifest.
- For a virtual station, the *effective* lat/lon in surf_station_list_YEAR.txt is the stack lat/lon. Original source lat/lon, source ID, unmodified source elevation, relocation flag, coverage, and numeric IFSTN are persisted in station_selection_YEAR.json. Station elevation method is unchanged.
- Legacy six-digit numeric USAF station IDs are preserved if unique. Alphanumeric USAF and distinct WBAN records sharing one USAF receive deterministic seven-digit integer aliases, with collision detection that fails closed. The original 11-character NOAA identity is always preserved in filenames and provenance; scripts that generate SMERGE control blocks and final station metadata use the same alias.
- Temperature (DegC), humidity (%), and pressure (mb): after hourly indexing, each gap uses the preceding valid hour with **no duration cap**. Before the first valid hour, data remains missing (9999), rather than fabricating a future observation. Wind direction/speed also use unbounded forward fill; calm follows the user-approved **Scheme C** in the scoped copy.
- Precipitation (AA1-AA4/one-hour only) and cloud-cover missing-data pathways remain unchanged at the user's request. Neither is silently included in the new previous-hour filler.
- Selection and raw station filenames are enforced; rejected, out-of-case or stale station intermediates are not allowed to feed downstream SMERGE implicitly. Published final SURF.DAT numerical equivalence is NOT demonstrated.

Run (from repository root, use a clean research case):
python3 -m native_cpp.modules.p5_smerge.data_prep.prepare_inputs --expected-year 2022 --stack-lat 31.939774444 --stack-lon 117.141610855
Above is a dry-run. Add --execute for network/file writes.

## NOAA manual source verification

- Official NODD **CSV** bucket: https://noaa-global-hourly-pds.s3.amazonaws.com/
- Direct 2022 example (Luogang/Xinqiao, station 58321099999):
  https://noaa-global-hourly-pds.s3.amazonaws.com/2022/58321099999.csv
- Former retired endpoint: https://www.ncei.noaa.gov/data/global-hourly/access/2022/58321099999.csv
- NOAA migration notice:
  https://www.nesdis.noaa.gov/news/service-location-change-integrated-surface-data-global-hourly
- NOAA ISD CSV bucket registry: https://registry.opendata.aws/noaa-isd/

The copied downloader verifies full semantic header names STATION, DATE, WND, TMP, DEW, SLP and that every STATION cell agrees with the filename. Parsing uses csv.DictReader keyed by **column name**, never ordinal column position. WND is a five-part direction/QC/type/speed/QC compound; TMP and SLP likewise have independent compound decoding. Independent regression tests reorder the source columns, prove 25 C does not become wind, and verify missing headers fail closed. GF1, CIG and AA1-AA4 are optional input variables: absent/invalid observations retain legacy missing treatment. This is a schema guard, not a claim that all NOAA records are scientifically complete.

## User-approved Scheme C — 2026-10-10

Primary SMERGE GENERIC wind speeds preserve valid source or preceding-hour-held values without a P5 numerical floor (including 0.0 and speeds below 0.5 m/s). Wind direction is not fabricated by shortest-arc interpolation. The sole encoding exception: direction at *exact zero speed* becomes 0 degrees in GENERIC, since calm direction is undefined; original NOAA direction and independently held direction are retained in the wind audit.

The previous 0.5 m/s category survives as an audit-only low-wind flag, distinct from original CALMET's computational 0.0001, 0.001, stable 0.5 m/s, and ICALM=0 controls. The CTEAS original SMERGE and CALMET are unchanged and perform their own solver-specific calm handling. The legacy wind-audit column wind_speed_calculation_m_s is now equal to the unclamped GENERIC wind speed; new explicit wind_speed_generic_m_s and summary.wind_policy=P5_C_SOURCE_WIND_V1 avoid ambiguity.

Review the detailed source-provenance and constraints in CALM_POLICY_C_VENDOR_AUDIT.md. No Fortran numerical parity is claimed until comparing reference runs using *identical new inputs*.

## Hybrid wind source update (2026-10-11)

**Approved policy**: P5 wind direction/speed are read ONLY from the same-station/year NOAA ISD-Lite archive, with no C/V/N wind-type import and no fallback to full-ISD WND. Temperature, pressure, humidity and all other weather variables still originate from the full ISD CSV. Source data join by UTC hour, keep calm 0/0 versus north 360 distinct, use per-field previous noncalm-WD/previous-WS when source wind missing, never assign calm WD=0 to a later moving wind. Each component's original/held source and age is audited. Details: [ISD_LITE_HYBRID_WIND_POLICY.md](ISD_LITE_HYBRID_WIND_POLICY.md). Old sections above describe historic single-source design and are superseded for wind. This is not a claim of full Fortran numerical parity.
