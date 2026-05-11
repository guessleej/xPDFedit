"""工具登錄 — 靜態定義所有 30+ 工具"""
from __future__ import annotations
import logging
from .base import ToolBase, ToolParam, ToolResult
from pathlib import Path
import asyncio, shutil

logger = logging.getLogger(__name__)


# ─── PDF 工具 ────────────────────────────────────────────────────────────────

class PdfMergeTool(ToolBase):
    tool_id = "pdf-merge"
    name_zh = "PDF 合併"
    name_en = "PDF Merge"
    description_zh = "將多個 PDF 檔案依序合併為單一文件"
    category = "pdf"
    icon = "Combine"
    color = "blue"
    tags = ["PDF", "合併"]
    multi_file = True

    @property
    def params(self):
        return [
            ToolParam("output_name", "string", "輸出檔名", required=False, default="merged.pdf", placeholder="merged.pdf"),
        ]

    async def execute(self, input_path: Path, params: dict, workdir: Path) -> ToolResult:
        try:
            import fitz
            extra = [Path(p) for p in params.get("extra_files", [])]
            files = [input_path] + extra
            output_name = params.get("output_name", "merged.pdf")
            output_path = workdir / output_name
            merged = fitz.open()
            for f in files:
                with fitz.open(str(f)) as doc:
                    merged.insert_pdf(doc)
            merged.save(str(output_path))
            page_count = merged.page_count
            merged.close()
            return ToolResult(True, output_path, output_name, "application/pdf", metadata={"pages": page_count, "sources": len(files)})
        except Exception as e:
            return ToolResult(False, error=str(e))


class PdfSplitTool(ToolBase):
    tool_id = "pdf-split"
    name_zh = "PDF 分拆"
    name_en = "PDF Split"
    description_zh = "依頁碼範圍或每隔 N 頁拆分 PDF"
    category = "pdf"
    icon = "Scissors"
    color = "blue"
    tags = ["PDF", "分拆"]

    @property
    def params(self):
        return [
            ToolParam("mode", "select", "拆分模式", required=True, default="range",
                      options=[{"label": "指定頁碼範圍", "value": "range"}, {"label": "每 N 頁一份", "value": "chunk"}]),
            ToolParam("range", "string", "頁碼範圍（如 1-3,5,7-9）", required=False, placeholder="1-3,5,7-9"),
            ToolParam("chunk_size", "integer", "每份頁數", required=False, default=1, min_val=1, max_val=999),
        ]

    async def execute(self, input_path: Path, params: dict, workdir: Path) -> ToolResult:
        try:
            import fitz, zipfile
            doc = fitz.open(str(input_path))
            total = doc.page_count
            mode = params.get("mode", "range")
            output_zip = workdir / f"split_{input_path.stem}.zip"

            if mode == "range":
                ranges_str = params.get("range", f"1-{total}")
                pages = _parse_page_range(ranges_str, total)
                groups = [pages]
            else:
                chunk = int(params.get("chunk_size", 1))
                all_pages = list(range(total))
                groups = [all_pages[i:i+chunk] for i in range(0, total, chunk)]

            with zipfile.ZipFile(str(output_zip), "w") as zf:
                for idx, group in enumerate(groups):
                    out = fitz.open()
                    for pg in group:
                        out.insert_pdf(doc, from_page=pg, to_page=pg)
                    fname = f"part_{idx+1:03d}.pdf"
                    out_path = workdir / fname
                    out.save(str(out_path))
                    out.close()
                    zf.write(str(out_path), fname)
            doc.close()
            return ToolResult(True, output_zip, output_zip.name, "application/zip")
        except Exception as e:
            return ToolResult(False, error=str(e))


