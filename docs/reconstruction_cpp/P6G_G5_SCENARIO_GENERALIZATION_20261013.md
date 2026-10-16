# P6G G5 — separate GUI, native-only orchestration, projected station selection

Date: 2026-10-13. **PR #54** (Draft, stacked onto PR #40). No legacy GUI/P4/P5/prepare_met production files are modified by the final PR diff. Original/reference Fortran sources and pinned Hefei 143h P6 physics are unchanged. GitHub-hosted Ubuntu runners only.

## 1. Architecture decision

**Keep the current product intact.** The existing `./calpuff-cli desktopgui` and `engine/gui/workbench.py` still use the old stage orchestration, and must remain a reference/legacy product while the native rebuild is incomplete.

The new G5 GUI is copied into `engine/gui_g5/`:

- `workbench.py`: physical copy of the PySide6 workbench, updated title, stage descriptions, case coordinates and G5-only execution command.
- `app.py`: separate case-management facade. New cases are created through `engine.gui_g5.case_setup`, **not** the legacy `engine.preprocess.bin.new_case`.
- `main.py` / `__main__.py`: independent GUI entrypoint `python3 -m engine.gui_g5.main` (`bash cteas-g5gui`).
- `case_setup.py`: defines case.yaml, distinct stack and domain centre, published WGS-84 UTM `grid.cmn` (SW corner rounded to 0.001 km), year window and vertical ZFACE; source coordinate is converted into the configured grid zone.
- `pipeline.py`: an exclusive G5 stage-control interface; **never falls back** to legacy `engine.orchestrator.cli`, original CALMET, original CALPUFF, or old preprocessing modules.

The UI represents native P1–P7 stages and their acceptance boundaries. Currently `preprocess` (P1–P3), `upperair` (full P4 writer), `met` (generic P6), `puff` (generic P7) and `all` are fail-closed. **Do not mark G5 end-to-end production-ready because its GUI can be opened.**

**P5 is the only provisionally executable native stage** in the new dispatcher. It requires an existing executable supplied explicitly by `CTEAS_G5_P5_BIN` and invokes `native_cpp.modules.p5_smerge.data_prep.prepare_inputs --native-cpp-bin … --stack-lat … --stack-lon … --execute`. This is still subject to its own source-data checks and is **not** a generic P6/P7 physics qualification. P4 native station selection and year-specific test code are implemented but lack the accepted generic publication scheduler for multiple annual UP.DAT inputs.

## 2. P4/P5 projected selection

The native reconstructed P4 IGRA and P5 NOAA selection share `engine/run_met/station_grid.py`:

- Use the published `grid.cmn` numerical UTM zone, hemisphere, origin, NX/NY and DGRIDKM, **not** approximated geographic bbox.
- Include all edges/corners; reject invalid projection, dimensions and unrepresentable station coordinates.
- Native P4 evaluates eligible stations per year and preserves its strict original 00/12 UTC sounding coverage and virtual-proxy policy.
- Native P5 retains independently qualified annual raw NOAA coverage, primary/secondary policy and station-identity controls.

**The old GUI's** `engine/preprocess/read62_upperair_data`, `engine/preprocess/smerge_surf_data`, `engine/preprocess/bin/run_preprocessing_pipeline.py`, `engine/run_met/prepare_met.py` and original `engine/gui/` are deliberately untouched. They retain historical behavior (including approximate legacy selectors). Only the copied G5 product must eventually use fully qualified native P1–P7 stage adapters.

## 3. Executing the new UI and diagnostics

Run `python3 -m engine.gui_g5.main` from the repository root with PySide6 installed. This does not replace `./calpuff-cli desktopgui`.

Create a new G5 case in that GUI, enter study-domain centre, study length/width, grid spacing, stack longitude/latitude, vertical layers and start/end, and save. The G5 copy publishes the derived `grid.cmn`, `center_location`, `stack_location` and `research_time`. Users must explicitly synchronize `project/current` for the intended case before running.

Headless stage inspection: `python3 -m engine.gui_g5.pipeline plan --case <case> --stage <preprocess|upperair|surface|met|puff|all>`. A plan with `ready: false` or a blocked native stage must not be construed as an accepted simulation. The `run` action refuses unsupported stages without executing a legacy workflow.

CI (Ubuntu): `.github/workflows/g5-gui-isolation.yml` and `.github/workflows/p4-p5-shared-utm.yml`. The former verifies source isolation, independent cases, stack-versus-centre UTM handling and fail-closed stage routing; the latter protects native P4/P5 selection tests. Headless source checks do not by themselves certify interactive PySide6 GUI behavior.

## 4. Next acceptance gates

1. Complete the native P4 multistation/multiyear UP.DAT scheduler and P1/P2/P3 dynamic-grid adapters for the G5 GUI, with exact metadata provenance and independent original reference testing.
2. Replace remaining P6D fixed 50×50×9, 100 m, one-surface/one-upper and 143-hour assumptions **only after** all dependent geometry, station buffers, previous-hour COMP state and output layout are audited.
3. Run original CALMET numerical parity over multiple NX/NY/NZ, resolutions, station combinations, regions and year boundaries, and keep frozen Hefei 143h G3/G4 45-field acceptance unmodified.
4. Accept complete P6F independently sourced header/metadata, integrate validated P7 multi-hour puff lifecycle and original CALPUFF scientific comparison.
5. Only then unlock the GUI's P6/P7/all commands. Do not silently opt into legacy physics or change numeric tolerances.

### Explicit status

- `G5_SEPARATE_GUI=IMPLEMENTED`
- `G5_GUI_HEADLESS_TESTS=SEE_CI`
- `G5_LEGACY_GUI_MODIFIED=FALSE`
- `G5_NATIVE_P4_P5_UTM=IMPLEMENTED_PENDING_FULL_REGRESSION`
- `G5_GENERIC_P6_P7_EXECUTION=BLOCKED_NOT_ACCEPTED`
- `G5_FULL_END_TO_END_PHYSICS=NOT_ACCEPTED`
