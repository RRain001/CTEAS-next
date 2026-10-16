from __future__ import annotations

import sys

from engine.core.paths import TUTORIAL_ROOT

try:
    from PySide6.QtWidgets import QApplication
except ModuleNotFoundError as exc:  # pragma: no cover
    if exc.name == "PySide6":
        install_cmd = ".venv/bin/pip install PySide6"
        print(
            "Desktop GUI requires PySide6.\n"
            f"Run this from the repo root ({TUTORIAL_ROOT}):\n"
            f"  {install_cmd}",
            file=sys.stderr,
        )
        raise SystemExit(2)
    raise

from .workbench import MainWindow, SOFTWARE_TITLE


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(SOFTWARE_TITLE)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
