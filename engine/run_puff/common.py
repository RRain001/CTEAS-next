#!/usr/bin/env python3
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from engine.core.paths import TEMPLATE_FILES, case_paths, load_case_config, resolve_case_name

PUFF_TEMPLATE_FALLBACK = TEMPLATE_FILES["puff"]


def load_case_config_with_name(case_name: str | None = None) -> tuple[str, dict[str, Any]]:
    resolved_case = resolve_case_name(case_name)
    return resolved_case, load_case_config(resolved_case)


def parse_research_time(case_name: str, path: Path | None = None) -> tuple[datetime, datetime]:
    if path is None:
        cfg = load_case_config(case_name)
        paths = case_paths(cfg, case_name, required=["grid_dir"])
        path = paths["grid_dir"] / "research_time"

    text = path.read_text(encoding="utf-8", errors="ignore")
    m_begin = re.search(r"BEGIN\s*:\s*(\d{8}-\d{6})", text)
    m_end = re.search(r"END\s*:\s*(\d{8}-\d{6})", text)
    if not m_begin or not m_end:
        raise ValueError(f"Cannot parse BEGIN/END from: {path}")
    begin = datetime.strptime(m_begin.group(1), "%Y%m%d-%H%M%S")
    end = datetime.strptime(m_end.group(1), "%Y%m%d-%H%M%S")
    if end < begin:
        raise ValueError(f"END earlier than BEGIN in: {path}")
    return begin, end