class PdfCompressTool(ToolBase):
    tool_id = "pdf-compress"
    name_zh = "PDF 壓縮"
    name_en = "PDF Compress"
    description_zh = "優化 PDF 影像品質與字型，縮小檔案大小"
    category = "pdf"
    icon = "PackageMinus"
    color = "blue"
    tags = ["PDF", "壓縮", "最佳化"]

    @property
    def params(self):
        return [
            ToolParam("quality", "select", "壓縮品質", required=False, default="balanced",
                      options=[
                          {"label": "最小體積（積極壓縮，畫質較低）", "value": "min"},
                          {"label": "平衡（推薦，兼顧大小與畫質）",    "value": "balanced"},
                          {"label": "高品質（輕度壓縮，保留細節）",    "value": "high"},
                      ]),
        ]

    async def execute(self, input_path: Path, params: dict, workdir: Path) -> ToolResult:
        try:
            import fitz, io
            level = params.get("quality", "balanced")

            # JPEG 重壓品質：數字越小壓縮越積極
            quality_map = {"min": 18, "balanced": 42, "high": 68}
            # 圖片最大邊長（超過才縮圖）
            max_dim_map = {"min": 900, "balanced": 1400, "high": 2200}
            # 最小圖片像素數（低於此不處理）
            min_px_map  = {"min": 4096, "balanced": 16384, "high": 40000}

            quality = quality_map.get(level, 42)
            max_dim = max_dim_map.get(level, 1400)
            min_px  = min_px_map.get(level, 16384)
            output_path = workdir / f"compressed_{input_path.name}"

            # PIL 可選（用於縮圖）
            try:
                from PIL import Image
                HAS_PIL = True
            except ImportError:
                HAS_PIL = False

            doc = fitz.open(str(input_path))

            seen: set = set()
            for page in doc:
                for img_info in page.get_images(full=True):
                    xref = img_info[0]
                    if xref in seen:
                        continue
                    seen.add(xref)
                    try:
                        pix = fitz.Pixmap(doc, xref)
                        if pix.width * pix.height < min_px:
                            continue
                        # CMYK 或含 alpha → 轉 RGB
                        if pix.n > 3 or pix.alpha:
                            pix = fitz.Pixmap(fitz.csRGB, pix)

                        # 縮圖：超出最大邊長才縮
                        need_resize = max(pix.width, pix.height) > max_dim
                        if need_resize and HAS_PIL:
                            img = Image.open(io.BytesIO(pix.tobytes("png")))
                            img.thumbnail((max_dim, max_dim), Image.LANCZOS)
                            buf = io.BytesIO()
                            img.save(buf, format="JPEG", quality=quality, optimize=True)
                            jpeg_bytes = buf.getvalue()
                            new_w, new_h = img.size
                        else:
                            jpeg_bytes = pix.tobytes("jpeg", jpg_quality=quality)
                            new_w, new_h = pix.width, pix.height

                        # 只有真的變小才替換
                        orig_len = len(doc.xref_stream(xref))
                        if len(jpeg_bytes) >= orig_len:
                            continue

                        doc.update_stream(xref, jpeg_bytes, compress=False)
                        doc.xref_set_key(xref, "Filter", "/DCTDecode")
                        doc.xref_set_key(xref, "ColorSpace", "/DeviceRGB")
                        doc.xref_set_key(xref, "BitsPerComponent", "8")
                        doc.xref_set_key(xref, "Width",  str(new_w))
                        doc.xref_set_key(xref, "Height", str(new_h))
                    except Exception:
                        continue

            # 注意：deflate_images=True 會對已有 DCTDecode 的 JPEG 再包一層 Flate，反而更大，故不用
            doc.save(str(output_path), garbage=4, deflate=True, deflate_fonts=True)
            doc.close()

            import shutil
            original_size = input_path.stat().st_size
            output_size   = output_path.stat().st_size

            # 保底：若結果比原始更大，直接回傳原始檔
            if output_size >= original_size:
                shutil.copy2(str(input_path), str(output_path))
                output_size = original_size

            ratio = round((1 - output_size / original_size) * 100, 1)
            ratio_str = f"{ratio}%" if ratio > 0 else "已是最佳化，無需壓縮"
            return ToolResult(True, output_path, output_path.name, "application/pdf",
                              metadata={"壓縮率": ratio_str,
                                        "原始大小": f"{original_size // 1024} KB",
                                        "壓縮後":   f"{output_size  // 1024} KB"})
        except Exception as e:
            return ToolResult(False, error=str(e))


class PdfEncryptTool(ToolBase):
    tool_id = "pdf-encrypt"
    name_zh = "PDF 加密"
    name_en = "PDF Encrypt"
    description_zh = "為 PDF 設定開啟密碼與權限密碼"
    category = "pdf"
    icon = "Lock"
    color = "red"
    tags = ["PDF", "加密", "安全"]

    @property
    def params(self):
        return [
            ToolParam("user_password", "password", "開啟密碼", required=True, placeholder="輸入開啟密碼"),
            ToolParam("owner_password", "password", "擁有者密碼（選填）", required=False, placeholder="留空則與開啟密碼相同"),
            ToolParam("allow_print", "boolean", "允許列印", required=False, default=True),
            ToolParam("allow_copy", "boolean", "允許複製", required=False, default=False),
        ]

    async def execute(self, input_path: Path, params: dict, workdir: Path) -> ToolResult:
        try:
            import fitz
            user_pw = params.get("user_password", "")
            owner_pw = params.get("owner_password") or user_pw
            perm = fitz.PDF_PERM_ACCESSIBILITY
            if params.get("allow_print", True):
                perm |= fitz.PDF_PERM_PRINT
            if params.get("allow_copy", False):
                perm |= fitz.PDF_PERM_COPY
            output_path = workdir / f"encrypted_{input_path.name}"
            doc = fitz.open(str(input_path))
            encrypt_meth = fitz.PDF_ENCRYPT_AES_256
            doc.save(str(output_path), encryption=encrypt_meth, user_pw=user_pw, owner_pw=owner_pw, permissions=perm)
            doc.close()
            return ToolResult(True, output_path, output_path.name, "application/pdf")
        except Exception as e:
            return ToolResult(False, error=str(e))


class PdfDecryptTool(ToolBase):
    tool_id = "pdf-decrypt"
    name_zh = "PDF 解密"
    name_en = "PDF Decrypt"
    description_zh = "移除 PDF 密碼保護"
    category = "pdf"
    icon = "Unlock"
    color = "yellow"
    tags = ["PDF", "解密", "安全"]

    @property
    def params(self):
        return [ToolParam("password", "password", "PDF 密碼", required=True)]

    async def execute(self, input_path: Path, params: dict, workdir: Path) -> ToolResult:
        try:
            import fitz
            doc = fitz.open(str(input_path))
            if doc.is_encrypted:
                if not doc.authenticate(params.get("password", "")):
                    return ToolResult(False, error="密碼錯誤")
            output_path = workdir / f"decrypted_{input_path.name}"
            doc.save(str(output_path))
            doc.close()
            return ToolResult(True, output_path, output_path.name, "application/pdf")
        except Exception as e:
            return ToolResult(False, error=str(e))


