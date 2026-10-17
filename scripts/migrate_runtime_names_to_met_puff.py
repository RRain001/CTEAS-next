#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from engine.core.paths import CASES_DIR


TEXT_SUFFIXES = {".csv", ".inp", ".json", ".log", ".md", ".txt", ".yaml", ".yml"}
TEXT_REPLACEMENTS = [
    ("calmet.dat.aux", "met.dat.aux"),
    ("calmet_runtime.log", "met_runtime.log"),
    ("calpuff_runtime.log", "puff_runtime.log"),
    ("calmet.inp", "met.inp"),
    ("calmet.lst", "met.lst"),
    ("calmet.dat", "met.dat"),
    ("calpuff.inp", "puff.inp"),
    ("calpuff.lst", "puff.lst"),
    ("calpuff.con", "puff.con"),
    ("calpuff.dry", "puff.dry"),
    ("calpuff.wet", "puff.wet"),
    ("calpuff.vis", "puff.vis"),
    ("run/calmet/", "run/met/"),
    ("run/calpuff/", "run/puff/"),
    ("deliverables/calmet/", "deliverables/met/"),
    ("deliverables/calpuff/", "deliverables/puff/"),
    ("run_calmet_dir", "run_met_dir"),
    ("run_calpuff_dir", "run_puff_dir"),
    ("plot_calpuff_snapshot", "plot_puff_snapshot"),
    ("plot_calpuff_animation", "plot_puff_animation"),
    ("plot_calpuff_annual", "plot_puff_annual"),
    ("plot_calpuff_seasonal", "plot_puff_seasonal"),
    ("plot_daily_from_calpuff", "plot_daily_from_puff"),
    ("--calmet-inp", "--met-inp"),
    ('"stage": "calmet"', '"stage": "met"'),
    ('"stage": "calpuff"', '"stage": "puff"'),
    ("--stage calmet", "--stage met"),
    ("--stage calpuff", "--stage puff"),
    ("_calmet", "_met"),
    ("_calpuff", "_puff"),
    ("calmet_dat", "met_dat"),
    ("calmet_lst", "met_lst"),
    ("calpuff_con", "puff_con"),
    ("calpuff_lst", "puff_lst"),
    ("\ncalmet:\n", "\nmet:\n"),
    ("\ncalpuff:\n", "\npuff:\n"),
]

FILE_RENAMES = [
    (Path("run/met"), "calmet.inp", "met.inp"),
    (Path("run/met"), "calmet.lst", "met.lst"),
    (Path("run/met"), "calmet.dat", "met.dat"),
    (Path("run/met"), "calmet.dat.aux", "met.dat.aux"),
    (Path("run/met"), "calmet_runtime.log", "met_runtime.log"),
    (Path("run/puff"), "calpuff.inp", "puff.inp"),
    (Path("run/puff"), "calpuff.lst", "puff.lst"),
    (Path("run/puff"), "calpuff.con", "puff.con"),
    (Path("run/puff"), "calpuff.dry", "puff.dry"),
    (Path("run/puff"), "calpuff.wet", "puff.wet"),
    (Path("run/puff"), "calpuff.vis", "puff.vis"),
    (Path("run/puff"), "calpuff_runtime.log", "puff_runtime.log"),
    (Path("deliverables/met"), "calmet.lst", "met.lst"),
    (Path("deliverables/met"), "calmet.dat", "met.dat"),
    (Path("deliverables/puff"), "calpuff.lst", "puff.lst"),
    (Path("deliverables/puff"), "calpuff.con", "puff.con"),
    (Path("deliverables/puff"), "calpuff.dry", "puff.dry"),
    (Path("deliverables/puff"), "calpuff.wet", "puff.wet"),
    (Path("deliverables/puff"), "calpuff.vis", "puff.vis"),
]


def _apply_replacements(text: str) -> str:
    updated = text
    for old, new in TEXT_REPLACEMENTS:
        updated = updated.replace(old, new)
    return updated


