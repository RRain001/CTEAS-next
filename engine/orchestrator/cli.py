#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from engine.core.paths import case_dir, case_yaml_path, current_case_name, load_case_config, resolve_case_name
from engine.core.runtime_names import MET_DAT, MET_LST, PUFF_CON, PUFF_DRY, PUFF_LST, PUFF_VIS, PUFF_WET
from engine.validators.case_schema import CaseSchemaError, validate_case_config


STAGE_ORDER = ["preprocess", "upperair", "surface", "met", "puff"]
DEPRECATED_STAGE_ALIASES = {"calmet": "met", "calpuff": "puff"}


@dataclass(frozen=True)
class DeliverableSpec:
    name: str
    source_candidates: list[Path]
    deliverable_rel: Path
    link_back_rel: Path | None
    required: bool


def _normalize_stage_name(stage: str) -> str:
    normalized = DEPRECATED_STAGE_ALIASES.get(stage, stage)
    if normalized != stage:
        print(f"[WARN] Stage name '{stage}' is deprecated. Use '{normalized}'.")
    return normalized


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _existing_path(candidates: list[Path]) -> Path | None:
    for path in candidates:
        if path.exists():
            return path
    return None


def _upperair_complete(case_root: Path) -> bool:
    final_dir = case_root / "met" / "upperair" / "final"
    return any(final_dir.glob("up_*.dat"))


def _stage_completion(case_root: Path, stage: str) -> bool:
    stage = _normalize_stage_name(stage)
    if stage == "preprocess":
        geo_ok = (case_root / "geo" / "makegeo" / "geo.dat").exists()
        if not geo_ok:
            return False
        try:
            cfg = yaml.safe_load((case_root / "case.yaml").read_text(encoding="utf-8")) or {}
        except Exception:
            return False
        pre = cfg.get("preprocess") or {}
        pipeline = pre.get("pipeline") or {}
        run_upperair = bool(pipeline.get("run_upperair", False))
        run_surface = bool(pipeline.get("run_surface", False))

        upper_ok = True
        surface_ok = True
        if run_upperair:
            upper_ok = _upperair_complete(case_root)
        if run_surface:
            surface_ok = (case_root / "met" / "surface" / "final" / "surf.dat").exists()
        return bool(upper_ok and surface_ok)
    if stage == "met":
        return (case_root / "run" / "met" / MET_DAT).exists() and (case_root / "run" / "met" / MET_LST).exists()
    if stage == "upperair":
        return _upperair_complete(case_root)
    if stage == "surface":
        return (case_root / "met" / "surface" / "final" / "surf.dat").exists()
    if stage == "puff":
        lst_ok = _existing_path([case_root / "run" / "puff" / PUFF_LST, case_root / "run" / "puff" / PUFF_LST.upper()]) is not None
        con_ok = _existing_path([case_root / "run" / "puff" / PUFF_CON, case_root / "run" / "puff" / PUFF_CON.upper()]) is not None
        return bool(lst_ok and con_ok)
    raise ValueError(f"Unknown stage: {stage}")


def _stage_sequence(requested: str) -> list[str]:
    requested = _normalize_stage_name(requested)
    if requested == "all":
        return STAGE_ORDER.copy()
    if requested not in STAGE_ORDER:
        raise ValueError(f"Unsupported stage: {requested}")
    return [requested]


def _stage_command(case_name: str, stage: str) -> list[str]:
    stage = _normalize_stage_name(stage)
    if stage == "preprocess":
        return [sys.executable, "-m", "engine.preprocess.bin.run_preprocessing_pipeline", "--case", case_name]
    if stage == "upperair":
        return [sys.executable, "-m", "engine.preprocess.bin.run_preprocessing_pipeline", "--case", case_name, "--only-upperair"]
    if stage == "surface":
        return [sys.executable, "-m", "engine.preprocess.bin.run_preprocessing_pipeline", "--case", case_name, "--only-surface"]
    if stage == "met":
        return [sys.executable, "-m", "engine.run_met.run_met", "--case", case_name]
    if stage == "puff":
        return [sys.executable, "-m", "engine.run_puff.run_puff", "--case", case_name]
    raise ValueError(f"Unknown stage: {stage}")