class PdfWatermarkTool(ToolBase):
    tool_id = "pdf-watermark"
    name_zh = "PDF 浮水印"
    name_en = "PDF Watermark"
    description_zh = "在每頁加上文字或圖片浮水印"
    category = "pdf"
    icon = "Droplets"
    color = "cyan"
    tags = ["PDF", "浮水印"]

    @property
    def params(self):
        return [
            ToolParam("text", "string", "浮水印文字", required=True, placeholder="機密文件"),
            ToolParam("opacity", "number", "透明度 (0.1-1.0)", required=False, default=0.3, min_val=0.1, max_val=1.0),
            ToolParam("angle", "integer", "旋轉角度", required=False, default=45, min_val=0, max_val=360),
            ToolParam("color", "select", "顏色", required=False, default="gray",
                      options=[{"label": "灰色", "value": "gray"}, {"label": "紅色", "value": "red"}, {"label": "藍色", "value": "blue"}]),
        ]

    async def execute(self, input_path: Path, params: dict, workdir: Path) -> ToolResult:
        try:
            import fitz, math
            text = params.get("text", "CONFIDENTIAL")
            opacity = float(params.get("opacity", 0.3))
            angle = int(params.get("angle", 45))
            color_map = {"gray": (0.5, 0.5, 0.5), "red": (0.8, 0.1, 0.1), "blue": (0.1, 0.1, 0.8)}
            color = color_map.get(params.get("color", "gray"), (0.5, 0.5, 0.5))
            output_path = workdir / f"watermarked_{input_path.name}"
            doc = fitz.open(str(input_path))
            for page in doc:
                center = fitz.Point(page.rect.width / 2, page.rect.height / 2)
                rot_mat = fitz.Matrix(1, 0, 0, 1, 0, 0).prerotate(angle)
                page.insert_text(
                    center,
                    text=text, fontsize=48, color=color,
                    fill_opacity=opacity,
                    morph=(center, rot_mat),
                    render_mode=0,
                )
            doc.save(str(output_path))
            doc.close()
            return ToolResult(True, output_path, output_path.name, "application/pdf")
        except Exception as e:
            return ToolResult(False, error=str(e))


class PdfRotateTool(ToolBase):
    tool_id = "pdf-rotate"
    name_zh = "PDF 旋轉"
    name_en = "PDF Rotate"
    description_zh = "旋轉 PDF 頁面方向"
    category = "pdf"
    icon = "RotateCw"
    color = "indigo"
    tags = ["PDF", "旋轉"]

    @property
    def params(self):
        return [
            ToolParam("angle", "select", "旋轉角度", required=True, default="90",
                      options=[{"label": "順時針 90°", "value": "90"}, {"label": "180°", "value": "180"}, {"label": "逆時針 90°", "value": "270"}]),
            ToolParam("pages", "string", "頁碼（留空=全部）", required=False, placeholder="1-3,5"),
        ]

    async def execute(self, input_path: Path, params: dict, workdir: Path) -> ToolResult:
        try:
            import fitz
            angle = int(params.get("angle", 90))
            output_path = workdir / f"rotated_{input_path.name}"
            doc = fitz.open(str(input_path))
            pages_str = params.get("pages", "")
            if pages_str:
                pages = _parse_page_range(pages_str, doc.page_count)
            else:
                pages = list(range(doc.page_count))
            for i in pages:
                doc[i].set_rotation(angle)
            doc.save(str(output_path))
            doc.close()
            return ToolResult(True, output_path, output_path.name, "application/pdf")
        except Exception as e:
            return ToolResult(False, error=str(e))


class PdfExtractTextTool(ToolBase):
    tool_id = "pdf-extract-text"
    name_zh = "擷取文字"
    name_en = "Extract Text"
    description_zh = "從 PDF 中提取所有文字內容"
    category = "pdf"
    icon = "FileText"
    color = "green"
    tags = ["PDF", "擷取", "文字"]

    @property
    def params(self):
        return [
            ToolParam("format", "select", "輸出格式", required=False, default="txt",
                      options=[{"label": "純文字 (.txt)", "value": "txt"}, {"label": "JSON 含座標", "value": "json"}]),
        ]

    async def execute(self, input_path: Path, params: dict, workdir: Path) -> ToolResult:
        try:
            import fitz, json
            fmt = params.get("format", "txt")
            doc = fitz.open(str(input_path))
            if fmt == "json":
                data = []
                for i, page in enumerate(doc):
                    blocks = page.get_text("dict")["blocks"]
                    data.append({"page": i + 1, "blocks": blocks})
                output_path = workdir / f"{input_path.stem}_text.json"
                output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
                ct = "application/json"
            else:
                text = ""
                for i, page in enumerate(doc):
                    text += f"\n--- 第 {i+1} 頁 ---\n"
                    text += page.get_text()
                output_path = workdir / f"{input_path.stem}_text.txt"
                output_path.write_text(text, encoding="utf-8")
                ct = "text/plain"
            doc.close()
            return ToolResult(True, output_path, output_path.name, ct)
        except Exception as e:
            return ToolResult(False, error=str(e))


class PdfExtractImagesTool(ToolBase):
    tool_id = "pdf-extract-images"
    name_zh = "擷取圖片"
    name_en = "Extract Images"
    description_zh = "從 PDF 中提取所有嵌入圖片"
    category = "pdf"
    icon = "Image"
    color = "pink"
    tags = ["PDF", "擷取", "圖片"]

    async def execute(self, input_path: Path, params: dict, workdir: Path) -> ToolResult:
        try:
            import fitz, zipfile
            doc = fitz.open(str(input_path))
            output_zip = workdir / f"{input_path.stem}_images.zip"
            count = 0
            with zipfile.ZipFile(str(output_zip), "w") as zf:
                for page_num, page in enumerate(doc):
                    for img_idx, img in enumerate(page.get_images()):
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        ext = base_image.get("ext", "png")
                        img_data = base_image["image"]
                        fname = f"page{page_num+1:03d}_img{img_idx+1:03d}.{ext}"
                        img_path = workdir / fname
                        img_path.write_bytes(img_data)
                        zf.write(str(img_path), fname)
                        count += 1
            doc.close()
            return ToolResult(True, output_zip, output_zip.name, "application/zip", metadata={"image_count": count})
        except Exception as e:
            return ToolResult(False, error=str(e))


