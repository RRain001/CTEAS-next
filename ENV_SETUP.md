# Environment Setup

## Repo Root

In the current remote migration context, the canonical repository root is:

```bash
/home/lhy/CTEAS
```

Commands below should be run from the repository root. If the repo is checked
out elsewhere, use the same commands from that local root without hardcoding
the path.

## Preferred Setup

`bootstrap_venv.sh` is the preferred environment setup entrypoint.

Requirements:

- Python `>= 3.11`
- `uv` preferred when available
- standard `python -m venv` + `pip` fallback when `uv` is not available

```bash
cd /home/lhy/CTEAS
./bootstrap_venv.sh
```

## Supported Overrides

`bootstrap_venv.sh` supports these environment variables:

- `PYTHON_BIN`: explicit Python executable for `venv` creation or version checks
- `UV_PYTHON`: Python version or interpreter hint passed to `uv venv`
- `PIP_INDEX`: overrides the default package index

Examples:

```bash
PYTHON_BIN=python3.11 ./bootstrap_venv.sh
UV_PYTHON=3.11 ./bootstrap_venv.sh
PIP_INDEX=https://pypi.org/simple ./bootstrap_venv.sh
```

## Behavior Notes

- If an existing `.venv` uses Python `< 3.11`, the script stops with an error
  instead of silently reusing it.
- When `uv` is available, the script prefers `uv venv` / `uv pip`.
- When `uv` is not available, the script falls back to `python -m venv`,
  `ensurepip` if needed, and `pip install -r requirements.txt`.

## Run Commands

```bash
./calpuff-cli run --case test --stage all
./calpuff-cli desktopgui
```

Do not copy `.venv` across machines. Recreate it from `requirements.txt` or by
rerunning `./bootstrap_venv.sh` on the target machine.
