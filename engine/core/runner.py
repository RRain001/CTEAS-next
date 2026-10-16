from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from .platform_utils import get_binary_path, get_platform_key


def build_binary_command(
    binary_name: str,
    *args: str,
    platform_key: str | None = None,
    bin_root: Path,
    legacy_bin_root: Path | None = None,
) -> list[str]:
    selected_platform = platform_key or get_platform_key()
    binary_path = get_binary_path(
        binary_name,
        platform_key=selected_platform,
        bin_root=bin_root,
        legacy_bin_root=legacy_bin_root,
    )
    return [str(binary_path), *args]


def run_binary(
    binary_name: str,
    *args: str,
    cwd: str | Path | None = None,
    platform_key: str | None = None,
    bin_root: Path,
    legacy_bin_root: Path | None = None,
    **kwargs: Any,
) -> subprocess.CompletedProcess[str]:
    cmd = build_binary_command(
        binary_name,
        *args,
        platform_key=platform_key,
        bin_root=bin_root,
        legacy_bin_root=legacy_bin_root,
    )
    if isinstance(cwd, Path):
        cwd = str(cwd)
    return subprocess.run(cmd, cwd=cwd, **kwargs)