class PdfMetadataTool(ToolBase):
    tool_id = "pdf-metadata"
    name_zh = "中繼資料管理"
    name_en = "PDF Metadata"
    description_zh = "查看或清除 PDF 的作者、標題等中繼資料"
    category = "pdf"
    icon = "Info"
    color = "slate"
    tags = ["PDF", "中繼資料", "隱私"]

    @property
    def params(self):
        return [
            ToolParam("action", "select", "動作", required=True, default="view",
                      options=[{"label": "檢視中繼資料", "value": "view"}, {"label": "清除中繼資料", "value": "clear"}]),
        ]

    async def execute(self, input_path: Path, params: dict, workdir: Path) -> ToolResult:
        try:
            import fitz, json
            doc = fitz.open(str(input_path))
            action = params.get("action", "view")
            if action == "view":
                meta = doc.metadata
                output_path = workdir / f"{input_path.stem}_metadata.json"
                output_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
                doc.close()
                return ToolResult(True, output_path, output_path.name, "application/json", metadata=meta)
            else:
                for key in ["title", "author", "subject", "keywords", "creator", "producer"]:
                    doc.set_metadata({})
                output_path = workdir / f"clean_{input_path.name}"
                doc.save(str(output_path))
                doc.close()
                return ToolResult(True, output_path, output_path.name, "application/pdf")
        except Exception as e:
            return ToolResult(False, error=str(e))


class PdfPagesTool(ToolBase):
    tool_id = "pdf-pages"
    name_zh = "頁面管理"
    name_en = "Page Manager"
    description_zh = "刪除、重排 PDF 頁面"
    category = "pdf"
    icon = "LayoutList"
    color = "violet"
    tags = ["PDF", "頁面", "重排"]

    @property
    def params(self):
        return [
            ToolParam("action", "select", "動作", required=True, default="delete",
                      options=[{"label": "刪除頁面", "value": "delete"}, {"label": "保留頁面", "value": "keep"}]),
            ToolParam("pages", "string", "頁碼（如 1,3-5）", required=True, placeholder="1,3-5"),
        ]

    async def execute(self, input_path: Path, params: dict, workdir: Path) -> ToolResult:
        try:
            import fitz
            doc = fitz.open(str(input_path))
            total = doc.page_count
            pages = _parse_page_range(params.get("pages", ""), total)
            action = params.get("action", "delete")
            if action == "delete":
                for pg in sorted(pages, reverse=True):
                    doc.delete_page(pg)
            else:
                delete_pages = [i for i in range(total) if i not in pages]
                for pg in sorted(delete_pages, reverse=True):
                    doc.delete_page(pg)
            output_path = workdir / f"pages_{input_path.name}"
            doc.save(str(output_path))
            doc.close()
            return ToolResult(True, output_path, output_path.name, "application/pdf")
        except Exception as e:
            return ToolResult(False, error=str(e))


class PdfWordCountTool(ToolBase):
    tool_id = "pdf-wordcount"
    name_zh = "字數統計"
    name_en = "Word Count"
    description_zh = "統計 PDF 各頁的字數與字元數"
    category = "pdf"
    icon = "Hash"
    color = "teal"
    tags = ["PDF", "統計", "字數"]

    async def execute(self, input_path: Path, params: dict, workdir: Path) -> ToolResult:
        try:
            import fitz, json
            doc = fitz.open(str(input_path))
            result = []
            total_chars = 0
            for i, page in enumerate(doc):
                text = page.get_text()
                chars = len(text.replace("\n", "").replace(" ", ""))
                words = len(text.split())
                result.append({"page": i+1, "characters": chars, "words": words})
                total_chars += chars
            doc.close()
            output_data = {"pages": result, "total_characters": total_chars}
            output_path = workdir / f"{input_path.stem}_wordcount.json"
            output_path.write_text(json.dumps(output_data, ensure_ascii=False, indent=2))
            return ToolResult(True, output_path, output_path.name, "application/json", metadata=output_data)
        except Exception as e:
            return ToolResult(False, error=str(e))


class PdfStampTool(ToolBase):
    tool_id = "pdf-stamp"
    name_zh = "PDF 蓋章"
    name_en = "PDF Stamp"
    description_zh = "在 PDF 頁面指定位置蓋上印章文字"
    category = "pdf"
    icon = "Stamp"
    color = "orange"
    tags = ["PDF", "蓋章", "簽章"]

    @property
    def params(self):
        return [
            ToolParam("text", "string", "印章文字", required=True, placeholder="核准 Approved"),
            ToolParam("position", "select", "位置", required=False, default="center",
                      options=[{"label": "置中", "value": "center"}, {"label": "左上", "value": "top-left"}, {"label": "右下", "value": "bottom-right"}]),
            ToolParam("color", "select", "顏色", required=False, default="red",
                      options=[{"label": "紅色", "value": "red"}, {"label": "藍色", "value": "blue"}, {"label": "綠色", "value": "green"}]),
        ]

    async def execute(self, input_path: Path, params: dict, workdir: Path) -> ToolResult:
        try:
            import fitz
            text = params.get("text", "APPROVED")
            color_map = {"red": (0.8,0.1,0.1), "blue": (0.1,0.1,0.8), "green": (0.1,0.7,0.1)}
            color = color_map.get(params.get("color", "red"), (0.8,0.1,0.1))
            output_path = workdir / f"stamped_{input_path.name}"
            doc = fitz.open(str(input_path))
            for page in doc:
                w, h = page.rect.width, page.rect.height
                pos_map = {"center": (w/2, h/2), "top-left": (80, 80), "bottom-right": (w-80, h-80)}
                point = pos_map.get(params.get("position", "center"), (w/2, h/2))
                page.insert_text(fitz.Point(*point), text, fontsize=36, color=color, rotate=0)
            doc.save(str(output_path))
            doc.close()
            return ToolResult(True, output_path, output_path.name, "application/pdf")
        except Exception as e:
            return ToolResult(False, error=str(e))


