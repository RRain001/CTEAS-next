# Project Structure For ChatGPT

Date: 2026-06-26

Scope:
- Project root: `.`
- This report is read-only and based on on-disk inspection only
- `win_puff` is out of scope

## 1. Basic Environment Information

Commands requested by `plan.md` were executed from `.`.

### Host

```text
uname -a:
Darwin songruyaotianqingyou.local 25.4.0 Darwin Kernel Version 25.4.0 ... RELEASE_ARM64_T8142 arm64

uname -m:
arm64
```

### Python

```text
which python3:
/usr/local/bin/python3

python3 --version:
Python 3.14.5

python3 -c "import platform, sys; ...":
Darwin x86_64
/usr/local/opt/python@3.14/bin/python3.14
```

### Docker

```text
docker --version:
Docker version 29.5.3, build d1c06ef

docker buildx version:
github.com/docker/buildx v0.34.1-desktop.1 c79576280a671664e17eb68da98ec3136b614aed

docker run --rm --platform linux/arm64 debian:12 uname -m:
aarch64

docker run --rm --platform linux/amd64 debian:12 uname -m:
x86_64
```

### Interpretation

- Real host machine is Apple Silicon ARM64.
- Current `python3` process is running as `Darwin x86_64`, so Python is under Rosetta/x86_64 compatibility.
- Docker on this machine can start both:
  - `linux/arm64`
  - `linux/amd64`

This distinction matters because project Python code checks `platform.system()` and `platform.machine()`, not `uname -m`.

## 2. Project Directory Tree

### High-level structure

Top-level directories found:

```text
.
./bin
./bin/linux-arm64
./bin/linux-x86_64
./bin/windows-x86_64
./calpuff_terrain_and_landuse_data
./docker
./docs
./engine
./project
./scripts
```

### Directory roles

- GUI code:
  - `engine/gui/`
  - `engine/pyside_gui.py`
- Core code:
  - `engine/core/`
- Preprocess code:
  - `engine/preprocess/`
- CALMET code:
  - `engine/run_met/`
- CALPUFF code:
  - `engine/run_puff/`
- Postprocessing code:
  - `engine/postprocessing/`
- Case data:
  - `project/cases/<case>/`
- Current active case link:
  - `project/current`
- Binary directory:
  - `bin/`
- Vendor / third-party program directory:
  - `engine/vendor/`
  - `engine/vendor/bin/`
  - `engine/vendor/src/`
- Static terrain / landuse datasets:
  - `calpuff_terrain_and_landuse_data/`

### `project/current`

`project/current` is a symbolic link, not a real directory.

```text
project/current -> cases/smoke5d
```

This means the active case is switched by moving the symlink target, while actual case content stays under `project/cases/<case>/`.

### Cases present on disk

```text
project/cases/123
project/cases/smoke5d
project/cases/test
```

### Notes on directory naming

- `bin/linux-arm64/` currently exists but contains only `.gitkeep`.
- `bin/windows-x86_64/` currently exists but contains only `.gitkeep`.
- Real runnable native binaries currently exist only under `bin/linux-x86_64/`.
- A logical `DATA_DIR` exists in `engine/core/paths.py`, but no top-level `data/` directory is currently present in the inspected tree.

## 3. Python Entrypoints And Module Entrypoints

## Unified launcher

Top-level shell launcher:

- `calpuff-cli`

Behavior:

- `./calpuff-cli webgui` -> removed with explicit error
- `./calpuff-cli desktopgui` -> `python -m engine.ui.desktop.main`
- `./calpuff-cli streamlitgui` -> removed with explicit error
- anything else -> `python -m engine.orchestrator.cli`

It prefers project `.venv/bin/python`, otherwise falls back to system `python3`.

## GUI entrypoints

### Desktop GUI

- Module:
  - `engine.ui.desktop.main`
- Compatibility module:
  - `engine.pyside_gui`
- Backing PySide6 window code:
  - `engine/gui/workbench.py`

Recommended commands:

```bash
./calpuff-cli desktopgui
```

or

```bash
python3 -m engine.ui.desktop.main
```

### Removed web GUI

- `engine.gui` 现在只保留废弃提示，不再启动 Web 服务。

