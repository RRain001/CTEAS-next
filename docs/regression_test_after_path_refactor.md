# Regression Test After Path Refactor

Date: 2026-06-26

Scope:
- Workspace: `.`
- Current case: `project/current -> cases/smoke5d`
- Excluded: `win_puff`

## Test Environment

- Host OS: macOS (`darwin/x86_64`)
- Default system Python: `python3 3.14.5`
- Project venv:
  - Rebuilt local `.venv` because the checked-in venv directory was incomplete (`bin/python` missing)
  - Installed `requirements.txt` into `.venv`
- Note:
  - Native `.x` files under `bin/linux-x86_64/` are Linux ELF executables
  - On this macOS host, binary execution is expected to stop at runtime platform checks

## Commands Run

### Static checks

```bash
python3 -m compileall engine
python3 -m py_compile engine/pyside_gui.py engine/gui/workbench.py
python3 -m py_compile engine/preprocess/bin/run_preprocessing_pipeline.py
python3 -m py_compile engine/preprocess/read62_upperair_data/run_upperair_pipeline.py engine/preprocess/smerge_surf_data/run_isd_surface_pipeline.py
```

### Path and config checks

```bash
ls -la project/current
find -L project/current -maxdepth 3 -type f | sort | head -100
find . -type f -name '*.x' -exec file {} \;
./.venv/bin/python scripts/check_paths.py
./.venv/bin/python -c "from pathlib import Path; from engine.validators.case_schema import validate_case_yaml; validate_case_yaml(Path('project/current/case.yaml')); print('[OK] case schema validation passed')"
```

### Module-level smoke checks

```bash
./.venv/bin/python -m engine.run_met.prepare_met --case smoke5d
./.venv/bin/python -m engine.run_puff.prepare_puff --case smoke5d
./.venv/bin/python -m engine.preprocess.grid.configure_grid_cmn
./.venv/bin/python -m engine.preprocess.terrel.auto_select_srtm_to_terrel --dry-run
./.venv/bin/python -m engine.preprocess.ctgproc.auto_select_landuse_to_ctgproc --dry-run
./.venv/bin/python -m engine.preprocess.makegeo.auto_config_makegeo --dry-run
./.venv/bin/python -c "import engine.pyside_gui, engine.gui.workbench, engine.preprocess.read62_upperair_data.run_read62, engine.preprocess.smerge_surf_data.run_smerge_and_monitor, engine.run_met.run_met, engine.run_puff.run_puff, engine.orchestrator.cli; print('[OK] GUI and runtime module imports passed')"
./.venv/bin/python -m engine.orchestrator.cli run --case smoke5d --stage all --resume
./.venv/bin/python -m engine.preprocess.read62_upperair_data.run_read62 --case smoke5d --year 2023
./.venv/bin/python -m engine.preprocess.smerge_surf_data.run_smerge_and_monitor
./.venv/bin/python -m engine.run_met.run_met --case smoke5d --skip-prepare
./.venv/bin/python -m engine.run_puff.run_puff --case smoke5d --skip-prepare
```

### Pure-Python postprocessing checks

```bash
./.venv/bin/python -m engine.postprocessing.plot_daily_from_puff \
  --conc-file project/current/run/puff/puff.con \
  --met-inp project/current/run/met/met.inp \
  --x 500.0 --y 3540.436 \
  --csv-output project/current/run/puff/postprocessing/regression_point_timeseries.csv \
  --output project/current/run/puff/postprocessing/regression_daily_concentration.png

./.venv/bin/python -m engine.postprocessing.plot_windrose_style \
  --output project/current/run/puff/postprocessing/regression_windrose.png \
  --csv project/current/met/surface/isd2smerge_ready/583210-99999.csv \
  --month-column Month --direction-column deg --speed-column ms-1

MPLBACKEND=Agg MPLCONFIGDIR=/private/tmp/cteas-mpl-snapshot \
./.venv/bin/python -m engine.postprocessing.plot_puff_snapshot \
  --mode snapshot \
  --conc-file project/current/run/puff/puff.con \
  --met-inp project/current/run/met/met.inp \
  --out project/current/run/puff/postprocessing/regression_snapshot.png \
  --scale linear --vmin 0.0005 --vmax 0.05 --threshold 1.2e-3 \
  --terrain-file project/current/run/puff/qaterr.grd
```

## Passed

