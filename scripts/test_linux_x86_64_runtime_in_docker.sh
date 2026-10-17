#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_IMAGE="${RUNTIME_IMAGE:-debian:12}"
CASE_NAME="${1:-smoke5d_docker_test}"
USE_DOCKER_PROXY="${USE_DOCKER_PROXY:-0}"
PROXY_HOST="${PROXY_HOST:-host.docker.internal}"
PROXY_PORT="${PROXY_PORT:-7897}"
DOCKER_HTTP_PROXY="${DOCKER_HTTP_PROXY:-http://${PROXY_HOST}:${PROXY_PORT}}"
DOCKER_HTTPS_PROXY="${DOCKER_HTTPS_PROXY:-http://${PROXY_HOST}:${PROXY_PORT}}"
DOCKER_ALL_PROXY="${DOCKER_ALL_PROXY:-http://${PROXY_HOST}:${PROXY_PORT}}"

echo "Docker platform: linux/amd64"
echo "Test case: ${CASE_NAME}"
echo "Proxy enabled: ${USE_DOCKER_PROXY}"
echo "Proxy host: ${PROXY_HOST}"
echo "Proxy port: ${PROXY_PORT}"
echo "Runtime image: ${RUNTIME_IMAGE}"

PROXY_ARGS=()
if [[ "${USE_DOCKER_PROXY}" == "1" ]]; then
  PROXY_ARGS=(
    -e "HTTP_PROXY=${DOCKER_HTTP_PROXY}"
    -e "HTTPS_PROXY=${DOCKER_HTTPS_PROXY}"
    -e "ALL_PROXY=${DOCKER_ALL_PROXY}"
    -e "http_proxy=${DOCKER_HTTP_PROXY}"
    -e "https_proxy=${DOCKER_HTTPS_PROXY}"
    -e "all_proxy=${DOCKER_ALL_PROXY}"
  )
fi

DOCKER_CMD=(
  docker run --rm
  --platform linux/amd64
  -e "CASE_NAME=${CASE_NAME}"
  -v "${ROOT_DIR}:/work"
  -w /work
)
if [[ ${#PROXY_ARGS[@]} -gt 0 ]]; then
  DOCKER_CMD+=("${PROXY_ARGS[@]}")
fi
DOCKER_CMD+=("${RUNTIME_IMAGE}" bash -lc)

if ! docker images --format '{{.Repository}}:{{.Tag}}' | grep -Fx "${RUNTIME_IMAGE}" >/dev/null 2>&1; then
  if ! docker pull "${RUNTIME_IMAGE}"; then
    echo "Docker image pull failed. Check Docker Desktop proxy settings or run with USE_DOCKER_PROXY=1." >&2
    exit 1
  fi
fi

"${DOCKER_CMD[@]}" '
set -euo pipefail

retry() {
  local n=1
  local max=3
  local delay=5
  until "$@"; do
    if [ "$n" -ge "$max" ]; then
      echo "[ERROR] Command failed after $n attempts: $*"
      return 1
    fi
    echo "[WARN] Command failed. Retry $n/$max after ${delay}s: $*"
    n=$((n+1))
    sleep "$delay"
  done
}

echo "=== system ==="
uname -a
uname -m

echo "=== apt deps ==="
if ! retry apt-get update; then
  echo "Container apt network failed. Check Clash Allow LAN and Docker proxy settings." >&2
  exit 10
fi
if ! retry apt-get install -y --no-install-recommends \
  bash \
  file \
  ca-certificates \
  python3 \
  python3-venv \
  python3-pip \
  libgfortran5 \
  libquadmath0 \
  libstdc++6 \
  libx11-6 \
  libxext6 \
  libxrender1 \
  libglib2.0-0 \
  libfontconfig1 \
  fonts-dejavu-core; then
  echo "[ERROR] apt dependency install failed" >&2
  exit 11
fi
rm -rf /var/lib/apt/lists/*

python3 -c "import platform, sys; print(platform.system(), platform.machine()); print(sys.executable)"

echo "=== python venv ==="
python3 -m venv .venv-docker
. .venv-docker/bin/activate
if ! retry python -m pip install --upgrade pip; then
  echo "[ERROR] pip bootstrap failed" >&2
  exit 12
fi
if ! retry python -m pip install -r requirements-docker-runtime.txt; then
  echo "[ERROR] pip runtime dependency install failed" >&2
  exit 13
fi

echo "=== compile check ==="
python -m compileall engine

echo "=== native binary check ==="
file bin/linux-x86_64/*.x
ls -l bin/linux-x86_64/*.x
chmod +x bin/linux-x86_64/*.x

echo "=== platform check ==="
python - <<PY
from engine.core.platform_utils import get_platform_key
print("platform_key =", get_platform_key())
PY

echo "=== registry check ==="
python scripts/check_native_binaries.py --platform linux-x86_64
python scripts/check_native_runner_mapping.py --platform linux-x86_64

echo "=== case check ==="
python scripts/check_current_case.py

echo "=== prepare checks ==="
python -m engine.run_met.prepare_met --case "$CASE_NAME"
python -m engine.run_puff.prepare_puff --case "$CASE_NAME"

echo "=== smoke native checks ==="
python -m engine.preprocess.read62_upperair_data.run_read62 --case "$CASE_NAME" --year 2023 || true
python -m engine.run_met.run_met --case "$CASE_NAME" --skip-prepare || true
python -m engine.run_puff.run_puff --case "$CASE_NAME" --skip-prepare || true

echo "=== inspect outputs ==="
find "project/cases/$CASE_NAME/run" -maxdepth 2 -type f | sort | tail -80 || true
find "project/cases/$CASE_NAME/deliverables" -maxdepth 2 -type f | sort || true
'
