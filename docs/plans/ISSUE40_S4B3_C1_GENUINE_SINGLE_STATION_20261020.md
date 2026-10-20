# Issue #40 S4-B3 | genuine 2022 C1 1SS/1US first-hour probe, no new physics path

Prerequisite: S4-B2 [#203](https://github.com/RRain001/CTEAS-next/pull/203) merged as `81168122a02e6c23a40d0c9bf79b8d1ec5758f9d`. In CI the existing C2 2SS/2US 6h and new same-actor C2 candidate yielded **byte-identical** selected 270-field original-format results. This is **old C2 vs new C2**, not independently rerun Fortran.

B3 exercises the **same new executable and exact shared 17-stage G14 actor** against the repository-owned authentic, frozen C1 2022 1SS/1US input files:
- `project/cases/hefei5km_2022_reference_case_20261011/run/met/met.inp`
- `project/cases/hefei5km_2022_reference_case_20261011/geo/makegeo/geo.dat`
- `project/cases/hefei5km_2022_reference_case_20261011/run/smerge/surf.dat`
- `project/cases/hefei5km_2022_reference_case_20261011/met/upperair/final/up_58424.dat`

No input station counts, original 00/12 UTC upper soundings or observed SURF hourly fields are synthesized or modified. Original G19 and the G14 scheduler first validate the **entire 143h source**; the new `--probe-prefix-hours 1` then intentionally executes and serializes only the **first causal hour** while clearly reporting `PREFIX_PROBE=YES`, `DECLARED_SOURCE_HOURS=143`, and vendor parity NOT RUN. Production use still requires `--selected-experimental`; normal complete-hour execution still demands the entire source. The old frozen C1 P6D/E and C2 binaries and shared physical kernels are untouched.

**Gate:** first verify genuine C1 G19 1SS/1US source admission, then attempt exactly one live causal G14 selected hour through unchanged DIAGNO/COMP/P6F; always capture actual source file SHA/trace, and fail closed on errors. A failure becomes a specific source/physics/state blocker, not justification to modify formulas or fabricate weather. Success is at most `C1_1H_NEW_RUNNER_PRODUCED_UNVERIFIED`; never `C1_143H_ORIGINAL_PARITY_PASS`. Independent C1 frozen original-vs-native 45-field and actual Huoshan science remain upcoming B3/C/D.

No P7, Docker, wet deposition, S5 or unrelated physics.

## Actual 2026-10-20 observed result and resolved input mismatch

First original C1 source test failed in the strict generic UP reader: `UP.DAT sounding outside bounded header interval`, run [#39435611928](https://github.com/RRain001/CTEAS-next/actions/runs/39435611928). Direct inspection on the runner showed untouched READ62 C1 `UP.DAT` metadata declares **2022-JD1 00Z → JD6 23Z**, but the file contains **731 strictly increasing 00/12Z soundings** from **2022-01-01 00Z to 2023-01-01 00Z**. This is original archive supply beyond the short model period, not the user's invention of an extra observing station.

The existing strict standalone `read_upper_dynamic()` behavior is retained by default. Only `g19_load_original_source_case()` opts into a **bounded, real chronological trailing archive** of at most 366 days beyond the declared upper header end; earlier-than-header observations, wrong station IDs, malformed observations, ordering violations and original format controls remain fail closed. No source files are rewritten or false sounding times introduced. This is a source admission compatibility measure, **not proof unchanged original CALMET READ62 would use every archived sounding identically**. On [Actions #39436312655](https://github.com/RRain001/CTEAS-next/actions/runs/39436312655), genuine 1SS/1US G19 source admission passed: NX=50, NY=50, NZ=9, HOURS=143; candidate physics then hit the next independent blocker.

## New scientifically material G18A blocker (do NOT bypass)

The authentic first-hour shared selected G14 execution (same binary) reached COMP and rejected with `G18A input provenance or selected COMP scope`. In `p6g_g18a_selected_comp_mixht.hpp`, the selected G18A test-only COMP entry explicitly refuses `frame.stations.surface.size()<2||frame.stations.upper.size()<2`. This is a **two-surface/two-upper test acceptance guard**, not evidence that actual original CALMET or the underlying MIXHTST equation intrinsically requires two stations.

The diagnostic workflow now treats **exactly this known and identified restriction** as `BLOCKED_EXPECTED` with zero candidate output. Any other C1 failure is CI failure. Existing C2 6h byte-exact regression continues. Removing this restriction requires a separately audited **actual C1 source → selected COMP → P6F** numerical reconstruction with unchanged Fortran comparator and original single-site history; a source-only admission PASS is not the authority to delete it. Never replace the single-site inputs with a duplicated phantom station.

Latest acceptance: `S4_B3_C1_SOURCE_ADMISSION=PASS_SOURCE_ONLY`; `S4_B3_C1_SELECTED_COMP=UNSUPPORTED_1SS_1US`; `C1_SHARED_NEW_RUNNER_45FIELDS=NOT_ACCEPTED`; `C1_C2_143H_SINGLE_BINARY=NOT_RUN`; `NEW_SITE_ORIGINAL_CALMET=NOT_RUN`.
