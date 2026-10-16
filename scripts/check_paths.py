#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys


SCRIPT_PATH = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.core.paths import (
    BIN_DIR,
    CONFIG_DIR,
    CURRENT_PROJECT_DIR,
    DATA_DIR,
    ENGINE_DIR,
    OUTPUT_DIR,
    PROJECT_DIR,
    TUTORIAL_ROOT,
    current_case_name,
    current_project_path,
    executable_path,
    resolve_executable,
)


EXECUTABLES = ("terrel", "ctgproc", "makegeo", "met", "puff", "read62", "smerge")


def expect(name: str, actual: Path, expected: Path) -> None:
    print(f"{name}: {actual}")
    if actual != expected:
        raise SystemExit(f"[FAIL] {name} mismatch: expected {expected}, got {actual}")


def main() -> int:
    expected_root = PROJECT_ROOT

    expect("TUTORIAL_ROOT", TUTORIAL_ROOT, expected_root)
    expect("ENGINE_DIR", ENGINE_DIR, expected_root / "engine")
    expect("PROJECT_DIR", PROJECT_DIR, expected_root / "project")
    expect("CURRENT_PROJECT_DIR", CURRENT_PROJECT_DIR, expected_root / "project" / "current")
    expect("DATA_DIR", DATA_DIR, expected_root / "data")
    expect("BIN_DIR", BIN_DIR, expected_root / "bin")
    expect("OUTPUT_DIR", OUTPUT_DIR, expected_root / "output")
    expect("CONFIG_DIR", CONFIG_DIR, expected_root / "engine" / "config")

    current_case = current_case_name()
    print(f"current_case_name: {current_case}")
    print(f"current_project_path(): {current_project_path()}")

    for name in EXECUTABLES:
        auto_path = executable_path(name)
        resolved = resolve_executable(name)
        print(f"{name}: executable_path={auto_path}")
        print(f"{name}: resolve_executable={resolved}")
        if not resolved.exists():
            raise SystemExit(f"[FAIL] executable missing: {name} -> {resolved}")

    print("[OK] path self-check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
