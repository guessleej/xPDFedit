from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ToolParam:
    name: str
    type: str           # string | integer | boolean | select | file | password | number
    label_zh: str
    label_en: str = ""
    required: bool = False
    default: Any = None
    options: list[dict] = field(default_factory=list)
    placeholder: str = ""
    min_val: float | None = None
    max_val: float | None = None
    description: str = ""


@dataclass
class ToolResult:
    success: bool
    output_path: Path | None = None
    output_filename: str = ""
    content_type: str = "application/octet-stream"
    message: str = ""
    metadata: dict = field(default_factory=dict)
    error: str = ""


class ToolBase(ABC):
    tool_id: str = ""
    name_zh: str = ""
    name_en: str = ""
    description_zh: str = ""
    description_en: str = ""
    category: str = "general"
    icon: str = "File"
    color: str = "blue"
    tags: list[str] = []
    enabled: bool = True
    multi_file: bool = False

    @property
    def params(self) -> list[ToolParam]:
        return []

    @abstractmethod
    async def execute(self, input_path: Path, params: dict, workdir: Path) -> ToolResult:
        """執行工具，input_path 可能為 None（某些工具不需要輸入檔案）"""

    def to_dict(self) -> dict:
        return {
            "tool_id": self.tool_id,
            "name_zh": self.name_zh,
            "name_en": self.name_en,
            "description_zh": self.description_zh,
            "category": self.category,
            "icon": self.icon,
            "color": self.color,
            "tags": self.tags,
            "enabled": self.enabled,
            "multi_file": self.multi_file,
            "params": [
                {
                    "name": p.name,
                    "type": p.type,
                    "label_zh": p.label_zh,
                    "label_en": p.label_en,
                    "required": p.required,
                    "default": p.default,
                    "options": p.options,
                    "placeholder": p.placeholder,
                    "min_val": p.min_val,
                    "max_val": p.max_val,
                    "description": p.description,
                }
                for p in self.params
            ],
        }
