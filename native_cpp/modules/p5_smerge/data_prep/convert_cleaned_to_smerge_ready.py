#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from engine.core.paths import current_project_path
from .p5_case_paths import case_root

CASE_ROOT = case_root()

INPUT_DIR = CASE_ROOT / "met" / "surface" / "isd2smerge_cleaned"
OUTPUT_DIR = CASE_ROOT / "met" / "surface" / "isd2smerge_ready"


def convert_one(path: Path, out_path: Path) -> None:
    out_text = path.read_text(encoding="utf-8", errors="ignore")
    if out_text and not out_text.endswith("\n"):
        out_text += "\n"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(out_text, encoding="utf-8")


def main() -> int:
    if not INPUT_DIR.exists():
        print(f"Input dir not found: {INPUT_DIR}")
        return 1

    files = sorted([p for p in INPUT_DIR.iterdir() if p.is_file() and p.suffix.lower() == ".csv"])
    if not files:
        print(f"No csv files in: {INPUT_DIR}")
        return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in files:
        out_path = OUTPUT_DIR / path.name
        convert_one(path, out_path)

    print(f"数据处理完成, 数据保存路径: {OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