## Orchestrator entrypoint

- Module:
  - `engine.orchestrator.cli`
- Command structure:
  - subcommand `run`
  - `--case`
  - `--stage` in `preprocess|upperair|surface|calmet|calpuff|all`
  - `--resume`

Recommended commands:

```bash
python3 -m engine.orchestrator.cli run --case smoke5d --stage all
python3 -m engine.orchestrator.cli run --case smoke5d --stage all --resume
python3 -m engine.orchestrator.cli run --case smoke5d --stage met
```

## READ62 / upperair entrypoints

Main upperair pipeline:

- `engine.preprocess.read62_upperair_data.run_upperair_pipeline`

Sub-steps:

- `engine.preprocess.read62_upperair_data.download_igra`
- `engine.preprocess.read62_upperair_data.parse_igra_to_csv`
- `engine.preprocess.read62_upperair_data.read`
- `engine.preprocess.read62_upperair_data.run_read62`
- `engine.preprocess.read62_upperair_data.merge_final_upperair`

Recommended commands:

```bash
python3 -m engine.preprocess.read62_upperair_data.run_upperair_pipeline --python python3
python3 -m engine.preprocess.read62_upperair_data.run_upperair_pipeline --python python3 --skip-download
python3 -m engine.preprocess.read62_upperair_data.run_read62 --case smoke5d --year 2023
```

## SMERGE / surface met entrypoints

Main surface pipeline:

- `engine.preprocess.smerge_surf_data.run_isd_surface_pipeline`

Sub-steps:

- `engine.preprocess.smerge_surf_data.download_isd_by_grid`
- `engine.preprocess.smerge_surf_data.isd_to_smerge_and_fill`
- `engine.preprocess.smerge_surf_data.clean_merge_filled_by_research_time`
- `engine.preprocess.smerge_surf_data.convert_cleaned_to_smerge_ready`
- `engine.preprocess.smerge_surf_data.generate_smerge_input_sections`
- `engine.preprocess.smerge_surf_data.run_smerge_and_monitor`

Recommended commands:

```bash
python3 -m engine.preprocess.smerge_surf_data.run_isd_surface_pipeline --python python3
python3 -m engine.preprocess.smerge_surf_data.run_isd_surface_pipeline --python python3 --skip-download
python3 -m engine.preprocess.smerge_surf_data.run_smerge_and_monitor
```

Observed bug to record only:

- `engine/preprocess/smerge_surf_data/run_smerge_and_monitor.py` uses `subprocess.STDOUT` but does not import `subprocess`.

## Preprocess aggregator entrypoint

- Module:
  - `engine.preprocess.bin.run_preprocessing_pipeline`

Recommended commands:

```bash
python3 -m engine.preprocess.bin.run_preprocessing_pipeline --case smoke5d
python3 -m engine.preprocess.bin.run_preprocessing_pipeline --case smoke5d --only-upperair
python3 -m engine.preprocess.bin.run_preprocessing_pipeline --case smoke5d --only-surface
```

## CALMET entrypoints

- Prepare:
  - `engine.run_met.prepare_met`
- Run:
  - `engine.run_met.run_met`

Recommended commands:

```bash
python3 -m engine.run_met.prepare_met --case smoke5d
python3 -m engine.run_met.run_met --case smoke5d
python3 -m engine.run_met.run_met --case smoke5d --skip-prepare
```

## CALPUFF entrypoints

- Prepare:
  - `engine.run_puff.prepare_puff`
- Run:
  - `engine.run_puff.run_puff`

Recommended commands:

```bash
python3 -m engine.run_puff.prepare_puff --case smoke5d
python3 -m engine.run_puff.run_puff --case smoke5d
python3 -m engine.run_puff.run_puff --case smoke5d --skip-prepare
```

## Postprocessing entrypoints

Main CLI modules:

- `engine.postprocessing.plot_puff_snapshot`
- `engine.postprocessing.plot_puff_animation`
- `engine.postprocessing.plot_puff_annual`
- `engine.postprocessing.plot_puff_seasonal`
- `engine.postprocessing.extract_point_data`
- `engine.postprocessing.plot_daily_from_puff`
- `engine.postprocessing.plot_daily_concentration_fangda`
- `engine.postprocessing.plot_windrose_style`