def _ensure_stage_dependencies(case_root: Path, stage: str) -> None:
    stage = _normalize_stage_name(stage)
    if stage == "met" and not _stage_completion(case_root, "preprocess"):
        raise RuntimeError("met stage requires preprocess outputs (geo/makegeo/geo.dat)")
    if stage == "puff" and not _stage_completion(case_root, "met"):
        raise RuntimeError("puff stage requires met outputs (run/met/met.dat, met.lst)")


def _materialize_runtime_paths(case_root: Path, stage: str) -> None:
    stage = _normalize_stage_name(stage)
    if stage == "met":
        paths = [case_root / "run" / "met" / MET_DAT, case_root / "run" / "met" / MET_LST]
    elif stage == "puff":
        paths = [
            case_root / "run" / "puff" / PUFF_CON,
            case_root / "run" / "puff" / PUFF_LST,
            case_root / "run" / "puff" / PUFF_DRY,
            case_root / "run" / "puff" / PUFF_WET,
            case_root / "run" / "puff" / PUFF_VIS,
        ]
    else:
        return

    for path in paths:
        if path.is_symlink():
            path.unlink()


def _deliverable_specs(case_root: Path) -> list[DeliverableSpec]:
    return [
        DeliverableSpec(
            name="met_dat",
            source_candidates=[case_root / "run" / "met" / MET_DAT],
            deliverable_rel=Path("met") / MET_DAT,
            link_back_rel=Path("run") / "met" / MET_DAT,
            required=False,
        ),
        DeliverableSpec(
            name="met_lst",
            source_candidates=[case_root / "run" / "met" / MET_LST],
            deliverable_rel=Path("met") / MET_LST,
            link_back_rel=Path("run") / "met" / MET_LST,
            required=False,
        ),
        DeliverableSpec(
            name="puff_con",
            source_candidates=[case_root / "run" / "puff" / PUFF_CON, case_root / "run" / "puff" / PUFF_CON.upper()],
            deliverable_rel=Path("puff") / PUFF_CON,
            link_back_rel=Path("run") / "puff" / PUFF_CON,
            required=False,
        ),
        DeliverableSpec(
            name="puff_dry",
            source_candidates=[case_root / "run" / "puff" / PUFF_DRY, case_root / "run" / "puff" / PUFF_DRY.upper()],
            deliverable_rel=Path("puff") / PUFF_DRY,
            link_back_rel=Path("run") / "puff" / PUFF_DRY,
            required=False,
        ),
        DeliverableSpec(
            name="puff_wet",
            source_candidates=[case_root / "run" / "puff" / PUFF_WET, case_root / "run" / "puff" / PUFF_WET.upper()],
            deliverable_rel=Path("puff") / PUFF_WET,
            link_back_rel=Path("run") / "puff" / PUFF_WET,
            required=False,
        ),
        DeliverableSpec(
            name="puff_vis",
            source_candidates=[case_root / "run" / "puff" / PUFF_VIS, case_root / "run" / "puff" / PUFF_VIS.upper()],
            deliverable_rel=Path("puff") / PUFF_VIS,
            link_back_rel=Path("run") / "puff" / PUFF_VIS,
            required=False,
        ),
    ]


