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


def case_root() -> Path:
    declared = os.environ.get(ROOT_ENV)
    if not declared:
        return current_project_path()
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
    declared = os.environ.get(HISTORY_ENV)
    if not declared:
        return engine_path("resources", "isd", "isd-history.txt")
    path = Path(declared)
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise ValueError("P5 history must be an absolute, regular, read-only source")
    return path
