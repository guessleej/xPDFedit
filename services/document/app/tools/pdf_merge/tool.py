"""PDF 合併工具 — 示範工具實作（從 jt-doc-tools pdf_merge 遷移）"""
from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF

from app.engine.base import ToolBase, ToolParam, ToolResult


class Tool(ToolBase):
    tool_id = "pdf-merge"
    name_zh = "PDF 合併"
    name_en = "PDF Merge"
    description_zh = "將多個 PDF 合併為單一文件"
    category = "pdf"
    icon = "merge"

    @property
    def params(self) -> list[ToolParam]:
        return [
            ToolParam(
                name="files",
                type="file_list",
                label_zh="要合併的 PDF 檔案（依序）",
                label_en="PDF files to merge (in order)",
                required=True,
            ),
            ToolParam(
                name="output_name",
                type="string",
                label_zh="輸出檔名",
                label_en="Output filename",
                required=False,
                default="merged.pdf",
            ),
        ]

    async def execute(self, input_path: Path, params: dict, workdir: Path) -> ToolResult:
        # input_path 為第一個檔案；params["extra_files"] 含其餘
        files: list[Path] = [input_path] + [Path(p) for p in params.get("extra_files", [])]
        output_name = params.get("output_name", "merged.pdf")
        output_path = workdir / output_name

        merged = fitz.open()
        for f in files:
            with fitz.open(str(f)) as doc:
                merged.insert_pdf(doc)

        merged.save(str(output_path))
        merged.close()

        return ToolResult(
            success=True,
            output_path=output_path,
            output_filename=output_name,
            content_type="application/pdf",
            metadata={"page_count": merged.page_count, "source_count": len(files)},
        )