def _publish_deliverables(case_name: str, case_root: Path, stage_results: dict[str, str]) -> None:
    deliverables_dir = case_root / "deliverables"
    staging_dir = case_root / ".deliverables_staging"
    prev_dir = case_root / ".deliverables_prev"

    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir(parents=True, exist_ok=True)

    copied: dict[str, str] = {}

    for spec in _deliverable_specs(case_root):
        src = _existing_path(spec.source_candidates)
        if src is None:
            if spec.required:
                raise RuntimeError(f"Required deliverable missing: {spec.name}")
            continue
        dest = staging_dir / spec.deliverable_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        copied[spec.name] = str(dest.relative_to(staging_dir))

    snapshot_dst = staging_dir / "case_snapshot" / "case.yaml"
    snapshot_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(case_yaml_path(case_name), snapshot_dst)

    run_summary = {
        "generated_at_utc": _now_utc(),
        "case": case_name,
        "stage_results": stage_results,
        "deliverables": copied,
    }
    summary_dst = staging_dir / "logs" / "run_summary.json"
    summary_dst.parent.mkdir(parents=True, exist_ok=True)
    summary_dst.write_text(json.dumps(run_summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if prev_dir.exists():
        shutil.rmtree(prev_dir)
    if deliverables_dir.exists():
        deliverables_dir.rename(prev_dir)

    os.replace(staging_dir, deliverables_dir)
    if prev_dir.exists():
        shutil.rmtree(prev_dir)

    for spec in _deliverable_specs(case_root):
        if spec.link_back_rel is None:
            continue
        published = deliverables_dir / spec.deliverable_rel
        if not published.exists():
            continue
        run_path = case_root / spec.link_back_rel
        run_path.parent.mkdir(parents=True, exist_ok=True)
        if run_path.exists() or run_path.is_symlink():
            if run_path.is_dir() and not run_path.is_symlink():
                raise RuntimeError(f"Refusing to overwrite directory with deliverable file: {run_path}")
            run_path.unlink()
        shutil.copy2(published, run_path)

    summary_path = case_root / "logs" / "run_summary.json"
    if summary_path.exists() or summary_path.is_symlink():
        if summary_path.is_dir() and not summary_path.is_symlink():
            raise RuntimeError(f"Refusing to overwrite directory with run summary: {summary_path}")
        summary_path.unlink()
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(deliverables_dir / "logs" / "run_summary.json", summary_path)


def _resolve_case(case_arg: str | None, case_yaml_arg: str | None) -> str:
    if case_arg:
        return case_arg
    if case_yaml_arg:
        path = Path(case_yaml_arg).resolve()
        if path.name != "case.yaml":
            raise ValueError(f"Expected case.yaml path, got: {path}")
        if path.parent.parent.name != "cases":
            raise ValueError(f"case.yaml must be under project/cases/<case>/case.yaml: {path}")
        return path.parent.name
    return resolve_case_name(None)


def run_pipeline(case_name: str, stage: str, resume: bool) -> int:
    cfg = load_case_config(case_name)
    validate_case_config(cfg)

    current = current_case_name()
    if current != case_name:
        raise RuntimeError(
            f"project/current 当前指向 '{current}'，与目标案例 '{case_name}' 不一致。"
            "根据当前策略不会自动切换，请先手动切换案例后再执行。"
        )
    root = case_dir(case_name)

    stage_results: dict[str, str] = {}
    for item in _stage_sequence(stage):
        if item != "preprocess":
            _ensure_stage_dependencies(root, item)
        if resume and _stage_completion(root, item):
            print(f"[SKIP] stage={item} already complete")
            stage_results[item] = "skipped"
            continue

        _materialize_runtime_paths(root, item)
        cmd = _stage_command(case_name, item)
        print(f"[RUN] {' '.join(cmd)}")
        proc = subprocess.run(cmd, cwd=str(root.parents[2]))
        if proc.returncode != 0:
            stage_results[item] = f"failed({proc.returncode})"
            print(f"[FAIL] stage={item} exit={proc.returncode}")
            return proc.returncode
        stage_results[item] = "completed"

    _publish_deliverables(case_name, root, stage_results)
    print(f"[OK] deliverables updated: {root / 'deliverables'}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CTEAS orchestration CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="Run pipeline for a case")
    run_parser.add_argument("case_yaml", nargs="?", help="Optional path to case.yaml")
    run_parser.add_argument("--case", help="Case name under project/cases")
    run_parser.add_argument(
        "--stage",
        choices=["preprocess", "upperair", "surface", "met", "puff", "calmet", "calpuff", "all"],
        default="all",
    )
    run_parser.add_argument("--resume", action="store_true", help="Skip completed stage outputs")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command != "run":
        parser.error(f"Unsupported command: {args.command}")

    try:
        case_name = _resolve_case(args.case, args.case_yaml)
        return run_pipeline(case_name=case_name, stage=_normalize_stage_name(args.stage), resume=args.resume)
    except (CaseSchemaError, FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"[ERROR] {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
