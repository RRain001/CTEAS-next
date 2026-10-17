# Path Inventory

Scope: Python, YAML, shell, TOML, and INI files under the CTEAS project.

Scan command used:

```bash
rg -n '"/|'\''/|\\\\|project/current|project/|data/|output/|bin/|\.x|\.yaml|\.yml' . \
  -g '*.py' -g '*.yaml' -g '*.yml' -g '*.sh' -g '*.toml' -g '*.ini'
```

## Categories

| Category | Meaning | Handling |
| --- | --- | --- |
| `internal_project_path` | Path inside this repository or current case. | Use `engine.core.paths` constants/functions and `Path` joins. |
| `external_user_path` | User-selected external input or output path. | Keep as user input; convert to `Path` only at use sites. |
| `display_only_path` | Text shown to users, help strings, log labels, or diagnostics. | Keep when it is not used for file I/O; prefer dynamic path text when showing real paths. |
| `binary_path` | Native executable path or `.x` executable lookup. | Route through `executable_path()`, `resolve_executable()`, or `run_binary()`. |
| `config_relative_path` | YAML or generated YAML relative path such as `project/current/...`. | Keep as relative config; resolve through `resolve_case_path()`/`case_paths()`. |
| `shell_path` | Shell script relative path. | Keep when based on script-derived project root. |
| `uncertain` | Candidate that may be URL, regex, generated model input, or external path. | Do not modify without confirmation. |

## Modified Internal Project Paths

| File | Category | Change |
| --- | --- | --- |
| `engine/core/paths.py` | `internal_project_path` | Added canonical directory aliases and helper functions: `tutorial_path`, `project_path`, `current_project_path`, `case_path`, `engine_path`, `data_path`, `bin_path`, `output_path`, `config_path`. |
| `engine/validators/case_schema.py` | `internal_project_path` | Replaced `ENGINE_ROOT / "config" / ...` with `config_path(...)`. |
| `engine/gui/app.py` | `internal_project_path` | Reused `CASES_ROOT` from `engine.core.paths` instead of deriving the project root locally. |
| `engine/gui/workbench.py` | `internal_project_path`, `display_only_path` | Reused `current_project_path()`, `resolve_case_path()`, and `tutorial_path()` for current-case paths, GUI path resolution, and local font path. |
| `engine/postprocessing/_core.py` | `internal_project_path` | Replaced default CALPUFF/CALMET/postprocessing paths with `current_project_path(...)`; local font uses `tutorial_path(...)`. |
| `engine/postprocessing/plot_windrose_style.py` | `internal_project_path` | Replaced current-case defaults with `current_project_path(...)`; local font uses `tutorial_path(...)`. |
| `engine/postprocessing/plot_daily_concentration_fangda.py` | `internal_project_path` | Replaced current-case defaults with `current_project_path(...)`; local font uses `tutorial_path(...)`. |
| `engine/postprocessing/extract_point_data.py` | `internal_project_path` | Replaced default CALPUFF/CALMET/postprocessing paths with `current_project_path(...)`. |
| `engine/preprocess/grid/configure_grid_cmn.py` | `internal_project_path` | Replaced local project-root derivation with `current_project_path(...)` and `VENDOR_SRC_DIR`. |
| `engine/preprocess/read62_upperair_data/*.py` | `internal_project_path` | Replaced local project-root derivation with `current_project_path(...)`, `case_path(...)`, and `engine_path(...)` where applicable. |
| `engine/preprocess/smerge_surf_data/*.py` | `internal_project_path` | Replaced local project-root/current-case/resource paths with `current_project_path(...)` and `engine_path(...)` where applicable. |
| `engine/preprocess/ctgproc/auto_select_landuse_to_ctgproc.py` | `internal_project_path`, `binary_path` | Replaced current-case and landuse defaults with unified helpers; retained existing executable lookup functions. |
| `engine/preprocess/terrel/auto_select_srtm_to_terrel.py` | `internal_project_path`, `binary_path` | Replaced current-case and SRTM defaults with unified helpers; retained existing executable lookup functions. |
| `engine/preprocess/makegeo/auto_config_makegeo.py` | `internal_project_path`, `binary_path` | Replaced current-case default with `current_project_path(...)`; retained existing executable lookup functions. |
| `engine/preprocess/bin/new_case.py` | `internal_project_path`, `config_relative_path` | Replaced local project-root/template/vendor paths with `CASES_ROOT`, `TEMPLATES_DIR`, and `VENDOR_SRC_DIR`; generated YAML relative paths are kept. |
| `engine/preprocess/bin/switch_case.py` | `internal_project_path` | Replaced local project-root/current symlink paths with `CASES_ROOT` and `CURRENT_LINK`. |
| `engine/preprocess/bin/run_preprocessing_pipeline.py` | `internal_project_path` | Replaced script root with `engine_path("preprocess")`; changed internal `Path("a/b")` literals to `Path("a") / "b"` joins. |
| `engine/orchestrator/cli.py` | `internal_project_path` | Changed deliverable relative paths from `Path("a/b")` to `Path("a") / "b"` joins. |

