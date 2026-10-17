from __future__ import annotations

from pathlib import Path

import yaml


TUTORIAL_ROOT = Path(__file__).resolve().parents[2]
PROJECT_DIR = TUTORIAL_ROOT / "project"
CASES_DIR = PROJECT_DIR / "cases"
CURRENT_LINK = PROJECT_DIR / "current"
CURRENT_CASE_FILE = PROJECT_DIR / "current_case.yaml"


def _read_current_case_file() -> str | None:
    if not CURRENT_CASE_FILE.exists():
        return None
    data = yaml.safe_load(CURRENT_CASE_FILE.read_text(encoding="utf-8")) or {}
    case_name = data.get("current_case")
    if isinstance(case_name, str):
        case_name = case_name.strip()
        if case_name:
            return case_name
    return None


def _legacy_current_case_name() -> str | None:
    if CURRENT_LINK.is_symlink():
        try:
            target = CURRENT_LINK.resolve()
        except OSError:
            return None
        if target.parent == CASES_DIR:
            return target.name
    return None


def _legacy_current_case_dir() -> Path | None:
    if CURRENT_LINK.is_symlink():
        try:
            return CURRENT_LINK.resolve()
        except OSError:
            return None
    if CURRENT_LINK.exists() and CURRENT_LINK.is_dir():
        return CURRENT_LINK.resolve()
    return None


def get_current_case_name() -> str | None:
    return _read_current_case_file() or _legacy_current_case_name()


def get_case_dir(case_name: str | None = None) -> Path:
    if case_name:
        return CASES_DIR / case_name

    current_case = get_current_case_name()
    if current_case:
        return CASES_DIR / current_case

    legacy_dir = _legacy_current_case_dir()
    if legacy_dir is not None:
        return legacy_dir

    raise ValueError("No current case configured. Use project/current_case.yaml or project/current.")


def get_current_case_dir() -> Path:
    return get_case_dir()


def set_current_case(case_name: str) -> None:
    case_dir = CASES_DIR / case_name
    if not case_dir.is_dir():
        raise FileNotFoundError(f"Case directory not found: {case_dir}")

    CURRENT_CASE_FILE.write_text(
        yaml.safe_dump({"current_case": case_name}, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    target = Path("cases") / case_name
    if CURRENT_LINK.exists() or CURRENT_LINK.is_symlink():
        CURRENT_LINK.unlink()
    try:
        CURRENT_LINK.symlink_to(target)
    except OSError:
        # Windows may not allow symlink creation; current_case.yaml remains source of truth.
        pass
