from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import yaml

from PySide6.QtCore import QProcess, Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QFont, QFontDatabase, QGuiApplication, QMovie, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QProgressBar,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from engine.core.paths import (
    CASES_ROOT,
    TUTORIAL_ROOT,
    case_dir,
    case_yaml_path,
    current_project_path,
    current_case_name,
    ensure_current_case,
    resolve_case_path,
    tutorial_path,
)
from engine.core.runtime_names import MET_DAT, MET_INP, MET_LST, PUFF_CON, PUFF_LST
from engine.gui_g5.app import create_case, list_case_summaries, load_case_yaml
from engine.gui_g5.pipeline import stage_readiness, validate_case
from engine.gui_g5.case_setup import write_case_grid, projected_stack_utm_km
from engine.preprocess.grid.center_location_to_utm import convert_lon_lat
# G5 must start without the optional legacy plotting stack (matplotlib).
# Load compatibility-only postprocessing parsers only when a plot is requested.
def index_time_records(*args: Any, **kwargs: Any) -> Any:
    from engine.postprocessing._core import index_time_records as parser
    return parser(*args, **kwargs)


def parse_calmet_grid(*args: Any, **kwargs: Any) -> Any:
    from engine.postprocessing._core import parse_calmet_grid as parser
    return parser(*args, **kwargs)



SOFTWARE_TITLE = "CTEAS G5 — 原生 P1–P7 重构版（独立试验）"
DATE_FMT = "%Y%m%d-%H%M%S"
STAGE_DISPLAY = {
    "all": "全部",
    "preprocess": "地形处理",
    "upperair": "高空气象",
    "surface": "地面气象",
    "met": "诊断风场",
    "puff": "烟团模型",
    "post_conc_plot": "后处理-浓度云图",
    "post_animation": "后处理-云图动画",
    "post_point": "后处理-点位浓度",
    "post_windrose": "后处理-风玫瑰",
}


@dataclass
class StageSpec:
    name: str
    stage: str
    desc: str
    deps: list[str]
    inputs: list[str]
    outputs: list[str]
    output_dir_rel: str


@dataclass
class FieldSpec:
    key: str
    label: str
    group: str
    widget: str
    default: Any
    required: bool
    tooltip: str


@dataclass(frozen=True)
class PostprocessSpec:
    job: str
    stage: str
    label: str
    default_output: str


STAGES: list[StageSpec] = [
    StageSpec(
        name="地面气象",
        stage="surface",
        desc="P5 原生 C++ SURF.DAT（需明确配置原生可执行程序）。",
        deps=[],
        inputs=["preprocess.research_time", "独立执行 stage=surface"],
        outputs=["met/surface/final/surf.dat"],
        output_dir_rel="met/surface/final",
    ),
    StageSpec(
        name="高空气象",
        stage="upperair",
        desc="P4 READ62 原生链；完整跨年 UP.DAT 自动集成尚未验收。",
        deps=[],
        inputs=["preprocess.research_time", "独立执行 stage=upperair"],
        outputs=["met/upperair/final/UP.DAT"],
        output_dir_rel="met/upperair/final",
    ),
    StageSpec(
        name="地形处理",
        stage="preprocess",
        desc="P1/P2/P3 原生地形/地类/GEO；通用配置尚未验收。",
        deps=[],
        inputs=["preprocess.grid", "preprocess.research_time"],
        outputs=["geo/makegeo/geo.dat", "(可选) met/upperair/final/UP.DAT", "(可选) met/surface/final/surf.dat"],
        output_dir_rel="geo",
    ),
    StageSpec(
        name="诊断风场",
        stage="met",
        desc="P6 原生 CALMET：目前仅冻结合肥案例通过，任意场景禁止直接启动。",
        deps=["preprocess"],
        inputs=["geo/makegeo/geo.dat", "met/surface/final/surf.dat", "met/upperair/final/UP.DAT"],
        outputs=[f"run/met/{MET_DAT}", f"run/met/{MET_LST}"],
        output_dir_rel="run/met",
    ),
    StageSpec(
        name="烟团模型",
        stage="puff",
        desc="P7 原生 CALPUFF：通用真实案例验收尚未完成。",
        deps=["met"],
        inputs=[f"run/met/{MET_DAT}", f"run/met/{MET_LST}"],
        outputs=[f"run/puff/{PUFF_CON}", f"run/puff/{PUFF_LST}"],
        output_dir_rel="run/puff",
    ),
]


FIELDS: list[FieldSpec] = [
    FieldSpec("preprocess.research_time.begin", "开始时间", "时空范围", "str", "", True, "格式 YYYYMMDD-HHMMSS"),
    FieldSpec("preprocess.research_time.end", "结束时间", "时空范围", "str", "", True, "格式 YYYYMMDD-HHMMSS"),
    FieldSpec("preprocess.grid.center.longitude", "中心经度", "时空范围", "float", 0.0, True, "范围 -180~180"),
    FieldSpec("preprocess.grid.center.latitude", "中心纬度", "时空范围", "float", 0.0, True, "范围 -90~90"),
    FieldSpec("preprocess.grid.domain.length_km", "长度(km)", "时空范围", "float", 50.0, True, "必须为正数"),
    FieldSpec("preprocess.grid.domain.width_km", "宽度(km)", "时空范围", "float", 50.0, True, "必须为正数"),
    FieldSpec("preprocess.grid.resolution_km", "水平网格分辨率(km)", "时空范围", "float", 1.0, True, "必须为正数"),
    FieldSpec("settings.timezone", "时区", "时空范围", "str", "UTC+0000", True, "例如 UTC+0800"),
    FieldSpec("preprocess.grid.nz", "垂直层数", "时空范围", "int", 9, True, "必须为正整数"),
    FieldSpec("preprocess.upperair.pstop_hpa", "高空压力下限(hPa)", "高空气象", "float", 500.0, True, "必须为正数"),
]


POSTPROCESS_SPECS = {
    "conc_plot": PostprocessSpec("conc_plot", "post_conc_plot", "浓度云图", "conc_snapshot.png"),
    "animation": PostprocessSpec("animation", "post_animation", "云图动画", "conc_yearly.mp4"),
    "point": PostprocessSpec("point", "post_point", "点位浓度与日浓度", "daily_concentration.png"),
    "windrose": PostprocessSpec("windrose", "post_windrose", "风玫瑰图", "windrose.png"),
}


QSS = """
QMainWindow {
    background: #eef3f8;
}
QWidget {
    color: #1d2b3a;
    font-size: 10.5pt;
}
QGroupBox {
    border: 1px solid #d8e2ee;
    border-radius: 10px;
    margin-top: 10px;
    background: #ffffff;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 2px 10px;
    background: #eef5ff;
    border: 1px solid #d8e2ee;
    border-radius: 9px;
}
QGroupBox#PostCard, QGroupBox#LogCard {
    background: #ffffff;
    border: 1px solid #c4d2e6;
    border-radius: 12px;
    margin-top: 12px;
}
QGroupBox#PostCard::title, QGroupBox#LogCard::title {
    background: #e0eaf8;
    border: 1px solid #c4d2e6;
    border-radius: 9px;
    padding: 2px 12px;
}
QGroupBox#InnerCard {
    background: #ffffff;
    border: 1px solid #d8e2ee;
    border-radius: 10px;
}
QGroupBox#InnerCard::title {
    background: #eef5ff;
    border: 1px solid #d8e2ee;
    border-radius: 9px;
    padding: 2px 10px;
}
QTabWidget#LogTabs::pane, QStackedWidget#PostPages {
    background: #ffffff;
    border: 1px solid #d8e2ee;
    border-radius: 10px;
}
QFrame#TopCard, QFrame#BottomCard, QFrame.Card {
    background: #ffffff;
    border: 1px solid #d8e2ee;
    border-radius: 12px;
}
QFrame#SectionCard {
    background: #ffffff;
    border: 1px solid #d8e2ee;
    border-radius: 12px;
}
QFrame#SectionHeader {
    background: #eef5ff;
    border: 0;
    border-top-left-radius: 12px;
    border-top-right-radius: 12px;
    border-bottom: 1px solid #d8e2ee;
}
QLabel#SectionTitle {
    font-size: 11.5pt;
    font-weight: 700;
    color: #22364d;
}
QPushButton {
    border-radius: 8px;
    min-height: 32px;
    padding: 0 12px;
    border: 1px solid #c9d7e8;
    background: #ffffff;
    color: #1d2b3a;
}
QPushButton[role="primary"] {
    background: #0f5ba7;
    border: 1px solid #0f5ba7;
    color: #ffffff;
}
QPushButton[role="primary"]:hover {
    background: #0c4f93;
    border-color: #0c4f93;
}
QPushButton[role="secondary"] {
    background: #eaf1f9;
    border: 1px solid #b7cadf;
    color: #0f3f73;
}
QPushButton[role="secondary"]:hover {
    background: #d9e8f8;
}
QPushButton[role="danger"] {
    background: #fff1f2;
    border: 1px solid #fecdd3;
    color: #be123c;
}
QPushButton[role="danger"]:hover {
    background: #ffe4e6;
}
QPushButton[role="ghost"] {
    background: #ffffff;
    border: 1px solid #d9e4f2;
    color: #334155;
}
QPushButton[role="ghost"]:hover {
    background: #f8fbff;
}
QPushButton:disabled {
    background: #edf2f7;
    border-color: #d3dde8;
    color: #93a4b8;
}
QLineEdit, QComboBox, QPlainTextEdit, QTextEdit {
    background: #ffffff;
    border: 1px solid #c6d3e2;
    border-radius: 8px;
    min-height: 28px;
    padding: 4px 8px;
}
QListWidget#NavList {
    background: #ffffff;
    border: 1px solid #dbe4f1;
    border-radius: 12px;
    padding: 8px;
}
QListWidget#NavList::item {
    padding: 7px 10px;
    border-radius: 8px;
}
QListWidget#NavList::item:selected {
    background: #d8e8fa;
    color: #0c3d70;
    font-weight: 700;
}
QTableWidget {
    background: white;
    border: 1px solid #dbe4f1;
    border-radius: 10px;
    gridline-color: #edf2f8;
    alternate-background-color: #f8fbff;
}
QHeaderView::section {
    background: #eef4fb;
    color: #334155;
    border: 0;
    border-bottom: 1px solid #dbe4f1;
    padding: 6px 8px;
    font-weight: 700;
}
QComboBox {
    min-height: 32px;
    padding-right: 28px;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: 1px solid #c6d3e2;
}
QComboBox::down-arrow {
    width: 10px;
    height: 10px;
}
QComboBox QAbstractItemView {
    border: 1px solid #c6d3e2;
    selection-background-color: #d9e8f8;
    selection-color: #0f3f73;
    outline: 0;
    padding: 4px;
}
QComboBox QAbstractItemView::item {
    min-height: 28px;
}
QLabel[kind="badge_ok"] {
    background: #ecfdf3;
    color: #166534;
    border: 1px solid #bbf7d0;
    border-radius: 9px;
    padding: 2px 8px;
    font-weight: 700;
}
QLabel[kind="badge_bad"] {
    background: #fff1f2;
    color: #b91c1c;
    border: 1px solid #fecdd3;
    border-radius: 9px;
    padding: 2px 8px;
    font-weight: 700;
}
QLabel[kind="badge_info"] {
    background: #eef2ff;
    color: #1e3a8a;
    border: 1px solid #c7d2fe;
    border-radius: 9px;
    padding: 2px 8px;
    font-weight: 700;
}
QLabel[kind="muted"] {
    color: #64748b;
    font-size: 9.5pt;
}
QPushButton[kind="stage_picker"] {
    min-height: 34px;
    border-radius: 9px;
    border: 1px solid #b7cadf;
    background: #ffffff;
    color: #0f3f73;
    padding: 0 12px;
    font-weight: 600;
}
QPushButton[kind="stage_picker"]:hover {
    background: #e8f1fb;
}
QPushButton[kind="stage_picker"]:checked {
    background: #0f5ba7;
    color: #ffffff;
    border-color: #0f5ba7;
}
QPushButton[kind="stage_picker"]:disabled {
    background: #f1f5f9;
    color: #94a3b8;
    border-color: #d5dee9;
}
QStatusBar {
    background: #ffffff;
    border-top: 1px solid #dbe4f1;
}
QProgressBar {
    border: 1px solid #c6d3e2;
    border-radius: 6px;
    background: #f0f4f9;
    min-height: 18px;
}
QProgressBar::chunk {
    background: #0f5ba7;
    border-radius: 6px;
}
"""


DEFAULT_POINT_SOURCE = {
    "name": "P1",
    "x_km": 513.385,
    "y_km": 3533.769,
    "stack_height_m": 70.0,
    "base_elev_m": 0.0,
    "stack_diameter_m": 2.0,
    "exit_velocity_mps": 11.11,
    "exit_temp_k": 293.0,
    "building_downwash_flag": 0.0,
    "zpltfm_m": 0.0,
    "fmfac": 1.0,
    "emissions": [222222.0, 0.0],
}


def _get_path(data: dict[str, Any], key: str, default: Any = None) -> Any:
    cur: Any = data
    for p in key.split("."):
        if not isinstance(cur, dict) or p not in cur:
            return default
        cur = cur[p]
    return cur


def _set_path(data: dict[str, Any], key: str, value: Any) -> None:
    parts = key.split(".")
    cur = data
    for p in parts[:-1]:
        nxt = cur.get(p)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[p] = nxt
        cur = nxt
    cur[parts[-1]] = value


def _del_path(data: dict[str, Any], key: str) -> None:
    parts = key.split(".")
    cur: Any = data
    for p in parts[:-1]:
        if not isinstance(cur, dict) or p not in cur:
            return
        cur = cur[p]
    if isinstance(cur, dict):
        cur.pop(parts[-1], None)


def _case_dirs() -> list[str]:
    if not CASES_ROOT.exists():
        return []
    return sorted([p.name for p in CASES_ROOT.iterdir() if p.is_dir()])


def _fmt_time(ts: datetime | None) -> str:
    if ts is None:
        return "-"
    return ts.strftime("%Y-%m-%d %H:%M:%S")


def _status_zh(status: str) -> str:
    if status == "idle":
        return "空闲"
    if status == "running":
        return "运行中"
    if status in {"success", "done"}:
        return "成功"
    if status == "cancelled":
        return "已取消"
    if status.startswith("failed"):
        return status.replace("failed", "失败", 1)
    return status


def _short_run_dir(path_text: str) -> str:
    p = Path(path_text)
    parts = p.parts
    if len(parts) >= 2:
        return "/".join(parts[-2:])
    return path_text


def _to_case_path(path_text: str, case_name: str) -> Path:
    return resolve_case_path(path_text, case_name)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _format_emissions_inline(yaml_text: str) -> str:
    pattern = re.compile(
        r"(?m)^(\s*)emissions:\s*\n\s*-\s*([0-9eE+\-.]+)\s*\n\s*-\s*([0-9eE+\-.]+)\s*$"
    )

    def repl(match: re.Match[str]) -> str:
        indent = match.group(1)
        v1 = match.group(2)
        v2 = match.group(3)
        return f"{indent}emissions: [{v1}, {v2}]"

    return pattern.sub(repl, yaml_text)


