from __future__ import annotations

import platform
from pathlib import Path

from engine.native.registry import get_physical_binary_name


LINUX_X86_64 = "linux-x86_64"
LINUX_ARM64 = "linux-arm64"
WINDOWS_X86_64 = "windows-x86_64"
SUPPORTED_PLATFORMS = (LINUX_X86_64, LINUX_ARM64, WINDOWS_X86_64)


class UnsupportedPlatformError(RuntimeError):
    pass


def get_platform_key() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "linux":
        if machine in {"x86_64", "amd64"}:
            return LINUX_X86_64
        if machine in {"aarch64", "arm64"}:
            return LINUX_ARM64
    if system == "windows":
        if machine in {"x86_64", "amd64"}:
            return WINDOWS_X86_64

    raise UnsupportedPlatformError(f"Unsupported runtime platform: system={system!r}, machine={machine!r}")


def binary_filename(binary_name: str, platform_key: str) -> str:
    if platform_key == WINDOWS_X86_64:
        return f"{binary_name}.exe"
    if platform_key in {LINUX_X86_64, LINUX_ARM64}:
        return f"{binary_name}.x"
    raise UnsupportedPlatformError(f"Unsupported platform key: {platform_key}")


def get_binary_path(
    binary_name: str,
    *,
    platform_key: str,
    bin_root: Path,
    legacy_bin_root: Path | None = None,
) -> Path:
    physical_name = get_physical_binary_name(binary_name)
    candidate = bin_root / platform_key / binary_filename(physical_name, platform_key)
    if candidate.exists():
        return candidate

    if legacy_bin_root is not None:
        legacy_candidate = legacy_bin_root / binary_filename(physical_name, platform_key)
        if legacy_candidate.exists():
            return legacy_candidate

    return candidate