Recommended commands:

```bash
python3 -m engine.postprocessing.plot_puff_snapshot --mode snapshot --conc-file project/current/run/puff/puff.con --met-inp project/current/run/met/met.inp
python3 -m engine.postprocessing.extract_point_data --conc-file project/current/run/puff/puff.con --met-inp project/current/run/met/met.inp --x 500.0 --y 3540.436
python3 -m engine.postprocessing.plot_daily_from_puff --conc-file project/current/run/puff/puff.con --met-inp project/current/run/met/met.inp --x 500.0 --y 3540.436
python3 -m engine.postprocessing.plot_windrose_style --csv project/current/met/surface/isd2smerge_ready/583210-99999.csv --month-column Month --direction-column deg --speed-column ms-1
```

## 4. Current Path Module And Platform Module

### `TUTORIAL_ROOT`

In `engine/core/paths.py`:

```python
TUTORIAL_ROOT = Path(__file__).resolve().parents[2]
```

Given the current on-disk layout, this resolves to:

```text
.
```

### `project/current`

In `engine/core/paths.py`:

```python
PROJECT_DIR = TUTORIAL_ROOT / "project"
CURRENT_PROJECT_DIR = PROJECT_DIR / "current"
```

So the path object points to:

```text
./project/current
```

At runtime this is a symlink to:

```text
project/cases/smoke5d
```

### `bin/linux-x86_64`

In `engine/core/paths.py`:

```python
BIN_DIR = TUTORIAL_ROOT / "bin"
```

In `engine/core/platform_utils.py`:

```python
LINUX_X86_64 = "linux-x86_64"
```

So Linux x86_64 native binaries resolve under:

```text
./bin/linux-x86_64
```

### Current platform detection

`engine/core/platform_utils.py` only recognizes:

- `linux + x86_64|amd64` -> `linux-x86_64`
- `linux + aarch64|arm64` -> `linux-arm64`
- `windows + x86_64|amd64` -> `windows-x86_64`

Everything else raises:

```python
UnsupportedPlatformError
```

### Will `darwin/x86_64` or `darwin/arm64` be rejected?

Yes.

Current code has no macOS branch, so both of these are rejected:

- `system='darwin', machine='x86_64'`
- `system='darwin', machine='arm64'`

Important nuance:

- `engine.core.paths.executable_path(..., platform=None)` catches unsupported host and falls back to `linux-x86_64` for path resolution only.
- `engine.core.runner.run_binary(...)` calls `get_platform_key()` directly unless an explicit `platform_key` is supplied.
- Therefore:
  - binary path lookup may still point at `bin/linux-x86_64/*.x`
  - actual binary execution on macOS is still rejected

### Does current code support Docker `linux-x86_64`?

Yes, in principle.

If Python inside the container reports:

```text
platform.system() == "Linux"
platform.machine() == "x86_64"
```

then `get_platform_key()` returns `linux-x86_64`, and `run_binary()` will use `bin/linux-x86_64/<name>.x`.

### Does current code support future Docker `linux-arm64`?

Yes, in principle.

If Python inside the container reports:

```text
platform.system() == "Linux"
platform.machine() in {"aarch64", "arm64"}
```

then `get_platform_key()` returns `linux-arm64`.

This will only be useful after real ARM64 binaries exist under:

```text
bin/linux-arm64/*.x
```

## 5. Native Binary Inventory

### Runtime binary directories

- Primary normalized runtime directory:
  - `bin/linux-x86_64/`
- Legacy runtime directory:
  - `engine/vendor/bin/`
- Source-tree duplicate copies:
  - `engine/vendor/src/*/*.x`

### Primary runtime binaries

All primary runtime binaries currently present under `bin/linux-x86_64/` are Linux x86_64 ELF executables.

