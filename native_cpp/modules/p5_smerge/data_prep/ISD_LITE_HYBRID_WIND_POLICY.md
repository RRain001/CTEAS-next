# P5 wind data contract — approved policy v2, 2026-10-11

**ACTIVE:** P5_ISD_LITE_WIND_V2_WHOLE_VECTOR_HOLD_CALM_REPLACE.
Older Scheme C (retain original zero wind) and Hybrid V1 (independently
forward-fill direction and speed) are superseded. Original CTEAS scripts
under engine/preprocess and vendor SMERGE/CALMET Fortran remain unchanged.

## P5 annual three-case station selection (approved 2026-10-11)

Use UTC calendar years, with raw coverage = unique original UTC-hour
records / 8760 (leap year: 8784), counting a record even if both wind
fields are missing. Do not confuse absent source hours with records whose
wind components are marked missing. Full ISD supplies all nonwind data;
same-station/year ISD-Lite supplies all wind.

**No station inside domain**: scan external station-history candidates
from nearest to farthest distance to stack. Select the first whose annual
raw record coverage is STRICTLY GREATER THAN 90% in BOTH complete ISD and
ISD-Lite, and relocate this as the ONLY virtual station. Exactly 90% fails.
Restart this search independently each year; never reuse a prior year's
station merely because it was previously eligible.

**Exactly one in-domain station**: keep it REGARDLESS of original record
coverage, provided both NOAA sources are parseable. Apply full-calendar
hour reconstruction and all approved stage-1 whole-vector missing repair
and stage-2 original-calm replacement to this one primary. Impossible
leading wind conditions fail explicitly; never fabricate observations.

**Two or more in-domain stations**: retain all in their true coordinates.
Every year choose exactly one PRIMARY with maximum original ISD-Lite
unique-hour coverage. Ties: higher original complete-ISD count, then
station ID ascending. The PRIMARY alone receives the full annual fill
and calm replacement used by the single in-domain case. All other
AUXILIARY stations keep ONLY their original hourly rows. If NOAA goes
18h -> 20h, do not insert 19h. Never fill any missing wind or nonwind
fields; never modify real calm to nonzero wind. Standardize (0deg,0m/s)
and (360deg,0m/s) to (0deg,0m/s). If either wind component is missing or
invalid, invalidate BOTH, encoding direction=9999 and speed=9999.
Every other missing met variable also uses 9999. ISD-Lite's source
-9999 is never written to SMERGE GENERIC. No -9999/9999 mixture.

Each annual station manifest records station_selection_case, primary_sid,
station wind_treatment, original source coverage and provenance. The
primary wind_treatment is COMPLETE_FILL_AND_CALM_REPLACE; an auxiliary is
RAW_SPARSE_STANDARDIZE_ONLY. An auxiliary *_filled.csv is a backwards-
compatible filename and does NOT mean any values have been filled.
Across multiple years SMERGE numeric station aliases are reconciled to
remain stable even when station roles or membership change.

**CALMET input gate**: every UTC hour in the active research interval must
have a complete moving wind vector from its annual PRIMARY (direction
in (0,360] and speed>0) after the P5 transformation, or processing fails.
This guarantees at least one noncalm model-input station per modeled
hour, not scientific accuracy. Partial wind vectors and long data gaps
are explicitly auditable.

### Original Fortran SMERGE sparse file EOF compatibility

The original vendor SMERGE v5.7.0 JDAT=8 reader was empirically
tested with a 144-hour, two-station case. When the auxiliary's final
original record stopped before the CALMET run ended, SMERGE could raise
Fortran Read-past-ENDFILE in RDWRITS even though interior missing hours
were handled with 9999. This is an ORIGINAL READER limitation.

Therefore, ONLY when targeting the original Fortran binary, the P5
control builder may create a separate temporary file under
run/smerge/original_smerge_sparse_runtime/ containing an extra all-9999
terminal record at the FINAL MODELED HOUR. It does NOT insert any
interior missing hours, does NOT replace calm winds, and does NOT
overwrite the sparse auxiliary in isd2smerge_ready/. The extra
terminal record is an I/O guard, NOT a real observation or
meteorological imputation. A future true native SMERGE writer can
handle sparse time axes without requiring this legacy adapter.

## Sources and coverage
- Download full NOAA Global Hourly ISD CSV and official same-station/year
  ISD-Lite gzip. Full ISD supplies all nonwind fields; ISD-Lite exclusively
  supplies wind direction and wind speed, without C/V/N or WND fallback.
- Merge by UTC hour, NOT by source row number. Reindex to every calendar-hour
  from Jan 1 00:00 through Dec 31 23:00, including gaps such as 18 -> 20
  (insert 19 with no original source).
