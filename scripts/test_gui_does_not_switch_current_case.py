#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from PySide6.QtWidgets import QApplication

from engine.core.case_manager import get_current_case_name
from engine.ui.desktop.workbench import MainWindow


def main() -> int:
    before = get_current_case_name()
    app = QApplication([])
    window = MainWindow()
    app.processEvents()
    after = get_current_case_name()
    window.close()

    print(f"before: {before}")
    print(f"after: {after}")
    if before != after:
        print("FAIL: MainWindow initialization switched current case", file=sys.stderr)
        return 1
    print("PASS: MainWindow initialization did not switch current case")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
