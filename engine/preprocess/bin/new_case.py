#!/usr/bin/env python3
from pathlib import Path
import argparse
import shutil
import math

from engine.core.paths import CASES_ROOT, TEMPLATES_DIR, VENDOR_SRC_DIR
from engine.core.runtime_names import MET_INP, PUFF_INP
from engine.preprocess.grid.center_location_to_utm import convert_lon_lat


def _replace_grid_key_line(line: str, key: str, value: str) -> str:
    if line.strip().startswith(f"! {key} ="):
        return f"! {key} =  {value}       !"
    return line


def _write_initial_grid_files(case_dir: Path) -> None:
    grid_dir = case_dir / "grid"
    grid_dir.mkdir(parents=True, exist_ok=True)

    lon = 117.0
    lat = 32.0
    length_km = 50.0
    width_km = 50.0
    dgrid_km = 1.0
    nz = 9
    begin = "20230101-000000"
    end = "20231231-230000"

    utm = convert_lon_lat(lon, lat)
    xref_km = float(utm["x_km"]) - length_km / 2.0
    yref_km = float(utm["y_km"]) - width_km / 2.0
    nx = max(1, int(math.ceil(length_km / dgrid_km)))
    ny = max(1, int(math.ceil(width_km / dgrid_km)))

    (grid_dir / "center_location").write_text(
        f"longitude:{lon:.6f}\nlatitude:{lat:.6f}\n",
        encoding="utf-8",
    )
    (grid_dir / "research_time").write_text(
        f"BEGIN:{begin}\nEND:{end}\n",
        encoding="utf-8",
    )

    source_grid_cmn = VENDOR_SRC_DIR / "grid" / "grid.cmn"
    if source_grid_cmn.exists():
        lines = source_grid_cmn.read_text(encoding="utf-8").splitlines()
    else:
        lines = [
            "! IUTMZN =  0       !",
            "! LSOHEM =  N       !",
            "! XREFKM =  0       !",
            "! YREFKM =  0       !",
            "! DGRIDKM =  1       !",
            "! NX =  1       !",
            "! NY =  1       !",
            "! NZ =  9       !",
        ]

    out: list[str] = []
    for line in lines:
        line = _replace_grid_key_line(line, "IUTMZN", str(int(utm["zone"])))
        line = _replace_grid_key_line(line, "LSOHEM", str(utm["hemisphere"]))
        line = _replace_grid_key_line(line, "XREFKM", f"{xref_km:.3f}")
        line = _replace_grid_key_line(line, "YREFKM", f"{yref_km:.3f}")
        line = _replace_grid_key_line(line, "DGRIDKM", f"{dgrid_km:g}")
        line = _replace_grid_key_line(line, "NX", str(nx))
        line = _replace_grid_key_line(line, "NY", str(ny))
        line = _replace_grid_key_line(line, "NZ", str(nz))
        out.append(line)
    (grid_dir / "grid.cmn").write_text("\n".join(out) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description='在 project/cases 下创建新案例目录。')
    parser.add_argument('case_name', help='案例名称，例如 nanjing_2024')
    args = parser.parse_args()

    case_dir = CASES_ROOT / args.case_name
    if case_dir.exists():
        print(f'案例已存在: {case_dir}')
        return 1

    for rel in [
        Path('grid'),
        Path('met') / 'surface',
        Path('met') / 'upperair',
        Path('geo') / 'ctgproc',
        Path('geo') / 'terrel',
        Path('geo') / 'makegeo',
        Path('run') / 'met',
        Path('run') / 'puff',
        Path('run') / 'read62',
        Path('run') / 'smerge',
        Path('logs'),
    ]:
        (case_dir / rel).mkdir(parents=True, exist_ok=True)

    template_targets = {
        "terrel.inp": case_dir / "geo" / "terrel" / "terrel.inp",
        "ctgproc.inp": case_dir / "geo" / "ctgproc" / "ctgproc.inp",
        "makegeo.inp": case_dir / "geo" / "makegeo" / "makegeo.inp",
        MET_INP: case_dir / "run" / "met" / MET_INP,
        PUFF_INP: case_dir / "run" / "puff" / PUFF_INP,
        "read62.inp": case_dir / "run" / "read62" / "read62.inp",
        "smerge.inp": case_dir / "run" / "smerge" / "smerge.inp",
    }
    for template_name, target in template_targets.items():
        source = TEMPLATES_DIR / template_name
        if not source.exists():
            print(f"缺少模板文件: {source}")
            return 1
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    _write_initial_grid_files(case_dir)

    (case_dir / 'case.yaml').write_text(
        f"""schema_version: 1
case_name: {args.case_name}
paths:
  grid_dir: project/current/grid
  met_surface_dir: project/current/met/surface
  met_upperair_dir: project/current/met/upperair
  geo_ctgproc_dir: project/current/geo/ctgproc
  geo_terrel_dir: project/current/geo/terrel
  geo_makegeo_dir: project/current/geo/makegeo
  run_met_dir: project/current/run/met
  run_puff_dir: project/current/run/puff
  run_read62_dir: project/current/run/read62
  run_smerge_dir: project/current/run/smerge
settings:
  timezone: UTC+0000
  pstop_hpa_default: 500
preprocess:
  grid:
    center:
      longitude: 117.0
      latitude: 32.0
    domain:
      length_km: 50
      width_km: 50
    resolution_km: 1
    nz: 9
  research_time:
    begin: 20230101-000000
    end: 20231231-230000
  upperair:
    pstop_hpa: 500
    auto_select_all: true
met:
  station_selection:
    isurft_mode: spatial
    iupt_mode: spatial
    iupwnd_mode: spatial
  options:
    lcfiles: true
    irtype: 1
    lcalgrd: true
    lsave: true
    lprint: false
    noobs: 0
    npsta: 0
    icloud: 0
    iforms: 2
    iformp: 2
    iformc: 2
    iwfcod: 1
    ifradj: 1
    ikine: 0
    iobr: 0
puff:
  options:
    lcfiles: true
    source_mode: case_yaml
    nspec: 1
    nse: 1
    mchem: 0
    idry: 0
    iwet: 0
    ndecay: 0
  point_sources: []
""",
        encoding='utf-8',
    )
    print(f'已创建案例: {case_dir}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