| File | `file` output summary | Executable | Inferred module |
| -- | -- | -- | -- |
| `bin/linux-x86_64/terrel.x` | ELF 64-bit LSB executable, x86-64, dynamically linked, GNU/Linux 3.2.0 | yes | terrain preprocessing / TERREL |
| `bin/linux-x86_64/ctgproc.x` | ELF 64-bit LSB executable, x86-64, dynamically linked, GNU/Linux 3.2.0 | yes | landuse preprocessing / CTGPROC |
| `bin/linux-x86_64/makegeo.x` | ELF 64-bit LSB executable, x86-64, dynamically linked, GNU/Linux 3.2.0 | yes | geo merge / MAKEGEO |
| `bin/linux-x86_64/read62.x` | ELF 64-bit LSB executable, x86-64, dynamically linked, GNU/Linux 3.2.0 | yes | upperair conversion / READ62 |
| `bin/linux-x86_64/smerge.x` | ELF 64-bit LSB executable, x86-64, dynamically linked, GNU/Linux 3.2.0 | yes | surface meteorology merge / SMERGE |
| `bin/linux-x86_64/met.x` | ELF 64-bit LSB executable, x86-64, dynamically linked, GNU/Linux 3.2.0 | yes | diagnostic wind field / CALMET |
| `bin/linux-x86_64/puff.x` | ELF 64-bit LSB executable, x86-64, dynamically linked, GNU/Linux 3.2.0 | yes | puff dispersion model / CALPUFF |

### Duplicate copies

Historical cleanup records show that equivalent ELF x86_64 copies once existed in:

- `engine/vendor/bin/*.x`
- `engine/vendor/src/*/*.x`

Those duplicates are no longer part of the active runtime layout; the normalized target layout is `bin/<platform>/`.

### Current architecture status

- `bin/linux-x86_64/*.x`: present and real ELF x86_64 binaries
- `bin/linux-arm64/`: empty placeholder only
- `bin/windows-x86_64/`: empty placeholder only

## 6. `.x` Call Relationships

Current Python code resolves native executables mostly through unified helpers:

- `engine.core.paths.resolve_executable()`
- `engine.core.paths.executable_path()`
- `engine.core.platform_utils.get_binary_path()`
- `engine.core.runner.run_binary()`

### READ62

- Python entry:
  - `engine.preprocess.read62_upperair_data.run_read62`
- Executable:
  - `read62.x`
- Resolution path:
  - `resolve_executable("read62")`
  - `run_binary("read62", ...)`

### SMERGE

- Python entry:
  - `engine.preprocess.smerge_surf_data.run_smerge_and_monitor`
- Executable:
  - `smerge.x`
- Resolution path:
  - `resolve_executable("smerge")`
  - `run_binary("smerge", ...)`

### CALMET

- Python entry:
  - `engine.run_met.run_met`
- Executable:
  - `met.x`
- Resolution path:
  - `resolve_executable("met")`
  - `run_binary("met", ...)`

### CALPUFF

- Python entry:
  - `engine.run_puff.run_puff`
- Executable:
  - `puff.x`
- Resolution path:
  - `resolve_executable("puff")`
  - `run_binary("puff", ...)`

### TERREL / CTGPROC / MAKEGEO

These are called from preprocess helper modules and use:

- `executable_path("<name>", platform="linux-x86_64")` for CLI default display
- `resolve_executable("<name>")` for actual execution

### Are paths now unified?

Mostly yes.

The main runtime `.x` call sites inspected in Python now flow through centralized helpers rather than directly concatenating `./xxx.x` paths.

### Are there still direct hardcoded `.x` paths?

No active hardcoded execution path was found in the inspected main runtime modules.

One remaining direct reference appears in a comment/docstring:

- `engine/preprocess/smerge_surf_data/run_smerge_and_monitor.py`
  - docstring still says `engine/vendor/bin/smerge.x smerge.inp`

That is documentation text, not the actual execution path.

## 7. Python Virtual Environment And Dependencies

### Dependency files found

Only this dependency file is present at root:

```text
requirements.txt
```

Not found:

- `pyproject.toml`
- `environment.yml`
- `setup.py`

### `requirements.txt`

```text
numpy==2.4.4
pandas==3.0.2
pyyaml==6.0.3
PySide6==6.11.0
matplotlib==3.10.9
imageio-ffmpeg==0.6.0
```

### Interpretation

- Current Python dependency declaration is minimal but sufficient for the visible Python layer.
- GUI depends on `PySide6`.
- Postprocessing depends on:
  - `matplotlib`
  - `numpy`
  - `pandas`