def _rename_case_path(case_root: Path, rel_dir: Path, old_name: str, new_name: str, dry_run: bool) -> bool:
    old_path = case_root / rel_dir / old_name
    if not (old_path.exists() or old_path.is_symlink()):
        return False

    new_path = old_path.with_name(new_name)
    new_path.parent.mkdir(parents=True, exist_ok=True)

    if old_path.is_symlink():
        target = os.readlink(old_path)
        new_target = _apply_replacements(target)
        if not dry_run:
            old_path.unlink()
            if new_path.exists() or new_path.is_symlink():
                new_path.unlink()
            new_path.symlink_to(new_target)
        return True

    if new_path.exists():
        raise FileExistsError(f"Refusing to overwrite existing file: {new_path}")
    if not dry_run:
        old_path.rename(new_path)
    return True


def _rename_run_dirs(case_root: Path, dry_run: bool) -> int:
    runs_dir = case_root / "runs"
    if not runs_dir.exists():
        return 0
    renamed = 0
    for item in sorted(runs_dir.iterdir()):
        if not item.is_dir():
            continue
        new_name = item.name
        if new_name.endswith("_calmet"):
            new_name = f"{new_name[:-7]}_met"
        elif new_name.endswith("_calpuff"):
            new_name = f"{new_name[:-8]}_puff"
        if new_name == item.name:
            continue
        target = item.with_name(new_name)
        if target.exists():
            raise FileExistsError(f"Refusing to overwrite existing directory: {target}")
        if not dry_run:
            item.rename(target)
        renamed += 1
    return renamed


def _iter_text_files(case_root: Path) -> list[Path]:
    files: list[Path] = []
    for path in case_root.rglob("*"):
        if path.is_symlink() or not path.is_file():
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        files.append(path)
    return files


def _rewrite_text_files(case_root: Path, dry_run: bool) -> int:
    updated = 0
    for path in _iter_text_files(case_root):
        original = path.read_text(encoding="utf-8", errors="ignore")
        rewritten = _apply_replacements(original)
        if rewritten == original:
            continue
        if not dry_run:
            path.write_text(rewritten, encoding="utf-8")
        updated += 1
    return updated


def _resolve_cases(case_args: list[str], use_all: bool) -> list[Path]:
    if use_all:
        return sorted(path for path in CASES_DIR.iterdir() if path.is_dir())
    if case_args:
        return [CASES_DIR / case_name for case_name in case_args]
    raise ValueError("Provide --all-cases or at least one --case name.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rename runtime file family from calmet/calpuff to met/puff.")
    parser.add_argument("--case", action="append", default=[], help="Case name under project/cases. Can be repeated.")
    parser.add_argument("--all-cases", action="store_true", help="Migrate all cases under project/cases.")
    parser.add_argument("--dry-run", action="store_true", help="Print intended scope without writing changes.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    cases = _resolve_cases(args.case, args.all_cases)
    changed_paths = 0
    changed_dirs = 0
    changed_texts = 0

    for case_root in cases:
        if not case_root.exists():
            raise FileNotFoundError(f"Case directory not found: {case_root}")
        print(f"[CASE] {case_root.name}")
        for rel_dir, old_name, new_name in FILE_RENAMES:
            if _rename_case_path(case_root, rel_dir, old_name, new_name, dry_run=args.dry_run):
                print(f"  rename {rel_dir / old_name} -> {rel_dir / new_name}")
                changed_paths += 1
        renamed_dirs = _rename_run_dirs(case_root, dry_run=args.dry_run)
        if renamed_dirs:
            print(f"  renamed run-history dirs: {renamed_dirs}")
            changed_dirs += renamed_dirs
        updated_texts = _rewrite_text_files(case_root, dry_run=args.dry_run)
        if updated_texts:
            print(f"  rewritten text files: {updated_texts}")
            changed_texts += updated_texts

    print(f"[SUMMARY] paths={changed_paths} run_dirs={changed_dirs} text_files={changed_texts}")
    if args.dry_run:
        print("[SUMMARY] dry-run only; no files were changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
