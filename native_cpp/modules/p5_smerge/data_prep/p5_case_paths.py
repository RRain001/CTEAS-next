"""#56: explicit, process-local paths for the existing P5 producer stages.

Set ONLY by the admitted D1-B runner. Legacy invocation without the environment
preserves current_project_path() and the existing default history.
This helper selects directories; it does not change NOAA or SMERGE science.
"""
from __future__ import annotations

import os
from pathlib import Path

from engine.core.paths import current_project_path, engine_path

ROOT_ENV = "CTEAS_P5_STAGED_CASE_ROOT"
HISTORY_ENV = "CTEAS_P5_STAGED_HISTORY_FILE"


def _paired_staged_environment() -> bool:
    """A declared isolated P5 case must never fall back to legacy global paths.

    The legacy no-environment invocation is retained byte-for-byte; staging
    only applies when the native P5 producer declares *both* source contexts.
    """
    root_set = ROOT_ENV in os.environ
    history_set = HISTORY_ENV in os.environ
    if root_set != history_set:
        raise ValueError("P5 staged case and history env must be declared together")
    if root_set and (not os.environ[ROOT_ENV] or not os.environ[HISTORY_ENV]):
        raise ValueError("P5 staged case/history cannot be empty")
    return root_set


def case_root() -> Path:
    if not _paired_staged_environment():
        return current_project_path()
    declared = os.environ[ROOT_ENV]
    root = Path(declared)
    if (not root.is_absolute() or root.is_symlink() or
            not root.is_dir() or not (root / "case.yaml").is_file()):
        raise ValueError("P5 staged case root must be an absolute, existing independent case")
    # These paths must be owned by the staged case, not redirected into
    # project/current or another case.
    for segment in ("grid", "met", "met/surface", "run", "run/smerge"):
        member = root / segment
        if member.is_symlink():
            raise ValueError("P5 staged directory symlink prohibited: " + segment)
    return root


def history_file() -> Path:
    if not _paired_staged_environment():
        return engine_path("resources", "isd", "isd-history.txt")
    declared = os.environ[HISTORY_ENV]
    path = Path(declared)
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise ValueError("P5 history must be an absolute, regular, read-only source")
    return path
