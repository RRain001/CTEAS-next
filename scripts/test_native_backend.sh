#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLATFORM="${1:-}"
REQUIRED=(terrel ctgproc makegeo read62 smerge met puff)

if [[ -z "$PLATFORM" ]]; then
  case "$(uname -s):$(uname -m)" in
    Linux:x86_64) PLATFORM="linux-x86_64" ;;
    Linux:aarch64|Linux:arm64) PLATFORM="linux-arm64" ;;
    *)
      echo "[WARN] Unsupported host for direct native execution: $(uname -s) $(uname -m)"
      echo "[INFO] Pass an explicit target such as: ./scripts/test_native_backend.sh linux-x86_64"
      exit 0
      ;;
  esac
fi

BIN_DIR="$ROOT_DIR/bin/$PLATFORM"
if [[ ! -d "$BIN_DIR" ]]; then
  echo "[ERROR] Binary directory not found: $BIN_DIR"
  exit 1
fi

for name in "${REQUIRED[@]}"; do
  binary_name="$name"
  bin="$BIN_DIR/${binary_name}.x"
  if [[ ! -f "$bin" ]]; then
    echo "[ERROR] Missing binary: $bin"
    exit 1
  fi
  chmod +x "$bin"
  echo "[CHECK] present: $bin"
done

for name in "${REQUIRED[@]}"; do
  binary_name="$name"
  bin="$BIN_DIR/${binary_name}.x"
  if "$bin" --help >/tmp/"${name}_help.out" 2>/tmp/"${name}_help.err"; then
    echo "[CHECK] $name --help exited 0"
  else
    echo "[INFO] $name --help unsupported or returned non-zero; recorded only"
  fi
done

file "$BIN_DIR"/*.x
echo "[OK] Native backend smoke checks completed for $PLATFORM"
