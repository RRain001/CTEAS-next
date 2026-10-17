#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:-warmup}"
REMOTE_HOST="${REMOTE_HOST:-lhy-desktop}"
REMOTE_DIR="${REMOTE_DIR:-/home/lhy/CTEAS}"
CONFIRM_CUTOVER_DELETE="${CONFIRM_CUTOVER_DELETE:-}"
STATUS_OUT="${STATUS_OUT:-$(mktemp)}"
EXCLUDE_FILE="$(mktemp)"

cleanup() {
    rm -f "$STATUS_OUT" "$EXCLUDE_FILE"
}
trap cleanup EXIT

usage() {
    cat <<EOF
Usage: $(basename "$0") [warmup|cutover]

Environment:
  REMOTE_HOST   Target SSH host (default: lhy-desktop)
  REMOTE_DIR    Target directory (default: /home/lhy/CTEAS)
EOF
}

if [[ "$MODE" != "warmup" && "$MODE" != "cutover" ]]; then
    usage >&2
    exit 1
fi

for cmd in git rsync ssh; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "[ERROR] Missing command: $cmd" >&2
        exit 1
    fi
done

cat >"$EXCLUDE_FILE" <<'EOF'
.venv/
.git.backup_20260626_152023/
__pycache__/
.DS_Store
/plan.md
EOF

echo "[INFO] Sync mode: $MODE"
echo "[INFO] Remote: ${REMOTE_HOST}:${REMOTE_DIR}"
git -C "$ROOT_DIR" status --short | tee "$STATUS_OUT"

if grep -Eq '^\?\? ' "$STATUS_OUT"; then
    echo "[INFO] Untracked files are excluded by default only if matched in the rsync exclude set."
fi
if grep -Eq '^ D ' "$STATUS_OUT"; then
    echo "[INFO] Deleted tracked files will be mirrored on cutover sync."
fi

ssh "$REMOTE_HOST" "mkdir -p '$REMOTE_DIR'"

RSYNC_ARGS=(
    -aH
    --progress
    --human-readable
    --partial
    --exclude-from="$EXCLUDE_FILE"
    -e ssh
)

if [[ "$MODE" == "cutover" ]]; then
    if [[ "$CONFIRM_CUTOVER_DELETE" != "1" ]]; then
        echo "[ERROR] cutover mode enables rsync --delete and may remove remote files not present locally." >&2
        echo "[ERROR] Re-run with CONFIRM_CUTOVER_DELETE=1 to allow destructive remote deletion." >&2
        echo "[ERROR] Example: CONFIRM_CUTOVER_DELETE=1 ./scripts/sync_to_lhy_desktop.sh cutover" >&2
        exit 1
    fi
    RSYNC_ARGS+=(--delete)
fi

DELETE_ENABLED="no"
if [[ "$MODE" == "cutover" ]]; then
    DELETE_ENABLED="yes"
fi

echo "[INFO] Resolved mode: ${MODE}"
echo "[INFO] Resolved REMOTE_HOST: ${REMOTE_HOST}"
echo "[INFO] Resolved REMOTE_DIR: ${REMOTE_DIR}"
echo "[INFO] rsync --delete enabled: ${DELETE_ENABLED}"

rsync "${RSYNC_ARGS[@]}" "$ROOT_DIR"/ "${REMOTE_HOST}:${REMOTE_DIR}/"

ssh "$REMOTE_HOST" "cd '$REMOTE_DIR' && python3 - <<'PY'
import os
import subprocess

root = os.getcwd()
repaired = []
tracked = subprocess.check_output(['git', 'ls-files', '-z'])
for raw in tracked.split(b'\0'):
    if not raw:
        continue
    rel = raw.decode()
    path = os.path.join(root, rel)
    if os.path.exists(path):
        continue
    parent = os.path.dirname(path) or root
    if not os.path.isdir(parent):
        continue
    target = os.path.basename(path)
    candidates = [
        name for name in os.listdir(parent)
        if name != target and name.lower() == target.lower()
    ]
    if len(candidates) != 1:
        continue
    src = os.path.join(parent, candidates[0])
    os.rename(src, path)
    repaired.append((candidates[0], target))

if repaired:
    print('[INFO] Repaired case-sensitive paths:')
    for src, dst in repaired:
        print(f'  {src} -> {dst}')
PY
cd '$REMOTE_DIR' && git status --short || true"
