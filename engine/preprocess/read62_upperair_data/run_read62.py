import argparse
import os
import re
from pathlib import Path

from engine.core.paths import BIN_ROOT, TEMPLATE_FILES, VENDOR_BIN_DIR, case_path, current_case_name, current_project_path, resolve_executable
from engine.core.runner import run_binary

CASE_ROOT = current_project_path()
DATA_DIR = CASE_ROOT / 'met' / 'upperair'
CASE_READ62_INP = CASE_ROOT / 'run' / 'read62' / 'read62.inp'
TEMPLATE_INP = TEMPLATE_FILES['read62']
PSTOP_DEFAULT = 500


def _replace_bang_var(text: str, var: str, value: str) -> str:
    pat = re.compile(rf'!\s*{re.escape(var)}\s*=\s*.*?!')
    repl = f'! {var} = {value} !'
    return pat.sub(repl, text)


def _replace_num_var(text: str, var: str, value: int) -> str:
    pat = re.compile(rf'!\s*{re.escape(var)}\s*=\s*[-+]?\d+\s*!')
    repl = f'! {var}  = {value}  !'
    return pat.sub(repl, text)


def _rel_to(base_dir: Path, target: Path) -> str:
    return os.path.relpath(target.resolve(), start=base_dir.resolve())


def build_inp_content(base_text: str, sounding_file: Path, year: int, updat_file: Path, runlst_file: Path, pstop: int) -> str:
    out = base_text
    # READ62 runs with cwd=project/current/run/read62, so all relative paths must
    # be resolved from CASE_READ62_INP.parent, not from engine/vendor/bin.
    base_dir = CASE_READ62_INP.parent
    out = _replace_bang_var(out, 'INDAT', _rel_to(base_dir, sounding_file))
    out = _replace_bang_var(out, 'UPDAT', _rel_to(base_dir, updat_file))
    out = _replace_bang_var(out, 'RUNLST', _rel_to(base_dir, runlst_file))
    out = _replace_bang_var(out, 'PSTOP', str(pstop))

    out = _replace_num_var(out, 'IBYR', year)
    out = _replace_num_var(out, 'IBMO', 1)
    out = _replace_num_var(out, 'IBDY', 1)
    out = _replace_num_var(out, 'IBHR', 0)
    out = _replace_num_var(out, 'IBSEC', 0)

    out = _replace_num_var(out, 'IEYR', year)
    out = _replace_num_var(out, 'IEMO', 12)
    out = _replace_num_var(out, 'IEDY', 31)
    out = _replace_num_var(out, 'IEHR', 23)
    out = _replace_num_var(out, 'IESEC', 0)
    return out


def run_one_station(sounding: Path, year: int, pstop: int, out_dir: Path) -> int:
    station = sounding.stem
    updat = out_dir / f'up_{station}_{year}.dat'
    runlst = out_dir / f'read62_{station}_{year}.lst'

    base_text = TEMPLATE_INP.read_text(encoding='utf-8', errors='ignore')
    new_text = build_inp_content(base_text, sounding, year, updat, runlst, pstop)

    CASE_READ62_INP.parent.mkdir(parents=True, exist_ok=True)
    CASE_READ62_INP.write_text(new_text, encoding='utf-8')
    proc = run_binary(
        'read62',
        CASE_READ62_INP.name,
        cwd=CASE_READ62_INP.parent,
        text=True,
        capture_output=True,
        bin_root=BIN_ROOT,
        legacy_bin_root=VENDOR_BIN_DIR,
    )

    if proc.returncode != 0:
        if proc.stdout.strip():
            print(proc.stdout[-1200:])
        if proc.stderr.strip():
            print(proc.stderr[-1200:])
    print(f'站点 {station}')
    return proc.returncode


def main() -> int:
    ap = argparse.ArgumentParser(description='批量执行 READ62（从 igra2fsl 读取所有站点）')
    ap.add_argument('--case', help='Case name under project/cases; defaults to current case')
    ap.add_argument('--year', type=int, help='年份，例如 2023')
    ap.add_argument('--pstop', type=float, help='可选：覆盖PSTOP；默认读取 parse_igra_to_csv.py 生成的 pstop_hpa.txt')
    args = ap.parse_args()
    case_name = args.case or current_case_name()
    if case_name:
        global CASE_ROOT, DATA_DIR, CASE_READ62_INP
        CASE_ROOT = case_path(case_name)
        DATA_DIR = CASE_ROOT / 'met' / 'upperair'
        CASE_READ62_INP = CASE_ROOT / 'run' / 'read62' / 'read62.inp'
    try:
        resolve_executable('read62')
    except (FileNotFoundError, ValueError) as exc:
        print(f'[ERROR] {exc}')
        return 1
    year = args.year
    if year is None:
        raise SystemExit('year is required; pass --year YYYY')
    year_dir = DATA_DIR / str(year)
    pstop_file = year_dir / 'pstop_hpa.txt'
    if args.pstop is not None:
        pstop = float(args.pstop)
    elif pstop_file.exists():
        try:
            pstop = float(pstop_file.read_text(encoding='utf-8').strip())
        except ValueError:
            pstop = float(PSTOP_DEFAULT)
    else:
        pstop = float(PSTOP_DEFAULT)
    fsl_dir = year_dir / 'igra2fsl'
    out_dir = year_dir / 'fsl_data'
    out_dir.mkdir(parents=True, exist_ok=True)
    if not fsl_dir.exists():
        print(f'未找到目录: {fsl_dir}')
        print('请先执行 read.py 生成 FSL 文本')
        return 1

    sounding_files = sorted(fsl_dir.glob('*.txt'))
    if not sounding_files:
        print(f'目录中没有站点txt文件: {fsl_dir}')
        return 1

    print(f'年份: {year}')
    print(f'输入路径: {fsl_dir}')
    print(f'输出路径: {out_dir}')
    print(f'站点数量: {len(sounding_files)}')
    _ = pstop

    ok = 0
    fail = 0
    for sounding in sounding_files:
        code = run_one_station(sounding, year, pstop, out_dir)
        if code == 0:
            ok += 1
        else:
            fail += 1

    print('--- 批量执行完成 ---')
    print(f'成功: {ok}')
    print(f'失败: {fail}')
    return 0 if fail == 0 else 2


if __name__ == '__main__':
    raise SystemExit(main())
