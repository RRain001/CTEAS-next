# CTEAS-next agent instructions

## Scope and acceptance
- This is the **partial C++20** reconstruction of selected P1–P7 CALMET/CALPUFF pathways, **not** a whole-option Fortran replacement. Consult `README.md` and `docs/physics/CALMET_CALPUFF_OPTION_MATRIX.{md,csv}` before implementing or changing physics.
- C1 (2022 143h) and C2 (controlled synthetic 2024 143h) each **PASS_SCOPED**, as audited in `docs/science_acceptance/C1_C2_143H_RERUN_20261017.md`; Issue #6 is closed for these limited cases. **Full science acceptance NOT_READY.** Do not infer generic P6/P7 or `MWET>0` acceptance from these results.
- C1 original CALMET input was an SHA-locked frozen MET, not freshly rerun original Fortran CALMET. C2 is not independently measured atmospheric observations. Preserve these scientific qualifications.

## Mandatory UTM grid-origin precision (owner decision 2026-10-17)
- **For every current and future case, computational UTM `XREFKM` and `YREFKM` are in km at exactly THREE decimal places (0.001 km = 1 m). Do not increase their precision.** Geographic center latitude/longitude used for projection can retain their original precision, but must not be passed directly to P1/P2 sampling without first quantizing the computed UTM grid origin.
- Treat the generated `grid.cmn` numeric origin as authoritative and carry precisely those three-decimal values into P1/P2/P3, CALMET, manifests and any original comparator. Mere `:.3f` display formatting is insufficient if the computation secretly uses higher-precision floats.
- Frozen Hefei 2022 case: `XREFKM=510.885`, `YREFKM=3531.269`; currently selected P1/P2/P3 C++ CLI must fail closed on any other value or non-three-decimal spelling, not silently round. Future new geographic cases require their own reviewed profile but **the same 3-decimal-km precision**.
- A frozen `MET.DAT` is only an independent reference for an exactly matching GEO/UP/SURF/control input set. Never cross-compare a new GEO with an old-GEO MET or relax science tolerances.
- Evidence: [S2-2C root-cause report](docs/plans/STAGE2_2C_GEO_ORIGIN_ROOT_CAUSE_20261017.md); original 493 exceedances came from 18 terrain heights sampled differently at sub-meter-shifted grid origins. Both original/native 143h same-input comparisons pass when origins match.

## Source ownership and trusted scientific baseline
- Native C++ sources/tests: `native_cpp/`; Python legacy engine and GUI: `engine/`; G5 explicitly native-only authority: `engine/gui_g5/pipeline.py`, currently rejects generic P6/P7/all. Do **not** route G5 through `engine.orchestrator.cli` or legacy model executables.
- The unchanged original CALMET 6.5.0 Fortran source is at old `RRain001/CTEAS@dfad99a78ed84d655e21411c9d25eb0d2583bf13:engine/vendor/src/CALMET_v6.5.0_L150223/calmet.for`; CALPUFF 7.2.1 at `engine/vendor/src/CALPUFF_v7.2.1_L150618/calpuff.for`. Follow `docs/physics/VENDOR_SOURCE_LOCATOR.md`.
- Never add external `engine/vendor/**`, restricted CGIAR/SRTM terrain or fonts to the public repository, Action artifacts, logs or Docker images. Restore only from authorized local sources via `scripts/migration/configure_external_assets.py` with hash checks; see `docs/migration/THIRD_PARTY_ASSETS.md`.
- New physics work requires option-specific code authority, frozen input/source provenance, original-versus-native comparison, first differences and an updated option matrix. **Never** silently relax numerical tolerances or fake a PASS from empty plumes.

## Files and runtime
- Preserve still-tracked `project/cases/**` raw inputs, input decks and hash-pinned reference baselines as a deliberate scientific migration exception. Duplicate `deliverables` and generated logs were pruned; do not recreate them as tracked artifacts. Do not commit new generated case outputs, raw downloaded station data, binaries, virtual environments, giant artifacts or unrestricted local `project/` workspaces.
- `docs/migration/SOURCE_MANIFEST.json` records the **frozen pre-cleanup migration export**. Its original content can be checked on the historical commit, not assumed to describe the lean current `main` tree.
- Previously archived 119 disabled workflows, one-off P6 scripts, redundant `deliverables/` and obsolete deployment helpers were removed from current head on 2026-10-17. Restore historical code from pre-cleanup `2f1747434e4217a99b9b9c6fed4d413e90006bd5` via `git show` only if an explicitly authorized scientific task requires it. See `docs/maintenance/REPOSITORY_CLEANUP_20261017.md`.
- Keep C++ work compatible with Ubuntu GCC/GFortran; packaging can target Linux AMD64/ARM64. Python minimum 3.11. `./bootstrap_venv.sh` sets up Python.
- Portable software tests: `scripts/migration/validate_ubuntu.py --portable` and `scripts/migration/validate_python.py --portable`, with `--out` **outside** the checkout. As of the owner's 2026-10-23 change, GitHub Actions supports **workflow_dispatch only**; routine development and software tests run in Ubuntu Docker. Preserve source SHA and numerical acceptance gates; pushing a PR does not automatically launch cloud CI. See `docs/ci/SCIENCE_TRIGGER_POLICY.md`.
- Preserve existing supported legacy PySide6 entrypoints unless expressly migrating them. Current core GUI windows are still separate; do not casually conflate legacy and G5 execution.

## Project-wide manual cloud CI (owner decision 2026-10-23)
- All GitHub Actions workflows are **workflow_dispatch only**. Never add automatic push/PR or Issue-comment triggers without new user authorization. Earlier comment-dispatch bridges and `/cteas run` commands are retired.
- Run ordinary compile, smoke, full and reproducible scientific cases in Ubuntu Docker. Authorized agents may optionally submit a direct `gh workflow run <name>.yml --ref <branch>` or equivalent Actions API dispatch when an independently checked cloud run is necessary; query final status and exact tested SHA before reporting acceptance.
- Historical GitHub CI / original science requirements, licensing, numerical thresholds and independent review remain unchanged; manual scheduling does not make unexecuted or missing scientific cases PASS. See `docs/ci/SCIENCE_TRIGGER_POLICY.md`.
