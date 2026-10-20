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
