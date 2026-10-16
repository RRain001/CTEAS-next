#!/usr/bin/env python3
from pathlib import Path
import argparse

from engine.core.case_manager import set_current_case
from engine.core.paths import CASES_ROOT


def _list_cases(cases_root: Path) -> list[str]:
    if not cases_root.exists():
        return []
    return sorted([p.name for p in cases_root.iterdir() if p.is_dir()])


def main() -> int:
    parser = argparse.ArgumentParser(description='将 project/current 切换到 project/cases 下指定案例。')
    parser.add_argument('case_name', nargs='?', help='project/cases 下的案例名称')
    args = parser.parse_args()

    cases = _list_cases(CASES_ROOT)
    if not cases:
        print(f'未找到案例目录: {CASES_ROOT}')
        return 1

    case_name = args.case_name
    if not case_name:
        print('case_name is required in non-interactive mode')
        return 1

    target = CASES_ROOT / case_name
    if not target.exists():
        print(f'案例不存在: {target}')
        print(f'可用案例: {", ".join(cases)}')
        return 1

    set_current_case(case_name)
    print(f'已切换当前案例 -> {target}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