class PdfNupTool(ToolBase):
    tool_id = "pdf-nup"
    name_zh = "N-up 排版"
    name_en = "N-up Layout"
    description_zh = "將多頁 PDF 合印在同一頁（2-up, 4-up 等）"
    category = "pdf"
    icon = "LayoutGrid"
    color = "purple"
    tags = ["PDF", "排版", "列印"]

    @property
    def params(self):
        return [
            ToolParam("layout", "select", "排版模式", required=True, default="2up",
                      options=[{"label": "2-up（橫式）", "value": "2up"}, {"label": "4-up", "value": "4up"}]),
        ]

    async def execute(self, input_path: Path, params: dict, workdir: Path) -> ToolResult:
        try:
            import fitz
            layout = params.get("layout", "2up")
            n = 4 if layout == "4up" else 2
            doc = fitz.open(str(input_path))
            total = doc.page_count
            output_path = workdir / f"nup_{input_path.name}"
            new_doc = fitz.open()
            page_size = fitz.paper_size("a4")
            for i in range(0, total, n):
                new_page = new_doc.new_page(width=page_size[0], height=page_size[1])
                for j in range(n):
                    if i + j >= total:
                        break
                    if n == 2:
                        rect = fitz.Rect(0, j * page_size[1]/2, page_size[0], (j+1) * page_size[1]/2)
                    else:
                        row, col = j // 2, j % 2
                        rect = fitz.Rect(col * page_size[0]/2, row * page_size[1]/2,
                                         (col+1) * page_size[0]/2, (row+1) * page_size[1]/2)
                    new_page.show_pdf_page(rect, doc, i + j)
            new_doc.save(str(output_path))
            new_doc.close()
            doc.close()
            return ToolResult(True, output_path, output_path.name, "application/pdf")
        except Exception as e:
            return ToolResult(False, error=str(e))


class PdfDiffTool(ToolBase):
    tool_id = "pdf-diff"
    name_zh = "PDF 比較"
    name_en = "PDF Diff"
    description_zh = "比較兩個 PDF 的文字差異"
    category = "pdf"
    icon = "GitCompare"
    color = "amber"
    tags = ["PDF", "比較", "差異"]

    async def execute(self, input_path: Path, params: dict, workdir: Path) -> ToolResult:
        try:
            import fitz, json, difflib
            extra = params.get("extra_files", [])
            if not extra:
                return ToolResult(False, error="請上傳第二個 PDF 進行比較")
            doc1 = fitz.open(str(input_path))
            doc2 = fitz.open(str(extra[0]))
            text1 = "\n".join(page.get_text() for page in doc1)
            text2 = "\n".join(page.get_text() for page in doc2)
            differ = difflib.unified_diff(text1.splitlines(), text2.splitlines(), lineterm="", n=3)
            diff_text = "\n".join(list(differ))
            output_path = workdir / "diff.txt"
            output_path.write_text(diff_text, encoding="utf-8")
            doc1.close()
            doc2.close()
            return ToolResult(True, output_path, "diff.txt", "text/plain")
        except Exception as e:
            return ToolResult(False, error=str(e))


class PdfHiddenScanTool(ToolBase):
    tool_id = "pdf-hidden-scan"
    name_zh = "隱藏內容掃描"
    name_en = "Hidden Content Scan"
    description_zh = "掃描 PDF 中的隱藏文字、圖層、元資料等安全隱患"
    category = "pdf"
    icon = "ScanSearch"
    color = "red"
    tags = ["PDF", "安全", "掃描"]

    async def execute(self, input_path: Path, params: dict, workdir: Path) -> ToolResult:
        try:
            import fitz, json
            doc = fitz.open(str(input_path))
            report = {
                "metadata": doc.metadata,
                "page_count": doc.page_count,
                "is_encrypted": doc.is_encrypted,
                "has_links": any(page.get_links() for page in doc),
                "has_annotations": any(page.annots() for page in doc),
                "layers": doc.layer_ui_configs() if hasattr(doc, "layer_ui_configs") else [],
                "embedded_files": doc.embfile_count(),
            }
            doc.close()
            output_path = workdir / f"{input_path.stem}_scan_report.json"
            output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))
            return ToolResult(True, output_path, output_path.name, "application/json", metadata=report)
        except Exception as e:
            return ToolResult(False, error=str(e))