- Annual raw coverage: UNIQUE UTC hours with an ISD-Lite record divided by
  calendar hours (8760; leap year 8784), including records where both wind
  fields are missing. Missing entire hours and present-but-invalid wind
  records must be tracked separately. Domain and external fallback selection
  rules changed: nearest qualifying external source, STRICT >90% raw-time
  coverage on BOTH official input sources; in-domain station collection does
  not silently discard records based on wind quality.
- ISD-Lite field 8 is integer wind direction (degrees, 0..360); field 9
  integer speed in 0.1 m/s units; original missing is -9999. Model input
  must use 9999 missing sentinel. No original C/V/N provenance is inferred.

## Stage 1: 数据清洗和缺测处理完毕
- Complete OBSERVED noncalm wind: WD in (0,360], WS>0 => use as observed.
  This is the ONLY allowable source for later whole-vector forward hold.
- (WD,WS)=(0,0) => standard original calm, retain (0,0).
- (WD,WS)=(360,0) => accepted original calm, normalize to (0,0),
  preserve original source WD and count separately.
- Any other combo (partial missing -9999, both missing, WD=0 WS>0, or
  other invalid), or an entire missing original hour => invalidate the
  ENTIRE wind vector, not just the absent component, then carry the latest
  whole valid OBSERVED noncalm (WD,WS) pair together, without time limit.
  Observed calm must never seed the carry.
- If no previous valid OBSERVED noncalm wind exists, retain both fields as
  9999 (strict mode aborts); never backfill a missing source hour or
  synthesize a bearing.
- Every other meteorological field (temperature, pressure, humidity,
  precipitation and cloud fields) independently carries its own previous
  valid value without a duration cap. Leading missing stays 9999.
- Stage file: USAF-WBAN-YEAR_cleaned.csv with same 3 GENERIC header lines.
  Sidecar USAF-WBAN-YEAR_cleaned.stage.json has exact Chinese completion
  status, without contaminating the fixed SMERGE GENERIC header.

## Stage 2: 静风插值处理完毕
- ONLY PRIMARY observed calm hours from original categories (0,0)/(360,0) are
  replaced; no forward-held synthetic calm is eligible.
- Identify maximal contiguous original calm runs first.
- Interior calm run with REAL observed positive-speed bearings on BOTH
  sides: use one fixed shortest-circular-arc midpoint for the ENTIRE run,
  and one fixed WS=0.5 m/s for EVERY hour in that run.
- All modeled positive-speed bearings are in (0,360], never WD=0.
  For example 350/10 ->360; 170/190 ->180; 360/360 ->360.
- Exactly antipodal endpoint bearings (difference 180) have two equally
  short arcs. Choose the CLOCKWISE arc from the *earlier* valid observation
  to the later one, so the midpoint is earlier bearing +90 degrees, modulo
  360, with 0 encoded as 360. Examples: 90->270 = 180; 270->90 = 360;
  1->181 = 91; 181->1 = 271. This replaces the former rule incorrectly
  returning 180 for every opposite pair. Direction order matters.
- Beginning-of-year calm without real positive prior anchor: copy BOTH
  direction AND speed from the next real positive observed vector for the
  entire run (do not force 0.5). End-of-year calm without next anchor:
  copy BOTH components from preceding real positive vector.
- If a whole year has no positive observed wind endpoint, abort rather than
  invent input.
- Interpolation endpoints must be ORIGINAL valid noncalm observations, never
  forward-held data or previously inserted artificial calm replacements.
- Output file: USAF-WBAN-YEAR_calm_interpolated.csv with corresponding
  sidecar .stage.json bearing Chinese stage status. The downstream
  compatible USAF-WBAN-YEAR_filled.csv is numerically identical to stage2,
  and becomes research-period-clipped isd2smerge_ready/USAF-WBAN.csv.

## Mandatory annual audit
- Total calendar hours, present ISD-Lite raw hours and ratio,
  entire absent source hours and ratio.
- All wind-invalid hours (include absent + present-but-invalid), count/rate.
- All original calms, count/rate, separate (0,0) and (360,0).
- Complete true positive wind hours, whole-pair held hours and longest
  age, stage1/stage2 valid-vector counts, calm run count.
- Interior constant half-mps replaced hours vs boundary copied hours.
- Every individual source/hold/replaced vector; source UTC and real
  calm interpolation endpoint UTC.
- Raw source ISD-Lite gzip SHA256 and station-year metadata.

## SMERGE/CALMET boundary
SMERGE v5.7.0 GENERIC JDAT=8 only reads numeric wind pair, not C/V/N.
Partial pair with 9999 becomes missing. Original CALMET local wind-speed
safety minima are separate from this user-prescribed human calm replacement.
The new P5 results deliberately differ from Scheme C: original calm is
now replaced before model input. **Reference Fortran SURF.DAT and CALMET
numerical validation have NOT yet been demonstrated.** Data completion and
user-chosen artificial calm replacement are not higher-quality observations.
