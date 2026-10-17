# CTEAS-next agent instructions

## Scope and acceptance
- This is the **partial C++20** reconstruction of selected P1–P7 CALMET/CALPUFF pathways, **not** a whole-option Fortran replacement. Consult `README.md` and `docs/physics/CALMET_CALPUFF_OPTION_MATRIX.{md,csv}` before implementing or changing physics.
- C1 (2022 143h) and C2 (controlled synthetic 2024 143h) each **PASS_SCOPED**, as audited in `docs/science_acceptance/C1_C2_143H_RERUN_20261017.md`; Issue #6 is closed for these limited cases. **Full science acceptance NOT_READY.** Do not infer generic P6/P7 or `MWET>0` acceptance from these results.
- C1 original CALMET input was an SHA-locked frozen MET, not freshly rerun original Fortran CALMET. C2 is not independently measured atmospheric observations. Preserve these scientific qualifications.

## Source ownership and trusted scientific baseline
- Native C++ sources/tests: `native_cpp/`; Python legacy engine and GUI: `engine/`; G5 explicitly native-only authority: `engine/gui_g5/pipeline.py`, currently rejects generic P6/P7/all. Do **not** route G5 through `engine.orchestrator.cli` or legacy model executables.
- The unchanged original CALMET 6.5.0 Fortran source is at old `RRain001/CTEAS@dfad99a78ed84d655e21411c9d25eb0d2583bf13:engine/vendor/src/CALMET_v6.5.0_L150223/calmet.for`; CALPUFF 7.2.1 at `engine/vendor/src/CALPUFF_v7.2.1_L150618/calpuff.for`. Follow `docs/physics/VENDOR_SOURCE_LOCATOR.md`.
- Never add external `engine/vendor/**`, restricted CGIAR/SRTM terrain or fonts to the public repository, Action artifacts, logs or Docker images. Restore only from authorized local sources via `scripts/migration/configure_external_assets.py` with hash checks; see `docs/migration/THIRD_PARTY_ASSETS.md`.
- New physics work requires option-specific code authority, frozen input/source provenance, original-versus-native comparison, first differences and an updated option matrix. **Never** silently relax numerical tolerances or fake a PASS from empty plumes.

## Files and runtime
- Preserve existing tracked `project/cases/**` frozen fixtures as a deliberate scientific migration exception. Do not commit new generated case outputs, raw downloaded station data, binaries, virtual environments, giant artifacts or unrestricted local `project/` workspaces.
- `docs/migration/SOURCE_MANIFEST.json` records the **frozen pre-cleanup migration export**. Its original content can be checked on the historical commit, not assumed to describe the lean current `main` tree.
- Previously archived 119 disabled workflows, one-off P6 scripts and obsolete deployment helpers were removed from current head on 2026-10-17. Restore historical code from pre-cleanup `2f1747434e4217a99b9b9c6fed4d413e90006bd5` via `git show` only if an explicitly authorized scientific task requires it. See `docs/maintenance/REPOSITORY_CLEANUP_20261017.md`.
- Keep C++ work compatible with Ubuntu GCC/GFortran; packaging can target Linux AMD64/ARM64. Python minimum 3.11. `./bootstrap_venv.sh` sets up Python.
- Portable software tests: `scripts/migration/validate_ubuntu.py --portable` and `scripts/migration/validate_python.py --portable`, with `--out` **outside** the checkout. Four active Actions workflows in `.github/workflows/` are manual or strictly validated-request only; no default expensive push/PR runs.
- Preserve existing supported legacy PySide6 entrypoints unless expressly migrating them. Current core GUI windows are still separate; do not casually conflate legacy and G5 execution.
