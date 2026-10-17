#!/bin/sh
# Exact migration portable test selections, not full scientific/Fortran parity.
set -eu
export PYTHONDONTWRITEBYTECODE=1
export QT_QPA_PLATFORM=offscreen
export CXX=/usr/bin/g++-12
export FC=/usr/bin/gfortran-12
mkdir -p /tmp/cteas-software /tmp/cteas-python

if python scripts/migration/validate_ubuntu.py \
    --out /tmp/cteas-software --jobs 2 --portable --tests-only; then
  echo 'CONTAINER_CPP_PORTABLE=PASS'
else
  rc=$?
  echo 'CONTAINER_CPP_PORTABLE=FAIL; reporting recent per-suite logs'
  for f in /tmp/cteas-software/*-configure.log /tmp/cteas-software/*-build.log /tmp/cteas-software/*-ctest.log; do
    if [ -f "$f" ]; then
      echo "----- $f -----"
      tail -n 25 "$f"
    fi
  done
  exit "$rc"
fi

if python scripts/migration/validate_python.py \
    --out /tmp/cteas-python --portable; then
  echo 'CONTAINER_PYTHON_PORTABLE=PASS'
else
  rc=$?
  tail -n 150 /tmp/cteas-python/python-unittest.log || true
  exit "$rc"
fi

python - <<'PY'
from PySide6.QtWidgets import QApplication
from engine.gui_g5.workbench import MainWindow, SOFTWARE_TITLE
from engine.gui_g5.pipeline import STAGES, BLOCKED
assert set(STAGES) == {'preprocess', 'upperair', 'surface', 'met', 'puff', 'all'}
assert all(x in BLOCKED for x in ('preprocess', 'upperair', 'met', 'puff', 'all'))
app = QApplication([])
window = MainWindow()
assert window.windowTitle() == SOFTWARE_TITLE
assert window.pages.count() >= 3 and window.field_widgets
window.close()
app.quit()
print('CONTAINER_G5_OFFSCREEN_AND_FAIL_CLOSED=PASS_SOFTWARE')
PY
