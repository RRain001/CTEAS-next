# P6G G30A/G30B — same-frame source P6F candidate and independent failure controls

Date: 2026-10-15. PR #63 remains **Draft / unmerged**. All results below
are an **original-format candidate** 45-field 12 × 12 × 9, 2SS + 2US
first-hour, synthetic-source, all-land scientific *handoff* audit, NOT
original CALMET multi-station 45-field meteorological numerical equality.

## Evidence

- [G30A original-source CI #38693752462](https://github.com/RRain001/CTEAS/actions/runs/38693752462):
  **COMPLETED SUCCESS** in Debug and Release after removal of one invalid
  clock assertion that hard-coded the daylight 2024-01-01 02–03Z interval.
- [G30A+G30B CI #38694120108](https://github.com/RRain001/CTEAS/actions/runs/38694120108):
  **COMPLETED SUCCESS Debug and Release**, including independently verified
  P6F 45-field candidate and all G30B negative-case rejections.
- G30 same-code P6G frozen physical source ownership was **PASS**.
  A successful earlier P6G suite must not be extrapolated to a later HEAD;
  use only exact-commit CI for final overall regression claims.

## G30A source P6F candidate chain

1. The same `G19FileBackedCase` supplies actual original-format
   met.inp, source GEO.DAT, SURF.DAT and physically ordered two UP files.
   The existing `UnifiedMultistationHourlyScheduler` alone creates the
   *uncommitted* original first-hour frame.
2. G26A executes actual selected source DIAGNO checkpoints [0..11].
   G26B executes selected native MIXHT/AVEMIX/WSTARR/TEMP3D [12..15].
   **No replacement of original formulas**: these kernels have separate
   G20–G29 literal original-Fortran source-stage numerical checks.
3. G30A directly reuses the earlier accepted source-isolated
   `g18c5_selected_p6f_fields` (43 REAL4 + 2 INT4 fields),
   `g18c6_selected_one_hour_dataset` (source GEO/stations, 45 ordered
   CALMET.DAT 2.1 records), and `g18d1_validate_p6f_precommit`
   (source stamped G14 tentative frame → prepared P6F bytes).
   The **unchanged frozen P6F C++ writer** is linked as a separate
   translation unit. No handwritten replacement binary serializer.
4. The resulting candidate is emitted to a temporary **test-only
   file**, never to production output. The source G14 last [16]
   CommitOutput stage still returns `{Unknown,false}`, and no G14
   memory, AA/BB, CGAMMA, or other station-clock commit occurs.
5. Python independently walks *raw Fortran sequential record framing*
   and verifies original version, comments marking test-only origin,
   source geometry/UTM and station counts, static GEO field shapes,
   45 canonical hourly labels/order, physical value validity,
   INT4 IPGT [1..6]/IRH [0..100], and source-controlled first-hour
   UTC and per-record times.
6. **Thirty-eight REAL4 record fields (38 × 144 = 5,472 values per case)**
   are bit-checked against *separate earlier stage exports*:
   G24 original source U/V/WFACE top-face (27 fields); G29 9-layer
   temperature (9 fields); G28 post-AVEMIX ZI and WSTAR (2 fields).
   Three scenarios × two build modes yield **32,832 exact REAL4
   source-handoff comparisons**. Zero mismatches.
   Remaining 7 fields (IPGT, USTAR, EL, TEMPK, RHO, QSW, IRH) have complete
   native source ownership, record presence and value-range checks but
   do NOT have an independent literal original-CALMET whole-hour
   numeric comparison in this stage.

## G30B fail-closed verification

`reference/test_g30_source_p6f_fail_closed.py` verifies the *unmodified
baseline candidate first passes* the independent verifier, then requires
validation **failure** for each deliberately corrupted case:

1. Change one legal REAL4 U-LEV value (without breaking record framing).
2. Alter a canonical V-LEV record label.
3. Change the CALMET header end hour, independently tied to original
   G21 first-hour UTC clock.
4. Change static NEARS first cell to an invalid station ordinal.
5. Break a Fortran sequential trailer length.
6. Change a single independent G29 TEMP3D source row while preserving
   the original candidate bytes.

All six expected invalid submissions were **REJECTED** independently
in both Debug and Release; none was accepted by the verifier.

## Source-clock bug avoided

Initial G30A candidate binary creation completed on the first Release
run, but the independent *test* wrongly expected every fixture to use
the daylight 2024-01-01 02–03 UTC hour. Normal/steep G19 first-hour
sources are around the 2023 year-end boundary. The checker now derives
the unique UTC hour end from the **source G21 FRADJ 1296-row output**,
checks the exact previous hour and decoded per-field CALMET packed
calendar. This is **not** a change to C++ meteorological/serialization
logic or any scientific tolerance.

## Remaining hard blockers before native 17-stage G14 acceptance

1. Produce an **independent original unmodified CALMET 6.5.0 multi-SS
   full 1-hour run** from the *same* original-format source input,
   with a provably independent original MET.DAT/CALMET.DAT output.
   Isolated original Fortran G20–G29 source-stage tests are NOT a
   substitute for this authority.
2. Compare **all 45 output fields** (6,480 scalar cells per hour),
   record-for-record and grid-cell-for-grid-cell, under the previously
   frozen original-science acceptance tolerance and full source
   metadata checks. Diagnose any real physical residual rather than
   interpolating/copying original output into the candidate.
3. Accept true `CommitOutput` stage 16 and the full 17-stage G14
   production authority only after independent original one-hour
   scientific parity, durable file publication/restart safety and
   rollback/clock atomicity all pass; currently still fail closed.
4. Extend independent original multi-station comparison to 6h, 143h,
   and full year including observed AA/BB turnover, real previous-hour
   COMP and non-synthetic station/source data. Regress the frozen
   PR #53 single-station 143h 45-field science for every new code HEAD.
5. PR #63 remains **Draft**. No merge, no premature completed G14 hour,
   no change to frozen single-station physical formulas, vendor Fortran
   or scientific acceptance tolerances.
