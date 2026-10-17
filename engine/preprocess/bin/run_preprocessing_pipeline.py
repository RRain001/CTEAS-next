#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

from engine.core.paths import TEMPLATE_FILES, TUTORIAL_ROOT, case_dir, case_yaml_path, current_case_name, engine_path
from engine.core.runtime_names import MET_INP, PUFF_INP


ROOT = engine_path("preprocess")

STEP_TITLES = {
    "configure_grid_cmn": "配置网格通用参数",
    "auto_select_srtm_to_terrel": "自动创建SRTM地形数据",
    "auto_select_landuse_to_ctgproc": "自动创建土地利用数据",
    "auto_config_makegeo": "自动合并地形与土地利用数据",
    "run_upperair_pipeline": "高空数据预处理",
    "run_isd_surface_pipeline": "地表数据预处理",
}

INP_TEMPLATES = [
    ("terrel", Path("geo") / "terrel" / "terrel.inp"),
    ("ctgproc", Path("geo") / "ctgproc" / "ctgproc.inp"),
    ("makegeo", Path("geo") / "makegeo" / "makegeo.inp"),
    ("met", Path("run") / "met" / MET_INP),
    ("puff", Path("run") / "puff" / PUFF_INP),
    ("read62", Path("run") / "read62" / "read62.inp"),
    ("smerge", Path("run") / "smerge" / "smerge.inp"),
]


def load_case_config_for_name(case_name: str) -> dict[str, Any]:
    path = case_yaml_path(case_name)
    if not path.exists():
        raise FileNotFoundError(f"case.yaml not found: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def copy_inp_templates(case_name: str) -> None:
    case_root = case_dir(case_name)
    for template_key, dst_rel in INP_TEMPLATES:
        src = TEMPLATE_FILES[template_key]
        dst = case_root / dst_rel
        if not src.exists():
            raise FileNotFoundError(f"Template not found: {src}")
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)


def _module_name(script_rel: Path) -> str:
    return ".".join(("engine", "preprocess", *script_rel.with_suffix("").parts))


def run_step(name: str, script_rel: Path, python_bin: str, extra_args: list[str] | None = None) -> None:
    cmd = [python_bin, "-m", _module_name(script_rel)]
    if extra_args:
        cmd.extend(extra_args)

    title = STEP_TITLES.get(name, name)
    print(f"\n=== [{title}] 开始 ===")
    subprocess.run(cmd, cwd=str(TUTORIAL_ROOT), check=True)
    print(f"=== [{title}] 完成 ===")


def pipeline_steps(config: dict[str, Any], mode: str = "full") -> list[tuple[str, Path, list[str]]]:
    pre = config.get("preprocess") or {}
    pipeline = pre.get("pipeline") or {}
    upperair = pre.get("upperair") or {}
    surface = pre.get("surface") or {}

    run_upperair = bool(pipeline.get("run_upperair", False))
    run_surface = bool(pipeline.get("run_surface", False))

    steps: list[tuple[str, Path, list[str]]] = [("configure_grid_cmn", Path("grid") / "configure_grid_cmn.py", [])]
    if mode == "full":
        steps.extend(
            [
                ("auto_select_srtm_to_terrel", Path("terrel") / "auto_select_srtm_to_terrel.py", []),
                ("auto_select_landuse_to_ctgproc", Path("ctgproc") / "auto_select_landuse_to_ctgproc.py", []),
                ("auto_config_makegeo", Path("makegeo") / "auto_config_makegeo.py", []),
            ]
        )

    should_run_upperair = (mode == "upperair") or (mode == "full" and run_upperair)
    should_run_surface = (mode == "surface") or (mode == "full" and run_surface)

    if should_run_upperair:
        extra = []
        if bool(upperair.get("skip_download", False)):
            extra.append("--skip-download")
        if upperair.get("pstop_hpa") is not None:
            extra.extend(["--pstop", str(upperair["pstop_hpa"])])
        steps.append(("run_upperair_pipeline", Path("read62_upperair_data") / "run_upperair_pipeline.py", extra))

    if should_run_surface:
        extra = []
        if bool(surface.get("skip_download", False)):
            extra.append("--skip-download")
        steps.append(("run_isd_surface_pipeline", Path("smerge_surf_data") / "run_isd_surface_pipeline.py", extra))

    return steps


def main() -> int:
    parser = argparse.ArgumentParser(description="Run preprocess pipeline sequentially for an existing case.")
    parser.add_argument("--case", required=True, help="Case name under project/cases")
    parser.add_argument("--python", default=sys.executable, help="Python interpreter to run each step")
    parser.add_argument("--only-upperair", action="store_true", help="Run upperair meteorological flow only")
    parser.add_argument("--only-surface", action="store_true", help="Run surface meteorological flow only")
    args = parser.parse_args()

    print(f"将使用案例名称: {args.case}")

    try:
        current = current_case_name()
        if current != args.case:
            raise RuntimeError(
                f"project/current 当前指向 '{current}'，与目标案例 '{args.case}' 不一致。"
                "根据当前策略不会自动切换，请先在 GUI 里加载该案例后再执行。"
            )

        if args.only_upperair and args.only_surface:
            raise ValueError("Cannot use --only-upperair and --only-surface together")
        mode = "full"
        if args.only_upperair:
            mode = "upperair"
        elif args.only_surface:
            mode = "surface"

        config = load_case_config_for_name(args.case)
        for name, script_rel, configured_args in pipeline_steps(config, mode=mode):
            script_abs = ROOT / script_rel
            if not script_abs.exists():
                raise FileNotFoundError(f"Script not found: {script_rel} (base: {ROOT})")

            step_args = list(configured_args)
            run_step(name=name, script_rel=script_rel, python_bin=args.python, extra_args=step_args)
        if mode == "full":
            copy_inp_templates(args.case)
    except subprocess.CalledProcessError as exc:
        print(f"\n流程在某一步失败, 退出码: {exc.returncode}", file=sys.stderr)
        return exc.returncode
    except Exception as exc:
        print(f"\n流程错误: {exc}", file=sys.stderr)
        return 1

    print("\n前处理工作完成!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