def _read_vertical_levels_from_grid_cmn(path: Path) -> list[float]:
    if not path.exists():
        return []
    levels: list[float] = []
    pat = re.compile(r"^\s*!\s*ZFACE\s*=\s*([0-9eE+\-.]+)\s*!?\s*$")
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = pat.match(line)
        if m:
            try:
                levels.append(float(m.group(1)))
            except Exception:
                continue
    if levels and abs(levels[0]) < 1e-9:
        levels = levels[1:]
    return levels


def _write_vertical_levels_to_grid_cmn(path: Path, nz: int, levels: list[float]) -> None:
    if not path.exists():
        raise FileNotFoundError(f"未找到网格文件: {path}")
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    out: list[str] = []
    nz_written = False
    zface_start = False
    zface_written = False
    for line in lines:
        s = line.strip()
        if s.startswith("! NZ ="):
            out.append(f"! NZ =  {nz}       !")
            nz_written = True
            continue
        if s.startswith("! ZFACE ="):
            if not zface_start:
                zface_start = True
                out.append("! ZFACE =  0        !")
                for v in levels:
                    vtxt = str(int(v)) if abs(v - round(v)) < 1e-9 else f"{v:g}"
                    out.append(f"! ZFACE =  {vtxt}        !")
                zface_written = True
            continue
        out.append(line)
    if not nz_written:
        out.append(f"! NZ =  {nz}       !")
    if not zface_written:
        out.append("! ZFACE =  0        !")
        for v in levels:
            vtxt = str(int(v)) if abs(v - round(v)) < 1e-9 else f"{v:g}"
            out.append(f"! ZFACE =  {vtxt}        !")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