- YAML config loading depends on `pyyaml`.
- Animation / ffmpeg fallback support depends on `imageio-ffmpeg`.

### Does Docker runtime testing need `requirements.txt`?

Yes.

Reason:

- GUI is not needed for Docker runtime backend checks, but core orchestration and config loading still need Python dependencies such as `pyyaml`.
- Postprocessing checks need `numpy`, `pandas`, `matplotlib`.
- Running the same Python entrypoints inside Docker should use an isolated venv with `requirements.txt` installed.

## 8. Current Case Status

### Current case name

`project/current` points to:

```text
cases/smoke5d
```

So the active case is:

```text
smoke5d
```

### Key current inputs

Grid/config:

- `project/current/case.yaml`
- `project/current/grid/center_location`
- `project/current/grid/grid.cmn`
- `project/current/grid/research_time`

Upperair:

- `project/current/met/upperair/2023/CHM00058203-data.txt`
- `project/current/met/upperair/2023/pstop_hpa.txt`
- `project/current/met/upperair/2023/upperair_station_used_list.txt`
- `project/current/met/upperair/final/up_58203.dat`
- `project/current/met/upperair/final/stations.csv`

Surface:

- `project/current/met/surface/isd_raw/58321099999-2023.csv`
- `project/current/met/surface/final/surf.dat`
- `project/current/met/surface/final/stations.csv`
- `project/current/met/surface/isd2smerge_ready/583210-99999.csv`

Geo:

- `project/current/geo/terrel/terrel.dat`
- `project/current/geo/ctgproc/lu.dat`
- `project/current/geo/makegeo/geo.dat`

Run-stage working files:

- `project/current/run/read62/read62.inp`
- `project/current/run/smerge/smerge.inp`
- `project/current/run/met/met.inp`
- `project/current/run/puff/puff.inp`

### Existing outputs already on disk

Preprocess outputs:

- `project/current/geo/terrel/terrel.dat`
- `project/current/geo/ctgproc/lu.dat`
- `project/current/geo/makegeo/geo.dat`
- `project/current/met/upperair/final/up_58203.dat`
- `project/current/met/surface/final/surf.dat`

Model outputs:

- `project/current/deliverables/met/met.dat`
- `project/current/deliverables/met/met.lst`
- `project/current/deliverables/puff/puff.con`
- `project/current/run/puff/puff.lst`

Historical run records:

- `project/current/runs/20260514_*`

### Will READ62 / CALMET / CALPUFF overwrite current results?

Yes, potentially.

#### READ62

Likely overwrite targets:

- `project/current/run/read62/read62.inp`
- `project/current/met/upperair/<year>/fsl_data/up_*.dat`
- `project/current/met/upperair/<year>/read62_*.lst`
- after merge step, `project/current/met/upperair/final/up_*.dat`

#### CALMET

Likely overwrite targets:

- `project/current/run/met/met.inp`
- `project/current/run/met/met_runtime.log`
- `project/current/run/met/met.dat`
- `project/current/run/met/met.lst`

If run through orchestrator, deliverables may also be refreshed:

- `project/current/deliverables/met/met.dat`
- `project/current/deliverables/met/met.lst`

#### CALPUFF

Likely overwrite targets:

- `project/current/run/puff/puff.inp`
- `project/current/run/puff/puff_runtime.log`
- `project/current/run/puff/puff.lst`
- `project/current/run/puff/puff.con`

If run through orchestrator, deliverables may also be refreshed:

- `project/current/deliverables/puff/puff.con`

## 9. Docker Testing Recommendations

### A. Recommended script for testing existing Linux x86_64 `.x`

Target script name:

```text
scripts/test_linux_x86_64_runtime_in_docker.sh
```

Recommended content:

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="python:3.12-slim-bookworm"

docker run --rm \
  --platform linux/amd64 \
  -v "$ROOT_DIR:/work" \
  -w /work \
  "$IMAGE" \
  bash -lc '
set -euo pipefail

echo "=== system ==="
uname -a
uname -m
python3 -c "import platform, sys; print(platform.system(), platform.machine()); print(sys.executable)"

