#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

# 固定使用清华镜像源
PIP_INDEX="${PIP_INDEX:-https://pypi.tuna.tsinghua.edu.cn/simple}"
REQUIRED_PYTHON_MINOR="${REQUIRED_PYTHON_MINOR:-3.11}"
UV_PYTHON="${UV_PYTHON:-$REQUIRED_PYTHON_MINOR}"
PYTHON_BIN="${PYTHON_BIN:-}"

version_ge() {
    local python_bin="$1"
    local required_minor="$2"
    "$python_bin" - "$required_minor" <<'PY'
import sys

required = tuple(map(int, sys.argv[1].split(".")))
current = sys.version_info[:2]
raise SystemExit(0 if current >= required else 1)
PY
}

require_python() {
    local python_bin="$1"
    if ! command -v "$python_bin" >/dev/null 2>&1; then
        echo "[ERROR] Python executable not found: $python_bin"
        exit 1
    fi
    if ! version_ge "$python_bin" "$REQUIRED_PYTHON_MINOR"; then
        echo "[ERROR] $python_bin must be >= Python $REQUIRED_PYTHON_MINOR"
        "$python_bin" -V || true
        exit 1
    fi
}

if [ -n "$PYTHON_BIN" ]; then
    require_python "$PYTHON_BIN"
elif [ -x .venv/bin/python ] && ! version_ge .venv/bin/python "$REQUIRED_PYTHON_MINOR"; then
    echo "[ERROR] Existing .venv uses Python < $REQUIRED_PYTHON_MINOR"
    .venv/bin/python -V || true
    echo "[ERROR] Remove .venv or rerun with PYTHON_BIN/UV_PYTHON set to a compatible interpreter."
    exit 1
fi

if command -v uv >/dev/null 2>&1; then
    echo "[INFO] Using uv to create/update .venv"
    if [ ! -x .venv/bin/python ]; then
        if [ -n "$PYTHON_BIN" ]; then
            uv venv --seed --python "$PYTHON_BIN" .venv
        else
            uv venv --seed --python "$UV_PYTHON" .venv
        fi
    fi
    if ! .venv/bin/python -m pip -V >/dev/null 2>&1; then
        uv pip install --python .venv/bin/python pip
    fi
    uv pip install --python .venv/bin/python -i "$PIP_INDEX" -r requirements.txt
else
    echo "[INFO] uv not found, fallback to python venv + pip"
    if [ -z "$PYTHON_BIN" ]; then
        if ! command -v python3 >/dev/null 2>&1; then
            echo "[ERROR] python3 not found."
            exit 1
        fi
        PYTHON_BIN="python3"
    fi
    require_python "$PYTHON_BIN"
    if [ ! -x .venv/bin/python ]; then
        "$PYTHON_BIN" -m venv .venv
    fi
    if ! .venv/bin/python -m pip -V >/dev/null 2>&1; then
        .venv/bin/python -m ensurepip --upgrade || true
    fi
    .venv/bin/python -m pip install --upgrade pip
    .venv/bin/python -m pip config set global.index-url "$PIP_INDEX"
    .venv/bin/python -m pip install -i "$PIP_INDEX" -r requirements.txt
fi

echo "[INFO] Environment ready:"
.venv/bin/python -V
.venv/bin/python -m pip -V
echo "[INFO] Test imports:"
.venv/bin/python -c "import yaml, numpy, pandas; print('ok')"
