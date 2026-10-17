#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from engine.core.case_manager import get_current_case_dir, get_current_case_name
from engine.core.paths import case_yaml_path


def main() -> int:
    case_name = get_current_case_name()
    case_dir = get_current_case_dir()
    case_yaml_exists = case_yaml_path(case_name).exists() if case_name else False

    print(f"current_case_name: {case_name}")
    print(f"current_case_dir: {case_dir}")
    print(f"case.yaml exists: {'yes' if case_yaml_exists else 'no'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