class PdfToImageTool(ToolBase):
    tool_id = "pdf-to-image"
    name_zh = "PDF 轉圖片"
    name_en = "PDF to Image"
    description_zh = "將 PDF 每頁轉換為 PNG/JPG 圖片"
    category = "convert"
    icon = "FileImage"
    color = "emerald"
    tags = ["PDF", "轉換", "圖片"]

    @property
    def params(self):
        return [
            ToolParam("format", "select", "輸出格式", required=False, default="png",
                      options=[{"label": "PNG（高品質）", "value": "png"}, {"label": "JPG（小體積）", "value": "jpg"}]),
            ToolParam("dpi", "integer", "解析度 DPI", required=False, default=150, min_val=72, max_val=600),
        ]

    async def execute(self, input_path: Path, params: dict, workdir: Path) -> ToolResult:
        try:
            import fitz, zipfile
            fmt = params.get("format", "png")
            dpi = int(params.get("dpi", 150))
            mat = fitz.Matrix(dpi/72, dpi/72)
            doc = fitz.open(str(input_path))
            output_zip = workdir / f"{input_path.stem}_images.zip"
            with zipfile.ZipFile(str(output_zip), "w") as zf:
                for i, page in enumerate(doc):
                    pix = page.get_pixmap(matrix=mat)
                    fname = f"page_{i+1:03d}.{fmt}"
                    img_path = workdir / fname
                    if fmt == "png":
                        pix.save(str(img_path))
                    else:
                        pix.pil_save(str(img_path), format="JPEG", quality=85)
                    zf.write(str(img_path), fname)
            page_count = len(doc)
            doc.close()
            return ToolResult(True, output_zip, output_zip.name, "application/zip", metadata={"page_count": page_count})
        except Exception as e:
            return ToolResult(False, error=str(e))


class ImageToPdfTool(ToolBase):
    tool_id = "image-to-pdf"
    name_zh = "圖片轉 PDF"
    name_en = "Image to PDF"
    description_zh = "將 PNG/JPG/TIFF 圖片轉換為 PDF"
    category = "convert"
    icon = "FilePlus"
    color = "emerald"
    tags = ["轉換", "圖片", "PDF"]

    async def execute(self, input_path: Path, params: dict, workdir: Path) -> ToolResult:
        try:
            import fitz
            extra = [Path(p) for p in params.get("extra_files", [])]
            all_images = [input_path] + extra
            output_path = workdir / f"{input_path.stem}.pdf"
            doc = fitz.open()
            for img_path in all_images:
                img_doc = fitz.open(str(img_path))
                pdfbytes = img_doc.convert_to_pdf()
                img_doc.close()
                tmp = fitz.open("pdf", pdfbytes)
                doc.insert_pdf(tmp)
            doc.save(str(output_path))
            doc.close()
            return ToolResult(True, output_path, output_path.name, "application/pdf")
        except Exception as e:
            return ToolResult(False, error=str(e))


