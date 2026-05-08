"""
ToolBase — 工具抽象基底類別（保留 jt-doc-tools ToolBase 設計）

每個工具繼承此 ABC 並實作 execute()。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ToolParam:
    name: str
    type: str           # "string" | "integer" | "boolean" | "file" | "select"
    label_zh: str
    label_en: str
    required: bool = True
    default: Any = None
    options: list[dict] = field(default_factory=list)   # for "select"
    description: str = ""


@dataclass
class ToolResult:
    success: bool
    output_path: Path | None = None
    output_filename: str | None = None
    content_type: str = "application/octet-stream"
    message: str = ""
    metadata: dict = field(default_factory=dict)


class ToolBase(ABC):
    # 子類必須定義
    tool_id: str = ""
    name_zh: str = ""
    name_en: str = ""
    description_zh: str = ""
    category: str = "general"   # "pdf" | "office" | "image" | "security" | "ai"
    icon: str = "file"

    @property
    def params(self) -> list[ToolParam]:
        """工具參數定義（用於前端自動產生表單）"""
        return []

    @abstractmethod
    async def execute(self, input_path: Path, params: dict, workdir: Path) -> ToolResult:
        """執行工具主邏輯"""

    def to_api_schema(self) -> dict:
        """序列化為 API 回應格式"""
        return {
            "tool_id": self.tool_id,
            "name_zh": self.name_zh,
            "name_en": self.name_en,
            "description_zh": self.description_zh,
            "category": self.category,
            "icon": self.icon,
            "params": [
                {
                    "name": p.name,
                    "type": p.type,
                    "label_zh": p.label_zh,
                    "label_en": p.label_en,
                    "required": p.required,
                    "default": p.default,
                    "options": p.options,
                }
                for p in self.params
            ],
        }
