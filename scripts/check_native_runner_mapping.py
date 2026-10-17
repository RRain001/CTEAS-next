#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from engine.core.paths import BIN_ROOT, VENDOR_BIN_DIR
from engine.core.runner import build_binary_command


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check logical native names resolve to physical binaries.")
    parser.add_argument("--platform", default="linux-x86_64", help="Target platform key, default: linux-x86_64")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    platform = args.platform

    expected = {
        "met": BIN_ROOT / platform / "met.x",
        "puff": BIN_ROOT / platform / "puff.x",
    }

    failures: list[str] = []
    for logical_name, expected_path in expected.items():
        resolved = Path(
            build_binary_command(
                logical_name,
                platform_key=platform,
                bin_root=BIN_ROOT,
                legacy_bin_root=VENDOR_BIN_DIR,
            )[0]
        )
        print(f"{logical_name} resolves to {resolved}")
        if resolved != expected_path:
            failures.append(f"{logical_name} -> {resolved} (expected {expected_path})")

    if failures:
        print("runner mapping mismatches:")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("runner mapping OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