## Binary Paths

| File | Category | Handling |
| --- | --- | --- |
| `engine/core/platform_utils.py` | `binary_path` | Keeps the `.x` suffix mapping as the single filename rule for non-Windows binaries. |
| `engine/core/paths.py` | `binary_path` | Provides `executable_path()` and `resolve_executable()` on top of `BIN_DIR` and legacy vendor bin fallback. |
| `engine/core/runner.py` | `binary_path` | Provides `run_binary()` so callers do not embed executable paths. |
| `engine/preprocess/*`, `engine/run_met/run_met.py`, `engine/run_puff/run_puff.py` | `binary_path` | Native calls route through `resolve_executable()`, `executable_path()`, or `run_binary()`. |

## YAML And Config Paths

| File or pattern | Category | Handling |
| --- | --- | --- |
| `project/cases/*/case.yaml` | `config_relative_path` | Relative `project/current/...` values are kept because case loading resolves them through `case_paths()`/`resolve_case_path()`. |
| `engine/preprocess/bin/new_case.py` generated YAML template | `config_relative_path` | Relative `project/current/...` values are intentionally preserved. |
| `engine/config/case.schema.yaml` | `config_relative_path` | Schema metadata only; no platform executable path. |

## Shell Paths

| File | Category | Handling |
| --- | --- | --- |
| `bootstrap_venv.sh` | `shell_path` | Uses script-derived `ROOT_DIR`; `.venv/bin/python` is a relative virtualenv path. |
| `scripts/build_native_linux_x86_64.sh` | `shell_path`, `binary_path` | Uses script-derived `ROOT_DIR`; `bin/linux-x86_64/*.x` is target output relative to repo root. |
| `scripts/build_native_linux_arm64.sh` | `shell_path`, `binary_path` | Uses script-derived `ROOT_DIR`; `bin/linux-arm64/*.x` is target output relative to repo root. |
| `scripts/test_native_backend.sh` | `shell_path`, `binary_path` | Uses script-derived `ROOT_DIR`; platform bin dir is computed from argument or host platform. |

## Display-Only Or Non-Path Matches Kept

| File or pattern | Category | Reason kept |
| --- | --- | --- |
| `engine/gui/workbench.py` messages containing `project/current` | `display_only_path` | User-facing status and consistency text, not file I/O. |
| argparse help strings mentioning `project/cases` or `project/current` | `display_only_path` | CLI guidance only. |
| regex strings containing `/`, `\`, `.x`, or `.csv` | `display_only_path` | Pattern matching, not path construction. |
| URL strings in download scripts | `external_user_path` | Remote URLs, not local filesystem paths. |
| CALPUFF/CALMET template keys such as `XREFKM`, `xorig_km`, `point_x_km` | `display_only_path` | Domain variable names, not paths. |
| shebang lines `#!/usr/bin/env ...` | `display_only_path` | Interpreter directives, not project paths. |

## Uncertain

No remaining local filesystem path candidates were left in `uncertain` after this pass. Remaining grep hits are either centralized in `engine/core/paths.py`, display/help text, regex/domain strings, URLs, or YAML relative config strings.
