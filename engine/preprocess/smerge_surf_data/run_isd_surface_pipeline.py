#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from engine.core.paths import TUTORIAL_ROOT, current_project_path, engine_path

SCRIPT_DIR = engine_path("preprocess", "smerge_surf_data")


def run_step(title: str, cmd: list[str], cwd: Path) -> None:
    print(f"\n=== [{title}] 开始 ===", flush=True)
    subprocess.run(cmd, cwd=str(cwd), check=True)
    print(f"=== [{title}] 完成 ===", flush=True)


def module_cmd(python_bin: str, relative_script: str) -> list[str]:
    module_name = ".".join(("engine", "preprocess", *Path(relative_script).with_suffix("").parts))
    return [python_bin, "-m", module_name]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run ISD surface preprocessing pipeline sequentially")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--skip-download", action="store_true", help="skip step 1 download")
    args = parser.parse_args()

    py = args.python
    if not Path(py).exists():
        raise SystemExit(f"Python not found: {py}")

    # 1) download
    if not args.skip_download:
        run_step(
            "下载ISD数据",
            module_cmd(py, "smerge_surf_data/download_isd_by_grid.py"),
            TUTORIAL_ROOT,
        )

    # 2) convert + interpolate
    env = os.environ.copy()
    print("\n=== [转换并插值] 开始 ===", flush=True)
    subprocess.run(
        module_cmd(py, "smerge_surf_data/isd_to_smerge_and_fill.py"),
        cwd=str(TUTORIAL_ROOT),
        check=True,
        env=env,
    )
    print("=== [转换并插值] 完成 ===", flush=True)

    # 3) clean + merge by research time
    run_step(
        "清洗并按研究时段合并",
        module_cmd(py, "smerge_surf_data/clean_merge_filled_by_research_time.py"),
        TUTORIAL_ROOT,
    )

    # 4) format convert to smerge-ready
    run_step(
        "格式转换为SMERGE输入",
        module_cmd(py, "smerge_surf_data/convert_cleaned_to_smerge_ready.py"),
        TUTORIAL_ROOT,
    )

    # 5) update smerge input sections
    run_step(
        "更新SMERGE配置",
        module_cmd(py, "smerge_surf_data/generate_smerge_input_sections.py"),
        TUTORIAL_ROOT,
    )

    # 6) run smerge and monitor outputs
    run_step(
        "运行SMERGE并检查结果",
        module_cmd(py, "smerge_surf_data/run_smerge_and_monitor.py"),
        TUTORIAL_ROOT,
    )

    print(f"\n地面气象数据下载及处理完成, 数据保存路径: {current_project_path('met', 'surface', 'final')}/", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