echo "=== apt deps ==="
apt-get update
apt-get install -y --no-install-recommends \
  bash \
  file \
  libgfortran5 \
  libquadmath0 \
  libstdc++6 \
  libx11-6 \
  libxext6 \
  libxrender1 \
  libglib2.0-0 \
  libfontconfig1 \
  fonts-dejavu-core
rm -rf /var/lib/apt/lists/*

echo "=== python venv ==="
python3 -m venv .venv-docker
. .venv-docker/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo "=== binary inventory ==="
file bin/linux-x86_64/*.x
ls -l bin/linux-x86_64/*.x
chmod +x bin/linux-x86_64/*.x

echo "=== platform check ==="
python - <<PY
from engine.core.platform_utils import get_platform_key
print("platform_key =", get_platform_key())
PY

echo "=== case info ==="
ls -la project/current
readlink project/current || true
find -L project/current -maxdepth 3 -type f | sort | head -120

echo "=== smoke: upperair/read62 ==="
if python -m engine.preprocess.read62_upperair_data.run_read62 --case smoke5d --year 2023; then
  echo "[OK] READ62 finished"
else
  echo "[FAIL] READ62 failed"
fi

echo "=== smoke: calmet ==="
if python -m engine.run_met.run_met --case smoke5d --skip-prepare; then
  echo "[OK] CALMET finished"
else
  echo "[FAIL] CALMET failed"
fi

echo "=== smoke: calpuff ==="
if python -m engine.run_puff.run_puff --case smoke5d --skip-prepare; then
  echo "[OK] CALPUFF finished"
else
  echo "[FAIL] CALPUFF failed"
fi

echo "=== inspect likely outputs ==="
find project/current/run -maxdepth 2 -type f | sort | tail -80
find project/current/deliverables -maxdepth 2 -type f | sort || true
'
```

### Why this script shape is recommended

- It matches current repo layout:
  - mount project to `/work`
  - use `bin/linux-x86_64/*.x`
  - use existing `project/current`
- It tests the real Python runtime path selection logic inside Linux.
- It separates failure classes:
  - missing shared libraries
  - missing Python deps
  - missing inputs
  - permission problems
  - native program runtime errors

### Failure interpretation guide

- If `python -c "from engine.core.platform_utils import get_platform_key"` fails:
  - Python environment or package path issue
- If `file bin/linux-x86_64/*.x` is OK but binary execution fails with loader errors:
  - missing Linux shared libraries
- If entrypoint fails before launching `.x`:
  - Python-side path/config/import bug
- If `.x` runs but output files are missing or logs report model errors:
  - program input or scientific workflow issue, not Docker itself

### B. Future Linux ARM64 `.x` testing

Do not implement yet, but recommended direction:

- Build true ARM64 binaries into:

```text
bin/linux-arm64/*.x
```

- Then run almost the same test flow with:

```text
--platform linux/arm64
```

- Inside container confirm:

```text
platform.system() == Linux
platform.machine() in {aarch64, arm64}
```

- Main differences from x86_64 plan:
  - use `bin/linux-arm64/*.x`
  - ensure ARM64-compatible Debian image and runtime libraries
  - verify any Fortran runtime package names in ARM64 container

## 10. Practical Summary For ChatGPT

If another model needs to understand this repo quickly, the shortest accurate mental model is:

- This is a Python-controlled CALPUFF workflow project.
- Python orchestrates case management, preprocessing, CALMET, CALPUFF, and postprocessing.
- Actual heavy native programs are `.x` executables.
- The normalized runtime binary layout is intended to be:
  - `bin/linux-x86_64/*.x`
  - `bin/linux-arm64/*.x`
  - `bin/windows-x86_64/*.exe`
- Current real binaries exist only for `linux-x86_64`.
- The active case is selected by `project/current` symlink.
- Actual case data lives under `project/cases/<case>/`.
- Runtime path resolution is mostly centralized in `engine/core/paths.py` and `engine/core/platform_utils.py`.
- Current binary execution is Linux/Windows only; macOS is not a supported runtime target for native `.x`.
- On this machine, Docker can run both `linux/amd64` and `linux/arm64`, so Docker is the correct way to test native Linux backends from macOS.