- `engine` compileall passed.
- `engine/pyside_gui.py` and `engine/gui/workbench.py` py_compile passed.
- `engine/core/paths.py` self-check passed:
  - `TUTORIAL_ROOT=.`
  - `ENGINE_DIR=./engine`
  - `PROJECT_DIR=./project`
  - `CURRENT_PROJECT_DIR=./project/current`
  - `BIN_DIR=./bin`
  - All required executables resolved to `bin/linux-x86_64/*.x`
- `project/current` integrity check passed:
  - current case points to `smoke5d`
  - existing grid / met / geo / run / deliverables files are present
- Case schema validation passed.
- CALMET input rendering passed.
- CALPUFF input rendering passed.
- Grid configuration passed.
- TERREL dry-run path resolution passed.
- CTGPROC dry-run path resolution passed.
- MAKEGEO dry-run path resolution passed.
- GUI and runtime module import test passed.
- Pure-Python postprocessing passed:
  - `regression_point_timeseries.csv`
  - `regression_daily_concentration.png`
  - `regression_windrose.png`
  - `regression_snapshot.png`

## Failed

### 1. Orchestrator full resume run did not complete

- Command:
  - `./.venv/bin/python -m engine.orchestrator.cli run --case smoke5d --stage all --resume`
- Final blocking reason:
  - upperair stage enters `run_read62`
  - `engine.core.platform_utils.get_platform_key()` rejects local host `darwin/x86_64`
  - Linux ELF binary `read62.x` is not runnable on this macOS host
- Relation to path refactor:
  - Not a path regression
  - Path resolution succeeded; runtime platform guard blocked actual binary execution

### 2. READ62 runtime execution did not complete

- Command:
  - `./.venv/bin/python -m engine.preprocess.read62_upperair_data.run_read62 --case smoke5d --year 2023`
- Failure:
  - `Unsupported runtime platform: system='darwin', machine='x86_64'`
- Relation to path refactor:
  - Not a path regression
  - Binary path resolution succeeded, but host platform is unsupported for Linux `.x`

### 3. CALMET runtime execution did not complete

- Command:
  - `./.venv/bin/python -m engine.run_met.run_met --case smoke5d --skip-prepare`
- Failure:
  - `Unsupported runtime platform: system='darwin', machine='x86_64'`
- Relation to path refactor:
  - Not a path regression
  - Rendered input and path resolution are correct; actual ELF execution is blocked on macOS

### 4. CALPUFF runtime execution did not complete

- Command:
  - `./.venv/bin/python -m engine.run_puff.run_puff --case smoke5d --skip-prepare`
- Failure:
  - `Unsupported runtime platform: system='darwin', machine='x86_64'`
- Relation to path refactor:
  - Not a path regression
  - Rendered input and path resolution are correct; actual ELF execution is blocked on macOS

### 5. SMERGE runtime entry failed before platform check

- Command:
  - `./.venv/bin/python -m engine.preprocess.smerge_surf_data.run_smerge_and_monitor`
- Failure:
  - `NameError: name 'subprocess' is not defined`
- Relation to path refactor:
  - Not clearly related to path refactor
  - This is a code bug in the module itself and was not fixed in this round

## Files Fixed During This Regression Round

- `scripts/check_paths.py`
  - Added project-root `sys.path` bootstrap so the script works when executed directly from `scripts/`
- `engine/preprocess/bin/run_preprocessing_pipeline.py`
  - Changed child-step invocation from direct script path to `python -m ...`
- `engine/preprocess/read62_upperair_data/run_upperair_pipeline.py`
  - Changed child-step invocation from direct script path to `python -m ...`
- `engine/preprocess/smerge_surf_data/run_isd_surface_pipeline.py`
  - Changed child-step invocation from direct script path to `python -m ...`

## Still Needs Manual Confirmation

- Actual `.x` execution must be tested on a supported Linux host:
  - `read62.x`
  - `smerge.x`
  - `met.x`
  - `puff.x`
- If local GUI launch is required on macOS, use a writable Matplotlib config/cache directory to reduce font-cache noise.
- `engine.preprocess.smerge_surf_data.run_smerge_and_monitor` has an unrelated `subprocess` import bug that should be fixed separately if this module is expected to run.

## Conclusion

- Second-round path refactor did not break the main Python path organization:
  - unified roots are correct
  - current case resolves correctly
  - binary paths resolve correctly
  - render/dry-run/postprocessing paths work
- The newly found regressions fixed in this round were all invocation-path issues in pipeline subprocess launching.
- Remaining failures are dominated by host-platform incompatibility with Linux `.x` binaries, plus one unrelated `SMERGE` module bug.
