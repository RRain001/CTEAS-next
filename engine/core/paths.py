from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from engine.core.case_manager import get_current_case_dir, get_current_case_name, set_current_case
from engine.native.registry import NATIVE_PROGRAMS
from engine.core.runtime_names import MET_TEMPLATE, PUFF_TEMPLATE

from .platform_utils import (
    LINUX_ARM64,
    LINUX_X86_64,
    SUPPORTED_PLATFORMS,
    UnsupportedPlatformError,
    get_binary_path,
    get_platform_key,
)


TUTORIAL_ROOT = Path(__file__).resolve().parents[2]

ENGINE_DIR = TUTORIAL_ROOT / "engine"
PROJECT_DIR = TUTORIAL_ROOT / "project"
CURRENT_PROJECT_DIR = PROJECT_DIR / "current"
CASES_DIR = PROJECT_DIR / "cases"
DATA_DIR = TUTORIAL_ROOT / "data"
BIN_DIR = TUTORIAL_ROOT / "bin"
OUTPUT_DIR = TUTORIAL_ROOT / "output"
CONFIG_DIR = ENGINE_DIR / "config"
TEMPLATES_DIR = ENGINE_DIR / "templates"
VENDOR_DIR = ENGINE_DIR / "vendor"
VENDOR_BIN_DIR = VENDOR_DIR / "bin"
VENDOR_SRC_DIR = VENDOR_DIR / "src"

# Backward-compatible names used by existing modules.
ENGINE_ROOT = ENGINE_DIR
PROJECT_ROOT = PROJECT_DIR
CASES_ROOT = CASES_DIR
CURRENT_LINK = CURRENT_PROJECT_DIR
BIN_ROOT = BIN_DIR

TEMPLATE_FILES = {
    "terrel": TEMPLATES_DIR / "terrel.inp",
    "ctgproc": TEMPLATES_DIR / "ctgproc.inp",
    "makegeo": TEMPLATES_DIR / "makegeo.inp",
    "met": TEMPLATES_DIR / MET_TEMPLATE,
    "puff": TEMPLATES_DIR / PUFF_TEMPLATE,
    "calmet": TEMPLATES_DIR / MET_TEMPLATE,
    "calpuff": TEMPLATES_DIR / PUFF_TEMPLATE,
    "read62": TEMPLATES_DIR / "read62.inp",
    "smerge": TEMPLATES_DIR / "smerge.inp",
}

EXECUTABLE_NAMES = tuple(NATIVE_PROGRAMS.keys())


def tutorial_path(*parts: str) -> Path:
    return TUTORIAL_ROOT.joinpath(*parts)


def project_path(*parts: str) -> Path:
    return PROJECT_DIR.joinpath(*parts)


def current_project_path(*parts: str) -> Path:
    try:
        return get_current_case_dir().joinpath(*parts)
    except ValueError:
        return CURRENT_PROJECT_DIR.joinpath(*parts)


def case_path(case_name: str, *parts: str) -> Path:
    return CASES_DIR.joinpath(case_name, *parts)


def engine_path(*parts: str) -> Path:
    return ENGINE_DIR.joinpath(*parts)


def data_path(*parts: str) -> Path:
    return DATA_DIR.joinpath(*parts)


def bin_path(*parts: str) -> Path:
    return BIN_DIR.joinpath(*parts)


def output_path(*parts: str) -> Path:
    return OUTPUT_DIR.joinpath(*parts)


def config_path(*parts: str) -> Path:
    return CONFIG_DIR.joinpath(*parts)


def _coerce_platform_key(platform: str | None = None) -> str:
    if platform in {None, "auto"}:
        try:
            return get_platform_key()
        except UnsupportedPlatformError:
            return LINUX_X86_64
    if platform in {"linux", "linux-x86_64", "posix"}:
        return LINUX_X86_64
    if platform in {"linux-arm64", "linux-aarch64", LINUX_ARM64}:
        return LINUX_ARM64
    if platform in {"windows", "windows-x86_64"}:
        return "windows-x86_64"
    if platform in SUPPORTED_PLATFORMS:
        return platform
    raise ValueError(f"Unsupported executable platform: {platform}")


def executable_path(name: str, *, platform: str | None = None) -> Path:
    if name not in EXECUTABLE_NAMES:
        raise KeyError(f"Unknown executable name: {name}")
    selected = _coerce_platform_key(platform)
    legacy_dir = VENDOR_BIN_DIR / "windows" if selected == "windows-x86_64" else VENDOR_BIN_DIR
    return get_binary_path(name, platform_key=selected, bin_root=BIN_ROOT, legacy_bin_root=legacy_dir)


def resolve_executable(name: str, *, platform: str | None = None) -> Path:
    path = executable_path(name, platform=platform)
    selected = _coerce_platform_key(platform)
    if not path.exists():
        raise FileNotFoundError(f"{name} executable not found for {selected}. Expected: {path}")
    if selected != "windows-x86_64" and not path.is_file():
        raise FileNotFoundError(f"{name} executable is not a file: {path}")
    return path


BIN_FILES = {name: executable_path(name, platform="linux-x86_64") for name in EXECUTABLE_NAMES}


def case_dir(case_name: str) -> Path:
    return case_path(case_name)


def case_yaml_path(case_name: str) -> Path:
    return case_dir(case_name) / "case.yaml"


def current_case_name() -> str | None:
    return get_current_case_name()


def ensure_current_case(case_name: str) -> None:
    set_current_case(case_name)


def resolve_case_name(explicit_case: str | None = None) -> str:
    if explicit_case:
        return explicit_case
    current = current_case_name()
    if current:
        return current
    raise ValueError("No case selected. Use --case <name>, project/current_case.yaml, or project/current.")


def load_case_config(case_name: str) -> dict[str, Any]:
    path = case_yaml_path(case_name)
    if not path.exists():
        raise FileNotFoundError(f"case.yaml not found: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def resolve_case_path(path_str: str, case_name: str) -> Path:
    if path_str.startswith("project/current/"):
        suffix = path_str.split("project/current/", 1)[1]
        return (case_dir(case_name) / suffix).resolve()
    return (TUTORIAL_ROOT / path_str).resolve()


def case_paths(config: dict[str, Any], case_name: str, required: list[str] | None = None) -> dict[str, Path]:
    paths = config.get("paths", {})
    if required is None:
        required = list(paths.keys())
    missing = [key for key in required if key not in paths]
    if missing:
        raise ValueError(f"Missing case paths in case.yaml: {', '.join(missing)}")
    return {key: resolve_case_path(paths[key], case_name) for key in required}
