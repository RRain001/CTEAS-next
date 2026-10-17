#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from engine.core.platform_utils import binary_filename
from engine.core.paths import BIN_ROOT
from engine.native.registry import iter_required_programs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check native binary presence for a target platform.")
    parser.add_argument("--platform", default="linux-x86_64", help="Target platform key, default: linux-x86_64")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    platform = args.platform
    bin_dir = BIN_ROOT / platform

    print(f"platform: {platform}")
    print(f"bin_dir: {bin_dir}")

    missing: list[str] = []
    for name, spec in iter_required_programs():
        physical_name = str(spec["binary"])
        filename = binary_filename(physical_name, platform)
        path = bin_dir / filename
        status = "OK" if path.exists() else "MISSING"
        print(f"{name} -> {filename} {status}")
        print(f"  path: {path}")
        if not path.exists():
            missing.append(name)

    if missing:
        print("missing binaries:", ", ".join(missing))
        return 1

    print("all required binaries present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