class OfficeToPdfTool(ToolBase):
    tool_id = "office-to-pdf"
    name_zh = "Office 轉 PDF"
    name_en = "Office to PDF"
    description_zh = "將 Word/Excel/PowerPoint/ODF 轉為 PDF"
    category = "convert"
    icon = "FileOutput"
    color = "purple"
    tags = ["轉換", "Office", "PDF", "Word", "Excel"]

    async def execute(self, input_path: Path, params: dict, workdir: Path) -> ToolResult:
        try:
            import subprocess
            result = subprocess.run(
                ["libreoffice", "--headless", "--convert-to", "pdf", "--outdir", str(workdir), str(input_path)],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode != 0:
                return ToolResult(False, error=f"LibreOffice 錯誤: {result.stderr}")
            output_path = workdir / f"{input_path.stem}.pdf"
            if not output_path.exists():
                return ToolResult(False, error="轉換後找不到輸出檔案")
            return ToolResult(True, output_path, output_path.name, "application/pdf")
        except FileNotFoundError:
            return ToolResult(False, error="LibreOffice 未安裝，無法轉換 Office 文件")
        except Exception as e:
            return ToolResult(False, error=str(e))


class DocDeidentTool(ToolBase):
    tool_id = "doc-deident"
    name_zh = "文件去識別化"
    name_en = "Document De-identification"
    description_zh = "遮蔽 PDF/文字中的個資（姓名、身分證、電話、Email）"
    category = "security"
    icon = "UserX"
    color = "rose"
    tags = ["安全", "隱私", "去識別化", "個資"]

    @property
    def params(self):
        return [
            ToolParam("mask_id", "boolean", "遮蔽身分證號", required=False, default=True),
            ToolParam("mask_phone", "boolean", "遮蔽電話號碼", required=False, default=True),
            ToolParam("mask_email", "boolean", "遮蔽 Email", required=False, default=True),
            ToolParam("mask_char", "string", "遮蔽字元", required=False, default="*"),
        ]

    async def execute(self, input_path: Path, params: dict, workdir: Path) -> ToolResult:
        try:
            import re
            mask = params.get("mask_char", "*")
            text = input_path.read_text(encoding="utf-8", errors="ignore")
            if params.get("mask_id", True):
                text = re.sub(r'[A-Z][12]\d{8}', lambda m: mask * len(m.group()), text)
            if params.get("mask_phone", True):
                text = re.sub(r'0\d{1,2}[-\s]?\d{3,4}[-\s]?\d{4}', lambda m: mask * len(m.group()), text)
            if params.get("mask_email", True):
                text = re.sub(r'[\w.+-]+@[\w-]+\.[a-z]{2,}', lambda m: mask * len(m.group()), text)
            output_path = workdir / f"deident_{input_path.name}"
            output_path.write_text(text, encoding="utf-8")
            return ToolResult(True, output_path, output_path.name, "text/plain")
        except Exception as e:
            return ToolResult(False, error=str(e))


class AesZipTool(ToolBase):
    tool_id = "aes-zip"
    name_zh = "AES 加密壓縮"
    name_en = "AES Encrypted ZIP"
    description_zh = "使用 AES-256 加密建立有密碼保護的 ZIP"
    category = "security"
    icon = "Archive"
    color = "orange"
    tags = ["安全", "加密", "ZIP"]

    @property
    def params(self):
        return [ToolParam("password", "password", "ZIP 密碼", required=True)]

    async def execute(self, input_path: Path, params: dict, workdir: Path) -> ToolResult:
        try:
            import pyzipper
            password = params.get("password", "")
            output_path = workdir / f"{input_path.stem}_encrypted.zip"
            with pyzipper.AESZipFile(str(output_path), 'w', compression=pyzipper.ZIP_LZMA, encryption=pyzipper.WZ_AES) as zf:
                zf.setpassword(password.encode())
                zf.write(str(input_path), input_path.name)
            return ToolResult(True, output_path, output_path.name, "application/zip")
        except ImportError:
            import zipfile
            output_path = workdir / f"{input_path.stem}_encrypted.zip"
            with zipfile.ZipFile(str(output_path), 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.write(str(input_path), input_path.name)
            return ToolResult(True, output_path, output_path.name, "application/zip", message="提示：pyzipper 未安裝，已建立一般 ZIP（無加密）")
        except Exception as e:
            return ToolResult(False, error=str(e))


class PdfPageNumberTool(ToolBase):
    tool_id = "pdf-pageno"
    name_zh = "加入頁碼"
    name_en = "Add Page Numbers"
    description_zh = "在 PDF 每頁加上頁碼"
    category = "pdf"
    icon = "ListOrdered"
    color = "sky"
    tags = ["PDF", "頁碼"]

    @property
    def params(self):
        return [
            ToolParam("position", "select", "頁碼位置", required=False, default="bottom-center",
                      options=[{"label": "下方置中", "value": "bottom-center"}, {"label": "下方右側", "value": "bottom-right"}, {"label": "上方置中", "value": "top-center"}]),
            ToolParam("start", "integer", "起始頁碼", required=False, default=1, min_val=1),
            ToolParam("format", "string", "格式（{n} 為頁碼）", required=False, default="- {n} -", placeholder="第 {n} 頁"),
        ]

    async def execute(self, input_path: Path, params: dict, workdir: Path) -> ToolResult:
        try:
            import fitz
            start = int(params.get("start", 1))
            fmt = params.get("format", "- {n} -")
            pos = params.get("position", "bottom-center")
            output_path = workdir / f"numbered_{input_path.name}"
            doc = fitz.open(str(input_path))
            for i, page in enumerate(doc):
                text = fmt.replace("{n}", str(i + start))
                w, h = page.rect.width, page.rect.height
                if "bottom" in pos:
                    y = h - 20
                else:
                    y = 15
                if "center" in pos:
                    x = w / 2
                elif "right" in pos:
                    x = w - 30
                else:
                    x = 30
                page.insert_text(fitz.Point(x, y), text, fontsize=10, color=(0.3, 0.3, 0.3))
            doc.save(str(output_path))
            doc.close()
            return ToolResult(True, output_path, output_path.name, "application/pdf")
        except Exception as e:
            return ToolResult(False, error=str(e))


class PdfAnnotationsTool(ToolBase):
    tool_id = "pdf-annotations"
    name_zh = "擷取註解"
    name_en = "Extract Annotations"
    description_zh = "匯出 PDF 中的所有批注與標記"
    category = "pdf"
    icon = "MessageSquare"
    color = "lime"
    tags = ["PDF", "註解", "批注"]

    async def execute(self, input_path: Path, params: dict, workdir: Path) -> ToolResult:
        try:
            import fitz, json
            doc = fitz.open(str(input_path))
            annotations = []
            for i, page in enumerate(doc):
                for annot in page.annots():
                    annotations.append({
                        "page": i + 1,
                        "type": annot.type[1],
                        "content": annot.info.get("content", ""),
                        "author": annot.info.get("title", ""),
                        "rect": list(annot.rect),
                    })
            doc.close()
            output_path = workdir / f"{input_path.stem}_annotations.json"
            output_path.write_text(json.dumps(annotations, ensure_ascii=False, indent=2))
            return ToolResult(True, output_path, output_path.name, "application/json", metadata={"count": len(annotations)})
        except Exception as e:
            return ToolResult(False, error=str(e))


class TranslateDocTool(ToolBase):
    tool_id = "translate-doc"
    name_zh = "文件翻譯"
    name_en = "Document Translation"
    description_zh = "透過本地 LLM 將 PDF / 文字文件翻譯為指定語言"
    category = "ai"
    icon = "Languages"
    color = "violet"
    tags = ["AI", "翻譯", "LLM"]

    LANG_LABEL = {"zh-tw": "繁體中文", "zh-cn": "簡體中文", "en": "English", "ja": "日本語", "ko": "한국어"}

    @property
    def params(self):
        return [
            ToolParam("target_lang", "select", "目標語言", required=True, default="zh-tw",
                      options=[
                          {"label": "繁體中文", "value": "zh-tw"},
                          {"label": "簡體中文", "value": "zh-cn"},
                          {"label": "English",  "value": "en"},
                          {"label": "日本語",   "value": "ja"},
                          {"label": "한국어",   "value": "ko"},
                      ]),
        ]

    async def execute(self, input_path: Path, params: dict, workdir: Path) -> ToolResult:
        from app.config import settings
        import httpx

        if not settings.llm_base_url:
            return ToolResult(False, error="尚未設定 LLM 服務（請在 .env 設定 LLM_BASE_URL）")

        target_lang = params.get("target_lang", "zh-tw")
        lang_label  = self.LANG_LABEL.get(target_lang, target_lang)

        # ── 1. 擷取原文 ──────────────────────────────────────────
        suffix = input_path.suffix.lower()
        if suffix == ".pdf":
            try:
                import fitz
                doc = fitz.open(str(input_path))
                raw_text = "\n\n".join(page.get_text() for page in doc)
                doc.close()
            except Exception as e:
                return ToolResult(False, error=f"PDF 讀取失敗：{e}")
        elif suffix in (".txt", ".md", ".csv"):
            raw_text = input_path.read_text(encoding="utf-8", errors="replace")
        else:
            return ToolResult(False, error=f"不支援的格式：{suffix}（支援 PDF / TXT / MD / CSV）")

        raw_text = raw_text.strip()
        if not raw_text:
            return ToolResult(False, error="文件內容為空，無法翻譯")

        # ── 2. 分段（每段 ≤ 6000 字）────────────────────────────
        CHUNK = 6000
        chunks: list[str] = []
        buf = ""
        for para in raw_text.split("\n\n"):
            if len(buf) + len(para) > CHUNK and buf:
                chunks.append(buf.strip())
                buf = para
            else:
                buf = (buf + "\n\n" + para) if buf else para
        if buf.strip():
            chunks.append(buf.strip())

        system_prompt = (
            f"你是專業翻譯。請將以下內容忠實翻譯為{lang_label}，"
            "保留原有段落結構與格式，不要增加解釋或評論，只輸出翻譯結果。"
        )

        # ── 3. 判斷 API 類型：Ollama 原生 vs OpenAI-compatible ───
        base = settings.llm_base_url.rstrip("/")
        # Ollama 原生 API（直連 11434，支援 think:false）
        is_ollama = "11434" in base or base.endswith("/api")
        ollama_base = base.replace("/v1", "").replace("/api", "")

        translated_parts: list[str] = []
        async with httpx.AsyncClient(timeout=settings.llm_timeout) as client:
            for i, chunk in enumerate(chunks):
                try:
                    if is_ollama:
                        resp = await client.post(
                            f"{ollama_base}/api/chat",
                            json={
                                "model": settings.llm_model,
                                "think": False,
                                "stream": False,
                                "messages": [
                                    {"role": "system", "content": system_prompt},
                                    {"role": "user",   "content": chunk},
                                ],
                                "options": {"temperature": 0.2},
                            },
                        )
                        resp.raise_for_status()
                        translated_parts.append(resp.json()["message"]["content"])
                    else:
                        resp = await client.post(
                            f"{base}/chat/completions",
                            headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                            json={
                                "model": settings.llm_model,
                                "messages": [
                                    {"role": "system", "content": system_prompt},
                                    {"role": "user",   "content": chunk},
                                ],
                                "temperature": 0.2,
                            },
                        )
                        resp.raise_for_status()
                        translated_parts.append(resp.json()["choices"][0]["message"]["content"])
                except httpx.HTTPStatusError as e:
                    return ToolResult(False, error=f"LLM 回應錯誤 {e.response.status_code}：{e.response.text[:200]}")
                except Exception as e:
                    return ToolResult(False, error=f"LLM 請求失敗（段落 {i+1}/{len(chunks)}）：{e}")

        # ── 3. 組合輸出 ───────────────────────────────────────────
        result_text = "\n\n".join(translated_parts)
        stem = input_path.stem
        out_name = f"{stem}_translated_{target_lang}.txt"
        out_path = workdir / out_name
        out_path.write_text(result_text, encoding="utf-8")

        return ToolResult(True, out_path, out_name, "text/plain",
                          metadata={"目標語言": lang_label,
                                    "原文字數": str(len(raw_text)),
                                    "譯文字數": str(len(result_text)),
                                    "段落數":   str(len(chunks))})


# ─── 輔助函數 ────────────────────────────────────────────────────────────────

def _parse_page_range(s: str, total: int) -> list[int]:
    """將 '1-3,5,7-9' 解析為 0-based 頁碼列表"""
    pages = set()
    for part in s.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            for i in range(int(a), int(b) + 1):
                if 1 <= i <= total:
                    pages.add(i - 1)
        elif part.isdigit():
            i = int(part)
            if 1 <= i <= total:
                pages.add(i - 1)
    return sorted(pages)


# ─── 工具登錄 ────────────────────────────────────────────────────────────────

TOOL_REGISTRY: dict[str, ToolBase] = {}


def _register(*tools: ToolBase) -> None:
    for t in tools:
        TOOL_REGISTRY[t.tool_id] = t


_register(
    # PDF
    PdfMergeTool(), PdfSplitTool(), PdfCompressTool(), PdfEncryptTool(), PdfDecryptTool(),
    PdfWatermarkTool(), PdfRotateTool(), PdfStampTool(), PdfNupTool(), PdfDiffTool(),
    PdfExtractTextTool(), PdfExtractImagesTool(), PdfMetadataTool(), PdfPagesTool(),
    PdfWordCountTool(), PdfHiddenScanTool(), PdfAnnotationsTool(), PdfPageNumberTool(),
    # Convert
    PdfToImageTool(), ImageToPdfTool(), OfficeToPdfTool(),
    # Security
    DocDeidentTool(), AesZipTool(),
    # AI
    TranslateDocTool(),
)


def get_registry() -> dict[str, ToolBase]:
    return TOOL_REGISTRY
