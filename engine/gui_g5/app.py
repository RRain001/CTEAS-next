from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

from engine.core.paths import CASES_ROOT, TUTORIAL_ROOT


REMOVAL_MESSAGE = (
    "The retired WebGUI is not the G5 desktop application.\n"
    "Run python -m engine.gui_g5.main for the independent G5 PySide6 GUI,\n"
    "or ./calpuff-cli run --case <name> --stage <preprocess|upperair|surface|met|puff|all> for CLI orchestration."
)


def list_cases() -> list[str]:
    if not CASES_ROOT.exists():
        CASES_ROOT.mkdir(parents=True, exist_ok=True)
        return []
    return sorted([path.name for path in CASES_ROOT.iterdir() if path.is_dir()])


def case_yaml_path(name: str) -> Path:
    return CASES_ROOT / name / "case.yaml"


def load_case_yaml(name: str) -> dict[str, Any]:
    path = case_yaml_path(name)
    if not path.exists():
        raise FileNotFoundError(f"case.yaml not found: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def list_case_summaries() -> list[dict[str, str]]:
    summaries: list[dict[str, str]] = []
    for name in list_cases():
        display = name
        try:
            data = load_case_yaml(name)
            yaml_name = str(data.get("case_name") or "").strip()
            if yaml_name:
                display = f"{name} ({yaml_name})"
        except Exception:
            pass
        summaries.append({"name": name, "display": display})
    return summaries


def create_case(name: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
        raise ValueError("case name must match [A-Za-z0-9_-]+")
    if (CASES_ROOT / name).exists():
        raise ValueError(f"case already exists: {name}")

    cmd = [sys.executable, "-m", "engine.gui_g5.case_setup", name]
    proc = subprocess.run(
        cmd,
        cwd=str(TUTORIAL_ROOT),
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        message = (proc.stdout or "") + "\n" + (proc.stderr or "")
        raise RuntimeError(message.strip() or f"create case failed: {name}")


def main() -> int:
    print(REMOVAL_MESSAGE, file=sys.stderr)
    return 2
