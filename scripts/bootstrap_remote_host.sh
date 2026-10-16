#!/usr/bin/env bash
set -euo pipefail

PHASE="${1:-all}"
REMOTE_HOST="${REMOTE_HOST:-lhy-desktop}"
REMOTE_DIR="${REMOTE_DIR:-/home/lhy/CTEAS}"
PYTHON_VERSION="${PYTHON_VERSION:-3.11}"
CASE_NAME="${CASE_NAME:-smoke5d_docker_test}"

usage() {
    cat <<EOF
Usage: $(basename "$0") [pre-sync|post-sync|verify|all]

Environment:
  REMOTE_HOST     Target SSH host (default: lhy-desktop)
  REMOTE_DIR      Target directory (default: /home/lhy/CTEAS)
  PYTHON_VERSION  Python version for uv-managed venv (default: 3.11)
  CASE_NAME       Validation case name (default: smoke5d_docker_test)
EOF
}

if [[ "$PHASE" != "pre-sync" && "$PHASE" != "post-sync" && "$PHASE" != "verify" && "$PHASE" != "all" ]]; then
    usage >&2
    exit 1
fi

if ! command -v ssh >/dev/null 2>&1; then
    echo "[ERROR] ssh not found" >&2
    exit 1
fi

run_remote() {
    ssh "$REMOTE_HOST" "$@"
}

pre_sync() {
    run_remote bash -s -- "$REMOTE_DIR" "$PYTHON_VERSION" <<'EOF'
set -euo pipefail
remote_dir="$1"
python_version="$2"

sudo apt-get update
sudo apt-get install -y \
  rsync \
  git \
  file \
  build-essential \
  gfortran \
  libglib2.0-0 \
  libfontconfig1 \
  libx11-6 \
  libxext6 \
  libxrender1 \
  libxkbcommon-x11-0 \
  libxcb-cursor0

if ! command -v uv >/dev/null 2>&1; then
    echo "[ERROR] uv is required on remote host but not found." >&2
    exit 1
fi

mkdir -p "$remote_dir"
uv python install "$python_version"
EOF
}

post_sync() {
    run_remote bash -s -- "$REMOTE_DIR" "$PYTHON_VERSION" <<'EOF'
set -euo pipefail
remote_dir="$1"
python_version="$2"

cd "$remote_dir"
if [ ! -f bootstrap_venv.sh ]; then
    echo "[ERROR] bootstrap_venv.sh not found in $remote_dir" >&2
    exit 1
fi

chmod +x bootstrap_venv.sh calpuff-cli
UV_PYTHON="$python_version" REQUIRED_PYTHON_MINOR="$python_version" ./bootstrap_venv.sh
EOF
}

verify_remote() {
    run_remote bash -s -- "$REMOTE_DIR" "$CASE_NAME" <<'EOF'
set -euo pipefail
remote_dir="$1"
case_name="$2"

cd "$remote_dir"

echo "=== system ==="
uname -m
df -h /home/lhy
test -d "$remote_dir" || true

echo "=== python ==="
.venv/bin/python -V

echo "=== compileall ==="
.venv/bin/python -m compileall engine scripts

echo "=== checks ==="
.venv/bin/python scripts/check_current_case.py
.venv/bin/python scripts/check_native_binaries.py --platform linux-x86_64
.venv/bin/python scripts/check_native_runner_mapping.py --platform linux-x86_64

echo "=== prepare ==="
.venv/bin/python -m engine.run_met.prepare_met --case "$case_name"
.venv/bin/python -m engine.run_puff.prepare_puff --case "$case_name"

echo "=== gui import ==="
.venv/bin/python -c "import engine.gui.workbench, engine.ui.desktop.main; print('ok')"
EOF
}

case "$PHASE" in
    pre-sync)
        pre_sync
        ;;
    post-sync)
        post_sync
        ;;
    verify)
        verify_remote
        ;;
    all)
        pre_sync
        post_sync
        verify_remote
        ;;
esac
