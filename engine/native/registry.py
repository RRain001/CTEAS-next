from __future__ import annotations

from typing import Any


NATIVE_PROGRAMS = {
    "terrel": {
        "binary": "terrel",
        "suffix": ".x",
        "module": "terrain preprocessing",
        "required": True,
    },
    "ctgproc": {
        "binary": "ctgproc",
        "suffix": ".x",
        "module": "landuse preprocessing",
        "required": True,
    },
    "makegeo": {
        "binary": "makegeo",
        "suffix": ".x",
        "module": "geo preprocessing",
        "required": True,
    },
    "read62": {
        "binary": "read62",
        "suffix": ".x",
        "module": "upperair preprocessing",
        "required": True,
    },
    "smerge": {
        "binary": "smerge",
        "suffix": ".x",
        "module": "surface meteorology preprocessing",
        "required": True,
    },
    "met": {
        "binary": "met",
        "suffix": ".x",
        "display_name": "MET",
        "module": "diagnostic wind field",
        "required": True,
    },
    "puff": {
        "binary": "puff",
        "suffix": ".x",
        "display_name": "PUFF",
        "module": "puff dispersion model",
        "required": True,
    },
}


def get_program_metadata(program_name: str) -> dict[str, Any]:
    return dict(NATIVE_PROGRAMS.get(program_name, {}))


def get_physical_binary_name(program_name: str) -> str:
    meta = NATIVE_PROGRAMS.get(program_name)
    if meta is None:
        return program_name
    binary = meta.get("binary")
    return str(binary) if binary else program_name


def iter_required_programs() -> list[tuple[str, dict[str, object]]]:
    return [(name, spec) for name, spec in NATIVE_PROGRAMS.items() if bool(spec.get("required", False))]
