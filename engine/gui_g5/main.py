"""Separate entrypoint for the copied and adapted G5 PySide6 workbench."""
from __future__ import annotations

import sys


def main() -> int:
    try:
        from PySide6.QtWidgets import QApplication
    except ModuleNotFoundError as exc:
        if exc.name == "PySide6":
            print("Install PySide6 in the CTEAS Python environment to launch G5 GUI.", file=sys.stderr)
            return 2
        raise
    from .workbench import MainWindow, SOFTWARE_TITLE
    app = QApplication(sys.argv)
    app.setApplicationName(SOFTWARE_TITLE)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
