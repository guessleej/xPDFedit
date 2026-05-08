"""
工具登錄 — 保留 jt-doc-tools discover_tools() 設計，適配微服務架構

每個 Tool 子目錄需提供 tool.py 實作 ToolBase。
"""
from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import ToolBase

logger = logging.getLogger(__name__)

_registry: dict[str, "ToolBase"] = {}


def discover_tools(tools_dir: Path | None = None) -> dict[str, "ToolBase"]:
    """掃描 tools/ 目錄，動態載入所有工具"""
    global _registry
    if _registry:
        return _registry

    if tools_dir is None:
        tools_dir = Path(__file__).parent.parent / "tools"

    for tool_path in sorted(tools_dir.iterdir()):
        if not tool_path.is_dir() or tool_path.name.startswith("_"):
            continue
        try:
            mod = importlib.import_module(f"app.tools.{tool_path.name}.tool")
            tool_cls = getattr(mod, "Tool", None)
            if tool_cls is None:
                continue
            tool = tool_cls()
            _registry[tool.tool_id] = tool
            logger.info("載入工具: %s (%s)", tool.tool_id, tool.name_zh)
        except Exception as e:
            logger.warning("工具載入失敗 %s: %s", tool_path.name, e)

    logger.info("共載入 %d 個工具", len(_registry))
    return _registry


def get_tool(tool_id: str) -> "ToolBase | None":
    return _registry.get(tool_id)