class StageCard(QFrame):
    def __init__(self, spec: StageSpec, run_cb: Any, log_cb: Any, out_cb: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.spec = spec
        self.setObjectName("Card")
        lay = QVBoxLayout(self)

        top = QHBoxLayout()
        title = QLabel(spec.name)
        title.setStyleSheet("font-size: 15px; font-weight: 700;")
        self.state_label = QLabel("状态: -")
        self.state_label.setStyleSheet("font-weight: 700;")
        top.addWidget(title)
        top.addStretch(1)
        top.addWidget(self.state_label)
        lay.addLayout(top)

        self.desc_label = QLabel(spec.desc)
        self.desc_label.setWordWrap(True)
        lay.addWidget(self.desc_label)

        meta = QGridLayout()
        self.dep_label = QLabel("-")
        self.in_label = QLabel("-")
        self.out_label = QLabel("-")
        self.missing_label = QLabel("-")
        self.last_label = QLabel("-")
        self.result_label = QLabel("-")
        for w in [self.dep_label, self.in_label, self.out_label, self.missing_label, self.last_label, self.result_label]:
            w.setWordWrap(True)
        meta.addWidget(QLabel("依赖阶段"), 0, 0)
        meta.addWidget(self.dep_label, 0, 1)
        meta.addWidget(QLabel("必要输入"), 1, 0)
        meta.addWidget(self.in_label, 1, 1)
        meta.addWidget(QLabel("预期输出"), 2, 0)
        meta.addWidget(self.out_label, 2, 1)
        meta.addWidget(QLabel("缺失产物"), 3, 0)
        meta.addWidget(self.missing_label, 3, 1)
        meta.addWidget(QLabel("最近运行时间"), 4, 0)
        meta.addWidget(self.last_label, 4, 1)
        meta.addWidget(QLabel("最近运行结果"), 5, 0)
        meta.addWidget(self.result_label, 5, 1)
        lay.addLayout(meta)

        btns = QHBoxLayout()
        self.run_btn = QPushButton("运行")
        self.resume_btn = QPushButton("断点续跑")
        self.resume_btn.setToolTip("已完成产物会被跳过，仅执行缺失阶段。")
        self.log_btn = QPushButton("查看日志")
        self.out_btn = QPushButton("打开输出目录")
        self.run_btn.setProperty("role", "primary")
        self.resume_btn.setProperty("role", "secondary")
        self.log_btn.setProperty("role", "ghost")
        self.out_btn.setProperty("role", "ghost")
        self.run_btn.clicked.connect(lambda: run_cb(spec.stage, False))
        self.resume_btn.clicked.connect(lambda: run_cb(spec.stage, True))
        self.log_btn.clicked.connect(lambda: log_cb(spec.stage))
        self.out_btn.clicked.connect(lambda: out_cb(spec))
        btns.addWidget(self.run_btn)
        btns.addWidget(self.resume_btn)
        btns.addWidget(self.log_btn)
        btns.addWidget(self.out_btn)
        btns.addStretch(1)
        lay.addLayout(btns)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(SOFTWARE_TITLE)
        self.resize(1480, 900)
        self.setMinimumSize(1280, 760)

        self.case_names: list[str] = []
        self.case_data: dict[str, Any] = {}
        self.current_case: str = current_case_name() or ""
        self.field_widgets: dict[str, QWidget] = {}
        self.field_specs: dict[str, FieldSpec] = {x.key: x for x in FIELDS}
        self.field_error_labels: dict[str, QLabel] = {}
        self.issue_field_map: dict[int, str] = {}
        self.stage_cards: dict[str, StageCard] = {}
        self.point_widgets: dict[str, QLineEdit] = {}
        self.vertical_levels: list[Optional[float]] = []
        self.task_stage_code = "all"

        self.run_process: QProcess | None = None
        self.run_stdout_fp: Any = None
        self.run_stderr_fp: Any = None
        self.current_task: dict[str, Any] | None = None
        self.last_task_by_stage: dict[str, dict[str, Any]] = {}
        self.post_run_buttons: list[QPushButton] = []
        self.post_last_outputs: dict[str, Path] = {}
        self.post_preview_labels: dict[str, QLabel] = {}
        self.cancel_requested = False

        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(1500)
        self.refresh_timer.timeout.connect(self._refresh_runtime_views)

        self._build_ui()
        self._apply_style()
        self.load_cases()
        self.refresh_timer.start()

    def _vertical_source_grid_path(self) -> Path:
        if self.current_case:
            return case_dir(self.current_case) / "grid" / "grid.cmn"
        return current_project_path("grid", "grid.cmn")

    def _apply_style(self) -> None:
        QFontDatabase.addApplicationFont(str(tutorial_path("SourceHanSansSC-Regular-2.otf")))
        self.setFont(QFont("Source Han Sans SC", 11))
        self.setStyleSheet(QSS)

    def _build_ui(self) -> None:
        root = QWidget(self)
        self.setCentralWidget(root)
        main = QVBoxLayout(root)
        main.setContentsMargins(12, 12, 12, 8)
        main.setSpacing(10)

        top_card = QFrame()
        top_card.setObjectName("TopCard")
        top_lay = QVBoxLayout(top_card)
        top_lay.setContentsMargins(14, 12, 14, 12)
        top_lay.setSpacing(8)

        self.title_label = QLabel(SOFTWARE_TITLE)
        self.title_label.setStyleSheet("font-size: 17pt; font-weight: 700;")
        self.title_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.info_yaml = QLabel("配置文档：-")
        self.info_yaml.setProperty("kind", "muted")
        self.info_yaml.setTextInteractionFlags(Qt.TextSelectableByMouse)
        row1 = QHBoxLayout()
        row1.addWidget(self.title_label, 1)
        row1.addWidget(self.info_yaml, 2, alignment=Qt.AlignRight)

        self.info_case = QLabel("当前案例：-")
        self.info_current = QLabel("current：-")
        self.info_match = QLabel("一致性：-")
        self.info_task = QLabel("任务状态：空闲")
        self.info_match.setProperty("kind", "badge_bad")
        self.info_task.setProperty("kind", "badge_info")
        row2 = QHBoxLayout()
        row2.setSpacing(10)
        row2.addWidget(self.info_case)
        row2.addWidget(self.info_current)
        row2.addWidget(self.info_match)
        row2.addWidget(self.info_task)
        row2.addStretch(1)

        self.sync_btn = QPushButton("同步current到当前案例")
        self.sync_btn.setProperty("role", "secondary")
        self.sync_btn.clicked.connect(self.sync_current_case)
        self.sync_btn.setEnabled(False)
        row3 = QHBoxLayout()
        row3.addWidget(self.sync_btn, alignment=Qt.AlignLeft)
        row3.addStretch(1)

        for lbl in [self.info_case, self.info_current, self.info_match, self.info_task]:
            lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        top_lay.addLayout(row1)
        top_lay.addLayout(row2)
        top_lay.addLayout(row3)

        main.addWidget(top_card)

        splitter = QSplitter(Qt.Horizontal)
        self.nav = QListWidget()
        self.nav.setObjectName("NavList")
        self.nav.setFixedWidth(190)
        self.nav_items = [
            "项目总览",
            "参数配置",
            "任务管理",
            "日志查看",
            "结果后处理",
        ]
        for item in self.nav_items:
            self.nav.addItem(item)
        self.nav.currentRowChanged.connect(self._on_nav_changed)

        self.pages = QStackedWidget()
        self.page_overview = self._wrap_scroll(self._build_page_overview())
        self.page_params = self._wrap_scroll(self._build_page_params())
        self.page_tasks = self._wrap_scroll(self._build_page_tasks())
        self.page_logs = self._wrap_scroll(self._build_page_logs())
        self.page_post = self._wrap_scroll(self._build_page_post())

        for p in [
            self.page_overview,
            self.page_params,
            self.page_tasks,
            self.page_logs,
            self.page_post,
        ]:
            self.pages.addWidget(p)

        splitter.addWidget(self.nav)
        splitter.addWidget(self.pages)
        splitter.setStretchFactor(1, 1)
        main.addWidget(splitter, 1)

        status = QStatusBar(self)
        self.setStatusBar(status)
        self.sb_operation = QLabel("操作: 就绪")
        self.sb_stage = QLabel("阶段: -")
        self.sb_error = QLabel("最近错误: -")
        self.sb_progress_text = QLabel("进度: 空闲")
        self.sb_progress = QProgressBar()
        self.sb_progress.setFixedWidth(220)
        self.sb_progress.setRange(0, 1)
        self.sb_progress.setValue(0)

        status.addWidget(self.sb_operation, 2)
        status.addWidget(self.sb_stage, 1)
        status.addWidget(self.sb_error, 3)
        status.addPermanentWidget(self.sb_progress_text)
        status.addPermanentWidget(self.sb_progress)

        self.nav.setCurrentRow(0)

    def _build_page_overview(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        manage = QGroupBox("项目总览")
        grid = QGridLayout(manage)
        self.case_combo = QComboBox()
        self.case_combo.setView(QListView())
        self.case_combo.setMinimumWidth(420)
        self.case_combo.currentIndexChanged.connect(self._on_case_combo_changed)
        self.new_case_edit = QLineEdit()
        self.new_case_edit.setPlaceholderText("例如: test2")
        self.load_btn = QPushButton("加载")
        self.save_btn = QPushButton("保存 case.yaml")
        self.create_btn = QPushButton("新建案例")
        self.reload_btn = QPushButton("刷新案例列表")
        self.load_btn.setProperty("role", "primary")
        self.save_btn.setProperty("role", "secondary")
        self.create_btn.setProperty("role", "primary")
        self.reload_btn.setProperty("role", "ghost")
        self.load_btn.clicked.connect(self.load_selected_case)
        self.save_btn.clicked.connect(self.save_case_yaml)
        self.create_btn.clicked.connect(self.create_case_from_input)
        self.reload_btn.clicked.connect(self.load_cases)

        grid.addWidget(QLabel("当前案例"), 0, 0)
        grid.addWidget(self.case_combo, 0, 1, 1, 3)
        grid.addWidget(self.load_btn, 0, 4)
        grid.addWidget(QLabel("新建案例"), 1, 0)
        grid.addWidget(self.new_case_edit, 1, 1, 1, 3)
        grid.addWidget(self.create_btn, 1, 4)
        grid.addWidget(self.save_btn, 2, 3)
        grid.addWidget(self.reload_btn, 2, 4)
        lay.addWidget(manage)

        card = QGroupBox("状态摘要")
        form = QFormLayout(card)
        self.ov_case_count = QLabel("0")
        self.ov_current_case = QLabel("-")
        self.ov_case_yaml = QLabel("-")
        self.ov_runs_count = QLabel("0")
        self.ov_last_run = QLabel("-")
        self.ov_current_consistency = QLabel("-")
        self.ov_preprocess_error = QLabel("-")
        for lbl in [self.ov_case_count, self.ov_current_case, self.ov_case_yaml, self.ov_runs_count, self.ov_last_run, self.ov_current_consistency, self.ov_preprocess_error]:
            lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        form.addRow("案例数量", self.ov_case_count)
        form.addRow("当前选中案例", self.ov_current_case)
        form.addRow("配置文档", self.ov_case_yaml)
        form.addRow("运行记录数", self.ov_runs_count)
        form.addRow("最近运行", self.ov_last_run)
        form.addRow("current 一致性", self.ov_current_consistency)
        form.addRow("最近地形处理错误", self.ov_preprocess_error)
        lay.addWidget(card)

        artifact_box = QGroupBox("产物检查")
        artifact_lay = QVBoxLayout(artifact_box)
        top = QHBoxLayout()
        btn = QPushButton("刷新产物状态")
        btn.clicked.connect(self.refresh_artifact_table)
        top.addWidget(btn)
        top.addStretch(1)
        artifact_lay.addLayout(top)
        self.artifact_table = QTableWidget(0, 5)
        self.artifact_table.setHorizontalHeaderLabels(["阶段", "状态", "缺失产物", "输入检查", "说明"])
        self.artifact_table.horizontalHeader().setStretchLastSection(True)
        artifact_lay.addWidget(self.artifact_table)
        lay.addWidget(artifact_box)
        lay.addStretch(1)
        return w

    def _wrap_scroll(self, widget: QWidget) -> QScrollArea:
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        area.setWidget(widget)
        return area

    def _build_page_params(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)

        top = QHBoxLayout()
        self.btn_validate = QPushButton("配置检查")
        self.btn_validate.clicked.connect(self.validate_config_and_show)
        self.btn_save_params = QPushButton("保存 case.yaml")
        self.btn_validate.setProperty("role", "primary")
        self.btn_save_params.setProperty("role", "secondary")
        self.btn_save_params.clicked.connect(self.save_case_yaml)
        top.addWidget(self.btn_validate)
        top.addWidget(self.btn_save_params)
        top.addStretch(1)
        lay.addLayout(top)

        split = QSplitter(Qt.Horizontal)
        form_wrap = QWidget()
        form_lay = QVBoxLayout(form_wrap)
        st_body = QWidget()
        st_grid = QGridLayout(st_body)
        st_grid.setHorizontalSpacing(10)
        st_grid.setVerticalSpacing(6)
        st_grid.setColumnMinimumWidth(0, 126)
        st_grid.setColumnMinimumWidth(2, 126)
        st_grid.setColumnStretch(1, 1)
        st_grid.setColumnStretch(3, 1)
        row = 0
        row = self._add_field_row_pair(st_grid, row, "preprocess.research_time.begin", "preprocess.research_time.end")
        row = self._add_field_row_pair(st_grid, row, "preprocess.grid.center.longitude", "preprocess.grid.center.latitude")
        row = self._add_field_row_pair(st_grid, row, "preprocess.grid.domain.length_km", "preprocess.grid.domain.width_km")
        row = self._add_field_row_pair(st_grid, row, "preprocess.grid.resolution_km", "settings.timezone")
        row = self._add_field_row_pair(st_grid, row, "preprocess.grid.nz", None)
        self.nz_setup_btn = QPushButton("垂直层数设置")
        self.nz_setup_btn.setProperty("role", "secondary")
        self.nz_setup_btn.clicked.connect(self.open_vertical_levels_dialog)
        st_grid.addWidget(self.nz_setup_btn, row - 1, 2, 1, 2, alignment=Qt.AlignVCenter | Qt.AlignLeft)
        form_lay.addWidget(self._make_section_card("时空范围", st_body))

        upper_body = QWidget()
        upper_grid = QGridLayout(upper_body)
        upper_grid.setColumnMinimumWidth(0, 126)
        upper_grid.setColumnMinimumWidth(2, 126)
        upper_grid.setColumnStretch(1, 1)
        upper_grid.setColumnStretch(3, 1)
        spec = self.field_specs["preprocess.upperair.pstop_hpa"]
        upper_grid.addWidget(QLabel(self._field_label(spec)), 0, 0)
        pstop_widget = self._new_field_widget(spec)
        upper_grid.addWidget(self._wrap_field(spec, pstop_widget), 0, 1)
        tip = QLabel("说明：当地海拔0-2500米，建议500；当地海拔2500-4000米，建议400；当地海拔高于4000米，建议300")
        tip.setWordWrap(True)
        tip.setProperty("kind", "muted")
        upper_grid.addWidget(tip, 0, 2, 1, 2)
        form_lay.addWidget(self._make_section_card("高空气象", upper_body))

        src_body = QWidget()
        src_grid = QGridLayout(src_body)
        src_grid.setColumnMinimumWidth(0, 126)
        src_grid.setColumnMinimumWidth(2, 126)
        src_grid.setColumnStretch(1, 1)
        src_grid.setColumnStretch(3, 1)
        self._add_point_field_pair(src_grid, 0, "点源经度位置", "lon", "123.456", "纬度位置", "lat", "34.567")
        self._add_point_field_pair(src_grid, 1, "烟囱高度(m)", "stack_height_m", "50.0", "烟囱基底海拔(m)", "base_elev_m", "0.0")
        self._add_point_field_pair(src_grid, 2, "烟囱直径(m)", "stack_diameter_m", "2.0", "出口流速(m/s)", "exit_velocity_mps", "11.11")
        self._add_point_field_pair(src_grid, 3, "出口温度(K)", "exit_temp_k", "293.0", "排放率(Bq/s)", "emission_bq_s", "222222.0")
        pollutant_badge = QLabel("污染物 H-3")
        pollutant_badge.setProperty("kind", "badge_info")
        half_life_badge = QLabel("半衰期 已设置")
        half_life_badge.setProperty("kind", "badge_info")
        src_grid.addWidget(pollutant_badge, 4, 1, 1, 1, alignment=Qt.AlignLeft)
        src_grid.addWidget(half_life_badge, 4, 3, 1, 1, alignment=Qt.AlignLeft)
        form_lay.addWidget(self._make_section_card("排放源", src_body))
        form_lay.addStretch(1)

        issue_box = QFrame()
        issue_box.setObjectName("SectionCard")
        issue_box.setMaximumWidth(340)
        issue_lay = QVBoxLayout(issue_box)
        issue_lay.addWidget(QLabel("配置检查结果"))
        self.issue_list = QListWidget()
        self.issue_list.itemClicked.connect(self.on_issue_clicked)
        issue_lay.addWidget(self.issue_list, 1)

        split.addWidget(form_wrap)
        split.addWidget(issue_box)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 2)
        lay.addWidget(split, 1)
        return w

    def _new_field_widget(self, spec: FieldSpec, readonly: bool = False) -> QWidget:
        if spec.widget == "bool":
            wid = QCheckBox()
        else:
            wid = QLineEdit()
            wid.setMinimumWidth(240)
            if readonly:
                wid.setReadOnly(True)
        wid.setToolTip(f"{spec.tooltip}\n默认值: {spec.default}")
        self.field_widgets[spec.key] = wid
        return wid

    def _wrap_field(self, spec: FieldSpec, widget: QWidget) -> QWidget:
        row_wrap = QWidget()
        row_l = QVBoxLayout(row_wrap)
        row_l.setContentsMargins(0, 0, 0, 0)
        row_l.setSpacing(2)
        row_l.addWidget(widget)
        err = QLabel("")
        err.setStyleSheet("color:#be123c;")
        row_l.addWidget(err)
        self.field_error_labels[spec.key] = err
        return row_wrap

    def _field_label(self, spec: FieldSpec) -> str:
        return f"{spec.label} *" if spec.required else spec.label

    def _add_field_row_pair(self, grid: QGridLayout, row: int, left_key: str, right_key: str | None, readonly: bool = False) -> int:
        left_spec = self.field_specs[left_key]
        left_widget = self._new_field_widget(left_spec, readonly=readonly)
        grid.addWidget(QLabel(self._field_label(left_spec)), row, 0)
        grid.addWidget(self._wrap_field(left_spec, left_widget), row, 1)
        if right_key:
            right_spec = self.field_specs[right_key]
            right_widget = self._new_field_widget(right_spec, readonly=readonly)
            grid.addWidget(QLabel(self._field_label(right_spec)), row, 2)
            grid.addWidget(self._wrap_field(right_spec, right_widget), row, 3)
        return row + 1

    def _add_single_field(self, form: QFormLayout, key: str) -> None:
        spec = self.field_specs[key]
        w = self._new_field_widget(spec)
        form.addRow(spec.label, self._wrap_field(spec, w))

    def _add_point_field_pair(
        self,
        grid: QGridLayout,
        row: int,
        left_label: str,
        left_key: str,
        left_default: str,
        right_label: str,
        right_key: str,
        right_default: str,
    ) -> None:
        l = QLineEdit(left_default)
        r = QLineEdit(right_default)
        self.point_widgets[left_key] = l
        self.point_widgets[right_key] = r
        grid.addWidget(QLabel(left_label), row, 0)
        grid.addWidget(l, row, 1)
        grid.addWidget(QLabel(right_label), row, 2)
        grid.addWidget(r, row, 3)

    def _set_task_stage(self, stage_code: str) -> None:
        self.task_stage_code = stage_code
        for code, btn in self.stage_btns.items():
            btn.setChecked(code == stage_code)
        idx = self.task_stage_combo.findData(stage_code)
        if idx >= 0:
            self.task_stage_combo.setCurrentIndex(idx)

    def _make_filter_item(self, label_text: str, widget: QWidget, label_width: int = 48) -> QWidget:
        box = QWidget()
        layout = QHBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        label = QLabel(label_text)
        label.setFixedWidth(label_width)
        layout.addWidget(label)
        layout.addWidget(widget)
        return box

    def _make_section_card(self, title: str, body: QWidget) -> QFrame:
        card = QFrame()
        card.setObjectName("SectionCard")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        head = QFrame()
        head.setObjectName("SectionHeader")
        head_lay = QHBoxLayout(head)
        head_lay.setContentsMargins(12, 8, 12, 8)
        t = QLabel(title)
        t.setObjectName("SectionTitle")
        head_lay.addWidget(t)
        head_lay.addStretch(1)
        lay.addWidget(head)
        body_wrap = QWidget()
        body_lay = QVBoxLayout(body_wrap)
        body_lay.setContentsMargins(12, 10, 12, 10)
        body_lay.addWidget(body)
        lay.addWidget(body_wrap)
        return card

    def _build_page_workflow(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        tip = QLabel("说明：断点续跑会先检查阶段产物，完整则跳过，缺失才继续运行。")
        tip.setWordWrap(True)
        tip.setStyleSheet("color:#334155;")
        lay.addWidget(tip)
        for spec in STAGES:
            card = StageCard(spec, self.run_stage, self.view_latest_log_by_stage, self.open_stage_output_dir)
            self.stage_cards[spec.stage] = card
            lay.addWidget(card)
        lay.addStretch(1)
        return w

    def _build_page_tasks(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)

        run_card = QGroupBox("任务管理")
        run_lay = QVBoxLayout(run_card)
        run_lay.setSpacing(8)

        self.task_stage_combo = QComboBox()
        self.task_stage_combo.addItem("全部", "all")
        self.task_stage_combo.addItem("地形处理", "preprocess")
        self.task_stage_combo.addItem("高空气象", "upperair")
        self.task_stage_combo.addItem("地面气象", "surface")
        self.task_stage_combo.addItem("诊断风场", "met")
        self.task_stage_combo.addItem("烟团模型", "puff")
        self.task_stage_combo.hide()
        self.stage_btn_group = QButtonGroup(self)
        self.stage_btn_group.setExclusive(True)
        self.stage_btns: dict[str, QPushButton] = {}
        stage_picker = QWidget()
        stage_grid = QGridLayout(stage_picker)
        stage_grid.setContentsMargins(0, 4, 0, 6)
        stage_grid.setHorizontalSpacing(8)
        stage_grid.setVerticalSpacing(12)
        stage_grid.setColumnStretch(5, 1)

        for text, code, row, col, row_span in [
            ("全\n部", "all", 0, 0, 2),
            ("地形处理", "preprocess", 0, 1, 1),
            ("高空气象", "upperair", 0, 2, 1),
            ("地面气象", "surface", 0, 3, 1),
            ("诊断风场", "met", 0, 4, 1),
            ("烟团模型", "puff", 1, 1, 1),
        ]:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setProperty("kind", "stage_picker")
            if code == "all":
                btn.setFixedWidth(45)
                btn.setFixedHeight(76)
            else:
                btn.setFixedWidth(90)
                btn.setFixedHeight(36)
            btn.clicked.connect(lambda _checked=False, s=code: self._set_task_stage(s))
            self.stage_btn_group.addButton(btn)
            self.stage_btns[code] = btn
            stage_grid.addWidget(btn, row, col, row_span, 1)

        for text, tip, col in [
            ("土壤环节", "待接入：后续将接入土壤沉降计算", 2),
            ("植物环节", "待接入：后续将接入湿沉降计算", 3),
            ("剂量评价", "待接入：后续将接入剂量评价", 4),
        ]:
            btn = QPushButton(text)
            btn.setProperty("kind", "stage_picker")
            btn.setFixedWidth(90)
            btn.setFixedHeight(36)
            btn.setEnabled(False)
            btn.setToolTip(tip)
            stage_grid.addWidget(btn, 1, col, 1, 1)

        self._set_task_stage("all")
        self.task_resume = QCheckBox("断点续跑")
        self.task_resume.setChecked(True)
        self.task_resume_tip = QLabel("断点续跑会先检查阶段产物，完整则跳过该任务，缺失才继续运行")
        self.task_resume_tip.setStyleSheet("color:#475569;")
        self.task_run_btn = QPushButton("开始任务")
        self.task_cancel_btn = QPushButton("取消任务")
        self.task_retry_btn = QPushButton("失败重试")
        self.task_open_log_btn = QPushButton("打开日志目录")
        self.task_open_output_btn = QPushButton("打开输出目录")
        self.task_run_btn.setProperty("role", "primary")
        self.task_cancel_btn.setProperty("role", "danger")
        self.task_retry_btn.setProperty("role", "secondary")
        self.task_open_log_btn.setProperty("role", "ghost")
        self.task_open_output_btn.setProperty("role", "ghost")

        self.task_run_btn.clicked.connect(lambda: self.run_stage(self.task_stage_code, self.task_resume.isChecked()))
        self.task_cancel_btn.clicked.connect(self.cancel_task)
        self.task_retry_btn.clicked.connect(self.retry_last_failed)
        self.task_open_log_btn.clicked.connect(self.open_current_task_log_dir)
        self.task_open_output_btn.clicked.connect(self.open_current_task_output_dir)

        self.task_state = QLabel("状态: 空闲")
        self.task_pid = QLabel("PID: -")
        self.task_start = QLabel("开始时间: -")
        self.task_elapsed = QLabel("运行时长: -")
        self.task_case = QLabel("案例: -")
        self.task_stage = QLabel("阶段: -")

        top_row = QHBoxLayout()
        top_row.setSpacing(12)
        left_part = QHBoxLayout()
        left_part.setSpacing(8)
        stage_label = QLabel("阶段")
        stage_label.setFixedWidth(34)
        left_part.addWidget(stage_label, alignment=Qt.AlignTop)
        left_part.addWidget(stage_picker, 0, alignment=Qt.AlignTop)
        top_row.addLayout(left_part)
        top_row.addStretch(1)
        action_grid = QGridLayout()
        action_grid.setHorizontalSpacing(8)
        action_grid.setVerticalSpacing(8)
        action_grid.addWidget(self.task_run_btn, 0, 0)
        action_grid.addWidget(self.task_cancel_btn, 0, 1)
        action_grid.addWidget(self.task_retry_btn, 0, 2)
        action_grid.addWidget(self.task_open_log_btn, 1, 1)
        action_grid.addWidget(self.task_open_output_btn, 1, 2)
        top_row.addLayout(action_grid)
        run_lay.addLayout(top_row)

        info_grid = QGridLayout()
        info_grid.setContentsMargins(0, 10, 0, 0)
        info_grid.addWidget(self.task_state, 0, 0, 1, 2)
        info_grid.addWidget(self.task_pid, 0, 2, 1, 2)
        info_grid.addWidget(self.task_start, 1, 0, 1, 2)
        info_grid.addWidget(self.task_elapsed, 1, 2, 1, 2)
        info_grid.addWidget(self.task_case, 2, 0, 1, 2)
        info_grid.addWidget(self.task_stage, 2, 2, 1, 2)
        info_grid.addWidget(self.task_resume, 3, 0, 1, 1)
        info_grid.addWidget(self.task_resume_tip, 3, 1, 1, 3)
        run_lay.addLayout(info_grid)

        lay.addWidget(run_card)

        log_box = QGroupBox("当前任务日志")
        log_lay = QVBoxLayout(log_box)
        self.task_log = QPlainTextEdit()
        self.task_log.setReadOnly(True)
        self.task_log.setFont(QFont("Source Han Sans SC", 10))
        self.task_log.setPlaceholderText("暂无任务日志")
        log_lay.addWidget(self.task_log)
        lay.addWidget(log_box, 1)
        return w

    def _build_page_logs(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)

        card = QGroupBox("日志查看")
        card.setObjectName("LogCard")
        card_lay = QVBoxLayout(card)

        flt = QGroupBox()
        flt.setObjectName("InnerCard")
        fl = QGridLayout(flt)
        self.log_case_filter = QComboBox()
        self.log_case_filter.setView(QListView())
        self.log_stage_filter = QComboBox()
        self.log_stage_filter.setView(QListView())
        self.log_status_filter = QComboBox()
        self.log_status_filter.setView(QListView())
        self.log_keyword = QLineEdit()
        self.log_keyword.setPlaceholderText("关键词搜索")
        self.log_refresh_btn = QPushButton("刷新")
        self.log_refresh_btn.setProperty("role", "secondary")
        self.log_refresh_btn.clicked.connect(self.refresh_logs_table)

        self.log_stage_filter.addItem("全部", "全部")
        self.log_stage_filter.addItem("地形处理", "preprocess")
        self.log_stage_filter.addItem("高空气象", "upperair")
        self.log_stage_filter.addItem("地面气象", "surface")
        self.log_stage_filter.addItem("诊断风场", "met")
        self.log_stage_filter.addItem("烟团模型", "puff")
        self.log_stage_filter.addItem("后处理-浓度云图", "post_conc_plot")
        self.log_stage_filter.addItem("后处理-云图动画", "post_animation")
        self.log_stage_filter.addItem("后处理-点位浓度", "post_point")
        self.log_stage_filter.addItem("后处理-风玫瑰", "post_windrose")
        self.log_status_filter.addItems(["全部", "成功", "失败", "取消", "运行中"])

        self.log_case_filter.setFixedWidth(180)
        self.log_stage_filter.setFixedWidth(160)
        self.log_status_filter.setFixedWidth(140)
        row1 = QHBoxLayout()
        row1.setSpacing(16)
        row1.addWidget(self._make_filter_item("案例", self.log_case_filter, 40))
        row1.addWidget(self._make_filter_item("阶段", self.log_stage_filter, 40))
        row1.addWidget(self._make_filter_item("状态", self.log_status_filter, 40))
        row1.addStretch(1)
        row1.addWidget(self.log_refresh_btn)
        row2 = QHBoxLayout()
        row2.setSpacing(8)
        kw_label = QLabel("关键词")
        kw_label.setFixedWidth(56)
        row2.addWidget(kw_label)
        row2.addWidget(self.log_keyword, 1)
        fl.addLayout(row1, 0, 0, 1, 6)
        fl.addLayout(row2, 1, 0, 1, 6)
        card_lay.addWidget(flt)

        self.log_table = QTableWidget(0, 7)
        self.log_table.setHorizontalHeaderLabels(["案例", "阶段", "开始", "状态", "返回码", "错误摘要", "目录"])
        self.log_table.horizontalHeader().setStretchLastSection(True)
        self.log_table.setAlternatingRowColors(True)
        self.log_table.verticalHeader().setDefaultSectionSize(30)
        self.log_table.itemSelectionChanged.connect(self.on_log_row_selected)
        card_lay.addWidget(self.log_table, 1)

        actions = QHBoxLayout()
        self.log_open_dir_btn = QPushButton("打开日志目录")
        self.log_copy_err_btn = QPushButton("复制错误摘要")
        self.log_open_dir_btn.setProperty("role", "ghost")
        self.log_copy_err_btn.setProperty("role", "ghost")
        self.log_open_dir_btn.clicked.connect(self.open_selected_log_dir)
        self.log_copy_err_btn.clicked.connect(self.copy_selected_error)
        actions.addWidget(self.log_open_dir_btn)
        actions.addWidget(self.log_copy_err_btn)
        actions.addStretch(1)
        card_lay.addLayout(actions)

        tabs = QTabWidget()
        tabs.setObjectName("LogTabs")
        self.stdout_view = QPlainTextEdit()
        self.stdout_view.setReadOnly(True)
        self.stdout_view.setFont(QFont("Source Han Sans SC", 10))
        self.stderr_view = QPlainTextEdit()
        self.stderr_view.setReadOnly(True)
        self.stderr_view.setFont(QFont("Source Han Sans SC", 10))
        self.stdout_view.setPlaceholderText("请选择一条运行记录查看日志")
        self.stderr_view.setPlaceholderText("请选择一条运行记录查看日志")
        tabs.addTab(self.stdout_view, "标准输出")
        tabs.addTab(self.stderr_view, "错误输出")
        card_lay.addWidget(tabs, 1)

        lay.addWidget(card)
        lay.addStretch(1)
        return w

    def _build_page_post(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)

        card = QGroupBox("结果后处理")
        card.setObjectName("PostCard")
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(12, 22, 12, 12)
        card_lay.setSpacing(10)

        # Top row: picker buttons (left) + action buttons (right) — matches 任务管理 style
        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        picker = QWidget()
        picker_grid = QGridLayout(picker)
        picker_grid.setContentsMargins(0, 0, 0, 0)
        picker_grid.setHorizontalSpacing(8)
        picker_grid.setVerticalSpacing(8)
        self.post_btn_group = QButtonGroup(self)
        self.post_btn_group.setExclusive(True)
        self.post_pages = QStackedWidget()
        self.post_pages.setObjectName("PostPages")
        self.post_page_keys = ["conc_plot", "animation", "point", "windrose"]
        for idx, (label, key) in enumerate(
            [
                ("浓度云图", "conc_plot"),
                ("云图动画", "animation"),
                ("点位浓度", "point"),
                ("风玫瑰", "windrose"),
            ]
        ):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setProperty("kind", "stage_picker")
            btn.setFixedWidth(90)
            btn.setFixedHeight(36)
            btn.clicked.connect(lambda _checked=False, i=idx: self.post_pages.setCurrentIndex(i))
            self.post_btn_group.addButton(btn)
            picker_grid.addWidget(btn, idx // 3, idx % 3)
        picker_grid.setColumnStretch(3, 1)
        top_row.addWidget(picker)
        top_row.addStretch(1)

        # Action buttons grid — same style as 任务管理
        action_grid = QGridLayout()
        action_grid.setHorizontalSpacing(8)
        action_grid.setVerticalSpacing(8)
        self.post_run_btn = QPushButton("运行")
        self.post_cancel_btn = QPushButton("取消")
        self.post_reset_btn = QPushButton("恢复默认")
        self.post_open_dir_btn = QPushButton("打开输出目录")
        self.post_open_file_btn = QPushButton("打开结果文件")
        self.post_run_btn.setProperty("role", "primary")
        self.post_cancel_btn.setProperty("role", "danger")
        self.post_reset_btn.setProperty("role", "secondary")
        self.post_open_dir_btn.setProperty("role", "ghost")
        self.post_open_file_btn.setProperty("role", "ghost")
        self.post_run_btn.clicked.connect(self._run_current_post)
        self.post_cancel_btn.clicked.connect(self.cancel_task)
        self.post_reset_btn.clicked.connect(self._reset_current_post)
        self.post_open_dir_btn.clicked.connect(self.open_postprocess_output_dir)
        self.post_open_file_btn.clicked.connect(self._open_current_post_file)
        self.post_run_buttons.append(self.post_run_btn)
        action_grid.addWidget(self.post_run_btn, 0, 0)
        action_grid.addWidget(self.post_cancel_btn, 0, 1)
        action_grid.addWidget(self.post_reset_btn, 0, 2)
        action_grid.addWidget(self.post_open_dir_btn, 1, 1)
        action_grid.addWidget(self.post_open_file_btn, 1, 2)
        top_row.addLayout(action_grid)
        card_lay.addLayout(top_row)

        self.post_run_callbacks: dict[str, Any] = {}
        self.post_reset_callbacks: dict[str, Any] = {}
        self.post_output_keys: dict[str, str] = {}

        self.post_pages.addWidget(self._build_post_conc_tab())
        self.post_pages.addWidget(self._build_post_animation_tab())
        self.post_pages.addWidget(self._build_post_point_tab())
        self.post_pages.addWidget(self._build_post_windrose_tab())
        card_lay.addWidget(self.post_pages, 1)

        lay.addWidget(card)
        lay.addStretch(1)

        first_btn = self.post_btn_group.buttons()[0]
        first_btn.setChecked(True)
        return w

    def _current_post_page_key(self) -> str:
        idx = self.post_pages.currentIndex()
        if 0 <= idx < len(self.post_page_keys):
            return self.post_page_keys[idx]
        return "conc_plot"

    def _run_current_post(self) -> None:
        cb = self.post_run_callbacks.get(self._current_post_page_key())
        if cb:
            cb()

    def _reset_current_post(self) -> None:
        cb = self.post_reset_callbacks.get(self._current_post_page_key())
        if cb:
            cb()

    def _open_current_post_file(self) -> None:
        key = self.post_output_keys.get(self._current_post_page_key(), self._current_post_page_key())
        self.open_postprocess_output_file(key)

    def _post_form_tab(self, preview_key: str) -> tuple[QWidget, QFormLayout]:
        w = QWidget()
        lay = QVBoxLayout(w)
        body = QHBoxLayout()
        form_box = QGroupBox("参数")
        form_box.setObjectName("InnerCard")
        form = QFormLayout(form_box)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)
        body.addWidget(form_box, 4)
        preview = QGroupBox("预览")
        preview.setObjectName("InnerCard")
        preview_lay = QVBoxLayout(preview)
        preview_label = QLabel("运行后显示输出预览")
        preview_label.setAlignment(Qt.AlignCenter)
        preview_label.setMinimumHeight(260)
        preview_label.setStyleSheet("background:#f8fbff; border:1px solid #d8e2ee; border-radius:8px; color:#64748b;")
        preview_lay.addWidget(preview_label)
        self.post_preview_labels[preview_key] = preview_label
        body.addWidget(preview, 5)
        lay.addLayout(body, 1)
        return w, form


    def _build_post_conc_tab(self) -> QWidget:
        w, form = self._post_form_tab("conc_plot")
        self.post_conc_mode = QComboBox()
        self.post_conc_mode.setView(QListView())
        self.post_conc_mode.addItem("瞬时云图", "snapshot")
        self.post_conc_mode.addItem("年度平均", "annual")
        self.post_conc_mode.addItem("季节平均", "seasonal")
        self.post_conc_time = QLineEdit()
        self.post_conc_time.setPlaceholderText("YYYY-MM-DD HH:MM，瞬时云图时填写")
        self.post_conc_scale = QComboBox()
        self.post_conc_scale.addItems(["linear", "log"])
        self.post_conc_vmin = QLineEdit("5e-4")
        self.post_conc_vmax = QLineEdit("5e-2")
        self.post_conc_threshold = QLineEdit("1.2e-3")
        self.post_conc_output = QLineEdit("conc_snapshot.png")
        self.post_conc_mode.currentTextChanged.connect(self._on_conc_mode_changed)
        for idx, (label, widget) in enumerate([
            ("云图类型", self.post_conc_mode),
            ("时刻", self.post_conc_time),
            ("纵坐标", self.post_conc_scale),
            ("最小值", self.post_conc_vmin),
            ("最大值", self.post_conc_vmax),
            ("阈值", self.post_conc_threshold),
            ("输出文件", self.post_conc_output),
        ]):
            form.addRow(label, widget)
        self.post_run_callbacks["conc_plot"] = self.run_post_conc_plot
        self.post_reset_callbacks["conc_plot"] = self.reset_post_conc
        self.post_output_keys["conc_plot"] = "conc_plot"
        return w

    def _on_conc_mode_changed(self) -> None:
        mode = self.post_conc_mode.currentData()
        is_snapshot = mode == "snapshot"
        self.post_conc_time.setEnabled(is_snapshot)
        if not is_snapshot:
            self.post_conc_time.clear()
        self._sync_post_conc_defaults()

    def _build_post_animation_tab(self) -> QWidget:
        w, form = self._post_form_tab("animation")
        self.post_anim_format = QComboBox()
        self.post_anim_format.addItems(["mp4", "gif"])
        self.post_anim_start = QLineEdit()
        self.post_anim_start.setPlaceholderText("格式 YYYY-MM-DD HH:MM，留空默认跑全时刻")
        self.post_anim_end = QLineEdit()
        self.post_anim_end.setPlaceholderText("格式 YYYY-MM-DD HH:MM，留空默认跑全时刻")
        self.post_anim_fps = QLineEdit()
        self.post_anim_fps.setPlaceholderText("默认 10，帧率越高动画越流畅")
        self.post_anim_stride = QLineEdit()
        self.post_anim_stride.setPlaceholderText("默认 1 不跳帧，数据太密时设为 3~5")
        self.post_anim_max_frames = QLineEdit()
        self.post_anim_max_frames.setPlaceholderText("默认不限制，防止视频过长")
        self.post_anim_output = QLineEdit("conc_yearly.mp4")
        self.post_anim_format.currentTextChanged.connect(self._sync_post_animation_defaults)
        for idx, (label, widget) in enumerate([
            ("格式", self.post_anim_format),
            ("开始时刻", self.post_anim_start),
            ("结束时刻", self.post_anim_end),
            ("帧率 (fps)", self.post_anim_fps),
            ("步长", self.post_anim_stride),
            ("最大帧数", self.post_anim_max_frames),
            ("输出文件", self.post_anim_output),
        ]):
            form.addRow(label, widget)
        self.post_run_callbacks["animation"] = self.run_post_animation
        self.post_reset_callbacks["animation"] = self.reset_post_animation
        self.post_output_keys["animation"] = "animation"
        return w

    def _build_post_point_tab(self) -> QWidget:
        w, form = self._post_form_tab("point")
        self.post_point_lon = QLineEdit(str(DEFAULT_POINT_SOURCE.get("lon", "118.0")))
        self.post_point_lat = QLineEdit(str(DEFAULT_POINT_SOURCE.get("lat", "32.0")))
        self.post_point_output = QLineEdit("point_timeseries.csv")
        self.post_point_daily_output = QLineEdit("daily_concentration.png")
        for idx, (label, widget) in enumerate([
            ("经度", self.post_point_lon),
            ("纬度", self.post_point_lat),
            ("输出 CSV", self.post_point_output),
            ("日浓度 PNG", self.post_point_daily_output),
        ]):
            form.addRow(label, widget)
        self.post_run_callbacks["point"] = self.run_post_point_extract
        self.post_reset_callbacks["point"] = self.reset_post_point
        self.post_output_keys["point"] = "point"
        return w

    def _build_post_windrose_tab(self) -> QWidget:
        w, form = self._post_form_tab("windrose")
        self.post_wind_csv = QLineEdit()
        self.post_wind_csv.setText(str(self.default_windrose_csv()))
        self.post_wind_csv.setPlaceholderText("默认从 project/current/met/surface/isd2smerge_ready 选择")
        browse_btn = QPushButton("选择 CSV")
        browse_btn.setProperty("role", "ghost")
        browse_btn.clicked.connect(self.browse_post_wind_csv)
        csv_row = QWidget()
        csv_lay = QHBoxLayout(csv_row)
        csv_lay.setContentsMargins(0, 0, 0, 0)
        csv_lay.addWidget(self.post_wind_csv, 1)
        csv_lay.addWidget(browse_btn)
        self.post_wind_output = QLineEdit("windrose.png")
        for idx, (label, widget) in enumerate([
            ("CSV 文件", csv_row),
            ("输出 PNG", self.post_wind_output),
        ]):
            form.addRow(label, widget)
        self.post_run_callbacks["windrose"] = self.run_post_windrose
        self.post_reset_callbacks["windrose"] = self.reset_post_windrose
        self.post_output_keys["windrose"] = "windrose"
        return w

    def _build_simple_page(self, title: str, text: str) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        box = QGroupBox(title)
        b = QVBoxLayout(box)
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        b.addWidget(lbl)
        lay.addWidget(box)
        lay.addStretch(1)
        return w

    def _on_nav_changed(self, row: int) -> None:
        if row < 0:
            return
        self.pages.setCurrentIndex(row)

    def _current_case_name_from_combo(self) -> str:
        idx = self.case_combo.currentIndex()
        if idx < 0 or idx >= len(self.case_names):
            return ""
        return self.case_names[idx]

    def _on_case_combo_changed(self) -> None:
        name = self._current_case_name_from_combo()
        if name:
            self.current_case = name
            self._refresh_top_info()

    def load_cases(self) -> None:
        summaries = list_case_summaries()
        self.case_names = [x["name"] for x in summaries]
        current_name = current_case_name() or ""
        if current_name:
            self.current_case = current_name
        self.case_combo.blockSignals(True)
        self.case_combo.clear()
        for s in summaries:
            self.case_combo.addItem(s["display"])
        self.case_combo.blockSignals(False)

        self.log_case_filter.blockSignals(True)
        self.log_case_filter.clear()
        self.log_case_filter.addItem("全部")
        for name in self.case_names:
            self.log_case_filter.addItem(name)
        self.log_case_filter.blockSignals(False)

        self.ov_case_count.setText(str(len(self.case_names)))

        if self.case_names:
            if self.current_case in self.case_names:
                idx = self.case_names.index(self.current_case)
                self.case_combo.setCurrentIndex(idx)
                self.load_selected_case()
            else:
                self.case_combo.setCurrentIndex(-1)
                self.current_case = ""
                self.case_data = {}
                self._refresh_top_info()
                self._refresh_runtime_views()
                self._set_status("未选择案例")
        else:
            self.current_case = ""
            self.case_data = {}
            self._refresh_top_info()
            self._set_status_error("没有可用案例，请先新建")

    def load_selected_case(self) -> None:
        name = self._current_case_name_from_combo()
        if not name:
            return
        try:
            self.current_case = name
            self.case_data = load_case_yaml(name)
            self._fill_form_fields()
            self._refresh_top_info()
            self._refresh_runtime_views()
            self._refresh_post_time_dropdowns()
            self._set_status("已加载案例")
        except Exception as exc:
            self._set_status_error(str(exc))
            QMessageBox.critical(self, "加载失败", str(exc))

    def create_case_from_input(self) -> None:
        name = self.new_case_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入案例名称")
            return
        try:
            create_case(name)
            self.load_cases()
            if name in self.case_names:
                idx = self.case_names.index(name)
                self.case_combo.setCurrentIndex(idx)
                self.load_selected_case()
            self.new_case_edit.clear()
            self._set_status("已新建案例")
        except Exception as exc:
            self._set_status_error(str(exc))
            QMessageBox.critical(self, "新建失败", str(exc))

    def sync_current_case(self) -> None:
        if not self.current_case:
            return
        try:
            ensure_current_case(self.current_case)
            self._refresh_top_info()
            self._set_status("已同步 project/current")
        except Exception as exc:
            self._set_status_error(str(exc))
            QMessageBox.critical(self, "同步失败", str(exc))

    def _fill_form_fields(self) -> None:
        for spec in FIELDS:
            val = _get_path(self.case_data, spec.key, spec.default)
            w = self.field_widgets[spec.key]
            if isinstance(w, QCheckBox):
                w.setChecked(bool(val))
            elif isinstance(w, QLineEdit):
                w.setText("" if val is None else str(val))
            self.field_error_labels[spec.key].setText("")

        nz = int(float(_get_path(self.case_data, "preprocess.grid.nz", 9) or 9))
        source_levels = _read_vertical_levels_from_grid_cmn(self._vertical_source_grid_path())
        if source_levels:
            self.vertical_levels = [float(x) for x in source_levels[:nz]]
        else:
            existing_levels = _get_path(self.case_data, "preprocess.grid.vertical_levels_m", None)
            if isinstance(existing_levels, list) and existing_levels:
                self.vertical_levels = [float(x) for x in existing_levels[:nz]]
            else:
                self.vertical_levels = [float(20 * (i + 1)) for i in range(max(1, min(9, nz)))]
        self._ensure_vertical_levels_length(nz)

        points = _get_path(self.case_data, "puff.point_sources", [])
        src = points[0] if isinstance(points, list) and points and isinstance(points[0], dict) else DEFAULT_POINT_SOURCE
        lon = float(_get_path(self.case_data, "preprocess.stack.longitude",
                              _get_path(self.case_data, "preprocess.grid.center.longitude", 117.0)))
        lat = float(_get_path(self.case_data, "preprocess.stack.latitude",
                              _get_path(self.case_data, "preprocess.grid.center.latitude", 32.0)))
        self.point_widgets["lon"].setText(str(lon))
        self.point_widgets["lat"].setText(str(lat))
        self.point_widgets["stack_height_m"].setText(str(src.get("stack_height_m", 70.0)))
        self.point_widgets["base_elev_m"].setText(str(src.get("base_elev_m", 0.0)))
        self.point_widgets["stack_diameter_m"].setText(str(src.get("stack_diameter_m", 2.0)))
        self.point_widgets["exit_velocity_mps"].setText(str(src.get("exit_velocity_mps", 11.11)))
        self.point_widgets["exit_temp_k"].setText(str(src.get("exit_temp_k", 293.0)))
        em = src.get("emissions", [222222.0, 0.0])
        em0 = em[0] if isinstance(em, list) and em else 222222.0
        self.point_widgets["emission_bq_s"].setText(str(em0))

    def _collect_form_data(self) -> dict[str, Any]:
        data = json.loads(json.dumps(self.case_data)) if self.case_data else {}
        for spec in FIELDS:
            w = self.field_widgets[spec.key]
            if isinstance(w, QCheckBox):
                val: Any = w.isChecked()
            else:
                txt = w.text().strip() if isinstance(w, QLineEdit) else ""
                if spec.widget == "float":
                    val = float(txt)
                elif spec.widget == "int":
                    val = int(float(txt))
                else:
                    val = txt
            _set_path(data, spec.key, val)

        nz = int(float(_get_path(data, "preprocess.grid.nz", 9) or 9))
        self._ensure_vertical_levels_length(nz)

        lon = float(self.point_widgets["lon"].text().strip())
        lat = float(self.point_widgets["lat"].text().strip())
        # Use the EDITED case centre's zone, not the previous saved
        # grid.cmn (which may belong to a different region/UTM zone).
        _set_path(data, "preprocess.stack.longitude", lon)
        _set_path(data, "preprocess.stack.latitude", lat)
        x_km, y_km = projected_stack_utm_km(data)
        emission = float(self.point_widgets["emission_bq_s"].text().strip())
        source = {
            "name": "P1",
            "x_km": round(x_km, 3),
            "y_km": round(y_km, 3),
            "stack_height_m": float(self.point_widgets["stack_height_m"].text().strip()),
            "base_elev_m": float(self.point_widgets["base_elev_m"].text().strip()),
            "stack_diameter_m": float(self.point_widgets["stack_diameter_m"].text().strip()),
            "exit_velocity_mps": float(self.point_widgets["exit_velocity_mps"].text().strip()),
            "exit_temp_k": float(self.point_widgets["exit_temp_k"].text().strip()),
            "building_downwash_flag": 0.0,
            "zpltfm_m": 0.0,
            "fmfac": 1.0,
            "emissions": [emission, 0.0],
        }
        _set_path(data, "puff.point_sources", [source])
        _set_path(data, "puff.options.source_mode", "case_yaml")
        _set_path(data, "puff.options.nspec", 2)
        _set_path(data, "puff.options.nse", 1)

        # Do not remove station-selection/source-coverage configuration from
        # the new GUI: P4/P5 must re-evaluate year by year using these controls.
        _set_path(data, "preprocess.grid.vertical_levels_m", list(self.vertical_levels))
        return data

    def _ensure_vertical_levels_length(self, nz: int) -> None:
        if nz <= 0:
            nz = 1
        if len(self.vertical_levels) < nz:
            start = len(self.vertical_levels)
            for i in range(start, nz):
                self.vertical_levels.append(None)
        if len(self.vertical_levels) > nz:
            self.vertical_levels = self.vertical_levels[:nz]

    def open_vertical_levels_dialog(self) -> None:
        try:
            nz_widget = self.field_widgets.get("preprocess.grid.nz")
            nz = int(float(nz_widget.text().strip())) if isinstance(nz_widget, QLineEdit) else 9
        except Exception:
            QMessageBox.warning(self, "提示", "请先填写有效垂直层数")
            return
        source_levels = _read_vertical_levels_from_grid_cmn(self._vertical_source_grid_path())
        if source_levels:
            self.vertical_levels = [float(x) for x in source_levels[:nz]]
        self._ensure_vertical_levels_length(nz)

        dialog = QDialog(self)
        dialog.resize(420, min(560, 140 + nz * 28))
        dialog.setWindowTitle("垂直层数设置")
        dlay = QVBoxLayout(dialog)

        table = QTableWidget(nz, 2, dialog)
        table.setHorizontalHeaderLabels(["层号", "高度(m)"])
        table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        for i in range(nz):
            idx_item = QTableWidgetItem(str(i + 1))
            idx_item.setFlags(idx_item.flags() & ~Qt.ItemIsEditable)
            table.setItem(i, 0, idx_item)
            v = self.vertical_levels[i]
            table.setItem(i, 1, QTableWidgetItem("" if v is None else str(v)))
        dlay.addWidget(table)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        dlay.addWidget(btns)

        def accept_edit() -> None:
            new_levels: list[float] = []
            for i in range(nz):
                item = table.item(i, 1)
                txt = item.text().strip() if item else ""
                if not txt:
                    raise ValueError(f"第{i + 1}层高度不能为空")
                val = float(txt)
                if val <= 0:
                    raise ValueError(f"第{i + 1}层高度必须为正数")
                new_levels.append(val)
            self.vertical_levels = [float(x) for x in new_levels]
            _write_vertical_levels_to_grid_cmn(self._vertical_source_grid_path(), nz, new_levels)
            dialog.accept()

        def on_accept() -> None:
            try:
                accept_edit()
            except Exception as exc:
                QMessageBox.critical(dialog, "设置失败", str(exc))

        btns.accepted.connect(on_accept)
        btns.rejected.connect(dialog.reject)
        dialog.exec()

    def save_case_yaml(self) -> None:
        if not self.current_case:
            QMessageBox.warning(self, "提示", "请先选择案例")
            return
        try:
            errors, warnings = self.validate_config_only(show_messages=False)
            if errors:
                QMessageBox.critical(self, "保存失败", "存在配置错误，请先修复。")
                self.validate_config_and_show()
                return
            data = self._collect_form_data()
            validate_case(data)
            write_case_grid(case_dir(self.current_case), data)
            path = case_yaml_path(self.current_case)
            text = yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
            text = _format_emissions_inline(text)
            path.write_text(text, encoding="utf-8")
            self.case_data = data
            self._refresh_top_info()
            self._refresh_runtime_views()
            self._set_status(f"已保存 {path}")
            if warnings:
                QMessageBox.information(self, "保存成功（有警告）", "\n".join(warnings))
        except Exception as exc:
            self._set_status_error(str(exc))
            QMessageBox.critical(self, "保存失败", str(exc))

    def validate_config_and_show(self) -> None:
        errors, warnings = self.validate_config_only(show_messages=True)
        if errors:
            self._set_status_error(f"配置检查失败: {len(errors)}个错误")
        else:
            self._set_status(f"配置检查完成: {len(warnings)}个警告")

    def validate_config_only(self, show_messages: bool = False) -> tuple[list[str], list[str]]:
        for k, err in self.field_error_labels.items():
            err.setText("")
            w = self.field_widgets[k]
            w.setStyleSheet("")

        errors: list[str] = []
        warnings: list[str] = []
        self.issue_list.clear()
        self.issue_field_map.clear()

        data: dict[str, Any]
        try:
            data = self._collect_form_data()
        except Exception as exc:
            errors.append(f"字段格式错误: {exc}")
            if show_messages:
                QMessageBox.critical(self, "配置检查失败", str(exc))
            item = QListWidgetItem(f"ERROR: {exc}")
            self.issue_list.addItem(item)
            return errors, warnings

        def add_issue(kind: str, msg: str, field: str | None = None) -> None:
            if kind == "ERROR":
                errors.append(msg)
            else:
                warnings.append(msg)
            row = self.issue_list.count()
            item = QListWidgetItem(f"{kind}: {msg}")
            self.issue_list.addItem(item)
            if field:
                self.issue_field_map[row] = field
                lbl = self.field_error_labels.get(field)
                if lbl is not None and kind == "ERROR":
                    lbl.setText(msg)
                w = self.field_widgets.get(field)
                if w is not None and kind == "ERROR":
                    w.setStyleSheet("border:1px solid #be123c;")

        for spec in FIELDS:
            v = _get_path(data, spec.key)
            if spec.required and (v is None or (isinstance(v, str) and not v.strip())):
                add_issue("ERROR", f"{spec.label} 为必填项", spec.key)

        begin = str(_get_path(data, "preprocess.research_time.begin", "") or "")
        end = str(_get_path(data, "preprocess.research_time.end", "") or "")
        begin_dt = None
        end_dt = None
        try:
            begin_dt = datetime.strptime(begin, DATE_FMT)
        except Exception:
            add_issue("ERROR", "开始时间格式错误，应为 YYYYMMDD-HHMMSS", "preprocess.research_time.begin")
        try:
            end_dt = datetime.strptime(end, DATE_FMT)
        except Exception:
            add_issue("ERROR", "结束时间格式错误，应为 YYYYMMDD-HHMMSS", "preprocess.research_time.end")
        if begin_dt and end_dt and begin_dt >= end_dt:
            add_issue("ERROR", "开始时间必须早于结束时间", "preprocess.research_time.begin")

        lon = float(_get_path(data, "preprocess.grid.center.longitude", 0.0) or 0.0)
        lat = float(_get_path(data, "preprocess.grid.center.latitude", 0.0) or 0.0)
        if lon < -180 or lon > 180:
            add_issue("ERROR", "经度必须在[-180,180]", "preprocess.grid.center.longitude")
        if lat < -90 or lat > 90:
            add_issue("ERROR", "纬度必须在[-90,90]", "preprocess.grid.center.latitude")

        positive_fields = [
            "preprocess.grid.domain.length_km",
            "preprocess.grid.domain.width_km",
            "preprocess.grid.resolution_km",
            "preprocess.grid.nz",
            "preprocess.upperair.pstop_hpa",
        ]
        for f in positive_fields:
            try:
                num = float(_get_path(data, f, 0) or 0)
                if num <= 0:
                    add_issue("ERROR", f"{f} 必须为正数", f)
            except Exception:
                add_issue("ERROR", f"{f} 数值格式非法", f)

        try:
            plon = float(self.point_widgets["lon"].text().strip())
            plat = float(self.point_widgets["lat"].text().strip())
            if plon < -180 or plon > 180:
                add_issue("ERROR", "点源经度必须在[-180,180]", None)
            if plat < -90 or plat > 90:
                add_issue("ERROR", "点源纬度必须在[-90,90]", None)
            convert_lon_lat(plon, plat)
        except Exception as exc:
            add_issue("ERROR", f"点源经纬度非法: {exc}", None)

        for key, label in [
            ("stack_height_m", "烟囱高度"),
            ("stack_diameter_m", "烟囱直径"),
            ("exit_velocity_mps", "出口流速"),
            ("exit_temp_k", "出口温度"),
            ("emission_bq_s", "排放率"),
        ]:
            try:
                val = float(self.point_widgets[key].text().strip())
                if val <= 0:
                    add_issue("ERROR", f"{label}必须为正数", None)
            except Exception:
                add_issue("ERROR", f"{label}格式非法", None)
        try:
            base_elev = float(self.point_widgets["base_elev_m"].text().strip())
            if base_elev < 0:
                add_issue("ERROR", "烟囱基底海拔不能为负数", None)
        except Exception:
            add_issue("ERROR", "烟囱基底海拔格式非法", None)

        if self.current_case:
            cc = current_case_name()
            if cc != self.current_case:
                add_issue("ERROR", "当前GUI案例与project/current不一致，禁止运行", None)

        croot = case_dir(self.current_case) if self.current_case else None
        if croot and not self._stage_complete(croot, "met"):
            add_issue("WARN", "当前尚未检测到诊断风场产物，直接运行烟团模型会失败", None)

        if not errors and not warnings:
            ok_item = QListWidgetItem("配置检查通过")
            ok_item.setFlags(Qt.NoItemFlags)
            desc_item = QListWidgetItem("当前没有错误或警告")
            desc_item.setFlags(Qt.NoItemFlags)
            self.issue_list.addItem(ok_item)
            self.issue_list.addItem(desc_item)

        if show_messages and not errors:
            msg = "配置检查通过"
            if warnings:
                msg += "\n\n警告:\n" + "\n".join(warnings)
            QMessageBox.information(self, "检查结果", msg)
        return errors, warnings

    def on_issue_clicked(self, item: QListWidgetItem) -> None:
        row = self.issue_list.row(item)
        field = self.issue_field_map.get(row)
        if not field:
            return
        self.nav.setCurrentRow(1)
        w = self.field_widgets.get(field)
        if w is not None:
            w.setFocus()

    def _refresh_top_info(self) -> None:
        case_name = self.current_case or "-"
        yaml_path = case_yaml_path(self.current_case) if self.current_case else Path("-")
        cur_name = current_case_name()
        match = bool(self.current_case and self.current_case == cur_name)
        match_text = "一致" if match else "不一致"

        self.info_case.setText(f"当前案例：{case_name}")
        self.info_yaml.setText(f"配置文档：{yaml_path}")
        self.info_current.setText(f"current：{cur_name or '-'}")
        self.info_match.setText(f"current：{match_text}")
        self.info_match.setProperty("kind", "badge_ok" if match else "badge_bad")
        self.style().unpolish(self.info_match)
        self.style().polish(self.info_match)
        self.sync_btn.setEnabled(not match and bool(self.current_case))

        self.ov_current_case.setText(case_name)
        self.ov_case_yaml.setText(str(yaml_path))
        self.ov_current_consistency.setText(match_text)

        task_state = "idle" if self.current_task is None else str(self.current_task.get("status", "running"))
        self.info_task.setText(f"任务状态：{_status_zh(task_state)}")
        self.info_task.setProperty("kind", "badge_info")
        self.style().unpolish(self.info_task)
        self.style().polish(self.info_task)

    def _set_status(self, text: str) -> None:
        self.sb_operation.setText(f"操作: {text}")
        self.sb_error.setText("最近错误: -")

    def _set_status_error(self, text: str) -> None:
        self.sb_error.setText(f"最近错误: {text}")

    def _refresh_runtime_views(self) -> None:
        self._refresh_top_info()
        self.refresh_artifact_table()
        self.refresh_logs_table()
        self._refresh_overview_runs()
        self._refresh_task_runtime()

    def _refresh_overview_runs(self) -> None:
        runs = self._collect_runs(self.current_case if self.current_case else None)
        self.ov_runs_count.setText(str(len(runs)))
        if runs:
            top = runs[0]
            top_stage = STAGE_DISPLAY.get(str(top.get("stage", "")), str(top.get("stage", "-")))
            self.ov_last_run.setText(f"{top.get('start_time','-')} {top_stage} {_status_zh(str(top.get('status','-')))}")
        else:
            self.ov_last_run.setText("-")
        preprocess_err = "-"
        for r in runs:
            if r.get("stage") == "preprocess" and str(r.get("status", "")).startswith("failed"):
                preprocess_err = str(r.get("error_summary", "-"))
                break
        self.ov_preprocess_error.setText(preprocess_err)

    def _stage_complete(self, croot: Path, stage: str) -> bool:
        if stage == "surface":
            return (croot / "met" / "surface" / "final" / "surf.dat").exists()
        if stage == "upperair":
            final_dir = croot / "met" / "upperair" / "final"
            return any(final_dir.glob("up_*.dat"))
        if stage == "preprocess":
            geo_ok = (croot / "geo" / "makegeo" / "geo.dat").exists()
            return bool(geo_ok)
        if stage == "met":
            return (croot / "run" / "met" / MET_DAT).exists() and (croot / "run" / "met" / MET_LST).exists()
        if stage == "puff":
            lst_ok = (croot / "run" / "puff" / PUFF_LST).exists() or (croot / "run" / "puff" / PUFF_LST.upper()).exists()
            con_ok = (croot / "run" / "puff" / PUFF_CON).exists() or (croot / "run" / "puff" / PUFF_CON.upper()).exists()
            return bool(lst_ok and con_ok)
        return False

    def _stage_missing_outputs(self, croot: Path, stage: str) -> list[str]:
        missing: list[str] = []
        if stage == "surface":
            p = croot / "met" / "surface" / "final" / "surf.dat"
            if not p.exists():
                missing.append("met/surface/final/surf.dat")
        elif stage == "upperair":
            final_dir = croot / "met" / "upperair" / "final"
            if not any(final_dir.glob("up_*.dat")):
                missing.append("met/upperair/final/up_*.dat")
        elif stage == "preprocess":
            if not (croot / "geo" / "makegeo" / "geo.dat").exists():
                missing.append("geo/makegeo/geo.dat")
        elif stage == "met":
            if not (croot / "run" / "met" / MET_DAT).exists():
                missing.append(f"run/met/{MET_DAT}")
            if not (croot / "run" / "met" / MET_LST).exists():
                missing.append(f"run/met/{MET_LST}")
        elif stage == "puff":
            if not ((croot / "run" / "puff" / PUFF_CON).exists() or (croot / "run" / "puff" / PUFF_CON.upper()).exists()):
                missing.append(f"run/puff/{PUFF_CON}")
            if not ((croot / "run" / "puff" / PUFF_LST).exists() or (croot / "run" / "puff" / PUFF_LST.upper()).exists()):
                missing.append(f"run/puff/{PUFF_LST}")
        return missing

    def _latest_run_by_stage(self, stage: str) -> dict[str, Any] | None:
        runs = self._collect_runs(self.current_case)
        for r in runs:
            if r.get("stage") == stage:
                return r
        return None

    def _stage_status(self, spec: StageSpec) -> tuple[str, str]:
        if not self.current_case:
            return "未配置", "未选择案例"

        croot = case_dir(self.current_case)
        if self.current_task and self.current_task.get("status") == "running" and self.current_task.get("stage") == spec.stage:
            return "运行中", "任务执行中"

        if self._stage_complete(croot, spec.stage):
            return "已完成", "产物已就绪"

        dep_failed = []
        for dep in spec.deps:
            if not self._stage_complete(croot, dep):
                dep_failed.append(dep)
        if dep_failed:
            return "缺少输入", f"依赖未完成: {', '.join(dep_failed)}"

        if spec.stage in {"surface", "upperair"}:
            begin = str(_get_path(self.case_data, "preprocess.research_time.begin", ""))
            end = str(_get_path(self.case_data, "preprocess.research_time.end", ""))
            if not begin or not end:
                return "未配置", "时间范围未配置"

        if spec.stage == "preprocess":
            if not _get_path(self.case_data, "preprocess.grid", None):
                return "未配置", "网格参数缺失"

        last = self._latest_run_by_stage(spec.stage)
        if last and str(last.get("status", "")).lower().startswith("failed"):
            return "失败", str(last.get("error_summary", "上次运行失败"))

        return "可运行", "输入条件满足"

    def refresh_stage_cards(self) -> None:
        for spec in STAGES:
            card = self.stage_cards.get(spec.stage)
            if card is None:
                continue
            card.dep_label.setText("、".join(spec.deps) if spec.deps else "无")
            card.in_label.setText("\n".join(spec.inputs))
            card.out_label.setText("\n".join(spec.outputs))

            if self.current_case:
                croot = case_dir(self.current_case)
                missing = self._stage_missing_outputs(croot, spec.stage)
                card.missing_label.setText("\n".join(missing) if missing else "无")
                latest = self._latest_run_by_stage(spec.stage)
                if latest:
                    card.last_label.setText(str(latest.get("start_time", "-")))
                    card.result_label.setText(str(latest.get("status", "-")))
                else:
                    card.last_label.setText("-")
                    card.result_label.setText("-")
            else:
                card.missing_label.setText("-")
                card.last_label.setText("-")
                card.result_label.setText("-")

            state, detail = self._stage_status(spec)
            colors = {
                "未配置": "#6b7280",
                "缺少输入": "#b45309",
                "可运行": "#0f766e",
                "运行中": "#1d4ed8",
                "已完成": "#166534",
                "失败": "#b91c1c",
            }
            card.state_label.setText(f"状态: {state}")
            card.state_label.setStyleSheet(f"font-weight:700; color:{colors.get(state, '#1d2b3a')};")
            card.desc_label.setText(f"{spec.desc} 说明: {detail}")

            can_run = state in {"可运行", "失败", "已完成", "缺少输入", "未配置"}
            card.run_btn.setEnabled(can_run)
            card.resume_btn.setEnabled(can_run)

    def refresh_artifact_table(self) -> None:
        self.artifact_table.setRowCount(0)
        if not self.current_case:
            return
        croot = case_dir(self.current_case)
        for spec in STAGES:
            row = self.artifact_table.rowCount()
            self.artifact_table.insertRow(row)
            state, detail = self._stage_status(spec)
            missing = self._stage_missing_outputs(croot, spec.stage)

            auto_note = "可自动判断"

            self.artifact_table.setItem(row, 0, QTableWidgetItem(STAGE_DISPLAY.get(spec.stage, spec.stage)))
            self.artifact_table.setItem(row, 1, QTableWidgetItem(state))
            self.artifact_table.setItem(row, 2, QTableWidgetItem("; ".join(missing) if missing else "无"))
            self.artifact_table.setItem(row, 3, QTableWidgetItem(detail))
            self.artifact_table.setItem(row, 4, QTableWidgetItem(auto_note))

    def _collect_runs(self, case_filter: str | None) -> list[dict[str, Any]]:
        runs: list[dict[str, Any]] = []
        cases = [case_filter] if case_filter else _case_dirs()
        for case_name in cases:
            if not case_name:
                continue
            runs_dir = case_dir(case_name) / "runs"
            if not runs_dir.exists():
                continue
            for item in runs_dir.iterdir():
                if not item.is_dir():
                    continue
                meta = _read_json(item / "run_meta.json")
                if not meta:
                    continue
                meta["run_dir"] = str(item)
                meta["case"] = meta.get("case", case_name)
                runs.append(meta)

        def sort_key(x: dict[str, Any]) -> str:
            return str(x.get("start_time", ""))

        runs.sort(key=sort_key, reverse=True)
        return runs

    def refresh_logs_table(self) -> None:
        case_f = self.log_case_filter.currentText().strip() if self.log_case_filter.count() else "全部"
        stage_f = str(self.log_stage_filter.currentData()) if self.log_stage_filter.count() else "全部"
        status_f = self.log_status_filter.currentText().strip() if self.log_status_filter.count() else "全部"
        kw = self.log_keyword.text().strip().lower()

        runs = self._collect_runs(None)
        rows: list[dict[str, Any]] = []
        for r in runs:
            c = str(r.get("case", ""))
            s = str(r.get("stage", ""))
            st = str(r.get("status", ""))
            err = str(r.get("error_summary", ""))
            if case_f != "全部" and c != case_f:
                continue
            if stage_f != "全部" and s != stage_f:
                continue
            if status_f == "成功" and st not in {"success", "done"}:
                continue
            if status_f == "失败" and not st.startswith("failed"):
                continue
            if status_f == "取消" and st != "cancelled":
                continue
            if status_f == "运行中" and st != "running":
                continue
            if kw and kw not in (json.dumps(r, ensure_ascii=False).lower()):
                continue
            if kw:
                stdout_txt = (Path(str(r.get("run_dir"))) / "stdout.log").read_text(encoding="utf-8", errors="ignore") if (Path(str(r.get("run_dir"))) / "stdout.log").exists() else ""
                stderr_txt = (Path(str(r.get("run_dir"))) / "stderr.log").read_text(encoding="utf-8", errors="ignore") if (Path(str(r.get("run_dir"))) / "stderr.log").exists() else ""
                if kw not in stdout_txt.lower() and kw not in stderr_txt.lower() and kw not in err.lower():
                    continue
            rows.append(r)

        self.log_table.setRowCount(0)
        for r in rows:
            row = self.log_table.rowCount()
            self.log_table.insertRow(row)
            self.log_table.setItem(row, 0, QTableWidgetItem(str(r.get("case", ""))))
            stage_code = str(r.get("stage", ""))
            self.log_table.setItem(row, 1, QTableWidgetItem(STAGE_DISPLAY.get(stage_code, stage_code)))
            self.log_table.setItem(row, 2, QTableWidgetItem(str(r.get("start_time", ""))))
            self.log_table.setItem(row, 3, QTableWidgetItem(_status_zh(str(r.get("status", "")))))
            self.log_table.setItem(row, 4, QTableWidgetItem(str(r.get("return_code", ""))))
            self.log_table.setItem(row, 5, QTableWidgetItem(str(r.get("error_summary", ""))))
            full_dir = str(r.get("run_dir", ""))
            dir_item = QTableWidgetItem(_short_run_dir(full_dir))
            dir_item.setToolTip(full_dir)
            dir_item.setData(Qt.UserRole, full_dir)
            self.log_table.setItem(row, 6, dir_item)

    def on_log_row_selected(self) -> None:
        row = self.log_table.currentRow()
        if row < 0:
            return
        run_dir_item = self.log_table.item(row, 6)
        if run_dir_item is None:
            return
        full_dir = str(run_dir_item.data(Qt.UserRole) or run_dir_item.text())
        rdir = Path(full_dir)
        out = rdir / "stdout.log"
        err = rdir / "stderr.log"
        self.stdout_view.setPlainText(out.read_text(encoding="utf-8", errors="ignore") if out.exists() else "")
        self.stderr_view.setPlainText(err.read_text(encoding="utf-8", errors="ignore") if err.exists() else "")

    def open_selected_log_dir(self) -> None:
        row = self.log_table.currentRow()
        if row < 0:
            return
        run_dir_item = self.log_table.item(row, 6)
        if run_dir_item is None:
            return
        full_dir = str(run_dir_item.data(Qt.UserRole) or run_dir_item.text())
        QDesktopServices.openUrl(QUrl.fromLocalFile(full_dir))

    def copy_selected_error(self) -> None:
        row = self.log_table.currentRow()
        if row < 0:
            return
        err_item = self.log_table.item(row, 5)
        if err_item is None:
            return
        QApplication.clipboard().setText(err_item.text())
        self._set_status("已复制错误摘要")

    def postprocess_output_dir(self) -> Path:
        return case_dir(self.current_case) / "run" / "puff" / "postprocessing"

    def postprocess_output_path(self, name: str) -> Path:
        text = name.strip()
        if not text:
            raise ValueError("输出文件名不能为空")
        path = Path(text)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("输出文件必须是当前后处理目录内的相对路径")
        return self.postprocess_output_dir() / path

    def postprocess_case_inputs(self) -> tuple[Path, Path, Path | None]:
        croot = case_dir(self.current_case)
        conc_file = croot / "run" / "puff" / PUFF_CON
        calmet_inp = croot / "run" / "met" / MET_INP
        terrain_candidates = [
            croot / "run" / "puff" / "qaterr.grd",
            croot / "geo" / "makegeo" / "qaterr.grd",
        ]
        terrain_file = next((p for p in terrain_candidates if p.exists()), None)
        return conc_file, calmet_inp, terrain_file

    def _load_calpuff_times(self) -> list[str]:
        """从当前 case 的 puff.con 读取所有时刻，返回格式化字符串列表。"""
        try:
            ok, msg = self._require_conc_inputs()
            if not ok:
                return []
            conc_file, calmet_inp, _ = self.postprocess_case_inputs()
            grid = parse_calmet_grid(calmet_inp)
            records = index_time_records(conc_file, grid.nx, grid.ny)
            return [r.start.strftime("%Y-%m-%d %H:%M") for r in records]
        except Exception:
            return []

    def _refresh_post_time_dropdowns(self) -> None:
        times = self._load_calpuff_times()
        if times:
            self._set_status(f"已加载 {len(times)} 个时刻")
        else:
            self._set_status_error("未能加载时刻，请确认案例已选择且 puff.con 存在")

    def _require_post_case(self) -> tuple[bool, str]:
        if not self.current_case:
            return False, "请先选择案例"
        return True, ""

    def _require_conc_inputs(self) -> tuple[bool, str]:
        ok, msg = self._require_post_case()
        if not ok:
            return ok, msg
        conc_file, calmet_inp, _terrain = self.postprocess_case_inputs()
        if not conc_file.exists():
            return False, f"缺少浓度文件: {conc_file}"
        if not calmet_inp.exists():
            return False, f"缺少 MET 输入文件: {calmet_inp}"
        return True, ""

    def _float_from_widget(self, widget: QLineEdit, label: str) -> float:
        try:
            return float(widget.text().strip())
        except ValueError as exc:
            raise ValueError(f"{label} 必须是数字") from exc

    def _int_from_widget(self, widget: QLineEdit, label: str, default: int | None = None) -> int | None:
        text = widget.text().strip()
        if not text and default is not None:
            return default
        if not text:
            return None
        try:
            return int(text)
        except ValueError as exc:
            raise ValueError(f"{label} 必须是整数") from exc

    def _validate_scale_values(self, scale: str, vmin: float, vmax: float) -> None:
        if vmin >= vmax:
            raise ValueError("vmin 必须小于 vmax")
        if scale == "log" and vmin <= 0:
            raise ValueError("log 色标要求 vmin > 0")

    def _set_post_buttons_enabled(self, enabled: bool) -> None:
        for btn in self.post_run_buttons:
            btn.setEnabled(enabled)

    def refresh_post_preview(self, output_key: str, path: Path | None = None) -> None:
        label = self.post_preview_labels.get(output_key)
        if label is None:
            return
        target = path or self.post_last_outputs.get(output_key)
        if target is None or not target.exists():
            label.setMovie(None)
            label.setPixmap(QPixmap())
            label.setText("运行后显示输出预览")
            return
        suffix = target.suffix.lower()
        if suffix in {".png", ".jpg", ".jpeg"}:
            pix = QPixmap(str(target))
            if not pix.isNull():
                label.setMovie(None)
                label.setText("")
                label.setPixmap(pix.scaled(label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
                return
        if suffix == ".gif":
            movie = QMovie(str(target))
            movie.setScaledSize(label.size())
            label.setPixmap(QPixmap())
            label.setMovie(movie)
            movie.start()
            return
        if suffix == ".mp4":
            label.setMovie(None)
            label.setPixmap(QPixmap())
            label.setText(f"视频已生成:\n{target.name}\n点击'打开结果文件'查看")
            return
        label.setMovie(None)
        label.setPixmap(QPixmap())
        label.setText(str(target))

    def _warn_missing_terrain(self, terrain_file: Path | None) -> None:
        if terrain_file is None:
            self._set_status("未找到地形底图，将不叠加地形")

    def _sync_post_conc_defaults(self) -> None:
        mode = self.post_conc_mode.currentData()
        self.post_conc_output.setText(
            {"snapshot": "conc_snapshot.png", "annual": "conc_annual.png", "seasonal": "conc_seasonal.png"}[mode]
        )

    def _sync_post_animation_defaults(self) -> None:
        self.post_anim_output.setText(f"conc_yearly.{self.post_anim_format.currentText()}")

    def reset_post_conc(self) -> None:
        self.post_conc_mode.setCurrentIndex(0)
        self.post_conc_time.clear()
        self.post_conc_scale.setCurrentText("linear")
        self.post_conc_vmin.setText("5e-4")
        self.post_conc_vmax.setText("5e-2")
        self.post_conc_threshold.setText("1.2e-3")
        self._on_conc_mode_changed()

    def reset_post_animation(self) -> None:
        self.post_anim_format.setCurrentText("mp4")
        self.post_anim_start.clear()
        self.post_anim_end.clear()
        self.post_anim_fps.clear()
        self.post_anim_stride.clear()
        self.post_anim_max_frames.clear()
        self._sync_post_animation_defaults()

    def _parse_optional_post_time(self, text: str, field_name: str) -> str:
        value = text.strip()
        if not value:
            return ""
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M").strftime("%Y-%m-%d %H:%M")
        except ValueError as exc:
            raise ValueError(f"{field_name}格式应为 YYYY-MM-DD HH:MM") from exc

    def _find_time_record_index(self, records: list[Any], time_text: str, field_name: str) -> int:
        for i, record in enumerate(records):
            if record.start.strftime("%Y-%m-%d %H:%M") == time_text:
                return i
        raise ValueError(f"{field_name}不在当前结果时刻列表中: {time_text}")

    def reset_post_point(self) -> None:
        self.post_point_lon.setText(str(DEFAULT_POINT_SOURCE.get("lon", "118.0")))
        self.post_point_lat.setText(str(DEFAULT_POINT_SOURCE.get("lat", "32.0")))
        self.post_point_output.setText("point_timeseries.csv")
        self.post_point_daily_output.setText("daily_concentration.png")

    def reset_post_windrose(self) -> None:
        self.post_wind_csv.setText(str(self.default_windrose_csv()))
        self.post_wind_output.setText("windrose.png")

    def browse_post_wind_csv(self) -> None:
        base_dir = current_project_path("met", "surface", "isd2smerge_ready")
        path, _ = QFileDialog.getOpenFileName(self, "选择风玫瑰 CSV", str(base_dir), "CSV Files (*.csv);;All Files (*)")
        if path:
            self.post_wind_csv.setText(path)

    def default_windrose_csv(self) -> Path:
        base_dir = current_project_path("met", "surface", "isd2smerge_ready")
        files = sorted(base_dir.glob("*.csv"))
        return files[0] if files else base_dir / "*.csv"

    def run_postprocess_job(self, spec: PostprocessSpec, cmd: list[str], output_path: Path) -> None:
        ok, msg = self._require_post_case()
        if not ok:
            QMessageBox.warning(self, "无法运行", msg)
            return
        if self.current_task and self.current_task.get("status") == "running":
            QMessageBox.warning(self, "任务冲突", "当前已有任务运行中，暂不支持并发任务")
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = case_dir(self.current_case) / "runs" / f"{ts}_post_{spec.job}"
        run_dir.mkdir(parents=True, exist_ok=True)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        (run_dir / "command.txt").write_text(" ".join(cmd) + "\n", encoding="utf-8")
        start_time = datetime.now().isoformat(timespec="seconds")
        meta = {
            "case": self.current_case,
            "stage": spec.stage,
            "resume": False,
            "command": cmd,
            "start_time": start_time,
            "end_time": None,
            "status": "running",
            "return_code": None,
            "error_summary": "",
            "output_path": str(output_path),
        }
        (run_dir / "run_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        self.run_stdout_fp = (run_dir / "stdout.log").open("w", encoding="utf-8")
        self.run_stderr_fp = (run_dir / "stderr.log").open("w", encoding="utf-8")

        proc = QProcess(self)
        proc.setProgram(cmd[0])
        proc.setArguments(cmd[1:])
        proc.setWorkingDirectory(str(TUTORIAL_ROOT))
        env = proc.processEnvironment()
        env.insert("PYTHONUNBUFFERED", "1")
        proc.setProcessEnvironment(env)
        proc.readyReadStandardOutput.connect(self._on_proc_stdout)
        proc.readyReadStandardError.connect(self._on_proc_stderr)
        proc.finished.connect(self._on_proc_finished)

        self.cancel_requested = False
        self.run_process = proc
        self.current_task = {
            "case": self.current_case,
            "stage": spec.stage,
            "resume": False,
            "run_dir": str(run_dir),
            "status": "running",
            "start_dt": datetime.now(),
            "start_time": start_time,
            "pid": None,
            "command": cmd,
            "buffer": [],
            "log_cutoff": False,
            "output_dir": str(output_path.parent),
            "output_path": str(output_path),
            "post_job": spec.job,
        }
        self.post_last_outputs[spec.job] = output_path
        self._set_post_buttons_enabled(False)

        self.task_log.clear()
        self.task_state.setText("状态: 运行中")
        self.task_case.setText(f"案例: {self.current_case}")
        self.task_stage.setText(f"阶段: {spec.label}")
        self.task_start.setText(f"开始时间: {start_time}")
        self.task_pid.setText("PID: -")
        self.info_task.setText(f"任务状态：运行中")
        self.sb_stage.setText(f"阶段: {spec.label}")
        self.sb_progress_text.setText("进度: 运行中")
        self.sb_progress.setRange(0, 0)
        self._set_status(f"开始执行: {spec.label}")

        proc.start()
        if not proc.waitForStarted(5000):
            self._set_status_error("任务启动失败")
            QMessageBox.critical(self, "任务失败", "启动子进程失败")
            self._close_run_files()
            self.current_task = None
            self.run_process = None
            self._set_post_buttons_enabled(True)
            return
        pid = int(proc.processId())
        if self.current_task is not None:
            self.current_task["pid"] = pid
        self.task_pid.setText(f"PID: {pid}")

    def run_post_conc_plot(self) -> None:
        try:
            ok, msg = self._require_conc_inputs()
            if not ok:
                raise ValueError(msg)
            conc_file, calmet_inp, terrain_file = self.postprocess_case_inputs()
            scale = self.post_conc_scale.currentText()
            vmin = self._float_from_widget(self.post_conc_vmin, "最小值")
            vmax = self._float_from_widget(self.post_conc_vmax, "最大值")
            self._validate_scale_values(scale, vmin, vmax)
            output_path = self.postprocess_output_path(self.post_conc_output.text())
            cmd = [
                sys.executable, "-u", "-m", "engine.postprocessing.plot_puff_snapshot",
                "--mode", self.post_conc_mode.currentData(),
                "--conc-file", str(conc_file),
                "--met-inp", str(calmet_inp),
                "--out", str(output_path),
                "--scale", scale,
                "--vmin", str(vmin),
                "--vmax", str(vmax),
                "--threshold", self.post_conc_threshold.text().strip() or "0",
            ]
            if terrain_file is not None:
                cmd.extend(["--terrain-file", str(terrain_file)])
            self._warn_missing_terrain(terrain_file)
            time_val = self._parse_optional_post_time(self.post_conc_time.text(), "时刻")
            if time_val:
                grid = parse_calmet_grid(calmet_inp)
                records = index_time_records(conc_file, grid.nx, grid.ny)
                self._find_time_record_index(records, time_val, "时刻")
                cmd.extend(["--time", time_val])
            self.run_postprocess_job(POSTPROCESS_SPECS["conc_plot"], cmd, output_path)
        except ValueError as exc:
            self._set_status_error(str(exc))
            QMessageBox.warning(self, "无法运行", str(exc))

    def run_post_animation(self) -> None:
        try:
            ok, msg = self._require_conc_inputs()
            if not ok:
                raise ValueError(msg)
            conc_file, calmet_inp, terrain_file = self.postprocess_case_inputs()
            scale = self.post_conc_scale.currentText()
            vmin = self._float_from_widget(self.post_conc_vmin, "最小值")
            vmax = self._float_from_widget(self.post_conc_vmax, "最大值")
            threshold = self.post_conc_threshold.text().strip() or "0"
            self._validate_scale_values(scale, vmin, vmax)
            output_path = self.postprocess_output_path(self.post_anim_output.text())
            cmd = [
                sys.executable, "-u", "-m", "engine.postprocessing.plot_puff_animation",
                "--conc-file", str(conc_file),
                "--met-inp", str(calmet_inp),
                "--out", str(output_path),
                "--fps", self.post_anim_fps.text().strip() or "10",
                "--stride", self.post_anim_stride.text().strip() or "1",
                "--scale", scale,
                "--vmin", str(vmin),
                "--vmax", str(vmax),
                "--threshold", threshold,
            ]
            max_frames = self.post_anim_max_frames.text().strip()
            if max_frames:
                cmd.extend(["--max-frames", max_frames])
            if terrain_file is not None:
                cmd.extend(["--terrain-file", str(terrain_file)])
            self._warn_missing_terrain(terrain_file)
            # Start/end time: look up step index from time records
            start_val = self._parse_optional_post_time(self.post_anim_start.text(), "开始时刻")
            end_val = self._parse_optional_post_time(self.post_anim_end.text(), "结束时刻")
            if start_val or end_val:
                grid = parse_calmet_grid(calmet_inp)
                records = index_time_records(conc_file, grid.nx, grid.ny)
                if start_val:
                    start_idx = self._find_time_record_index(records, start_val, "开始时刻")
                    cmd.extend(["--start-step", str(start_idx)])
                if end_val:
                    end_idx = self._find_time_record_index(records, end_val, "结束时刻")
                    cmd.extend(["--end-step", str(end_idx + 1)])
            self.run_postprocess_job(POSTPROCESS_SPECS["animation"], cmd, output_path)
        except ValueError as exc:
            self._set_status_error(str(exc))
            QMessageBox.warning(self, "无法运行", str(exc))

    def run_post_point_extract(self) -> None:
        try:
            ok, msg = self._require_conc_inputs()
            if not ok:
                raise ValueError(msg)
            conc_file, calmet_inp, _terrain_file = self.postprocess_case_inputs()
            lon = float(self.post_point_lon.text().strip())
            lat = float(self.post_point_lat.text().strip())
            utm = convert_lon_lat(lon, lat)
            csv_path = self.postprocess_output_path(self.post_point_output.text())
            output_path = self.postprocess_output_path(self.post_point_daily_output.text())
            cmd = [
                sys.executable, "-u", "-m", "engine.postprocessing.plot_daily_from_puff",
                "--conc-file", str(conc_file),
                "--met-inp", str(calmet_inp),
                "--x", str(round(utm["x_km"], 3)),
                "--y", str(round(utm["y_km"], 3)),
                "--csv-output", str(csv_path),
                "--output", str(output_path),
            ]
            self.run_postprocess_job(POSTPROCESS_SPECS["point"], cmd, output_path)
        except ValueError as exc:
            self._set_status_error(str(exc))
            QMessageBox.warning(self, "无法运行", str(exc))

    def run_post_windrose(self) -> None:
        try:
            ok, msg = self._require_post_case()
            if not ok:
                raise ValueError(msg)
            output_path = self.postprocess_output_path(self.post_wind_output.text())
            cmd = [sys.executable, "-u", "-m", "engine.postprocessing.plot_windrose_style", "--output", str(output_path)]
            csv_text = self.post_wind_csv.text().strip()
            csv_path = Path(csv_text) if csv_text else self.default_windrose_csv()
            if not csv_path.exists():
                raise ValueError(f"CSV 不存在: {csv_path}")
            cmd.extend([
                "--csv", str(csv_path),
                "--month-column", "Month",
                "--direction-column", "deg",
                "--speed-column", "ms-1",
            ])
            self.run_postprocess_job(POSTPROCESS_SPECS["windrose"], cmd, output_path)
        except ValueError as exc:
            self._set_status_error(str(exc))
            QMessageBox.warning(self, "无法运行", str(exc))

    def open_postprocess_output_dir(self) -> None:
        if not self.current_case:
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.postprocess_output_dir())))

    def open_postprocess_output_file(self, output_key: str) -> None:
        path = self.post_last_outputs.get(output_key)
        if path is None:
            try:
                path = self.postprocess_output_dir() / POSTPROCESS_SPECS[output_key].default_output
            except Exception:
                path = None
        if path is None or not path.exists():
            QMessageBox.information(self, "提示", "尚未找到该结果文件")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _validate_ready_to_run(self, stage: str) -> tuple[bool, str]:
        if not self.current_case:
            return False, "请先选择案例"
        cur = current_case_name()
        if cur != self.current_case:
            return False, "当前GUI案例与project/current不一致，请先同步"

        errors, _ = self.validate_config_only(show_messages=False)
        if errors:
            return False, "配置检查未通过，请先修复错误"

        croot = case_dir(self.current_case)
        # G5 must never fall back to the legacy Fortran/Python orchestrator.
        # A stage is runnable only when the explicitly registered native path
        # is supported for this case and its dependencies are ready.
        return stage_readiness(stage, self.case_data, self.current_case, resume=False)

    def _make_run_dir(self, case_name: str, stage: str) -> Path:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = case_dir(case_name) / "runs" / f"{ts}_{stage}"
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    def run_stage(self, stage: str, resume: bool) -> None:
        ok, msg = self._validate_ready_to_run(stage)
        if not ok:
            self._set_status_error(msg)
            QMessageBox.warning(self, "无法运行", msg)
            return
        if self.current_task and self.current_task.get("status") == "running":
            QMessageBox.warning(self, "任务冲突", "当前已有任务运行中，暂不支持并发任务")
            return

        run_dir = self._make_run_dir(self.current_case, stage)
        cmd = [sys.executable, "-u", "-m", "engine.gui_g5.pipeline", "run", "--case", self.current_case, "--stage", stage]
        if resume:
            cmd.append("--resume")

        (run_dir / "command.txt").write_text(" ".join(cmd) + "\n", encoding="utf-8")
        start_time = datetime.now().isoformat(timespec="seconds")
        meta = {
            "case": self.current_case,
            "stage": stage,
            "resume": resume,
            "command": cmd,
            "start_time": start_time,
            "end_time": None,
            "status": "running",
            "return_code": None,
            "error_summary": "",
        }
        (run_dir / "run_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        self.run_stdout_fp = (run_dir / "stdout.log").open("w", encoding="utf-8")
        self.run_stderr_fp = (run_dir / "stderr.log").open("w", encoding="utf-8")

        proc = QProcess(self)
        proc.setProgram(cmd[0])
        proc.setArguments(cmd[1:])
        proc.setWorkingDirectory(str(TUTORIAL_ROOT))
        env = proc.processEnvironment()
        env.insert("PYTHONUNBUFFERED", "1")
        proc.setProcessEnvironment(env)
        proc.readyReadStandardOutput.connect(self._on_proc_stdout)
        proc.readyReadStandardError.connect(self._on_proc_stderr)
        proc.finished.connect(self._on_proc_finished)

        self.cancel_requested = False
        self.run_process = proc
        self.current_task = {
            "case": self.current_case,
            "stage": stage,
            "resume": resume,
            "run_dir": str(run_dir),
            "status": "running",
            "start_dt": datetime.now(),
            "start_time": start_time,
            "pid": None,
            "command": cmd,
            "buffer": [],
            "log_cutoff": False,
            "all_case_banner_seen": False,
            "all_grid_block_seen": False,
            "all_grid_block_skip": False,
            "all_preprocess_done_seen": False,
            "all_met_started": False,
            "all_met_done": False,
            "all_puff_started": False,
            "all_puff_done": False,
            "preprocess_done_pending": False,
        }

        self.task_log.clear()
        self.task_state.setText("状态: 运行中")
        self.task_case.setText(f"案例: {self.current_case}")
        self.task_stage.setText(f"阶段: {STAGE_DISPLAY.get(stage, stage)}")
        self.task_start.setText(f"开始时间: {start_time}")
        self.task_pid.setText("PID: -")
        self.sb_stage.setText(f"阶段: {STAGE_DISPLAY.get(stage, stage)}")
        self.sb_progress_text.setText("进度: 运行中")
        self.sb_progress.setRange(0, 0)
        self._set_status(f"开始执行: {' '.join(cmd)}")

        proc.start()
        if not proc.waitForStarted(5000):
            self._set_status_error("任务启动失败")
            QMessageBox.critical(self, "任务失败", "启动子进程失败")
            self._close_run_files()
            self.current_task = None
            self.run_process = None
            return

        pid = int(proc.processId())
        if self.current_task is not None:
            self.current_task["pid"] = pid
        self.task_pid.setText(f"PID: {pid}")

    def _append_live_log(self, text: str, is_err: bool) -> None:
        if self.current_task is None:
            return
        stage = str(self.current_task.get("stage", ""))
        lines = text.splitlines()
        append_lines: list[str] = []
        for ln in lines:
            if self.current_task.get("log_cutoff"):
                continue
            line = ln.rstrip("\n")
            if line.startswith("[RUN] "):
                continue
            if stage == "all":
                if line.startswith("将使用案例名称:"):
                    if self.current_task.get("all_case_banner_seen"):
                        continue
                    self.current_task["all_case_banner_seen"] = True
                if line.strip() == "=== [配置网格通用参数] 开始 ===":
                    if self.current_task.get("all_grid_block_seen"):
                        self.current_task["all_grid_block_skip"] = True
                        continue
                    self.current_task["all_grid_block_seen"] = True
                if self.current_task.get("all_grid_block_skip"):
                    if line.strip() == "=== [配置网格通用参数] 完成 ===":
                        self.current_task["all_grid_block_skip"] = False
                    continue
                if line.strip() == "地形处理工作完成!":
                    if self.current_task.get("all_preprocess_done_seen"):
                        continue
                    self.current_task["all_preprocess_done_seen"] = True
                if (not self.current_task.get("all_met_started")) and line.startswith("[INFO] 计算时间:"):
                    append_lines.append("=== [诊断风场计算] 开始 ===")
                    self.current_task["all_met_started"] = True
                if self.current_task.get("all_met_started") and (not self.current_task.get("all_met_done")) and line.startswith("[RESULT] 诊断风场计算完毕"):
                    append_lines.append(line)
                    append_lines.append("=== [诊断风场计算] 完成 ===")
                    self.current_task["all_met_done"] = True
                    continue
                if self.current_task.get("all_met_done") and (not self.current_task.get("all_puff_started")) and line.startswith("[INFO] 计算时间:"):
                    append_lines.append("=== [烟团模型计算] 开始 ===")
                    self.current_task["all_puff_started"] = True
                if self.current_task.get("all_puff_started") and (not self.current_task.get("all_puff_done")) and line.startswith("[RESULT] 烟团模型计算完毕"):
                    append_lines.append(line)
                    append_lines.append("=== [烟团模型计算] 完成 ===")
                    self.current_task["all_puff_done"] = True
                    continue
            if stage == "surface":
                append_lines.append(line)
                if "地面气象数据下载及处理完成, 数据保存路径:" in line:
                    self.current_task["log_cutoff"] = True
                continue
            if stage == "upperair":
                if "高空气象数据处理完毕!" in line:
                    upperair_final_dir = current_project_path("met", "upperair", "final")
                    line = f"高空气象数据下载及处理完成, 数据保存路径: {upperair_final_dir}/"
                    append_lines.append(line)
                    self.current_task["log_cutoff"] = True
                    continue
                append_lines.append(line)
                continue
            if stage == "preprocess":
                if line.strip() == "地形处理工作完成!":
                    self.current_task["preprocess_done_pending"] = True
                    continue
                if line.startswith("[OK] deliverables updated:"):
                    append_lines.append(line)
                    if self.current_task.get("preprocess_done_pending"):
                        append_lines.append("地形处理工作完成!")
                        self.current_task["preprocess_done_pending"] = False
                    continue
            append_lines.append(line)

        if not append_lines:
            return
        self.current_task["buffer"].extend(append_lines)
        if len(self.current_task["buffer"]) > 2000:
            self.current_task["buffer"] = self.current_task["buffer"][-2000:]
        self.task_log.setPlainText("\n".join(self.current_task["buffer"]))
        sb = self.task_log.verticalScrollBar()
        sb.setValue(sb.maximum())

        write_text = "\n".join(append_lines) + "\n"
        if is_err:
            self.run_stderr_fp.write(write_text)
            self.run_stderr_fp.flush()
        else:
            self.run_stdout_fp.write(write_text)
            self.run_stdout_fp.flush()

    def _on_proc_stdout(self) -> None:
        if not self.run_process:
            return
        raw = bytes(self.run_process.readAllStandardOutput()).decode("utf-8", errors="ignore")
        if raw:
            self._append_live_log(raw, is_err=False)

    def _on_proc_stderr(self) -> None:
        if not self.run_process:
            return
        raw = bytes(self.run_process.readAllStandardError()).decode("utf-8", errors="ignore")
        if raw:
            self._append_live_log(raw, is_err=True)

    def _extract_error_summary(self, text: str, rc: int, cancelled: bool) -> str:
        if cancelled:
            return "任务被用户取消"
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        for ln in reversed(lines):
            if "FileNotFoundError" in ln or "No such file or directory" in ln:
                return ln[:300]
        for ln in reversed(lines):
            if "[ERROR]" in ln or "[FAIL]" in ln:
                return ln[:300]
        if rc != 0 and lines:
            return lines[-1][:300]
        return ""

    def _on_proc_finished(self, exit_code: int, _exit_status: QProcess.ExitStatus) -> None:
        if self.current_task is None:
            self._close_run_files()
            return

        if self.current_task.get("stage") == "preprocess" and self.current_task.get("preprocess_done_pending"):
            self._append_live_log("地形处理工作完成!\n", is_err=False)
            self.current_task["preprocess_done_pending"] = False

        run_dir = Path(str(self.current_task["run_dir"]))
        stdout_text = (run_dir / "stdout.log").read_text(encoding="utf-8", errors="ignore") if (run_dir / "stdout.log").exists() else ""
        stderr_text = (run_dir / "stderr.log").read_text(encoding="utf-8", errors="ignore") if (run_dir / "stderr.log").exists() else ""

        cancelled = self.cancel_requested
        if cancelled:
            status = "cancelled"
        else:
            status = "success" if exit_code == 0 else f"failed({exit_code})"

        error_summary = self._extract_error_summary(stdout_text + "\n" + stderr_text, exit_code, cancelled)
        end_time = datetime.now().isoformat(timespec="seconds")
        meta = {
            "case": self.current_task["case"],
            "stage": self.current_task["stage"],
            "resume": self.current_task["resume"],
            "command": self.current_task["command"],
            "start_time": self.current_task["start_time"],
            "end_time": end_time,
            "status": status,
            "return_code": exit_code,
            "error_summary": error_summary,
        }
        if self.current_task.get("output_path"):
            meta["output_path"] = self.current_task["output_path"]
        if self.current_task.get("output_dir"):
            meta["output_dir"] = self.current_task["output_dir"]
        (run_dir / "run_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        self.last_task_by_stage[str(self.current_task["stage"])] = meta
        post_job = str(self.current_task.get("post_job", ""))
        output_path_text = str(self.current_task.get("output_path", ""))
        self.current_task["status"] = status
        self.task_state.setText(f"状态: {_status_zh(status)}")
        self.info_task.setText(f"任务状态：{_status_zh(status)}")
        self.sb_progress_text.setText(f"进度: {_status_zh(status)}")
        self.sb_progress.setRange(0, 1)
        self.sb_progress.setValue(1 if status == "success" else 0)

        if status == "success":
            self._set_status("任务完成")
        elif status == "cancelled":
            self._set_status_error("任务已取消")
        else:
            self._set_status_error(error_summary or status)

        self._close_run_files()
        self.run_process = None
        self.current_task = None
        self.cancel_requested = False
        self._set_post_buttons_enabled(True)
        if status == "success" and post_job and output_path_text:
            self.refresh_post_preview(post_job, Path(output_path_text))
        self._refresh_runtime_views()

    def _close_run_files(self) -> None:
        if self.run_stdout_fp is not None:
            self.run_stdout_fp.close()
            self.run_stdout_fp = None
        if self.run_stderr_fp is not None:
            self.run_stderr_fp.close()
            self.run_stderr_fp = None

    def cancel_task(self) -> None:
        if not self.run_process or self.current_task is None:
            QMessageBox.information(self, "提示", "当前没有运行中的任务")
            return
        self.cancel_requested = True
        self.run_process.kill()
        self._set_status("已发送取消信号")

    def retry_last_failed(self) -> None:
        runs = self._collect_runs(self.current_case)
        target: dict[str, Any] | None = None
        for r in runs:
            if str(r.get("status", "")).startswith("failed"):
                target = r
                break
        if not target:
            QMessageBox.information(self, "提示", "没有找到失败任务")
            return
        stage = str(target.get("stage", "all"))
        resume = bool(target.get("resume", True))
        self.run_stage(stage, resume)

    def open_current_task_log_dir(self) -> None:
        if self.current_task is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.current_task["run_dir"])))
            return
        runs = self._collect_runs(self.current_case)
        if runs:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(runs[0].get("run_dir"))))

    def open_current_task_output_dir(self) -> None:
        if not self.current_case:
            return
        stage = "all"
        if self.current_task is not None:
            if self.current_task.get("output_dir"):
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.current_task["output_dir"])))
                return
            stage = str(self.current_task.get("stage", "all"))
        rel = "run"
        for s in STAGES:
            if s.stage == stage:
                rel = s.output_dir_rel
                break
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(case_dir(self.current_case) / rel)))

    def view_latest_log_by_stage(self, stage: str) -> None:
        runs = self._collect_runs(self.current_case)
        target: dict[str, Any] | None = None
        for r in runs:
            if r.get("stage") == stage:
                target = r
                break
        if not target:
            QMessageBox.information(self, "提示", f"未找到 {stage} 历史日志")
            return
        self.nav.setCurrentRow(3)
        run_dir = str(target.get("run_dir", ""))
        for i in range(self.log_table.rowCount()):
            item = self.log_table.item(i, 6)
            if item and str(item.data(Qt.UserRole) or item.text()) == run_dir:
                self.log_table.selectRow(i)
                self.on_log_row_selected()
                break

    def open_stage_output_dir(self, spec: StageSpec) -> None:
        if not self.current_case:
            return
        out = case_dir(self.current_case) / spec.output_dir_rel
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(out)))

    def _refresh_task_runtime(self) -> None:
        if self.current_task is None:
            self.task_elapsed.setText("运行时长: -")
            return
        start_dt = self.current_task.get("start_dt")
        if isinstance(start_dt, datetime):
            delta = datetime.now() - start_dt
            secs = int(delta.total_seconds())
            self.task_elapsed.setText(f"运行时长: {secs}s")


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(SOFTWARE_TITLE)
    w = MainWindow()
    w.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
